"""Fresh Q7C terminal-scene qualification bound to explicit safe egress."""
from __future__ import annotations

import json
import hashlib
import math
import time
from pathlib import Path

from src.model_registry import require_qualification_runtime_profile
from src.spineforge_v19_transport import _request_once
from src.spineforge_relay_v1_compile import compile_scene_contract
from src.spineforge_relay_v1_contracts import (
    FrozenSpineRouteV1,
    ScenePlanV1,
    StoryStateV1,
    canonical_sha256,
)
from src.spineforge_relay_v1_events import evaluate_events
from src.spineforge_relay_v1_guard import (
    combine_scene_validation,
    deterministic_scene_findings,
    normalize_semantic_guard,
)
from src.spineforge_relay_v1_q5t import StructuredGuardV1, freeze_scene, save
from src.spineforge_relay_v1_q6 import _expected_advance, _sha, MAX_CALL_COST, WRITER, GUARD
from src.spineforge_relay_v1_q6b import relevant_character_canon
from src.spineforge_relay_v1_q6d import prop_authorization_policy, request_for


PROPOSAL = Path("evidence/spineforge-relay/SFR-V1-Q7C-EGRESS-PROPOSAL-20261007/proposal.json")
STORY_FIXTURE = Path("tests/fixtures/spineforge_relay_v1/q5t_lighthouse_scene01.json")
OUTPUT = Path("evidence/spineforge-relay/SFR-V1-Q7C-SC06-20261007")
MAX_TOTAL_COST = 0.60


def build_chain():
    proposal = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    source_path = Path(proposal["source_sc05_path"])
    if _sha(source_path) != proposal["source_sc05_sha256"]:
        raise RuntimeError("Q7C source scene bytes drift")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    story = json.loads(STORY_FIXTURE.read_text(encoding="utf-8"))
    state = StoryStateV1.model_validate(source["state_after"])
    if source["artifact"]["status"] != "ACCEPTED" or canonical_sha256(state) != source["artifact"]["state_after_sha256"]:
        raise RuntimeError("Q7C needs a bound accepted predecessor")
    if state.revision != 5 or state.next_spine_beat != "SC06" or canonical_sha256(state) != proposal["source_state_sha256"]:
        raise RuntimeError("Q7C predecessor revision/state drift")
    if canonical_sha256(story["story_intent"]) != state.story_intent_sha256:
        raise RuntimeError("Q7C intent drift")
    route = FrozenSpineRouteV1(global_spine_sha256=state.global_spine_sha256, beat_ids=story["route"])
    plan = ScenePlanV1.model_validate(proposal["scene_plan"])
    contract = compile_scene_contract(state, plan, route)
    if contract.model_dump(mode="json") != proposal["scene_contract"] or canonical_sha256(contract) != proposal["contract_sha256"]:
        raise RuntimeError("Q7C contract drift")
    expected = _expected_advance(state, contract)
    if canonical_sha256(expected) != proposal["expected_final_state_sha256"]:
        raise RuntimeError("Q7C expected state drift")
    return {"previous_accepted_scene": source}, story["story_intent"], route, state, [(plan, contract, state)], expected


def prepare():
    for model in (WRITER, GUARD):
        require_qualification_runtime_profile(model)
    fixture, intent, route, start, rows, expected = build_chain()
    files = [PROPOSAL, STORY_FIXTURE, Path(json.loads(PROPOSAL.read_text(encoding="utf-8"))["source_sc05_path"]),
             Path("src/spineforge_relay_v1_q7c.py"), Path("src/spineforge_relay_v1_q6d.py"),
             Path("src/spineforge_relay_v1_q6.py"), Path("src/spineforge_relay_v1_q6b.py"),
             Path("tests/fixtures/spineforge_relay_v1/q6b_identity_probe.json"), Path("src/generate.py"),
             Path("src/spineforge_relay_v1_q5t.py"), Path("src/spineforge_relay_v1_contracts.py"),
             Path("src/spineforge_relay_v1_compile.py"), Path("src/spineforge_relay_v1_state.py"),
             Path("src/spineforge_relay_v1_events.py"), Path("src/spineforge_relay_v1_guard.py"),
             Path("src/spineforge_v19_transport.py"), Path("src/model_registry.py"),
             Path("configs/model_runtime_profiles.yaml"), Path("prompts/spineforge_relay_v1_q6d_writer.md"),
             Path("prompts/spineforge_relay_v1_q6d_guard.md"), Path("docs/experiments/lighthouse-context-and-spine-draft.md")]
    return {"qualification_id": "SFR-V1-Q7C-SC06-20261007", "files": [{"path": p.as_posix(), "sha256": _sha(p)} for p in files],
            "start_state_sha256": canonical_sha256(start), "contract_sha256": canonical_sha256(rows[0][1]),
            "previous_accepted_scene_sha256": canonical_sha256(fixture["previous_accepted_scene"]),
            "route_sha256": canonical_sha256(route), "story_intent_sha256": canonical_sha256(intent),
            "expected_final_state_sha256": canonical_sha256(expected), "writer": WRITER, "guard": GUARD,
            "max_calls": 4, "max_rewrites_per_scene": 1, "automatic_retry": False, "production_write": False,
            "max_call_cost_usd": MAX_CALL_COST, "max_total_cost_usd": MAX_TOTAL_COST}


def authorization_for(preflight):
    return {"preflight_sha256": canonical_sha256(preflight), "paid_execution_authorized": True,
            "destination": "OpenRouter", "scenes": ["SC06"], "max_calls": 4,
            "max_rewrites_per_scene": 1, "automatic_retry": False, "state_application_on_accept": True,
            "max_total_cost_usd": MAX_TOTAL_COST,
            "user_instruction": "2026-10-07: user said devam edelim after the Q7C fresh SC06 plan; existing explicit OpenRouter story-data consent persists; max one rewrite, no retry, freeze only on acceptance."}


def execute(*, api_key: str, preflight: dict, authorization: dict, output=OUTPUT, call_fn=None):
    if preflight != prepare():
        raise RuntimeError("Q7C frozen preflight drift")
    if authorization != authorization_for(preflight):
        raise RuntimeError("Q7C authorization mismatch")
    if not api_key:
        raise RuntimeError("Missing credential")

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    claims = output.parent / "claims"
    claims.mkdir(exist_ok=True)
    claim = claims / "q7c-sc06-20261007.json"
    with claim.open("x", encoding="utf-8") as handle:
        json.dump({"status": "CLAIMED_BEFORE_INFERENCE", **authorization}, handle, indent=2)
        handle.write("\n")

    save(output / "authorization.json", authorization)
    save(output / "preflight.json", preflight)

    _fixture, intent, route, state, rows, expected_final = build_chain()
    canon = relevant_character_canon()
    prop_policy = prop_authorization_policy()
    ledger = []
    result = {
        "status": "REJECT_NON_CONVERGENT",
        "reason": "UNFINISHED",
        "accepted_scenes": [],
        "ledger": ledger,
        "automatic_retry": False,
        "state_advanced_to_revision": state.revision,
        "next_spine_beat": state.next_spine_beat,
    }

    def call(scene_id, stage, attempt, payload):
        kwargs, request = request_for(stage, payload)
        rates = require_qualification_runtime_profile(kwargs["model"])["metadata"]["pricing_usd_per_million_tokens"]
        planned = (
            len(json.dumps(request, ensure_ascii=False).encode("utf-8")) * float(rates["input"])
            + request["max_tokens"] * float(rates["output"])
        ) / 1_000_000
        if planned > MAX_CALL_COST or planned + sum(r["cost_usd"] or 0 for r in ledger) > MAX_TOTAL_COST:
            raise RuntimeError("Q7C conservative cost ceiling")

        row = {
            "scene_id": scene_id,
            "stage": stage,
            "attempt": attempt,
            "model": kwargs["model"],
            "request_sha256": canonical_sha256(request),
            "status": "STARTED",
            "planned_uncached_cost_usd": round(planned, 8),
            "provider_spend_cap_guaranteed": False,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "cost_usd": None,
        }
        ledger.append(row)
        prefix = output / f"{scene_id}-{attempt}-{stage}"
        save(str(prefix) + "-request.json", request)
        save(str(prefix) + "-started.json", row)
        start = time.perf_counter()
        body = {}
        try:
            text, body, actual = (call_fn or _request_once)(api_key=api_key, **kwargs)
            save(str(prefix) + "-response.json", {
                k: body[k] for k in ("id", "model", "choices", "usage") if k in body
            })
            save(str(prefix) + "-text.json", {"text": text})
            if actual != request:
                raise RuntimeError("Q7C dispatched request drift")
            if (body.get("choices") or [{}])[0].get("finish_reason") != "stop":
                raise RuntimeError("Incomplete provider response")
            usage = body.get("usage") or {}
            for source_key, target_key in (
                ("prompt_tokens", "input_tokens"),
                ("completion_tokens", "output_tokens"),
                ("total_tokens", "total_tokens"),
                ("cost", "cost_usd"),
            ):
                value = usage.get(source_key)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise RuntimeError("Missing/invalid ledger field: " + source_key)
                row[target_key] = value
            if row["cost_usd"] > MAX_CALL_COST or sum(x["cost_usd"] or 0 for x in ledger) > MAX_TOTAL_COST:
                raise RuntimeError("Q7C cost ceiling exceeded")
            row["status"] = "COMPLETE"
            return text
        except Exception as exc:
            row["status"] = "FAILED_NO_RETRY"
            row["failure_type"] = type(exc).__name__
            failed_body = body or (getattr(exc, "trace", {}) or {}).get("body", {})
            row["raw_usage"] = failed_body.get("usage")
            for source_key, target_key in (("prompt_tokens", "input_tokens"), ("completion_tokens", "output_tokens"), ("total_tokens", "total_tokens"), ("cost", "cost_usd")):
                value = (row["raw_usage"] or {}).get(source_key)
                if not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
                    row[target_key] = value
            if failed_body and not body:
                save(str(prefix) + "-failure-response.json", {k: failed_body[k] for k in ("id", "model", "choices", "usage") if k in failed_body})
            raise
        finally:
            row["latency_seconds"] = round(time.perf_counter() - start, 3)
            save(str(prefix) + "-ledger.json", row)

    try:
        for plan, _precompiled, _expected_before in rows:
            if state.next_spine_beat != plan.spine_beats[0]:
                raise RuntimeError("Q7C stale progression before scene")
            contract = compile_scene_contract(state, plan, route)
            rewrite = None
            scene_accepted = False

            for attempt in (1, 2):
                inputs = {
                    "story_intent": intent,
                    "previous_accepted_scene": _fixture["previous_accepted_scene"],
                    "story_state": state.model_dump(mode="json"),
                    "frozen_spine_route": route.model_dump(mode="json"),
                    "scene_contract": contract.model_dump(mode="json"),
                    "relevant_character_canon": canon,
                    "prop_authorization_policy": prop_policy,
                }
                payload = {**inputs, "attempt": attempt, "rewrite": rewrite}
                prose = call(plan.scene_id, "writer", attempt, payload).strip()
                det = deterministic_scene_findings(prose=prose, contract=contract)
                if not prose or prose.startswith(("{", "[", "```")):
                    raise RuntimeError("Writer response is not plain prose")

                raw = json.loads(call(
                    plan.scene_id,
                    "guard",
                    attempt,
                    {
                        **inputs,
                        "candidate_prose": prose,
                        "deterministic_findings": [f.model_dump(mode="json") for f in det],
                    },
                ))
                report = StructuredGuardV1.model_validate(raw)
                semantic = normalize_semantic_guard(
                    raw=report.residual.model_dump(mode="json"),
                    prose=prose,
                )
                det += evaluate_events(
                    contract=contract,
                    state=state,
                    prose=prose,
                    evidence=report.event_evidence,
                )
                validation = combine_scene_validation(
                    scene_id=contract.scene_id,
                    attempt=attempt,
                    deterministic=det,
                    semantic=semantic,
                )
                save(output / f"{plan.scene_id}-{attempt}-validation.json", validation.model_dump(mode="json"))

                if validation.decision == "ACCEPT":
                    delta, after, artifact = freeze_scene(state, contract, prose, validation)
                    bundle = {
                        "delta": delta.model_dump(mode="json"),
                        "state_after": after.model_dump(mode="json"),
                        "artifact": artifact.model_dump(mode="json"),
                    }
                    save(output / f"{plan.scene_id}-accepted.json", bundle)
                    state = after
                    scene_accepted = True
                    result["accepted_scenes"].append(plan.scene_id)
                    result["state_advanced_to_revision"] = state.revision
                    result["next_spine_beat"] = state.next_spine_beat
                    break

                rewrite = {
                    "candidate_prose": prose,
                    "validation": validation.model_dump(mode="json"),
                }

            if not scene_accepted:
                result["reason"] = "SCENE_REJECT_NON_CONVERGENT:" + plan.scene_id
                break
        else:
            if canonical_sha256(state) != canonical_sha256(expected_final):
                raise RuntimeError("Q7C final state differs from deterministic expected state")
            if state.next_spine_beat is not None or state.revision != 6:
                raise RuntimeError("Q7C story did not reach terminal revision 6")
            result["status"] = "ACCEPT"
            result["reason"] = "SC06_ACCEPTED_WITH_BOUND_UPPER_DOOR_EGRESS"
    except Exception as exc:
        result["reason"] = "FAILED_CLOSED_NO_RETRY"
        result["failure_type"] = type(exc).__name__

    result["known_cost_usd"] = round(sum(r["cost_usd"] or 0 for r in ledger), 8)
    result["usage_complete"] = all(
        all(r[k] is not None for k in ("cost_usd", "input_tokens", "output_tokens", "total_tokens"))
        for r in ledger
    )
    save(output / "result.json", result)
    return result
