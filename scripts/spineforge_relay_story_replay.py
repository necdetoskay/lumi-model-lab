"""Offline replay of saved Relay calls and state transitions. No inference.

Mechanical evidence consistency is distinct from editorial qualification.
A consistent ACCEPT bundle can still contain a semantic continuity defect.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from src.spineforge_relay_v1_runner import build_chain, runner_request_for, coverage_for, prepare
from src.spineforge_relay_v1_coverage import PlanCoverageContractV1, PlanObligationV1, PredicateOrderV1, compile_plan_coverage, evaluate_plan_coverage
from src.generate import _extract_text_content
from src.spineforge_relay_v1_source_archives import verify_historical_source
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


def verify_story(root, fixture_path):
    """Reproduce accepted scenes from complete saved requests/responses/ledgers."""
    schema = _read(fixture_path)["schema"]
    if schema == "spineforge-relay.repeatability-fixture.v5":
        from src import spineforge_span_story_runner as engine
    elif schema == "spineforge-relay.repeatability-fixture.v4":
        from src import spineforge_joint_story_runner as engine
    elif schema == "spineforge-relay.repeatability-fixture.v3":
        from src import spineforge_spatial_story_runner as engine
    else:
        from src import spineforge_relay_v1_runner as engine
    fixture, _intent, route, start, rows, expected_final = engine.build_chain(Path(fixture_path))
    request_factory = engine.runner_request_for
    previous = None
    root = Path(root)
    preflight = _read(root / "preflight.json")
    _require(preflight == engine.prepare(Path(fixture_path)), "frozen generic preflight")
    result = _read(root / "result.json")
    rejected_scene = None
    reference_failure = False
    state = start
    ledgers = []
    accepted_ids = []
    for plan, _precompiled, _expected_before in rows:
        if rejected_scene is not None:
            break
        contract = compile_scene_contract(state, plan, route)
        coverage = PlanCoverageContractV1.model_validate(_read(root / f"{plan.scene_id}-coverage-contract.json"))
        _require(coverage == engine.coverage_for(fixture, plan, contract), "frozen plan coverage")
        spatial = None
        if schema in {"spineforge-relay.repeatability-fixture.v3", "spineforge-relay.repeatability-fixture.v4", "spineforge-relay.repeatability-fixture.v5"}:
            if schema.endswith((".v4",".v5")):
                from src.spineforge_joint_spatial import JointSpatialContractV1 as SpatialContractV1, evaluate_joint_spatial as evaluate_spatial
            else:
                from src.spineforge_relay_v1_spatial import SpatialContractV1, evaluate_spatial
            spatial = SpatialContractV1.model_validate(_read(root / f"{plan.scene_id}-spatial-contract.json"))
            _require(spatial == engine.spatial_for(fixture, plan, contract, state), "frozen spatial contract")
        rewrite = None
        bundle_path = root / f"{plan.scene_id}-accepted.json"
        bundle = _read(bundle_path) if bundle_path.exists() else None
        attempt_count = bundle["artifact"]["attempt"] if bundle else 2
        if bundle is None and schema.endswith(".v5") and result["reason"] == "FAILED_CLOSED_NO_RETRY":
            complete = [n for n in (1,2) if (root / f"{plan.scene_id}-{n}-guard-response.json").exists()]
            _require(bool(complete), "complete guard response for reference failure")
            attempt_count = max(complete)
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
                if spatial is not None:
                    _require(payload["spatial_contract"] == spatial.model_dump(mode="json"), "request spatial contract")
                _require(payload["plan_coverage_contract"] == coverage.model_dump(mode="json"), "request goal coverage")
                _require(payload["relevant_character_canon"] == fixture["relevant_character_canon"], "canon")
                _require(payload["prop_authorization_policy"] == fixture["prop_authorization_policy"], "prop policy")
                if stage == "writer":
                    _require(payload["attempt"] == attempt and payload["rewrite"] == rewrite, "bounded rewrite payload")
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
                _require(all(isinstance(response['usage'][k], int) and not isinstance(response['usage'][k], bool) for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')), 'integer token usage')
                _require(response['usage']['total_tokens'] == response['usage']['prompt_tokens'] + response['usage']['completion_tokens'], 'token sum')
                _require(ledger['cost_usd'] <= preflight['max_call_cost_usd'], 'per-call cost ceiling')
                if stage == "guard":
                    _require(payload["candidate_prose"] == prose, "guard candidate")
                    if schema.endswith(".v5"):
                        from src.spineforge_source_spans import source_table
                        _require(payload["source_span_table"] == source_table(prose), "trusted source table")
                    _require(payload["deterministic_findings"] == [f.model_dump(mode="json") for f in deterministic], "guard deterministic input")
                ledgers.append(ledger)
            guard_raw = json.loads(_read(root / f"{plan.scene_id}-{attempt}-guard-text.json")["text"])
            if schema.endswith(".v5"):
                from src.spineforge_source_spans import resolve_span_guard
                try:
                    guard = resolve_span_guard(guard_raw,prose)
                except ValueError as exc:
                    _require(bundle is None and attempt == attempt_count and result["reason"] == "FAILED_CLOSED_NO_RETRY" and result.get("failure_type") == type(exc).__name__, "recorded source reference failure")
                    rejected_scene = plan.scene_id
                    reference_failure = True
                    break
                _require(guard.model_dump(mode="json") == _read(root / f"{plan.scene_id}-{attempt}-resolved-guard.json"), "resolved guard evidence")
            else:
                guard = StructuredGuardV1.model_validate(guard_raw)
            semantic = normalize_semantic_guard(raw=guard.residual.model_dump(mode="json"), prose=prose)
            deterministic += evaluate_events(contract=contract, state=state, prose=prose, evidence=guard.event_evidence)
            if spatial is not None:
                deterministic += evaluate_spatial(contract=spatial, scene=contract, state=state, prose=prose, evidence=guard.event_evidence)
            deterministic += evaluate_plan_coverage(coverage=coverage, plan=plan, scene=contract, prose=prose, evidence=guard.event_evidence)
            validation = combine_scene_validation(scene_id=plan.scene_id, attempt=attempt, deterministic=deterministic, semantic=semantic)
            _require(validation.model_dump(mode="json") == _read(root / f"{plan.scene_id}-{attempt}-validation.json"), "validation")
            if attempt < attempt_count:
                _require(validation.decision == "REWRITE", "rewrite justification")
                rewrite = {"candidate_prose": prose, "validation": validation.model_dump(mode="json")}
                continue
            if bundle is None:
                _require(validation.decision == "REJECT_NON_CONVERGENT" and attempt == 2, "bounded terminal rejection")
                rejected_scene = plan.scene_id
                break
            _require(validation.decision == "ACCEPT", "final acceptance")
            delta, after, artifact = freeze_scene(state, contract, prose, validation)
            _require(bundle == {"delta": delta.model_dump(mode="json"), "state_after": after.model_dump(mode="json"), "artifact": artifact.model_dump(mode="json")}, "accepted state bundle")
            previous = {**bundle, "prose": prose}
            state = after
            accepted_ids.append(plan.scene_id)
    expected_status = "REJECT_NON_CONVERGENT" if rejected_scene else "ACCEPT"
    _require(result["status"] == expected_status and result["accepted_scenes"] == accepted_ids, "result decision")
    if rejected_scene:
        _require(result["reason"] == ("FAILED_CLOSED_NO_RETRY" if reference_failure else "SCENE_REJECT_NON_CONVERGENT:" + rejected_scene), "rejection reason")
        _require(not any((root / f"{p.scene_id}-accepted.json").exists() for p, _, _ in rows if p.scene_id not in accepted_ids), "no frozen rejected/later scene")
    _require(result["ledger"] == ledgers, "aggregate ledger")
    _require(result["automatic_retry"] is False and result["usage_complete"] is True, "retry/usage policy")
    _require(result["state_advanced_to_revision"] == state.revision and result["next_spine_beat"] == state.next_spine_beat, "result state")
    if not rejected_scene:
        _require(canonical_sha256(state) == canonical_sha256(expected_final), "terminal state")
    _require(len(list(root.glob("*-ledger.json"))) == len(ledgers), "no additional calls")
    _require(math.isclose(result["known_cost_usd"], sum(r["cost_usd"] for r in ledgers), abs_tol=1e-8), "cost sum")
    _require(len({_read(root / f"{r['scene_id']}-{r['attempt']}-{r['stage']}-response.json")["id"] for r in ledgers}) == len(ledgers), "distinct provider IDs")
    _require(len(ledgers) <= preflight["max_calls"] and result["known_cost_usd"] <= preflight["max_story_cost_usd"], "paid ceilings")
    return {"status": "OFFLINE_REPLAY_PASS", "semantic_qualification": "REQUIRES_SEPARATE_EDITORIAL_REVIEW",
        "recorded_decision": expected_status, "rejected_scene": rejected_scene,
        "accepted_scenes": accepted_ids, "final_revision": state.revision, "next_spine_beat": state.next_spine_beat,
        "final_state_sha256": canonical_sha256(state), "provider_calls": len(ledgers),
        "rewrite_count": sum(1 for r in ledgers if r["stage"] == "writer" and r["attempt"] == 2),
        "cost_usd": result["known_cost_usd"], "total_tokens": sum(r["total_tokens"] for r in ledgers),
        "sum_call_latency_seconds": round(sum(r["latency_seconds"] for r in ledgers), 3),
        "files": {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(root.rglob("*.json")) if p.name != "offline-replay.json"}}
