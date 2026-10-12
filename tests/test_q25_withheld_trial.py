"""Q25 request/reference separation and no-cost model pilot preflight."""
import copy
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from src.q25_withheld_trial import preflight, evaluate, unpack_request
from src.q25_openrouter_pilot import build_wire_request, upper_cost_usd, pricing_snapshot
from src.q25_raw_reconciliation import project_raw

ROOT = Path("evidence/q25/Q25-WITHHELD-TRIAL-20261012")
REQUEST = ROOT / "request.json"
REFERENCE = ROOT / "provisional-reference.json"
MODEL = "anthropic/claude-sonnet-5.5"


def read(p):
    return json.loads(p.read_text(encoding="utf8"))


def case():
    return read(REQUEST)


def labels():
    return read(REFERENCE)


def test_label_free_provider_wire_and_digest_are_stable():
    request, reference = case(), labels()
    before = copy.deepcopy((request, reference))
    p = preflight(request_package=request, model=MODEL)
    unpacked = unpack_request(request)
    wire = build_wire_request(
        seed=unpacked["seed"], prose=unpacked["prose"], model=MODEL,
        max_tokens=3500,
    )
    assert p["seed_sha256"] == reference["seed_sha256"]
    assert p["source_sha256"] == reference["source_sha256"]
    assert p["wire_sha256"] and len(p["wire_sha256"]) == 64
    assert p["request_id"] == reference["request_id"] == "KITE-01"
    assert p["reference_labels_loaded"] is False
    assert p["reference_labels_sent_to_model"] is False
    assert p["provider_calls"] == 0
    assert p["max_calls"] == 1
    assert p["max_cost_usd"] == "0.20"
    assert p["provider_dispatch_performed"] is False
    assert p["state_commit_authorized"] is False
    assert "raw_reference" not in json.dumps(wire, ensure_ascii=False)
    assert "AUTHOR_CURATED_NOT_INDEPENDENTLY_REVIEWED" not in json.dumps(
        wire, ensure_ascii=False)
    assert "gold_paper_star" not in json.dumps(wire, ensure_ascii=False)
    assert wire["messages"][1]["role"] == "user"
    assert wire["provider"]["allow_fallbacks"] is False
    assert wire["max_tokens"] == 3500
    assert (request, reference) == before
    assert preflight(request_package=request, model=MODEL) == p


def test_curated_reference_is_only_an_unverified_answer_key():
    request, reference = case(), labels()
    raw = reference["raw_reference"]
    baseline = evaluate(request_package=request, reference_package=reference,
                        raw_response=raw)
    score = baseline["overall"]
    assert baseline["reference_claim_count"] == 16
    assert score["true_positive"] == 16
    assert score["false_positive"] == 0
    assert score["false_negative"] == 0
    assert score["f1"] == 1.0
    assert baseline["evaluation_scope"] == (
        "ANSWER_WITHHELD_FROM_WIRE_REFERENCE_NOT_INDEPENDENTLY_CERTIFIED")
    assert baseline["reference_labels_sent_to_model"] is False
    assert baseline["reference_labels_independently_adjudicated"] is False
    assert baseline["independent_human_adjudication_complete"] is False
    assert baseline["real_model_success_measured"] is False
    assert baseline["state_commit_authorized"] is False
    assert baseline["provider_calls"] == 0
    projected = project_raw(seed=request["seed"], prose=request["prose_record"]["text"],
                            raw_output=raw, policy=request["policy"])
    assert projected["structural_consistency"]["reciprocal_container_pairs"] == 0
    assert projected["candidate_state"]["objects"]["wooden_box"]["contains"] == []
    assert projected["candidate_state"]["objects"]["blue_string"]["container"]["status"] == "NONE"
    assert projected["candidate_state"]["objects"]["blue_string"]["properties"]["found"][
        "terminal_proposal"] is True
    assert projected["candidate_state"]["objects"]["red_kite"]["properties"]["ready"][
        "terminal_proposal"] is True
    star = next(x for key, x in projected["candidate_state"]["objects"].items()
                if key.startswith("new_"))
    assert star["owner"]["status"] == "UNKNOWN"
    assert star["location"]["status"] == "UNKNOWN"
    assert projected["approved_obligation_closures"] == []
    assert projected["state_commit_authorized"] is False


def test_missing_predictions_have_zero_recall_not_production_success():
    request, reference = case(), labels()
    empty = copy.deepcopy(reference["raw_reference"])
    for key in ("objects", "terminal_relations", "character_claims",
                "goal_claims", "obligation_claims", "thread_claims",
                "property_claims"):
        empty[key] = []
    report = evaluate(request_package=request, reference_package=reference,
                      raw_response=empty)
    assert report["reference_claim_count"] == 16
    assert report["candidate_claim_count"] == 0
    assert report["overall"]["false_negative"] == 16
    assert report["overall"]["recall"] == 0.0
    assert report["real_model_success_measured"] is False


@pytest.mark.parametrize("mutation", [
    "wrong_request", "seed_tampered", "prose_tampered", "labels_injected",
    "unknown_model", "output_limit", "wrong_reference_id",
    "wrong_reference_hash", "forged_independent_review",
    "fabricated_quote", "invented_owner",
])
def test_trust_and_reference_boundaries_fail_closed(mutation):
    request, reference = case(), labels()
    candidate = copy.deepcopy(reference["raw_reference"])
    if mutation == "wrong_request":
        request["request_id"] = "unknown!id"
    elif mutation == "seed_tampered":
        request["seed"]["objects"]["red_kite"]["state"]["ready"] = True
    elif mutation == "prose_tampered":
        request["prose_record"]["text"] += " MADE UP."
    elif mutation == "labels_injected":
        request["raw_reference"] = reference["raw_reference"]
    elif mutation == "wrong_reference_id":
        reference["request_id"] = "WRONG-CASE"
    elif mutation == "wrong_reference_hash":
        reference["source_sha256"] = "0" * 64
    elif mutation == "forged_independent_review":
        reference["review_status"] = "INDEPENDENTLY_CERTIFIED"
    elif mutation == "fabricated_quote":
        candidate["property_claims"][0]["evidence"][0]["quote"] = "A magic voice told them the outcome."
    elif mutation == "invented_owner":
        candidate["terminal_relations"].append(dict(
            subject="new:gold_paper_star", kind="OWNED_BY",
            target="character:SomeoneElse",
            evidence={"quote": "altın renkli kâğıt yıldızı"},
        ))
    if mutation in ("wrong_request", "labels_injected", "unknown_model", "output_limit"):
        with pytest.raises(ValueError):
            preflight(
                request_package=request,
                model="unqualified/model" if mutation == "unknown_model" else MODEL,
                max_tokens=100000 if mutation == "output_limit" else 3500,
            )
    else:
        with pytest.raises(ValueError):
            evaluate(request_package=request, reference_package=reference,
                     raw_response=candidate)


def test_same_one_shot_cap_preflight_without_inventing_live_prices():
    request = unpack_request(case())
    wire = build_wire_request(seed=request["seed"], prose=request["prose"],
                              model=MODEL, max_tokens=3500)
    mock_catalog = {"data": [{
        "id": MODEL, "supported_parameters": ["response_format", "structured_outputs"],
        "context_length": 500000,
        "pricing": {"request": "0", "prompt": "0.000002", "completion": "0.00001"},
    }]}
    bound = upper_cost_usd(wire, pricing_snapshot(mock_catalog, MODEL))
    assert Decimal("0") < bound["upper_cost_usd"] <= Decimal("0.20")
    assert bound["input_tokens_upper_bound"] > 5000


def test_workflow_paid_job_remains_manual_one_call_and_cannot_load_labels():
    wf = Path(".github/workflows/q25-offline-diagnostic.yml").read_text("utf8")
    paid = wf.split("  paid-extractor-pilot:\n", 1)[1]
    assert "workflow_dispatch' && inputs.execute_paid == true && github.run_attempt == 1" in paid
    assert "case \"$Q25_TRIAL_CASE\" in" in paid
    assert "kite-01)" in paid
    assert "--request-package evidence/q25/Q25-WITHHELD-TRIAL-20261012/request.json" in paid
    assert "provisional-reference.json" not in paid
    assert "OPENROUTER_API_KEY" in paid
    assert paid.count("--execute-paid-once") == 1
    assert "--max-cost-usd 0.20" in paid
    assert "--max-tokens 3500" in paid


def test_preflight_cli_and_legacy_pilot_dryrun_never_dispatch():
    cmd = [sys.executable, "-X", "utf8", "-m", "src.q25_withheld_trial",
           "--request-package", str(REQUEST), "--model", MODEL]
    result = json.loads(subprocess.check_output(cmd, encoding="utf8", text=True))
    assert result == preflight(request_package=case(), model=MODEL)
    second = [sys.executable, "-X", "utf8", "-m", "src.q25_openrouter_pilot",
              "--request-package", str(REQUEST), "--model", MODEL,
              "--max-cost-usd", "0.20"]
    dryrun = json.loads(subprocess.check_output(second, encoding="utf8", text=True))
    assert dryrun["status"] == "DRY_RUN"
    assert dryrun["provider_calls"] == 0
    assert dryrun["max_calls"] == 1
    assert dryrun["state_commit_authorized"] is False
