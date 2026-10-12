"""Q25 one-call paid pilot guards are tested without any HTTP or spending."""
import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest

from src.q25_openrouter_pilot import (
    API, PilotStop, build_wire_request, decimal_price, enforce_preflight,
    paid_pilot, parse_completion, pricing_snapshot, upper_cost_usd,
    provider_safe_json_schema, classify_http_error_body, transport_json,
)
from src.q25_semantic_review import review_packet_digest

ROOT = Path("evidence/q25")
BASE = ROOT / "Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24"
RAW = ROOT / "Q25-STORY-STATE-CANDIDATES-20261012/raw-extractor-replay.json"
POLICY = ROOT / "Q25-ADMISSION-DRAFT-20261012/policy.json"
MODEL = "anthropic/claude-sonnet-5.5"


def load(p):
    return json.loads(p.read_text(encoding="utf8"))


def inputs():
    return {
        "seed": load(BASE / "seed-input.json"),
        "prose": load(BASE / "writer-2-text.json")["text"],
        "policy": load(POLICY), "model": MODEL, "max_tokens": 3500,
        "max_cost_usd": "0.20", "api_key": "stub-key",
    }


def catalog(price="0.000002", completion="0.00001", supported=None, request="0"):
    return {"data": [dict(
        id=MODEL,
        supported_parameters=(supported if supported is not None
            else ["response_format", "structured_outputs"]),
        context_length=1000000,
        pricing={"prompt": price, "completion": completion,
                 "request": request}
    )]}


class Stub:
    def __init__(self, *, cost=0.035, response=None,
                 key_remaining=1.0, catalog_response=None):
        self.calls = []
        self.cost = cost
        self.response = response
        self.key_remaining = key_remaining
        self.catalog_response = catalog_response

    def __call__(self, *, url, method="GET", api_key=None,
                 payload=None, timeout=None):
        self.calls.append((url, method, api_key is not None))
        if url.endswith("/models"):
            return self.catalog_response or catalog()
        if url.endswith("/key"):
            return {"data": {"limit": 1, "limit_remaining": self.key_remaining,
                             "is_free_tier": False}}
        if url.endswith("/chat/completions"):
            raw = self.response if self.response is not None else load(RAW)
            return {"id": "stub",
                    "choices": [{"finish_reason": "stop",
                                 "message": {"content": json.dumps(raw)}}],
                    "usage": {"prompt_tokens": 9000,
                              "completion_tokens": 2200,
                              "total_tokens": 11200, "cost": self.cost},
                    "model": MODEL}
        raise AssertionError(url)


def test_wire_uses_explicit_model_strict_schema_no_fallback_and_bounded_tokens():
    d = inputs()
    wire = build_wire_request(seed=d["seed"], prose=d["prose"],
                              model=d["model"], max_tokens=d["max_tokens"])
    assert wire["model"] == MODEL
    assert wire["provider"] == {"require_parameters": True, "allow_fallbacks": False}
    assert wire["response_format"]["type"] == "json_schema"
    assert wire["response_format"]["json_schema"]["strict"] is True
    assert wire["response_format"]["json_schema"]["schema"]["additionalProperties"] is False
    assert wire["max_tokens"] == 3500
    assert wire["stream"] is False
    assert wire["messages"][0]["role"] == "system"
    assert wire["messages"][1]["role"] == "user"
    assert load(BASE / "seed-input.json") == d["seed"]



def test_wire_schema_strips_unsupported_string_bounds_but_local_guard_remains_strict():
    from src.q25_extractor_adapter import RawExtractorOutput
    base = RawExtractorOutput.model_json_schema()
    original = copy.deepcopy(base)
    compatible = provider_safe_json_schema(base)
    assert base == original
    assert compatible["additionalProperties"] is False
    assert compatible["type"] == "object"
    assert compatible != base

    def traverse(obj):
        if isinstance(obj, list):
            for item in obj:
                yield from traverse(item)
        elif isinstance(obj, dict):
            yield obj
            for item in obj.values():
                yield from traverse(item)

    all_nodes = list(traverse(compatible))
    assert not any("minLength" in obj or "maxLength" in obj for obj in all_nodes)
    assert not any("minimum" in obj or "maximum" in obj for obj in all_nodes)
    assert any("enforced by application" in obj.get("description", "")
               for obj in all_nodes)
    assert all(obj.get("additionalProperties") is False
               for obj in all_nodes if obj.get("type") == "object")
    assert set(compatible["properties"]) == set(base["properties"])
    assert compatible["$defs"]["RawProperty"]["required"] == (
        base["$defs"]["RawProperty"]["required"])
    wire = build_wire_request(seed=inputs()["seed"], prose=inputs()["prose"],
                              model=MODEL, max_tokens=3500)
    assert wire["response_format"]["json_schema"]["schema"] == compatible
    assert wire["response_format"]["json_schema"]["strict"] is True
    assert wire["provider"]["allow_fallbacks"] is False
    # Removing only *wire* constraints may never relax the local Pydantic contract.
    damaged = load(RAW)
    damaged["objects"][0]["description"] = "X" * 501
    with pytest.raises(PilotStop, match="raw JSON contract"):
        parse_completion({"choices": [{
            "finish_reason": "stop",
            "message": {"content": json.dumps(damaged, ensure_ascii=False)}
        }]})


@pytest.mark.parametrize("damage", ["open_object", "too_many_optionals", "unsupported_minitems",
                                     "unsupported_schema_keyword"])
def test_provider_safe_schema_fails_closed_on_unqualified_schema(damage):
    from src.q25_extractor_adapter import RawExtractorOutput
    original = RawExtractorOutput.model_json_schema()
    modified = copy.deepcopy(original)
    if damage == "open_object":
        modified["$defs"]["RawObject"]["additionalProperties"] = True
    elif damage == "too_many_optionals":
        modified["properties"].update({
            "extra_" + str(i): {"type": "string"} for i in range(28)
        })
    elif damage == "unsupported_minitems":
        modified["properties"]["objects"]["minItems"] = 2
    else:
        modified["$defs"]["RawObject"]["patternProperties"] = {".*": {"type": "string"}}
    with pytest.raises(PilotStop):
        provider_safe_json_schema(modified)
    assert "minLength" in json.dumps(original)


def test_live_catalog_pricing_is_conservatively_bounded():
    snap = pricing_snapshot(catalog(), MODEL)
    bound = upper_cost_usd(build_wire_request(
        seed=inputs()["seed"], prose=inputs()["prose"],
        model=MODEL, max_tokens=3500), snap)
    assert Decimal("0") < bound["upper_cost_usd"] <= Decimal("0.20")
    assert bound["input_tokens_upper_bound"] > 10000
    assert bound["output_tokens_upper_bound"] == 3500


@pytest.mark.parametrize("bad", [
    {"price": "-0.1"}, {"price": "NaN"},
    {"price": "0"}, {"request": "0.001"},
    {"supported": ["response_format"]},
])
def test_price_or_capability_abnormality_blocks(bad):
    with pytest.raises(PilotStop):
        pricing_snapshot(catalog(**bad), MODEL)


@pytest.mark.parametrize("value", [float("nan"), "-1", "Infinity", True, None])
def test_bad_spending_caps_rejected(value):
    with pytest.raises(PilotStop):
        if value is None:
            decimal_price(value)
        else:
            from src.q25_openrouter_pilot import GLOBAL_CAP_USD
            cap = decimal_price(value)
            if not (0 < cap <= GLOBAL_CAP_USD):
                raise PilotStop("bad")


def test_key_limit_and_free_tier_are_strict():
    with pytest.raises(PilotStop, match="Insufficient"):
        enforce_preflight({"data": {"limit_remaining": 0.005}},
                         Decimal("0.08"))
    with pytest.raises(PilotStop, match="free-tier"):
        enforce_preflight({"data": {"is_free_tier": True}},
                         Decimal("0.08"))


def test_genuinely_one_paid_call_then_hash_bound_readonly_audit(tmp_path):
    d = inputs()
    before = copy.deepcopy(d)
    fake = Stub()
    dir_ = tmp_path / "pilot"
    ledger = paid_pilot(**d, archive_dir=dir_, client=fake)
    assert ledger["outcome"] == "SOURCE_BOUND_CANDIDATES_ONLY"
    assert ledger["provider_calls"] == 1
    assert ledger["attempted_calls"] == 1
    assert ledger["usage"]["actual_cost_usd"] == 0.035
    assert ledger["state_commit_authorized"] is False
    assert ledger["coverage_counts"] == {
        "CANDIDATE": 12, "PARTIAL_CANDIDATES": 1,
        "STRUCTURAL_ONLY": 23, "UNASSESSED": 32, "UNKNOWN": 2}
    assert fake.calls == [
        (API + "/models", "GET", False),
        (API + "/key", "GET", True),
        (API + "/chat/completions", "POST", True)]
    assert d == before
    assert sorted(p.name for p in dir_.iterdir()) == [
        "ledger.json", "offline-gate-result.json",
        "provider-response.json", "raw-extraction.json", "raw-terminal-hypothesis.json",
        "request.json", "semantic-review-packet.json",
    ]
    packet = load(dir_ / "semantic-review-packet.json")
    assert packet["candidate_count"] == 15
    assert packet["unresolved_terminal_fields"] == 70
    assert ledger["review_packet_sha256"] == review_packet_digest(packet)
    assert ledger["review_candidate_count"] == 15
    assert ledger["review_status"] == "AWAITING_EXTERNAL_REVIEW"
    candidate = load(dir_ / "raw-terminal-hypothesis.json")
    assert candidate["schema"] == "q25.raw-terminal-hypothesis.v1"
    assert candidate["state_commit_authorized"] is False
    assert candidate["independent_semantic_review_completed"] is False
    assert ledger["terminal_state_complete"] is False
    assert ledger["independent_semantic_review_complete"] is False
    assert packet["semantic_support_certified"] is False
    assert packet["state_commit_authorized"] is False
    for p in dir_.iterdir():
        assert "stub-key" not in p.read_text(encoding="utf8")
    assert load(BASE / "seed-input.json") == d["seed"]
    # Reusing the same archive must never spend a second time.
    with pytest.raises(FileExistsError):
        paid_pilot(**d, archive_dir=dir_, client=fake)
    assert len([c for c in fake.calls if c[1] == "POST"]) == 1


@pytest.mark.parametrize("rejection", [
    "no_budget", "catalog_price", "missing_api_key",
    "wrong_model", "oversized_output", "cap_exceeded",
])
def test_preflight_blocks_without_post_or_evidence(rejection, tmp_path):
    d = inputs()
    fake = Stub()
    if rejection == "no_budget":
        fake.key_remaining = 0
    elif rejection == "catalog_price":
        fake.catalog_response = catalog(price="0.003")
    elif rejection == "missing_api_key":
        d["api_key"] = ""
    elif rejection == "wrong_model":
        d["model"] = "unknown/model"
    elif rejection == "oversized_output":
        d["max_tokens"] = 50000
    elif rejection == "cap_exceeded":
        d["max_cost_usd"] = "0.21"
    with pytest.raises(PilotStop):
        paid_pilot(**d, archive_dir=tmp_path / "pilot", client=fake)
    assert not (tmp_path / "pilot").exists()
    assert all(c[1] != "POST" for c in fake.calls)


@pytest.mark.parametrize("response", [
    {"choices": []},
    {"choices": [{"finish_reason": "length",
                  "message": {"content": "{}"}}]},
    {"choices": [{"finish_reason": "stop",
                  "message": {"content": "not json"}}]},
    {"choices": [{"finish_reason": "stop",
                  "message": {"content": '{"state_commit_authorized":true}'}}]},
])
def test_invalid_completion_always_fails_closed(response):
    with pytest.raises(PilotStop):
        parse_completion(response)


@pytest.mark.parametrize("cost", [None, 0.25])
def test_missing_usage_or_over_budget_stops_without_retry(tmp_path, cost):
    fake = Stub(cost=cost)
    ledger = paid_pilot(**inputs(), archive_dir=tmp_path / "pilot",
                        client=fake)
    assert ledger["outcome"] == "STOP"
    assert ledger["provider_calls"] == 1
    assert ledger["attempted_calls"] == 1
    assert len([c for c in fake.calls if c[1] == "POST"]) == 1
    assert (tmp_path / "pilot" / "provider-response.json").exists()


def test_invalid_source_bound_response_never_generates_review_packet(tmp_path):
    bad = load(RAW)
    bad["source_sha256"] = "0" * 64
    stub = Stub(response=bad)
    archive = tmp_path / "pilot"
    result = paid_pilot(**inputs(), archive_dir=archive, client=stub)
    assert result["outcome"] == "REJECTED_BY_OFFLINE_GATE"
    assert result["state_commit_authorized"] is False
    assert "review_packet_sha256" not in result
    assert not (archive / "semantic-review-packet.json").exists()
    assert (archive / "raw-extraction.json").exists()
    assert len([c for c in stub.calls if c[1] == "POST"]) == 1


def test_http_error_never_exposes_auth_or_retries(monkeypatch):
    import urllib.error
    import urllib.request
    class FakeOpener:
        def open(self, req, timeout):
            raise urllib.error.HTTPError(
                req.full_url, 402, "credits", {}, None)
    monkeypatch.setattr(urllib.request, "build_opener",
                        lambda *a: FakeOpener())
    with pytest.raises(PilotStop, match="HTTP 402; no retry"):
        transport_json(url=API + "/chat/completions", method="POST",
                       api_key="sensitive-secret", payload={"hello": "test"})



def test_http_400_has_sanitized_schema_diagnostic_and_never_leaks_provider_body(monkeypatch):
    import io
    import urllib.error
    import urllib.request
    sensitive = "MY_SECRET_PRIVATE_PROMPT"
    response = {
        "error": {
            "message": "Schema rejected: minLength not supported. " + sensitive
        }
    }
    class FakeOpener:
        def open(self, req, timeout):
            raise urllib.error.HTTPError(
                req.full_url, 400, "invalid", {},
                io.BytesIO(json.dumps(response).encode("utf8")))
    monkeypatch.setattr(
        urllib.request, "build_opener", lambda *args: FakeOpener())
    with pytest.raises(PilotStop, match="category=SCHEMA_UNSUPPORTED_STRING_CONSTRAINT") as exc:
        transport_json(url=API + "/chat/completions", method="POST",
                       api_key="secret-key-never-log", payload={"hi": "there"})
    assert "MY_SECRET" not in str(exc.value)
    assert "secret-key" not in str(exc.value)
    assert "no retry attempted" in str(exc.value)


@pytest.mark.parametrize("message,category", [
    ("JSON schema compilation failed: too complex", "SCHEMA_GRAMMAR_COMPILATION"),
    ("response_format json_schema invalid", "SCHEMA_OR_RESPONSE_FORMAT_REJECTED"),
    ("Model does not support response_format", "SCHEMA_OR_RESPONSE_FORMAT_REJECTED"),
    ("No provider route available", "PROVIDER_ROUTING_REJECTED"),
    ("Context length exceeded", "MODEL_CONTEXT_LIMIT"),
    ("unknown problem including private entity identifiers", "UNCLASSIFIED"),
])
def test_only_safe_provider_error_categories_survive(message, category):
    payload = {"error": {"message": message + " EXTRA_PRIVATE_MARKER"}}
    result = classify_http_error_body(json.dumps(payload).encode())
    assert result == category
    assert "PRIVATE_MARKER" not in result



def test_github_paid_job_is_never_activated_by_ordinary_pr_or_rerun():
    wf = Path(".github/workflows/q25-offline-diagnostic.yml").read_text(encoding="utf8")
    assert "  workflow_dispatch:" in wf
    assert "  pull_request:" in wf
    assert "  paid-extractor-pilot:\n" in wf
    offline, paid = wf.split("  paid-extractor-pilot:\n", 1)
    assert "secrets.OPENROUTER_API_KEY" not in offline
    assert ("github.event_name == 'workflow_dispatch' && "
            "inputs.execute_paid == true && github.run_attempt == 1") in paid
    assert "secrets.OPENROUTER_API_KEY" in paid
    assert paid.count("--execute-paid-once") == 1
    assert "--max-cost-usd 0.20" in paid
    assert "--max-tokens 3500" in paid
    assert "run_attempt == 1" in paid
    assert "actions/upload-artifact@v4" in paid
    assert "retention-days: 7" in paid
