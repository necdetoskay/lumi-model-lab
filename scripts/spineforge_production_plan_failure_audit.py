"""Offline verification of bounded, complete-but-invalid planner responses."""
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from src.spineforge_relay_v1_contracts import canonical_sha256
from src.spineforge_seeded_design import verify_frozen_seed
from src.spineforge_story_design import StoryRequestV1
from src.spineforge_production_compact import CompactStoryPlanV1, compile_compact
from src.model_registry import normalize_openrouter_request


def verify_plan_failure(root, authority):
    root = Path(root)
    def read(name): return json.loads((root/name).read_text(encoding="utf8"))
    def require(value, reason):
        if not value: raise RuntimeError("Saved plan failure mismatch: " + reason)
    pf, result = read("preflight.json"), read("result.json")
    for s in pf["sources"]:
        require(hashlib.sha256((root/"frozen-sources"/s["path"]).read_bytes()).hexdigest() == s["sha256"], "source archive")
    for row, name in zip(pf["inputs"], ["request-input.json", "seed-input.json", "frozen-seed.json", "run-config.json"]):
        require(hashlib.sha256((root/name).read_bytes()).hexdigest() == row["sha256"], "frozen inputs")
    seed = verify_frozen_seed(root/"seed-input.json", root/"frozen-seed.json")
    request_input = StoryRequestV1.model_validate_json((root/"request-input.json").read_bytes())
    require(canonical_sha256(seed) == pf["seed_sha256"] and canonical_sha256(request_input) == pf["request_sha256"], "input identity")
    require(result["status"] == "REJECT_NON_CONVERGENT" and result["phase"] == "planning" and result["reason"] == "PLAN_REJECT_NON_CONVERGENT", "decision")
    require(result["provider_calls"] == 2 and result["usage_complete"] is True and result["automatic_retry"] is False, "bounded calls")
    cost = Decimal("0"); tokens = 0; latency = 0; failures = []
    for attempt, ledger in enumerate(result["ledger"], 1):
        prefix = f"plan-{attempt}-planner"
        require(ledger == read(prefix+"-ledger.json") and ledger["attempt"] == attempt and ledger["stage"] == "planner" and ledger["status"] == "COMPLETE", "ledger")
        kwargs = read(f"transport-captures/dispatch-{attempt}-input.json")
        require("api_key" not in kwargs, "no credential")
        dispatched = normalize_openrouter_request(kwargs["model"], dict(model=kwargs["model"], messages=[dict(role="system", content=kwargs["system_prompt"]), dict(role="user", content=kwargs["user_prompt"])], temperature=kwargs["temperature"], max_tokens=kwargs["max_tokens"]), request_class=kwargs["request_class"], structured_output=False)
        dispatched["response_format"] = kwargs["response_format"]
        dispatched["provider"] = {**dispatched.get("provider",{}), "require_parameters": True}
        require(dispatched == read(prefix+"-request.json") == read(f"transport-captures/dispatch-{attempt}-request.json") and canonical_sha256(dispatched) == ledger["request_sha256"], "request")
        body = read(prefix+"-response.json")
        require(body == read(f"transport-captures/dispatch-{attempt}-response.json") and body["choices"][0]["finish_reason"] == "stop", "complete response")
        text = read(prefix+"-text.json")["text"]
        require(text == body["choices"][0]["message"]["content"], "raw text")
        plan = CompactStoryPlanV1.model_validate_json(text)
        require(plan.model_dump(mode="json") == read(f"plan-{attempt}-compact.json"), "parsed proposal")
        structural = read(f"plan-{attempt}-structural.json")
        try: compile_compact(request_input, seed, plan)
        except (ValueError, RuntimeError, KeyError, TypeError) as exc:
            require(structural == dict(status="REJECTED_DESIGN", failure_type=type(exc).__name__, message=str(exc)), "reproduced structural rejection")
        else: raise RuntimeError("Saved plan failure mismatch: invalid plan admitted")
        failures.append(structural["message"])
        usage = body["usage"]
        require(all(type(usage[k]) is int and usage[k] >= 0 for k in ["prompt_tokens", "completion_tokens", "total_tokens"]), "integer usage")
        require(usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"] and (ledger["input_tokens"],ledger["output_tokens"],ledger["total_tokens"]) == (usage["prompt_tokens"],usage["completion_tokens"],usage["total_tokens"]), "usage totals")
        charge = Decimal(str(usage["cost"]))
        require(charge.is_finite() and charge >= 0 and charge == Decimal(str(ledger["cost_usd"])) and ledger["latency_seconds"] > 0, "charge/latency")
        cost += charge; tokens += usage["total_tokens"]; latency += ledger["latency_seconds"]
    require(len(result["ledger"]) == 2 and cost == Decimal(str(result["known_cost_usd"])), "aggregate")
    require(not (root/"story").exists() and not (root/"accepted-design.json").exists() and not list(root.glob("plan-3-*")) and not list(root.glob("*plan_guard*")), "no third attempt or downstream")
    for name, digest in read("manifest.json")["files"].items():
        require(hashlib.sha256((root/name).read_bytes()).hexdigest() == digest, "raw inventory")
    closed = json.loads(Path(authority).read_text(encoding="utf8"))
    scope = closed["grant"]["scopes"][0]; settled = closed["reservations"][scope["id"]]
    require(closed["status"] == "CLOSED" and settled["status"] == "SETTLED" and scope["preflight_sha256"] == canonical_sha256(pf) == settled["preflight_sha256"], "closed scope")
    require(settled["actual_calls"] == 2 and Decimal(settled["actual_cost_usd"]) == cost, "settlement")
    return dict(status="OFFLINE_PLAN_FAILURE_AUDIT_PASS", provider_calls=2, bounded_plan_rewrites=1,
        cost_usd=str(cost), total_tokens=tokens, latency_seconds=round(latency,3),
        structural_failures=failures, authority_status="CLOSED", reservation_status="SETTLED",
        seed_sha256=canonical_sha256(seed), plan_accepted=False, story_generated=False,
        state_advanced=False, no_retry=True, no_third_attempt=True)
