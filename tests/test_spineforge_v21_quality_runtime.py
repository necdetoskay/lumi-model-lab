from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_v21_quality_runtime import run_bounded_quality


STORY_ARTIFACT = Path(
    "evidence/spineforge-v20-paid-writer/37204419845/"
    "age12-island-v20-story-quality-repair-c10-product.json"
)
AUDIT_ARTIFACT = Path(
    "evidence/spineforge-v20-paid-writer/37203770084/"
    "age12-island-v20-story-quality-reaudit-c9-product.json"
)


def _source():
    artifact = json.loads(STORY_ARTIFACT.read_text(encoding="utf-8"))
    story = Path(artifact["repaired_story_path"]).read_text(encoding="utf-8")
    if story.endswith("\n"):
        story = story[:-1]
    return artifact, story


def _usage(cost=0.0):
    return {
        "api_calls": 1,
        "input_tokens": 100,
        "output_tokens": 20,
        "reasoning_tokens": 0,
        "total_tokens": 120,
        "cost_usd": cost,
        "latency_seconds": 1.0,
    }


def test_clean_initial_audit_accepts_after_one_call():
    artifact, story = _source()
    repair_called = False
    final_called = False

    def audit(_payload):
        return {"findings": [], "usage": _usage(0.01)}

    def repair(_payload):
        nonlocal repair_called
        repair_called = True
        raise AssertionError("repair must not run")

    def final(_payload):
        nonlocal final_called
        final_called = True
        raise AssertionError("final audit must not run")

    result = run_bounded_quality(
        source_story_artifact_id=artifact["artifact_id"],
        source_story_sha256=artifact["repaired_story_text_sha256"],
        source_story=story,
        story_segments=artifact["repaired_segments"],
        approved_spine_hash="spine",
        canon_invariants=[],
        initial_audit_fn=audit,
        scene_repair_fn=repair,
        final_audit_fn=final,
    )

    assert result["status"] == "ACCEPT"
    assert result["quality_model_calls"] == 1
    assert result["repair_count"] == 0
    assert result["final_audit_executed"] is False
    assert repair_called is False
    assert final_called is False


def test_bridge_case_repair_then_targeted_final_accept_uses_three_calls():
    artifact, story = _source()
    findings = json.loads(AUDIT_ARTIFACT.read_text(encoding="utf-8"))["findings"]
    seen_final = {}

    def audit(_payload):
        return {"findings": findings, "usage": _usage(0.03)}

    def repair(handoff):
        assert handoff["scene_cluster"]["start_span_id"] == "S159"
        assert handoff["scene_cluster"]["end_span_id"] == "S177"
        return {
            "replacement_scene": (
                "They reached the broken bridge at a run. "
                "Arda anchored the route line to the living trunk and clipped himself in. "
                "Nisa crossed first and belayed him from solid ground. "
                "When the bridge tore loose, a falling root snagged the line and pulled Arda toward the drop. "
                "Arda cut the loaded line from his harness, lunged for the ledge, and Nisa caught his wrist. "
                "Together they hauled him onto solid root."
            ),
            "usage": _usage(0.02),
        }

    def final(payload):
        seen_final.update(payload)
        return {"findings": [], "usage": _usage(0.015)}

    result = run_bounded_quality(
        source_story_artifact_id=artifact["artifact_id"],
        source_story_sha256=artifact["repaired_story_text_sha256"],
        source_story=story,
        story_segments=artifact["repaired_segments"],
        approved_spine_hash="spine",
        canon_invariants=["Arda performs the decisive cut."],
        initial_audit_fn=audit,
        scene_repair_fn=repair,
        final_audit_fn=final,
    )

    assert result["status"] == "ACCEPT"
    assert result["quality_model_calls"] == 3
    assert result["quality_usage_rollup"]["cost_usd"] == 0.065
    assert result["repair_count"] == 1
    assert result["final_audit_executed"] is True
    assert result["final_audit_scope"] == "REPAIRED_SCENE_PLUS_BOUNDARIES"
    assert "full_story" not in seen_final
    assert seen_final["routing_policy"]["full_story_reaudit_forbidden"] is True
    assert len(seen_final["replacement_scene"]) < len(story)
    assert result["rewrite"]["outside_cluster_unchanged"] is True


def test_final_blocking_finding_rejects_without_second_repair():
    artifact, story = _source()
    findings = json.loads(AUDIT_ARTIFACT.read_text(encoding="utf-8"))["findings"]
    repair_calls = 0

    def audit(_payload):
        return {"findings": findings, "usage": _usage(0.02)}

    def repair(_payload):
        nonlocal repair_calls
        repair_calls += 1
        return {
            "replacement_scene": (
                "They reached the broken bridge. Arda crossed it. "
                "The line pulled him toward the drop. He cut himself free. "
                "Nisa caught him."
            ),
            "usage": _usage(0.01),
        }

    def final(_payload):
        return {
            "findings": [
                {
                    "family": "causal_logic",
                    "severity": "moderate",
                    "repair_scope": "LOCAL_REPAIR",
                    "span_ids": ["R003"],
                    "exact_text": "The line pulled him toward the drop.",
                    "reason": "The line state still does not establish this force.",
                }
            ],
            "usage": _usage(0.01),
        }

    result = run_bounded_quality(
        source_story_artifact_id=artifact["artifact_id"],
        source_story_sha256=artifact["repaired_story_text_sha256"],
        source_story=story,
        story_segments=artifact["repaired_segments"],
        approved_spine_hash="spine",
        canon_invariants=[],
        initial_audit_fn=audit,
        scene_repair_fn=repair,
        final_audit_fn=final,
    )

    assert result["status"] == "REJECT_NON_CONVERGENT"
    assert result["quality_model_calls"] == 3
    assert result["repair_count"] == 1
    assert repair_calls == 1
    assert result["automatic_second_repair_executed"] is False


def test_language_naturalness_is_advisory_even_when_moderate():
    artifact, story = _source()

    def audit(_payload):
        return {
            "findings": [
                {
                    "family": "language_naturalness",
                    "severity": "moderate",
                    "repair_scope": "LOCAL_REPAIR",
                    "span_ids": ["S001"],
                    "exact_text": "x",
                    "reason": "awkward but understandable",
                }
            ],
            "usage": _usage(0.01),
        }

    result = run_bounded_quality(
        source_story_artifact_id=artifact["artifact_id"],
        source_story_sha256=artifact["repaired_story_text_sha256"],
        source_story=story,
        story_segments=artifact["repaired_segments"],
        approved_spine_hash="spine",
        canon_invariants=[],
        initial_audit_fn=audit,
        scene_repair_fn=lambda _: (_ for _ in ()).throw(AssertionError()),
        final_audit_fn=lambda _: (_ for _ in ()).throw(AssertionError()),
    )

    assert result["status"] == "ACCEPT"
    assert result["quality_model_calls"] == 1
    assert result["initial_blocking_count"] == 0
    assert result["initial_advisory_count"] == 1


def test_age_suitability_moderate_is_blocking():
    artifact, story = _source()
    repair_seen = False

    def audit(_payload):
        return {
            "findings": [
                {
                    "family": "age_suitability",
                    "severity": "moderate",
                    "repair_scope": "LOCAL_REPAIR",
                    "span_ids": ["S159"],
                    "exact_text": "x",
                    "reason": "Materially unsuitable for the target age.",
                }
            ],
            "usage": _usage(0.01),
        }

    def repair(_payload):
        nonlocal repair_seen
        repair_seen = True
        return {
            "replacement_scene": "They reached the bridge and safely turned back.",
            "usage": _usage(0.01),
        }

    def final(_payload):
        return {"findings": [], "usage": _usage(0.01)}

    result = run_bounded_quality(
        source_story_artifact_id=artifact["artifact_id"],
        source_story_sha256=artifact["repaired_story_text_sha256"],
        source_story=story,
        story_segments=artifact["repaired_segments"],
        approved_spine_hash="spine",
        canon_invariants=[],
        initial_audit_fn=audit,
        scene_repair_fn=repair,
        final_audit_fn=final,
    )

    assert repair_seen is True
    assert result["repair_count"] == 1


def test_stage_cost_ceiling_stops_before_more_calls():
    artifact, story = _source()
    findings = json.loads(AUDIT_ARTIFACT.read_text(encoding="utf-8"))["findings"]
    repair_called = False

    def audit(_payload):
        return {"findings": findings, "usage": _usage(0.041)}

    def repair(_payload):
        nonlocal repair_called
        repair_called = True
        raise AssertionError("repair must not run after cost ceiling")

    result = run_bounded_quality(
        source_story_artifact_id=artifact["artifact_id"],
        source_story_sha256=artifact["repaired_story_text_sha256"],
        source_story=story,
        story_segments=artifact["repaired_segments"],
        approved_spine_hash="spine",
        canon_invariants=[],
        initial_audit_fn=audit,
        scene_repair_fn=repair,
        final_audit_fn=lambda _: (_ for _ in ()).throw(AssertionError()),
    )

    assert result["status"] == "REJECT_COST_CEILING"
    assert result["quality_model_calls"] == 1
    assert repair_called is False
