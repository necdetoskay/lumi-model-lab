from __future__ import annotations

from typing import Any, Callable

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


def _usage(result: dict[str, Any], stage: str) -> dict[str, Any]:
    usage = dict(result.get("usage") or {})
    return {
        "stage": stage,
        "api_calls": int(usage.get("api_calls") or 1),
        "input_tokens": int(usage.get("input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
        "reasoning_tokens": int(usage.get("reasoning_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
        "cost_usd": float(usage.get("cost_usd") or 0.0),
        "latency_seconds": float(usage.get("latency_seconds") or 0.0),
    }


def _rollup(calls: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "api_calls": sum(row["api_calls"] for row in calls),
        "input_tokens": sum(row["input_tokens"] for row in calls),
        "output_tokens": sum(row["output_tokens"] for row in calls),
        "reasoning_tokens": sum(row["reasoning_tokens"] for row in calls),
        "total_tokens": sum(row["total_tokens"] for row in calls),
        "cost_usd": round(sum(row["cost_usd"] for row in calls), 9),
        "latency_seconds": round(sum(row["latency_seconds"] for row in calls), 3),
    }


def _stage_cost_ok(
    *,
    usage: dict[str, Any],
    stage: str,
    limits: dict[str, float],
) -> bool:
    return usage["cost_usd"] <= float(limits[stage])


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
) -> dict[str, Any]:
    limits = dict(DEFAULT_STAGE_COST_LIMITS_USD)
    if stage_cost_limits_usd:
        limits.update(stage_cost_limits_usd)

    calls: list[dict[str, Any]] = []
    initial_payload = build_initial_audit_payload(
        source_story_artifact_id=source_story_artifact_id,
        source_story_sha256=source_story_sha256,
        source_story=source_story,
        story_segments=story_segments,
        approved_spine_hash=approved_spine_hash,
        canon_invariants=canon_invariants,
    )
    initial_raw = initial_audit_fn(initial_payload)
    initial_usage = _usage(initial_raw, "INITIAL_AUDIT")
    calls.append(initial_usage)

    initial_blocking, initial_advisory = split_findings(
        initial_raw.get("findings") or []
    )
    if not _stage_cost_ok(
        usage=initial_usage, stage="INITIAL_AUDIT", limits=limits
    ):
        return _result(
            status="REJECT_COST_CEILING",
            calls=calls,
            initial_blocking=initial_blocking,
            initial_advisory=initial_advisory,
        )

    initial_action = next_quality_action(
        audit_phase="INITIAL",
        blocking_finding_count=len(initial_blocking),
        repair_count=0,
    )
    if initial_action == "ACCEPT":
        return _result(
            status="ACCEPT",
            calls=calls,
            initial_blocking=initial_blocking,
            initial_advisory=initial_advisory,
            accepted_story=source_story,
            accepted_story_sha256=source_story_sha256,
            repair_count=0,
            final_audit_executed=False,
        )

    try:
        repair_handoff = build_scene_repair_handoff(
            source_story_artifact_id=source_story_artifact_id,
            source_story_sha256=source_story_sha256,
            findings=initial_raw.get("findings") or [],
            story_segments=story_segments,
            approved_spine_hash=approved_spine_hash,
            canon_invariants=canon_invariants,
        )
    except RuntimeError as exc:
        return _result(
            status="REJECT_UNBOUNDED_REPAIR_SCOPE",
            calls=calls,
            initial_blocking=initial_blocking,
            initial_advisory=initial_advisory,
            failure_reason=str(exc),
            repair_count=0,
            final_audit_executed=False,
        )

    repair_raw = scene_repair_fn(repair_handoff)
    repair_usage = _usage(repair_raw, "SCENE_REPAIR")
    calls.append(repair_usage)
    if not _stage_cost_ok(
        usage=repair_usage, stage="SCENE_REPAIR", limits=limits
    ):
        return _result(
            status="REJECT_COST_CEILING",
            calls=calls,
            initial_blocking=initial_blocking,
            initial_advisory=initial_advisory,
            repair_count=1,
            final_audit_executed=False,
        )

    replacement_scene = str(repair_raw.get("replacement_scene") or "").strip()
    if not replacement_scene:
        raise RuntimeError("Scene repair returned no replacement_scene.")

    expected_indexes = {
        int(row["index"]) for row in repair_handoff["blocking_findings"]
    }
    resolved_indexes = {
        int(x) for x in (repair_raw.get("resolved_blocking_finding_indexes") or [])
    }
    if resolved_indexes != expected_indexes:
        raise RuntimeError(
            "Scene repair did not resolve exactly the blocking finding set."
        )

    rewrite = apply_scene_rewrite(
        source_story=source_story,
        story_segments=story_segments,
        cluster=repair_handoff["scene_cluster"],
        replacement_scene=replacement_scene,
    )
    final_payload = build_targeted_final_audit_payload(
        repaired_story_sha256=rewrite["repaired_story_sha256"],
        replacement_scene=replacement_scene,
        scene_repair_handoff=repair_handoff,
        approved_spine_hash=approved_spine_hash,
        canon_invariants=canon_invariants,
    )
    final_raw = final_audit_fn(final_payload)
    final_usage = _usage(final_raw, "FINAL_AUDIT")
    calls.append(final_usage)

    final_blocking, final_advisory = split_findings(
        final_raw.get("findings") or []
    )
    if not _stage_cost_ok(
        usage=final_usage, stage="FINAL_AUDIT", limits=limits
    ):
        return _result(
            status="REJECT_COST_CEILING",
            calls=calls,
            initial_blocking=initial_blocking,
            initial_advisory=initial_advisory,
            final_blocking=final_blocking,
            final_advisory=final_advisory,
            repair_count=1,
            final_audit_executed=True,
            rewrite=rewrite,
        )

    final_action = next_quality_action(
        audit_phase="FINAL",
        blocking_finding_count=len(final_blocking),
        repair_count=1,
    )
    status = "ACCEPT" if final_action == "ACCEPT" else "REJECT_NON_CONVERGENT"
    return _result(
        status=status,
        calls=calls,
        initial_blocking=initial_blocking,
        initial_advisory=initial_advisory,
        final_blocking=final_blocking,
        final_advisory=final_advisory,
        accepted_story=rewrite["repaired_story"] if status == "ACCEPT" else None,
        accepted_story_sha256=(
            rewrite["repaired_story_sha256"] if status == "ACCEPT" else None
        ),
        repair_count=1,
        final_audit_executed=True,
        rewrite=rewrite,
        final_audit_scope=final_payload["routing_policy"]["scope"],
    )


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
