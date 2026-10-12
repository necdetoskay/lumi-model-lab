"""Q6E: fresh SC03 qualification that relays mother-dragon location.

Starts from the already accepted Q6D SC02 state. SC01 and SC02 remain immutable.
The revised SC03 contract adds explicit mother-dragon location state so later
scenes cannot reintroduce her from an impossible position.
"""
from __future__ import annotations

import json
import math
import time
from copy import deepcopy
from pathlib import Path

from src.model_registry import require_qualification_runtime_profile
from src.spineforge_v19_transport import _request_once
from src.spineforge_relay_v1_compile import compile_scene_contract
from src.spineforge_relay_v1_contracts import (
    EventPredicateV1,
    FrozenSpineRouteV1,
    RequiredEventSpecV1,
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
from src.spineforge_relay_v1_q6 import _sha, MAX_CALL_COST, WRITER, GUARD
from src.spineforge_relay_v1_q6b import relevant_character_canon
from src.spineforge_relay_v1_q6d import prop_authorization_policy, request_for

SOURCE_SC02 = Path("evidence/spineforge-relay/SFR-V1-Q6D-SC02-SC03-20261007/SC02-accepted.json")
Q6_FIXTURE = Path("tests/fixtures/spineforge_relay_v1/q6_lighthouse_sc02_sc03.json")
STORY_FIXTURE = Path("tests/fixtures/spineforge_relay_v1/q5t_lighthouse_scene01.json")
OUTPUT = Path("evidence/spineforge-relay/SFR-V1-Q6E-SC03-20261007")
MAX_TOTAL_COST = 0.30


def build_inputs():
    source = json.loads(SOURCE_SC02.read_text(encoding="utf-8"))
    q6 = json.loads(Q6_FIXTURE.read_text(encoding="utf-8"))
    story = json.loads(STORY_FIXTURE.read_text(encoding="utf-8"))
    state = StoryStateV1.model_validate(source["state_after"])
    if state.revision != 2 or state.next_spine_beat != "SC03":
        raise RuntimeError("Q6E requires accepted Q6D SC02 revision 2 / SC03")

    raw = deepcopy(q6["scene_plans"][1])
    if raw["scene_id"] != "SC03":
        raise RuntimeError("Q6E source SC03 plan drift")
    raw["required_exit_state"]["/world/mother_dragon_location"] = "lighthouse_upper_room"
    raw["required_events"].append({
        "id": "SC03-E05",
        "actor": "sea_dragon",
        "action": "OCCUPY",
        "target": "lighthouse_upper_room",
        "required_observer": "Ekin",
        "satisfaction_mode": "ALL_PREDICATES",
        "evidence_mode": "DIRECT_OBSERVATION",
        "separate_physical_clue_required": False,
        "predicates": [
            {"id": "P1", "subject": "sea_dragon", "action": "OCCUPY", "target": "lighthouse_upper_room"},
            {"id": "P2", "subject": "Ekin", "action": "OBSERVE", "target": "sea_dragon_in_lighthouse_upper_room"},
        ],
        "allowed_provenance": ["DIRECT_OBSERVATION"],
        "forbidden_provenance": ["INVENTED_WORLD_RULE", "INVENTED_CLUE", "UNESTABLISHED_LORE"],
        "forbidden_evidence_subjects": ["outside_reentry", "secret_route"],
        "resulting_state": {"/world/mother_dragon_location": "lighthouse_upper_room"},
    })
    raw["immutable_facts"].append(
        "At SC03 exit the mother sea dragon remains physically inside the lighthouse upper room."
    )
    plan = ScenePlanV1.model_validate(raw)
    route = FrozenSpineRouteV1(
        global_spine_sha256=state.global_spine_sha256,
        beat_ids=story["route"],
    )
    contract = compile_scene_contract(state, plan, route)
    return story["story_intent"], route, state, plan, contract


def prepare():
    for model in (WRITER, GUARD):
        require_qualification_runtime_profile(model)
    intent, route, state, plan, contract = build_inputs()
    canon = relevant_character_canon()
    prop_policy = prop_authorization_policy()
    return {
        "qualification_id": "SFR-V1-Q6E-SC03-MOTHER-LOCATION-20261007",
        "source_sc02_sha256": _sha(SOURCE_SC02),
        "story_intent_sha256": canonical_sha256(intent),
        "route_sha256": canonical_sha256(route),
        "start_state_sha256": canonical_sha256(state),
        "plan_sha256": canonical_sha256(plan),
        "contract_sha256": canonical_sha256(contract),
        "relevant_character_canon": canon,
        "relevant_character_canon_sha256": canonical_sha256(canon),
        "prop_authorization_policy": prop_policy,
        "prop_authorization_policy_sha256": canonical_sha256(prop_policy),
        "writer": WRITER,
        "guard": GUARD,
        "max_rewrites": 1,
        "automatic_retry": False,
        "state_application_on_accept": True,
        "max_call_cost_usd": MAX_CALL_COST,
        "max_total_cost_usd": MAX_TOTAL_COST,
        "expected_revision": 3,
        "expected_next_spine_beat": "SC04",
        "expected_mother_dragon_location": "lighthouse_upper_room",
    }


def authorization_for(preflight):
    return {
        "preflight_sha256": canonical_sha256(preflight),
        "paid_execution_authorized": True,
        "scene": "SC03",
        "max_rewrites": 1,
        "automatic_retry": False,
        "state_application_on_accept": True,
        "max_total_cost_usd": MAX_TOTAL_COST,
        "user_instruction": (
            "2026-10-07: Q6E fresh SC03 qualification to relay mother-dragon location; "
            "one scene only; max one rewrite; no retry"
        ),
    }


def execute(*, api_key: str, preflight: dict, authorization: dict, output=OUTPUT, call_fn=None):
    if preflight != prepare():
        raise RuntimeError("Q6E frozen preflight drift")
    if authorization != authorization_for(preflight):
        raise RuntimeError("Q6E authorization mismatch")
    if not api_key:
        raise RuntimeError("Missing credential")

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    claims = output.parent / "claims"
    claims.mkdir(exist_ok=True)
    with (claims / "q6e-sc03-20261007.json").open("x", encoding="utf-8") as handle:
        json.dump({"status": "CLAIMED_BEFORE_INFERENCE", **authorization}, handle, indent=2)
        handle.write("\n")

    save(output / "authorization.json", authorization)
    save(output / "preflight.json", preflight)

    intent, route, state, plan, contract = build_inputs()
    canon = relevant_character_canon()
    prop_policy = prop_authorization_policy()
    ledger = []
    result = {
        "status": "REJECT_NON_CONVERGENT",
        "reason": "UNFINISHED",
        "ledger": ledger,
        "automatic_retry": False,
        "state_advanced": False,
    }

    def call(stage, attempt, payload):
        kwargs, request = request_for(stage, payload)
        rates = require_qualification_runtime_profile(kwargs["model"])["metadata"]["pricing_usd_per_million_tokens"]
        planned = (
            len(json.dumps(request, ensure_ascii=False).encode("utf-8")) * float(rates["input"])
            + request["max_tokens"] * float(rates["output"])
        ) / 1_000_000
        if planned > MAX_CALL_COST or planned + sum(r["cost_usd"] or 0 for r in ledger) > MAX_TOTAL_COST:
            raise RuntimeError("Q6E conservative cost ceiling")
        row = {
            "stage": stage, "attempt": attempt, "model": kwargs["model"],
            "request_sha256": canonical_sha256(request), "status": "STARTED",
            "planned_uncached_cost_usd": round(planned, 8),
            "provider_spend_cap_guaranteed": False,
            "input_tokens": None, "output_tokens": None, "total_tokens": None, "cost_usd": None,
        }
        ledger.append(row)
        prefix = output / f"{attempt}-{stage}"
        save(str(prefix) + "-request.json", request)
        started = time.perf_counter()
        try:
            text, body, actual = (call_fn or _request_once)(api_key=api_key, **kwargs)
            save(str(prefix) + "-response.json", {k: body[k] for k in ("id", "model", "choices", "usage") if k in body})
            save(str(prefix) + "-text.json", {"text": text})
            if actual != request:
                raise RuntimeError("Q6E dispatched request drift")
            if (body.get("choices") or [{}])[0].get("finish_reason") != "stop":
                raise RuntimeError("Incomplete provider response")
            usage = body.get("usage") or {}
            for sk, tk in (("prompt_tokens","input_tokens"),("completion_tokens","output_tokens"),("total_tokens","total_tokens"),("cost","cost_usd")):
                value = usage.get(sk)
                if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value) or value < 0:
                    raise RuntimeError("Missing/invalid ledger field: " + sk)
                row[tk] = value
            if row["cost_usd"] > MAX_CALL_COST or sum(x["cost_usd"] or 0 for x in ledger) > MAX_TOTAL_COST:
                raise RuntimeError("Q6E cost ceiling exceeded")
            row["status"] = "COMPLETE"
            return text
        except Exception as exc:
            row["status"] = "FAILED_NO_RETRY"
            row["failure_type"] = type(exc).__name__
            raise
        finally:
            row["latency_seconds"] = round(time.perf_counter() - started, 3)
            save(str(prefix) + "-ledger.json", row)

    try:
        rewrite = None
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
            prose = call("writer", attempt, payload).strip()
            det = deterministic_scene_findings(prose=prose, contract=contract)
            if not prose or prose.startswith(("{", "[", "```")):
                raise RuntimeError("Writer response is not plain prose")
            raw_guard = json.loads(call("guard", attempt, {
                **inputs,
                "candidate_prose": prose,
                "deterministic_findings": [f.model_dump(mode="json") for f in det],
            }))
            report = StructuredGuardV1.model_validate(raw_guard)
            semantic = normalize_semantic_guard(
                raw=report.residual.model_dump(mode="json"),
                prose=prose,
            )
            det += evaluate_events(contract=contract, state=state, prose=prose, evidence=report.event_evidence)
            validation = combine_scene_validation(
                scene_id="SC03", attempt=attempt, deterministic=det, semantic=semantic
            )
            save(output / f"{attempt}-validation.json", validation.model_dump(mode="json"))
            if validation.decision == "ACCEPT":
                delta, after, artifact = freeze_scene(state, contract, prose, validation)
                if after.revision != 3 or after.next_spine_beat != "SC04":
                    raise RuntimeError("Q6E unexpected progression")
                if after.world.get("mother_dragon_location") != "lighthouse_upper_room":
                    raise RuntimeError("Q6E mother location not persisted")
                save(output / "SC03-accepted.json", {
                    "delta": delta.model_dump(mode="json"),
                    "state_after": after.model_dump(mode="json"),
                    "artifact": artifact.model_dump(mode="json"),
                })
                result.update(
                    status="ACCEPT",
                    reason="SC03_ACCEPTED_WITH_MOTHER_LOCATION_STATE",
                    state_advanced=True,
                    revision=after.revision,
                    next_spine_beat=after.next_spine_beat,
                    state_after_sha256=canonical_sha256(after),
                )
                break
            rewrite = {"candidate_prose": prose, "validation": validation.model_dump(mode="json")}
        else:
            result["reason"] = "SC03_REJECT_NON_CONVERGENT"
    except Exception as exc:
        result["reason"] = "FAILED_CLOSED_NO_RETRY"
        result["failure_type"] = type(exc).__name__

    result["known_cost_usd"] = round(sum(r["cost_usd"] or 0 for r in ledger), 8)
    result["usage_complete"] = all(
        all(r[k] is not None for k in ("cost_usd","input_tokens","output_tokens","total_tokens"))
        for r in ledger
    )
    save(output / "result.json", result)
    return result
