from __future__ import annotations

from typing import Any, Callable
import hashlib
import math
from decimal import Decimal
from copy import deepcopy

from src.spineforge_v20_story_audit_artifact import _segment_story
from src.spineforge_v21_bounded_quality import (
    apply_scene_rewrite,
    build_scene_repair_handoff,
    next_quality_action,
    split_findings,
)


AuditFn = Callable[[dict[str, Any]], dict[str, Any]]
RepairFn = Callable[[dict[str, Any]], dict[str, Any]]

DEFAULT_STAGE_COST_LIMITS_USD = {
    "INITIAL_AUDIT": 0.040,
    "SCENE_REPAIR": 0.035,
    "FINAL_AUDIT": 0.025,
}


class QualityStop(RuntimeError):
    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status


def _usage(result: dict[str, Any], stage: str) -> dict[str, Any]:
    usage = result.get("usage")
    if not isinstance(usage, dict):
        raise RuntimeError("Exact provider usage is missing")
    for key in ("api_calls", "input_tokens", "output_tokens", "reasoning_tokens", "total_tokens"):
        if type(usage.get(key)) is not int or usage[key] < 0:
            raise RuntimeError(f"Invalid provider usage: {key}")
    if usage["api_calls"] != 1:
        raise RuntimeError("Each slot must make exactly one provider call")
    if usage["total_tokens"] != usage["input_tokens"] + usage["output_tokens"]:
        raise RuntimeError("Token accounting does not reconcile")
    for key in ("cost_usd", "latency_seconds"):
        value = usage.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise RuntimeError(f"Missing or invalid provider usage: {key}")
    return {"stage": stage, **usage}


def _rollup(calls: list[dict[str, Any]]) -> dict[str, Any]:
    known = [row["usage"] for row in calls if row.get("usage") is not None]
    complete = len(known) == len(calls)
    out = {"api_calls": len(calls), "accounting_complete": complete,
           "confirmed_cost_usd": float(sum((Decimal(str(r["cost_usd"])) for r in known), Decimal(0)))}
    for key in ("input_tokens", "output_tokens", "reasoning_tokens", "total_tokens", "cost_usd", "latency_seconds"):
        out[key] = float(sum((Decimal(str(r[key])) for r in known), Decimal(0))) if complete else None
        if complete and key.endswith("tokens"):
            out[key] = int(out[key])
    return out


def build_initial_audit_payload(
    *,
    source_story_artifact_id: str,
    source_story_sha256: str,
    source_story: str,
    story_segments: list[dict[str, Any]],
    approved_spine_hash: str,
    canon_invariants: list[str],
) -> dict[str, Any]:
    return {
        "schema": "spineforge-v21-initial-blocking-audit-input.v1",
        "audit_phase": "INITIAL",
        "source_story_artifact_id": source_story_artifact_id,
        "source_story_sha256": source_story_sha256,
        "approved_spine_hash": approved_spine_hash,
        "canon_invariants": canon_invariants,
        "full_story": source_story,
        "story_segments": story_segments,
        "routing_policy": {
            "blocking_only": True,
            "language_naturalness_advisory_only": True,
            "minor_findings_advisory_only": True,
        },
    }


def build_targeted_final_audit_payload(
    *,
    repaired_story_sha256: str,
    replacement_scene: str,
    scene_repair_handoff: dict[str, Any],
    approved_spine_hash: str,
    canon_invariants: list[str],
) -> dict[str, Any]:
    raw_segments = _segment_story(replacement_scene)
    scene_segments = [
        {
            "span_id": f"R{i:03d}",
            "text": row["text"],
            "paragraph_id": row["paragraph_id"],
            "paragraph_index": row["paragraph_index"],
        }
        for i, row in enumerate(raw_segments, 1)
    ]
    return {
        "schema": "spineforge-v21-targeted-final-audit-input.v1",
        "audit_phase": "FINAL",
        "repaired_story_sha256": repaired_story_sha256,
        "approved_spine_hash": approved_spine_hash,
        "canon_invariants": canon_invariants,
        "approved_constraints": scene_repair_handoff.get("approved_constraints"),
        "constraints_sha256": scene_repair_handoff.get("constraints_sha256"),
        "entry_boundary": scene_repair_handoff["entry_boundary"],
        "exit_boundary": scene_repair_handoff["exit_boundary"],
        "replacement_scene": replacement_scene,
        "replacement_scene_segments": scene_segments,
        "original_blocking_findings": scene_repair_handoff["blocking_findings"],
        "routing_policy": {
            "blocking_only": True,
            "scope": "REPAIRED_SCENE_PLUS_BOUNDARIES",
            "full_story_reaudit_forbidden": True,
            "language_naturalness_advisory_only": True,
            "minor_findings_advisory_only": True,
            "another_repair_forbidden": True,
        },
    }


def run_bounded_quality(
    *,
    source_story_artifact_id: str,
    source_story_sha256: str,
    source_story: str,
    story_segments: list[dict[str, Any]],
    approved_spine_hash: str,
    canon_invariants: list[str],
    initial_audit_fn: AuditFn,
    scene_repair_fn: RepairFn,
    final_audit_fn: AuditFn,
    stage_cost_limits_usd: dict[str, float] | None = None,
    approved_constraints: dict[str, Any] | None = None,
    reader_profile: dict[str, Any] | None = None,
    record_event: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    limits = dict(DEFAULT_STAGE_COST_LIMITS_USD)
    if stage_cost_limits_usd is not None:
        if set(stage_cost_limits_usd) != set(limits):
            raise RuntimeError("Incomplete stage cost policy")
        limits = dict(stage_cost_limits_usd)
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in limits.values()):
        raise RuntimeError("Invalid stage cost policy")
    if hashlib.sha256(source_story.encode()).hexdigest() != source_story_sha256:
        raise RuntimeError("Source story SHA mismatch before inference")
    story_segments = deepcopy(story_segments)
    # Exact frozen segmentation must cover the source even on the clean fast path.
    apply_scene_rewrite(source_story=source_story, story_segments=story_segments,
                        cluster={"start_span_id": story_segments[0]["span_id"],
                                 "end_span_id": story_segments[-1]["span_id"],
                                 "span_ids": [r["span_id"] for r in story_segments],
                                 "cluster_id": "SOURCE_VALIDATION"}, replacement_scene=source_story)
    if approved_constraints:
        from src.spineforge_v21_constraints import digest_json
        body = {k: v for k, v in approved_constraints.items() if k != "artifact_sha256"}
        if (digest_json(body) != approved_constraints["artifact_sha256"]
                or approved_constraints["approved_spine_hash"] != approved_spine_hash):
            raise RuntimeError("Approved constraints hash mismatch before inference")
    calls: list[dict[str, Any]] = []
    state: dict[str, Any] = {"initial_blocking": [], "initial_advisory": []}

    def invoke(stage, fn, payload):
        if len(calls) >= 3 or any(r["stage"] == stage for r in calls):
            raise QualityStop("REJECT_CALL_LIMIT", "Repeated stage forbidden")
        from src.spineforge_v21_constraints import digest_json
        row = {"stage": stage, "usage": None, "status": "STARTED",
               "input": deepcopy(payload), "input_sha256": digest_json(payload)}
        calls.append(row)
        # Persist BEFORE dispatch; ledger failure must never cause a retry.
        if record_event:
            record_event(deepcopy(row))
        try:
            raw = fn(deepcopy(payload))
        except Exception as exc:
            row["status"] = "FAILED"
            row["failure_type"] = type(exc).__name__
            row["provider_evidence"] = getattr(exc, "provider_evidence", None)
            reported = getattr(exc, "usage", None)
            if reported is not None:
                row["raw_usage"] = reported
                try:
                    row["usage"] = _usage({"usage": reported}, stage)
                except RuntimeError:
                    pass
            if record_event:
                record_event(deepcopy(row))
            raise QualityStop("REJECT_PROVIDER_FAILURE", f"{stage}: {type(exc).__name__}") from exc
        row["response"] = deepcopy(raw)
        row["response_sha256"] = digest_json(raw)
        row["raw_usage"] = raw.get("usage") if isinstance(raw, dict) else None
        try:
            row["usage"] = _usage(raw, stage)
        except (RuntimeError, AttributeError) as exc:
            row["status"] = "INVALID_USAGE"
            if record_event:
                record_event(deepcopy(row))
            raise QualityStop("REJECT_USAGE_ACCOUNTING", str(exc)) from exc
        row["status"] = "COMPLETED"
        if record_event:
            record_event(deepcopy(row))
        if Decimal(str(row["usage"]["cost_usd"])) > Decimal(str(limits[stage])):
            raise QualityStop("REJECT_COST_CEILING", stage)
        return raw

    def audit_findings(raw):
        try:
            return split_findings(raw["findings"])
        except (KeyError, TypeError, RuntimeError) as exc:
            raise QualityStop("REJECT_INVALID_RESPONSE", str(exc)) from exc

    try:
        initial_payload = build_initial_audit_payload(
            source_story_artifact_id=source_story_artifact_id,
            source_story_sha256=source_story_sha256, source_story=source_story,
            story_segments=story_segments, approved_spine_hash=approved_spine_hash,
            canon_invariants=canon_invariants)
        initial_payload["approved_constraints"] = approved_constraints
        initial_payload["reader_profile"] = reader_profile
        initial_raw = invoke("INITIAL_AUDIT", initial_audit_fn, initial_payload)
        blocking, advisory = audit_findings(initial_raw)
        state.update(initial_blocking=blocking, initial_advisory=advisory)
        if not blocking:
            return _result(status="ACCEPT", calls=calls, **state,
                           accepted_story=source_story, accepted_story_sha256=source_story_sha256)
        try:
            handoff = build_scene_repair_handoff(
                source_story_artifact_id=source_story_artifact_id,
                source_story_sha256=source_story_sha256, source_story=source_story,
                findings=initial_raw["findings"], story_segments=story_segments,
                approved_spine_hash=approved_spine_hash, canon_invariants=canon_invariants,
                approved_constraints=approved_constraints)
        except RuntimeError as exc:
            raise QualityStop("REJECT_UNBOUNDED_REPAIR_SCOPE", str(exc)) from exc
        handoff["reader_profile"] = reader_profile
        state["repair_count"] = 1
        repair_raw = invoke("SCENE_REPAIR", scene_repair_fn, handoff)
        replacement = repair_raw.get("replacement_scene")
        resolved = repair_raw.get("resolved_blocking_finding_indexes")
        expected = {r["index"] for r in handoff["blocking_findings"]}
        if (not isinstance(replacement, str) or not replacement.strip()
                or not isinstance(resolved, list) or any(type(i) is not int for i in resolved)
                or len(resolved) != len(set(resolved)) or set(resolved) != expected):
            raise QualityStop("REJECT_INVALID_REPAIR_CLAIM", "Repair must claim exactly the blocking set")
        replacement = replacement.strip()
        rewrite = apply_scene_rewrite(source_story=source_story, story_segments=story_segments,
                                      cluster=handoff["scene_cluster"], replacement_scene=replacement)
        state["rewrite"] = rewrite
        final_payload = build_targeted_final_audit_payload(
            repaired_story_sha256=rewrite["repaired_story_sha256"], replacement_scene=replacement,
            scene_repair_handoff=handoff, approved_spine_hash=approved_spine_hash,
            canon_invariants=canon_invariants)
        final_payload["reader_profile"] = reader_profile
        state.update(final_audit_executed=True, final_audit_scope="REPAIRED_SCENE_PLUS_BOUNDARIES")
        final_raw = invoke("FINAL_AUDIT", final_audit_fn, final_payload)
        blocking, advisory = audit_findings(final_raw)
        state.update(final_blocking=blocking, final_advisory=advisory)
        status = "REJECT_NON_CONVERGENT" if blocking else "ACCEPT"
        return _result(status=status, calls=calls, **state,
                       accepted_story=rewrite["repaired_story"] if status == "ACCEPT" else None,
                       accepted_story_sha256=rewrite["repaired_story_sha256"] if status == "ACCEPT" else None)
    except QualityStop as exc:
        return _result(status=exc.status, calls=calls, **state, failure_reason=str(exc))


def _result(
    *,
    status: str,
    calls: list[dict[str, Any]],
    initial_blocking: list[Any],
    initial_advisory: list[Any],
    final_blocking: list[Any] | None = None,
    final_advisory: list[Any] | None = None,
    accepted_story: str | None = None,
    accepted_story_sha256: str | None = None,
    repair_count: int = 0,
    final_audit_executed: bool = False,
    rewrite: dict[str, Any] | None = None,
    final_audit_scope: str | None = None,
    failure_reason: str | None = None,
) -> dict[str, Any]:
    rollup = _rollup(calls)
    if rollup["api_calls"] > 3:
        raise RuntimeError("v21 quality runtime exceeded three model calls.")
    return {
        "schema": "spineforge-v21-bounded-quality-result.v1",
        "status": status,
        "quality_model_calls": rollup["api_calls"],
        "quality_usage_rollup": rollup,
        "quality_calls": calls,
        "initial_blocking_count": len(initial_blocking),
        "initial_advisory_count": len(initial_advisory),
        "final_blocking_count": len(final_blocking or []),
        "final_advisory_count": len(final_advisory or []),
        "repair_count": repair_count,
        "final_audit_executed": final_audit_executed,
        "final_audit_scope": final_audit_scope,
        "accepted_story": accepted_story,
        "accepted_story_sha256": accepted_story_sha256,
        "rewrite": rewrite,
        "failure_reason": failure_reason,
        "automatic_retry_executed": False,
        "automatic_second_repair_executed": False,
        "translation_executed": False,
        "state_commit_executed": False,
    }
