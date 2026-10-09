"""Verify a recorded first-planner token-limit rejection without inference."""
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from src.spineforge_relay_v1_contracts import canonical_sha256
from src.spineforge_seeded_design import verify_frozen_seed
from src.model_registry import normalize_openrouter_request


def verify_truncation(root, authority):
    root = Path(root)
    def read(name):
        return json.loads((root / name).read_text(encoding="utf8"))
    def require(condition, reason):
        if not condition:
            raise RuntimeError("Saved truncation evidence mismatch: " + reason)
    pf, result = read("preflight.json"), read("result.json")
    for row in pf["sources"]:
        require(hashlib.sha256((root / "frozen-sources" / row["path"]).read_bytes()).hexdigest() == row["sha256"], "frozen source")
    for row, name in zip(pf["inputs"], ["request-input.json", "seed-input.json", "frozen-seed.json", "run-config.json"]):
        require(hashlib.sha256((root / name).read_bytes()).hexdigest() == row["sha256"], "frozen input")
    seed = verify_frozen_seed(root / "seed-input.json", root / "frozen-seed.json")
    require(canonical_sha256(seed) == pf["seed_sha256"], "seed identity")
    ledger = read("plan-1-planner-ledger.json")
    require(result["status"] == "REJECT_NON_CONVERGENT" and result["phase"] == "planning" and result["reason"] == "FAILED_CLOSED_NO_RETRY", "decision")
    require(result["provider_calls"] == 1 and result["usage_complete"] is True and result["automatic_retry"] is False, "dispatch count")
    require(result["ledger"] == [ledger] and ledger["status"] == "FAILED_NO_RETRY" and ledger["attempt"] == 1, "ledger")
    kwargs = read("transport-captures/dispatch-1-input.json")
    require("api_key" not in kwargs, "credential omitted")
    request = normalize_openrouter_request(kwargs["model"], dict(model=kwargs["model"], messages=[dict(role="system", content=kwargs["system_prompt"]), dict(role="user", content=kwargs["user_prompt"])], temperature=kwargs["temperature"], max_tokens=kwargs["max_tokens"]), request_class=kwargs["request_class"], structured_output=False)
    request["response_format"] = kwargs["response_format"]
    request["provider"] = {**request.get("provider", {}), "require_parameters": True}
    require(request == read("plan-1-planner-request.json") == read("transport-captures/dispatch-1-request.json") and canonical_sha256(request) == ledger["request_sha256"], "request")
    body = read("plan-1-planner-response.json")
    require(body == read("transport-captures/dispatch-1-response.json"), "response")
    choice, usage = body["choices"][0], body["usage"]
    require(choice["finish_reason"] == "length", "token-limit finish")
    text = read("plan-1-planner-text.json")["text"]
    require(text == choice["message"]["content"], "raw partial text")
    try:
        json.loads(text)
    except json.JSONDecodeError:
        pass
    else:
        raise RuntimeError("Saved truncation evidence mismatch: expected incomplete JSON")
    for key in ["prompt_tokens", "completion_tokens", "total_tokens"]:
        require(type(usage[key]) is int and usage[key] >= 0, "integer usage")
    require(usage["completion_tokens"] == request["max_tokens"] and usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"], "token totals")
    require((ledger["input_tokens"], ledger["output_tokens"], ledger["total_tokens"]) == (usage["prompt_tokens"], usage["completion_tokens"], usage["total_tokens"]), "ledger usage")
    cost = Decimal(str(usage["cost"]))
    require(cost.is_finite() and cost >= 0 and cost == Decimal(str(ledger["cost_usd"])) == Decimal(str(result["known_cost_usd"])), "cost")
    require(ledger["latency_seconds"] > 0, "latency")
    require(not (root / "story").exists() and not (root / "accepted-design.json").exists() and not list(root.glob("plan-2-*")) and not list(root.glob("*plan_guard*")), "no downstream/retry")
    for name, digest in read("manifest.json")["files"].items():
        require(hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, "raw inventory")
    closed = json.loads(Path(authority).read_text(encoding="utf8"))
    scope = closed["grant"]["scopes"][0]
    reservation = closed["reservations"][scope["id"]]
    require(closed["status"] == "CLOSED" and reservation["status"] == "SETTLED" and scope["preflight_sha256"] == canonical_sha256(pf) == reservation["preflight_sha256"], "closed scope")
    require(reservation["actual_calls"] == 1 and Decimal(reservation["actual_cost_usd"]) == cost, "settlement")
    return dict(status="OFFLINE_TRUNCATION_AUDIT_PASS", seed_sha256=canonical_sha256(seed), provider_calls=1, finish_reason="length", input_tokens=usage["prompt_tokens"], output_tokens=usage["completion_tokens"], total_tokens=usage["total_tokens"], cost_usd=str(cost), latency_seconds=ledger["latency_seconds"], authority_status="CLOSED", reservation_status="SETTLED", plan_accepted=False, story_generated=False, state_advanced=False, no_retry=True)
