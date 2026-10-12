"""Q6: real SC02 -> SC03 sequential relay qualification.

Starts only from the frozen accepted Q5T SC01 state. Each next scene is compiled
from the accepted prior StoryState. A failed scene stops the chain before the
next writer call. No automatic retry; max one semantic rewrite per scene.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path

from src.model_registry import require_qualification_runtime_profile
from src.spineforge_v19_transport import _request_once
from src.spineforge_relay_v1_compile import compile_scene_contract, _value_at
from src.spineforge_relay_v1_contracts import (
    FrozenSpineRouteV1,
    SceneDeltaV1,
    ScenePlanV1,
    StateMutation,
    StoryStateV1,
    canonical_sha256,
)
from src.spineforge_relay_v1_events import evaluate_events
from src.spineforge_relay_v1_guard import (
    combine_scene_validation,
    deterministic_scene_findings,
    normalize_semantic_guard,
)
from src.spineforge_relay_v1_q5t import (
    StructuredGuardV1,
    freeze_scene,
    request_for,
    save,
)

FIXTURE = Path("tests/fixtures/spineforge_relay_v1/q6_lighthouse_sc02_sc03.json")
SOURCE_ACCEPTED = Path("evidence/spineforge-relay/SFR-V1-Q5T-STRUCTURED-20261007/accepted-scene.json")
Q5T_FIXTURE = Path("tests/fixtures/spineforge_relay_v1/q5t_lighthouse_scene01.json")
OUTPUT = Path("evidence/spineforge-relay/SFR-V1-Q6-SC02-SC03-20261007")
WRITER = "openai/gpt-5.6-sol"
GUARD = "anthropic/claude-sonnet-5.5"
MAX_CALL_COST = 0.15
MAX_TOTAL_COST = 0.60


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _expected_advance(state: StoryStateV1, contract):
    mutations = []
    payload = state.model_dump(mode="json")
    for pointer, after in contract.required_exit_state.items():
        exists, before = _value_at(payload, pointer)
        if not exists or before != after:
            mutations.append(
                StateMutation(
                    path=pointer,
                    op="SET" if exists else "ADD",
                    before=before,
                    after=after,
                )
            )
    delta = SceneDeltaV1(
        scene_id=contract.scene_id,
        source_state_revision=state.revision,
        source_state_sha256=canonical_sha256(state),
        contract_sha256=canonical_sha256(contract),
        mutations=mutations,
    )
    from src.spineforge_relay_v1_state import apply_scene_delta
    return apply_scene_delta(state, delta, contract)


def build_chain():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    source = json.loads(SOURCE_ACCEPTED.read_text(encoding="utf-8"))
    q5t = json.loads(Q5T_FIXTURE.read_text(encoding="utf-8"))
    state = StoryStateV1.model_validate(source["state_after"])
    if state.revision != 1 or state.next_spine_beat != "SC02":
        raise RuntimeError("Q6 requires frozen accepted Q5T revision 1 / SC02")
    if fixture["route"] != q5t["route"]:
        raise RuntimeError("Q6 route drift")

    route = FrozenSpineRouteV1(
        global_spine_sha256=state.global_spine_sha256,
        beat_ids=fixture["route"],
    )
    rows = []
    expected = state
    for raw in fixture["scene_plans"]:
        plan = ScenePlanV1.model_validate(raw)
        contract = compile_scene_contract(expected, plan, route)
        rows.append((plan, contract, expected))
        expected = _expected_advance(expected, contract)
    return fixture, q5t["story_intent"], route, state, rows, expected


def _deps():
    paths = [
        Path(__file__).relative_to(Path.cwd()),
        FIXTURE,
        SOURCE_ACCEPTED,
        Q5T_FIXTURE,
        Path("src/spineforge_relay_v1_q5t.py"),
        Path("src/spineforge_relay_v1_events.py"),
        Path("src/spineforge_relay_v1_contracts.py"),
        Path("src/spineforge_relay_v1_compile.py"),
        Path("src/spineforge_relay_v1_state.py"),
        Path("src/spineforge_relay_v1_guard.py"),
        Path("prompts/spineforge_relay_v1_q5t_writer.md"),
        Path("prompts/spineforge_relay_v1_q5t_guard.md"),
        Path("configs/model_runtime_profiles.yaml"),
    ]
    return {p.as_posix(): _sha(p) for p in paths}


def prepare():
    for model in (WRITER, GUARD):
        require_qualification_runtime_profile(model)
    fixture, intent, route, start, rows, expected = build_chain()
    return {
        "qualification_id": fixture["qualification_id"],
        "source_accepted_sha256": _sha(SOURCE_ACCEPTED),
        "story_intent_sha256": canonical_sha256(intent),
        "route_sha256": canonical_sha256(route),
        "start_state_sha256": canonical_sha256(start),
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
        "dependencies": _deps(),
    }


def authorization_for(preflight):
    return {
        "preflight_sha256": canonical_sha256(preflight),
        "paid_execution_authorized": True,
        "scenes": ["SC02", "SC03"],
        "max_rewrites_per_scene": 1,
        "automatic_retry": False,
        "stop_chain_on_scene_failure": True,
        "state_application_on_accept": True,
        "max_total_cost_usd": MAX_TOTAL_COST,
        "user_instruction": (
            "2026-10-07: continue SFR-v1 Q6 sequential relay; "
            "bounded SC02 then SC03; no retry; stop on scene failure"
        ),
    }


def execute(*, api_key: str, preflight: dict, authorization: dict, output=OUTPUT, call_fn=None):
    if preflight != prepare():
        raise RuntimeError("Q6 frozen preflight drift")
    if authorization != authorization_for(preflight):
        raise RuntimeError("Q6 authorization mismatch")
    if not api_key:
        raise RuntimeError("Missing credential")

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    claims = output.parent / "claims"
    claims.mkdir(exist_ok=True)
    claim = claims / "q6-sc02-sc03-20261007.json"
    with claim.open("x", encoding="utf-8") as handle:
        json.dump({"status": "CLAIMED_BEFORE_INFERENCE", **authorization}, handle, indent=2)
        handle.write("\n")
    save(output / "authorization.json", authorization)
    save(output / "preflight.json", preflight)

    fixture, intent, route, state, rows, expected_final = build_chain()
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
            raise RuntimeError("Q6 conservative cost ceiling")

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
                raise RuntimeError("Q6 dispatched request drift")
            if (body.get("choices") or [{}])[0].get("finish_reason") != "stop":
                raise RuntimeError("Incomplete provider response")
            usage = body.get("usage") or {}
            for source, target in (
                ("prompt_tokens", "input_tokens"),
                ("completion_tokens", "output_tokens"),
                ("total_tokens", "total_tokens"),
                ("cost", "cost_usd"),
            ):
                value = usage.get(source)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise RuntimeError("Missing/invalid ledger field: " + source)
                row[target] = value
            if row["cost_usd"] > MAX_CALL_COST or sum(x["cost_usd"] or 0 for x in ledger) > MAX_TOTAL_COST:
                raise RuntimeError("Q6 cost ceiling exceeded")
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
                raise RuntimeError("Q6 stale progression before scene")
            contract = compile_scene_contract(state, plan, route)
            rewrite = None
            scene_accepted = False
            for attempt in (1, 2):
                inputs = {
                    "story_intent": intent,
                    "story_state": state.model_dump(mode="json"),
                    "frozen_spine_route": route.model_dump(mode="json"),
                    "scene_contract": contract.model_dump(mode="json"),
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
                save(
                    output / f"{plan.scene_id}-{attempt}-validation.json",
                    validation.model_dump(mode="json"),
                )
                if validation.decision == "ACCEPT":
                    delta, after, artifact = freeze_scene(
                        state, contract, prose, validation
                    )
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
                raise RuntimeError("Q6 final state differs from deterministic expected state")
            result["status"] = "ACCEPT"
            result["reason"] = "SC02_SC03_ACCEPTED_SEQUENTIALLY"
    except Exception as exc:
        result["reason"] = "FAILED_CLOSED_NO_RETRY"
        result["failure_type"] = type(exc).__name__

    result["known_cost_usd"] = round(
        sum(r["cost_usd"] or 0 for r in ledger), 8
    )
    result["usage_complete"] = all(
        all(r[k] is not None for k in ("cost_usd", "input_tokens", "output_tokens", "total_tokens"))
        for r in ledger
    )
    save(output / "result.json", result)
    return result
