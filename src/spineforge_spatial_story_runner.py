"""Generic spatial Relay runner, versioned to preserve recorded v1/v2 execution.

No story-specific state repair or fixture-name branching is permitted here.
All narrative-specific facts enter through a data fixture.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any

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
from src.spineforge_relay_v1_spatial import SpatialTopologyV1, SpatialStateV1, SpatialOperationV1, compile_spatial_contract, evaluate_spatial
from src.spineforge_relay_v1_coverage import PlanObligationV1, PredicateOrderV1, compile_plan_coverage, evaluate_plan_coverage
from src.model_registry import normalize_openrouter_request
from src.spineforge_relay_v1_guard import (
    combine_scene_validation,
    deterministic_scene_findings,
    normalize_semantic_guard,
)
from src.spineforge_relay_v1_q5t import StructuredGuardV1, freeze_scene, save
from src.spineforge_relay_v1_q6 import _expected_advance, MAX_CALL_COST, WRITER, GUARD
from src.spineforge_relay_v1_q6d import request_for

MAX_STORY_COST_USD = 0.60


def load_fixture(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema",
        "story_id",
        "story_intent",
        "route",
        "initial_state",
        "relevant_character_canon",
        "prop_authorization_policy",
        "scene_plans",
    }
    covered = raw.get("schema") == "spineforge-relay.repeatability-fixture.v3"
    if covered:
        required.update({"coverage_plans", "topology", "spatial_plans"})
    if set(raw) != required:
        raise RuntimeError("Q8 fixture keys drift")
    if raw["schema"] != "spineforge-relay.repeatability-fixture.v3":
        raise RuntimeError("Q8 fixture schema drift")
    if len(raw["route"]) < 2:
        raise RuntimeError("Q8 fixture needs at least two beats")
    if [p["scene_id"] for p in raw["scene_plans"]] != raw["route"]:
        raise RuntimeError("Q8 scene plans must cover route exactly")
    if covered and [p["scene_id"] for p in raw["coverage_plans"]] != raw["route"]:
        raise RuntimeError("Coverage plans must cover route exactly and in order")
    if [p["scene_id"] for p in raw["spatial_plans"]] != raw["route"]:
        raise RuntimeError("Spatial plans must cover route exactly and in order")
    return raw


def coverage_for(fixture, plan, contract):
    if fixture["schema"] == "spineforge-relay.repeatability-fixture.v1":
        return None
    row = next(p for p in fixture["coverage_plans"] if p["scene_id"] == plan.scene_id)
    if set(row) != {"scene_id", "obligations", "ordered_dependencies"}:
        raise ValueError("Coverage plan keys drift")
    return compile_plan_coverage(plan=plan, scene=contract,
        obligations=[PlanObligationV1.model_validate(o) for o in row["obligations"]],
        ordered_dependencies=[PredicateOrderV1.model_validate(o) for o in row["ordered_dependencies"]])


def spatial_for(fixture, plan, contract, state):
    row = next(p for p in fixture["spatial_plans"] if p["scene_id"] == plan.scene_id)
    if set(row) != {"scene_id", "operations", "expected_exit"}:
        raise ValueError("Spatial plan keys drift")
    return compile_spatial_contract(scene=contract, state=state,
        topology=SpatialTopologyV1.model_validate(fixture["topology"]),
        operations=[SpatialOperationV1.model_validate(o) for o in row["operations"]],
        expected_exit=SpatialStateV1.model_validate(row["expected_exit"]))


def runner_request_for(stage, payload):
    kwargs, request = request_for(stage, payload)
    if "plan_coverage_contract" not in payload:
        return kwargs, request
    for family in ("coverage", "spatial"):
        kwargs["system_prompt"] += "\n\n" + Path(f"prompts/spineforge_relay_v1_{family}_{stage}.md").read_text(encoding="utf-8").strip()
    request = normalize_openrouter_request(kwargs["model"], {
        "model": kwargs["model"], "messages": [
            {"role": "system", "content": kwargs["system_prompt"]},
            {"role": "user", "content": kwargs["user_prompt"]}],
        "temperature": kwargs["temperature"], "max_tokens": kwargs["max_tokens"]},
        request_class=kwargs["request_class"], structured_output=False)
    request["response_format"] = kwargs["response_format"]
    request["provider"] = {**request.get("provider", {}), "require_parameters": True}
    return kwargs, request


def build_chain(path: Path):
    fixture = load_fixture(path)
    intent = fixture["story_intent"]
    route_ids = fixture["route"]
    global_spine_sha256 = canonical_sha256(
        {"story_id": fixture["story_id"], "route": route_ids}
    )
    state_raw = json.loads(json.dumps(fixture["initial_state"]))
    state_raw.update({
        "schema_name": "spineforge-relay.story-state.v1",
        "story_id": fixture["story_id"],
        "global_spine_sha256": global_spine_sha256,
        "story_intent_sha256": canonical_sha256(intent),
    })
    state = StoryStateV1.model_validate(state_raw)
    if state.revision != 0 or state.next_spine_beat != route_ids[0]:
        raise RuntimeError("Q8 fixture must start at revision 0 / first beat")

    route = FrozenSpineRouteV1(
        global_spine_sha256=global_spine_sha256,
        beat_ids=route_ids,
    )
    rows = []
    expected = state
    for raw_plan in fixture["scene_plans"]:
        plan = ScenePlanV1.model_validate(raw_plan)
        contract = compile_scene_contract(expected, plan, route)
        coverage_for(fixture, plan, contract)
        spatial_for(fixture, plan, contract, expected)
        rows.append((plan, contract, expected))
        expected = _expected_advance(expected, contract)
    return fixture, intent, route, state, rows, expected


def prepare(path: Path) -> dict[str, Any]:
    for model in (WRITER, GUARD):
        require_qualification_runtime_profile(model)
    fixture, intent, route, start, rows, expected = build_chain(path)
    preflight = {
        "schema": "spineforge-relay.repeatability-preflight.v1",
        "fixture_path": path.as_posix(),
        "fixture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "story_id": fixture["story_id"],
        "story_intent_sha256": canonical_sha256(intent),
        "route_sha256": canonical_sha256(route),
        "start_state_sha256": canonical_sha256(start),
        "relevant_character_canon_sha256": canonical_sha256(fixture["relevant_character_canon"]),
        "prop_authorization_policy_sha256": canonical_sha256(fixture["prop_authorization_policy"]),
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
        "max_story_cost_usd": MAX_STORY_COST_USD,
    }
    if fixture["schema"] == "spineforge-relay.repeatability-fixture.v3":
        preflight["schema"] = "spineforge-relay.repeatability-preflight.v3"
        preflight["coverage_contract_sha256"] = [canonical_sha256(coverage_for(fixture, p, c)) for p, c, _ in rows]
        # Freeze executable modules and registry/config/prompt dependencies, not only fixture data.
        paths = sorted(Path("src").glob("spineforge_relay_v1*.py")) + [
            Path("src/spineforge_v19_transport.py"), Path("src/model_registry.py"),
            Path("configs/model_runtime_profiles.yaml"), Path("requirements.txt")]
        paths += [Path("src/spineforge_spatial_story_runner.py"), Path("src/spineforge_spatial_paid_entry.py")]
        paths += sorted(Path("prompts").glob("spineforge_relay_v1*.md"))
        preflight["source_encoding"] = "UTF-8 with CRLF normalized to LF"
        preflight["fixture_sha256"] = hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        preflight["sources"] = [{"path": p.as_posix(), "sha256": hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()} for p in paths]
        preflight["max_calls"] = len(rows) * 4
        preflight["topology_sha256"] = canonical_sha256(fixture["topology"])
        preflight["spatial_contract_sha256"] = [canonical_sha256(spatial_for(fixture, p, c, before)) for p, c, before in rows]
    return preflight


def execute_story(
    *,
    fixture_path: Path,
    api_key: str,
    preflight: dict[str, Any],
    output: Path,
    call_fn=None,
) -> dict[str, Any]:
    if preflight != prepare(fixture_path):
        raise RuntimeError("Q8 frozen preflight drift")
    if not api_key:
        raise RuntimeError("Missing credential")

    output.mkdir(parents=True, exist_ok=False)
    save(output / "preflight.json", preflight)
    fixture, intent, route, state, rows, expected_final = build_chain(fixture_path)
    canon = fixture["relevant_character_canon"]
    prop_policy = fixture["prop_authorization_policy"]
    ledger = []
    result = {
        "story_id": fixture["story_id"],
        "status": "REJECT_NON_CONVERGENT",
        "reason": "UNFINISHED",
        "accepted_scenes": [],
        "ledger": ledger,
        "automatic_retry": False,
        "state_advanced_to_revision": state.revision,
        "next_spine_beat": state.next_spine_beat,
    }

    def call(scene_id: str, stage: str, attempt: int, payload: dict[str, Any]) -> str:
        kwargs, request = runner_request_for(stage, payload)
        rates = require_qualification_runtime_profile(kwargs["model"])["metadata"]["pricing_usd_per_million_tokens"]
        planned = (
            len(json.dumps(request, ensure_ascii=False).encode("utf-8")) * float(rates["input"])
            + request["max_tokens"] * float(rates["output"])
        ) / 1_000_000
        if planned > MAX_CALL_COST:
            raise RuntimeError("Q8 per-call conservative ceiling")
        if planned + sum(r["cost_usd"] or 0 for r in ledger) > MAX_STORY_COST_USD:
            raise RuntimeError("Q8 per-story conservative ceiling")

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
        started = time.perf_counter()
        try:
            text, body, actual = (call_fn or _request_once)(api_key=api_key, **kwargs)
            save(str(prefix) + "-response.json", {
                k: body[k] for k in ("id", "model", "choices", "usage") if k in body
            })
            save(str(prefix) + "-text.json", {"text": text})
            if actual != request:
                raise RuntimeError("Q8 dispatched request drift")
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
            if row["cost_usd"] > MAX_CALL_COST:
                raise RuntimeError("Q8 provider cost exceeds per-call ceiling")
            if sum(x["cost_usd"] or 0 for x in ledger) > MAX_STORY_COST_USD:
                raise RuntimeError("Q8 provider cost exceeds per-story ceiling")
            row["status"] = "COMPLETE"
            return text
        except Exception as exc:
            row["status"] = "FAILED_NO_RETRY"
            row["failure_type"] = type(exc).__name__
            raise
        finally:
            row["latency_seconds"] = round(time.perf_counter() - started, 3)
            save(str(prefix) + "-ledger.json", row)
            print(
                "SFR_Q8_LEDGER "
                + json.dumps(
                    {
                        "story_id": fixture["story_id"],
                        "scene_id": scene_id,
                        "stage": stage,
                        "attempt": attempt,
                        "status": row["status"],
                        "cost_usd": row["cost_usd"],
                        "input_tokens": row["input_tokens"],
                        "output_tokens": row["output_tokens"],
                        "total_tokens": row["total_tokens"],
                    },
                    separators=(",", ":"),
                ),
                flush=True,
            )

    previous_accepted = None
    try:
        for plan, _precompiled, _expected_before in rows:
            contract = compile_scene_contract(state, plan, route)
            spatial = spatial_for(fixture, plan, contract, state)
            save(output / f"{plan.scene_id}-spatial-contract.json", spatial.model_dump(mode="json"))
            coverage = coverage_for(fixture, plan, contract)
            if coverage is not None:
                save(output / f"{plan.scene_id}-coverage-contract.json", coverage.model_dump(mode="json"))
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
                if coverage is not None:
                    inputs["spatial_contract"] = spatial.model_dump(mode="json")
                    inputs["plan_coverage_contract"] = coverage.model_dump(mode="json")
                    inputs["previous_accepted_scene"] = previous_accepted
                payload = {**inputs, "attempt": attempt, "rewrite": rewrite}
                prose = call(plan.scene_id, "writer", attempt, payload).strip()
                det = deterministic_scene_findings(prose=prose, contract=contract)
                if not prose or prose.startswith(("{", "[", "\x60\x60\x60")):
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
                det += evaluate_spatial(contract=spatial, scene=contract, state=state, prose=prose, evidence=report.event_evidence)
                if coverage is not None:
                    det += evaluate_plan_coverage(coverage=coverage, plan=plan, scene=contract, prose=prose, evidence=report.event_evidence)
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
                    previous_accepted = {**bundle, "prose": prose}
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
                raise RuntimeError("Q8 final state differs from deterministic expected state")
            if state.next_spine_beat is not None:
                raise RuntimeError("Q8 story did not terminate")
            result["status"] = "ACCEPT"
            result["reason"] = "GENERIC_STORY_ACCEPTED"
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
