"""Offline replay of saved Relay calls and state transitions. No inference.

Mechanical evidence consistency is distinct from editorial qualification.
A consistent ACCEPT bundle can still contain a semantic continuity defect.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from src.spineforge_relay_v1_spatial import (
    SpatialContractV1, SpatialTopologyV1, SpatialOperationV1, SpatialStateV1,
    compile_spatial_contract, evaluate_spatial,
)
from src.spineforge_relay_v1_q7e_inputs import build_chain, request_for
from src.spineforge_relay_v1_coverage import PlanCoverageContractV1, PlanObligationV1, PredicateOrderV1, compile_plan_coverage, evaluate_plan_coverage
from src.generate import _extract_text_content
from src.spineforge_relay_v1_compile import compile_scene_contract
from src.spineforge_relay_v1_contracts import canonical_sha256
from src.spineforge_relay_v1_events import evaluate_events
from src.spineforge_relay_v1_guard import (
    combine_scene_validation, deterministic_scene_findings, normalize_semantic_guard,
)
from src.spineforge_relay_v1_q5t import StructuredGuardV1, freeze_scene


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require(condition, message):
    if not condition:
        raise RuntimeError("Saved Relay evidence mismatch: " + message)


def verify_q7e(root):
    """Reproduce accepted scenes from complete saved requests/responses/ledgers."""
    fixture, _intent, route, start, rows, expected_final = build_chain()
    request_factory = request_for
    previous = fixture["previous_accepted_scene"]
    root = Path(root)
    preflight = _read(root / "preflight.json")
    for row in preflight["files"]:
        _require(hashlib.sha256(Path(row["path"]).read_bytes()).hexdigest() == row["sha256"], "frozen source bytes")
    state = start
    ledgers = []
    accepted_ids = []
    for plan, _precompiled, _expected_before in rows:
        contract = compile_scene_contract(state, plan, route)
        spatial = SpatialContractV1.model_validate(_read(root / f"{plan.scene_id}-spatial-contract.json"))
        spatial_plan = next(p for p in fixture["spatial_plans"] if p["scene_id"] == plan.scene_id)
        expected_spatial = compile_spatial_contract(scene=contract, state=state,
            topology=SpatialTopologyV1.model_validate(fixture["topology"]),
            operations=[SpatialOperationV1.model_validate(o) for o in spatial_plan["operations"]],
            expected_exit=SpatialStateV1.model_validate(spatial_plan["expected_exit"]))
        _require(spatial == expected_spatial, "frozen spatial operation plan")
        coverage = PlanCoverageContractV1.model_validate(_read(root / f"{plan.scene_id}-coverage-contract.json"))
        coverage_plan = next(p for p in fixture["coverage_plans"] if p["scene_id"] == plan.scene_id)
        expected_coverage = compile_plan_coverage(plan=plan, scene=contract,
            obligations=[PlanObligationV1.model_validate(o) for o in coverage_plan["obligations"]],
            ordered_dependencies=[PredicateOrderV1.model_validate(o) for o in coverage_plan["ordered_dependencies"]])
        _require(coverage == expected_coverage, "frozen plan coverage")
        bundle = _read(root / f"{plan.scene_id}-accepted.json")
        attempt_count = bundle["artifact"]["attempt"]
        _require(attempt_count in (1, 2), "attempt bound")
        for attempt in range(1, attempt_count + 1):
            prose = _read(root / f"{plan.scene_id}-{attempt}-writer-text.json")["text"].strip()
            deterministic = deterministic_scene_findings(prose=prose, contract=contract)
            for stage in ("writer", "guard"):
                prefix = root / f"{plan.scene_id}-{attempt}-{stage}"
                request = _read(str(prefix) + "-request.json")
                response = _read(str(prefix) + "-response.json")
                text = _read(str(prefix) + "-text.json")["text"]
                ledger = _read(str(prefix) + "-ledger.json")
                messages = request["messages"]
                payload = json.loads(messages[1]["content"])
                _require(payload["plan_coverage_contract"] == coverage.model_dump(mode="json"), "request goal coverage")
                _require(payload["spatial_contract"] == spatial.model_dump(mode="json"), "request spatial contract")
                _require(payload["previous_accepted_scene"] == previous, "predecessor prose/state")
                _require(payload["story_state"] == state.model_dump(mode="json"), "request state")
                _require(payload["scene_contract"] == contract.model_dump(mode="json"), "request contract")
                _require(payload["frozen_spine_route"] == route.model_dump(mode="json"), "request route")
                _require(canonical_sha256(payload["story_intent"]) == state.story_intent_sha256, "intent")
                _kwargs, expected_request = request_factory(stage, payload)
                _require(request == expected_request, "request dispatch profile")
                _require(canonical_sha256(request) == ledger["request_sha256"], "request fingerprint")
                _require(ledger["status"] == "COMPLETE", "incomplete call")
                _require(ledger["model"] == request["model"], "model ledger")
                _require(ledger["attempt"] == attempt and ledger["scene_id"] == plan.scene_id and ledger["stage"] == stage, "ledger attribution")
                choices = response.get("choices") or []
                _require(bool(choices) and choices[0].get("finish_reason") == "stop", "finish reason")
                _require(_extract_text_content(choices[0]["message"]) == text, "response text")
                for provider_key, ledger_key in (("prompt_tokens", "input_tokens"), ("completion_tokens", "output_tokens"), ("total_tokens", "total_tokens"), ("cost", "cost_usd")):
                    value = response["usage"][provider_key]
                    _require(not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0, "usage validity")
                    _require(value == ledger[ledger_key], "provider usage")
                _require(math.isfinite(ledger["latency_seconds"]) and ledger["latency_seconds"] >= 0, "latency")
                if stage == "guard":
                    _require(payload["candidate_prose"] == prose, "guard candidate")
                    _require(payload["deterministic_findings"] == [f.model_dump(mode="json") for f in deterministic], "guard deterministic input")
                ledgers.append(ledger)
            guard_raw = json.loads(_read(root / f"{plan.scene_id}-{attempt}-guard-text.json")["text"])
            guard = StructuredGuardV1.model_validate(guard_raw)
            semantic = normalize_semantic_guard(raw=guard.residual.model_dump(mode="json"), prose=prose)
            deterministic += evaluate_events(contract=contract, state=state, prose=prose, evidence=guard.event_evidence)
            deterministic += evaluate_spatial(contract=spatial, scene=contract, state=state, prose=prose, evidence=guard.event_evidence)
            deterministic += evaluate_plan_coverage(coverage=coverage, plan=plan, scene=contract, prose=prose, evidence=guard.event_evidence)
            validation = combine_scene_validation(scene_id=plan.scene_id, attempt=attempt, deterministic=deterministic, semantic=semantic)
            _require(validation.model_dump(mode="json") == _read(root / f"{plan.scene_id}-{attempt}-validation.json"), "validation")
            if attempt < attempt_count:
                _require(validation.decision == "REWRITE", "rewrite justification")
                continue
            _require(validation.decision == "ACCEPT", "final acceptance")
            delta, after, artifact = freeze_scene(state, contract, prose, validation)
            _require(bundle == {"delta": delta.model_dump(mode="json"), "state_after": after.model_dump(mode="json"), "artifact": artifact.model_dump(mode="json")}, "accepted state bundle")
            previous = bundle
            state = after
            accepted_ids.append(plan.scene_id)
    result = _read(root / "result.json")
    _require(result["status"] == "ACCEPT" and result["accepted_scenes"] == accepted_ids, "result acceptance")
    _require(result["ledger"] == ledgers, "aggregate ledger")
    _require(result["automatic_retry"] is False and result["usage_complete"] is True, "retry/usage policy")
    _require(result["state_advanced_to_revision"] == state.revision and result["next_spine_beat"] == state.next_spine_beat, "result state")
    _require(canonical_sha256(state) == canonical_sha256(expected_final), "terminal state")
    _require(math.isclose(result["known_cost_usd"], sum(r["cost_usd"] for r in ledgers), abs_tol=1e-8), "cost sum")
    return {"status": "OFFLINE_REPLAY_PASS", "semantic_qualification": "REQUIRES_SEPARATE_EDITORIAL_REVIEW",
        "accepted_scenes": accepted_ids, "final_revision": state.revision, "next_spine_beat": state.next_spine_beat,
        "final_state_sha256": canonical_sha256(state), "provider_calls": len(ledgers),
        "rewrite_count": sum(1 for r in ledgers if r["stage"] == "writer" and r["attempt"] == 2),
        "cost_usd": result["known_cost_usd"], "total_tokens": sum(r["total_tokens"] for r in ledgers),
        "sum_call_latency_seconds": round(sum(r["latency_seconds"] for r in ledgers), 3),
        "files": {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(root.rglob("*.json"))}}
