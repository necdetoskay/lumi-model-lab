"""Q7B: repeat SC04-SC06 from corrected Q6E SC03 state.

SC01-SC02 remain immutable. Q7B starts from the fresh accepted Q6E SC03
revision-3 StoryState carrying mother-dragon location and executes SC04, SC05 and SC06 sequentially. Writer and
guard share the qualified character canon and fail-closed actionable-prop policy.
"""
from __future__ import annotations

import json
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

FIXTURE = Path("tests/fixtures/spineforge_relay_v1/q7_lighthouse_sc04_sc06.json")
SOURCE_ACCEPTED = Path("evidence/spineforge-relay/SFR-V1-Q6E-SC03-20261007/SC03-accepted.json")
SOURCE_Q6E_RESULT = Path("evidence/spineforge-relay/SFR-V1-Q6E-SC03-20261007/result.json")
STORY_FIXTURE = Path("tests/fixtures/spineforge_relay_v1/q5t_lighthouse_scene01.json")
OUTPUT = Path("evidence/spineforge-relay/SFR-V1-Q7B-SC04-SC06-20261007")
MAX_TOTAL_COST = 0.90


def build_chain():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    source = json.loads(SOURCE_ACCEPTED.read_text(encoding="utf-8"))
    story = json.loads(STORY_FIXTURE.read_text(encoding="utf-8"))
    q6e = json.loads(SOURCE_Q6E_RESULT.read_text(encoding="utf-8"))
    if q6e.get("status") != "ACCEPT" or q6e.get("next_spine_beat") != "SC04":
        raise RuntimeError("Q7B requires accepted Q6E evidence ending at SC04")

    state = StoryStateV1.model_validate(source["state_after"])
    if state.revision != 3 or state.next_spine_beat != "SC04":
        raise RuntimeError("Q7B requires frozen accepted revision 3 / SC04")
    if fixture["route"] != story["route"]:
        raise RuntimeError("Q7B route drift")

    route = FrozenSpineRouteV1(
        global_spine_sha256=state.global_spine_sha256,
        beat_ids=fixture["route"],
    )
    rows = []
    expected = state
    for source_raw in fixture["scene_plans"]:
        raw = json.loads(json.dumps(source_raw))
        raw["entry_state"]["/world/mother_dragon_location"] = "lighthouse_upper_room"
        raw["required_exit_state"]["/world/mother_dragon_location"] = "lighthouse_upper_room"
        raw["immutable_facts"].append(
            "The mother sea dragon is already inside the lighthouse upper room at scene entry and does not re-enter from outside."
        )
        if raw["scene_id"] == "SC04":
            event = next(e for e in raw["required_events"] if e["id"] == "SC04-E03")
            event["resulting_state"]["/world/mother_dragon_location"] = "lighthouse_upper_room"
        if raw["scene_id"] == "SC06":
            event = next(e for e in raw["required_events"] if e["id"] == "SC06-E01")
            event["resulting_state"]["/world/mother_dragon_location"] = "lighthouse_upper_room"
            raw["forbidden"].append(
                "Do not make the mother sea dragon arrive, enter, or re-enter from outside; she is already inside the upper room."
            )
        plan = ScenePlanV1.model_validate(raw)
        contract = compile_scene_contract(expected, plan, route)
        rows.append((plan, contract, expected))
        expected = _expected_advance(expected, contract)
    return fixture, story["story_intent"], route, state, rows, expected


def prepare():
    for model in (WRITER, GUARD):
        require_qualification_runtime_profile(model)
    fixture, intent, route, start, rows, expected = build_chain()
    canon = relevant_character_canon()
    prop_policy = prop_authorization_policy()
    return {
        "qualification_id": "SFR-V1-Q7B-SC04-SC06-20261007",
        "source_accepted_sha256": _sha(SOURCE_ACCEPTED),
        "source_q6e_result_sha256": _sha(SOURCE_Q6E_RESULT),
        "story_intent_sha256": canonical_sha256(intent),
        "route_sha256": canonical_sha256(route),
        "start_state_sha256": canonical_sha256(start),
        "relevant_character_canon": canon,
        "relevant_character_canon_sha256": canonical_sha256(canon),
        "prop_authorization_policy": prop_policy,
        "prop_authorization_policy_sha256": canonical_sha256(prop_policy),
        "scene_contracts": [
            {
                "scene_id": plan.scene_id,
                "state_revision": before.revision,
                "state_sha256": canonical_sha256(before),
                "plan_sha256": canonical_sha256(plan),
                "contract_sha256": canonical_sha256(contract),
            }
            for plan, contract, before in rows
        ],
        "expected_final_state_sha256": canonical_sha256(expected),
        "writer": WRITER,
        "guard": GUARD,
        "max_rewrites_per_scene": 1,
        "automatic_retry": False,
        "stop_chain_on_scene_failure": True,
        "production_write": False,
        "max_call_cost_usd": MAX_CALL_COST,
        "max_total_cost_usd": MAX_TOTAL_COST,
    }


def authorization_for(preflight):
    return {
        "preflight_sha256": canonical_sha256(preflight),
        "paid_execution_authorized": True,
        "scenes": ["SC04", "SC05", "SC06"],
        "max_rewrites_per_scene": 1,
        "automatic_retry": False,
        "stop_chain_on_scene_failure": True,
        "state_application_on_accept": True,
        "max_total_cost_usd": MAX_TOTAL_COST,
        "user_instruction": (
            "2026-10-07: SFR-v1 Q7B complete story from corrected Q6E SC03 entity-location state; "
            "SC04 through SC06; max one rewrite per scene; no retry; stop on scene failure"
        ),
    }


def execute(*, api_key: str, preflight: dict, authorization: dict, output=OUTPUT, call_fn=None):
    if preflight != prepare():
        raise RuntimeError("Q7B frozen preflight drift")
    if authorization != authorization_for(preflight):
        raise RuntimeError("Q7B authorization mismatch")
    if not api_key:
        raise RuntimeError("Missing credential")

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    claims = output.parent / "claims"
    claims.mkdir(exist_ok=True)
    claim = claims / "q7b-sc04-sc06-20261007.json"
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
            raise RuntimeError("Q7B conservative cost ceiling")

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
        start = time.perf_counter()
        try:
            text, body, actual = (call_fn or _request_once)(api_key=api_key, **kwargs)
            save(str(prefix) + "-response.json", {
                k: body[k] for k in ("id", "model", "choices", "usage") if k in body
            })
            save(str(prefix) + "-text.json", {"text": text})
            if actual != request:
                raise RuntimeError("Q7B dispatched request drift")
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
                raise RuntimeError("Q7B cost ceiling exceeded")
            row["status"] = "COMPLETE"
            return text
        except Exception as exc:
            row["status"] = "FAILED_NO_RETRY"
            row["failure_type"] = type(exc).__name__
            raise
        finally:
            row["latency_seconds"] = round(time.perf_counter() - start, 3)
            save(str(prefix) + "-ledger.json", row)

    try:
        for plan, _precompiled, _expected_before in rows:
            if state.next_spine_beat != plan.spine_beats[0]:
                raise RuntimeError("Q7B stale progression before scene")
            contract = compile_scene_contract(state, plan, route)
            rewrite = None
            scene_accepted = False

            for attempt in (1, 2):
                inputs = {
                    "story_intent": intent,
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
                raise RuntimeError("Q7B final state differs from deterministic expected state")
            if state.next_spine_beat is not None or state.revision != 6:
                raise RuntimeError("Q7B story did not reach terminal revision 6")
            result["status"] = "ACCEPT"
            result["reason"] = "SC04_SC06_ACCEPTED_WITH_ENTITY_LOCATION_RELAY"
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
