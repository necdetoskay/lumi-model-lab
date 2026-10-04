from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spineforge_v21_bounded_quality import (
    build_bounded_quality_contract,
    build_scene_repair_cluster,
    next_quality_action,
    split_findings,
)


V20_REAUDIT = Path(
    "evidence/spineforge-v20-paid-writer/37203770084/"
    "age12-island-v20-story-quality-reaudit-c9-product.json"
)
V20_REPAIRED_STORY = Path(
    "evidence/spineforge-v20-paid-writer/37204419845/"
    "age12-island-v20-story-quality-repair-c10-product.json"
)


def _bridge_case():
    audit = json.loads(V20_REAUDIT.read_text(encoding="utf-8"))
    story = json.loads(V20_REPAIRED_STORY.read_text(encoding="utf-8"))
    return audit["findings"], story["repaired_segments"]


def test_v21_contract_is_bounded_and_non_looping():
    contract = build_bounded_quality_contract()
    assert contract["max_scene_repairs"] == 1
    assert contract["max_audits"] == 2
    assert contract["automatic_looping"] is False
    assert contract["minor_editorial_is_blocking"] is False
    assert contract["final_audit_may_request_another_repair"] is False
    assert contract["final_decisions"] == ["ACCEPT", "REJECT_NON_CONVERGENT"]


def test_v20_bridge_findings_split_blocking_from_editorial():
    findings, _ = _bridge_case()
    blocking, advisory = split_findings(findings)

    assert len(findings) == 13
    assert len(blocking) == 4
    assert len(advisory) == 9

    assert {row.family for row in blocking} == {
        "physical_feasibility",
        "causal_logic",
        "state_continuity",
        "spatial_consistency",
    }
    assert all(row.family != "language_naturalness" or not row.blocking for row in advisory)
    assert any(row.family == "language_naturalness" and row.severity == "moderate" for row in advisory)


def test_v20_bridge_findings_become_one_scene_repair_cluster():
    findings, segments = _bridge_case()
    result = build_scene_repair_cluster(
        findings=findings,
        story_segments=segments,
        context_paragraphs=0,
    )

    assert result["repair_required"] is True
    assert len(result["blocking_findings"]) == 4
    assert len(result["advisory_findings"]) == 9

    cluster = result["cluster"]
    assert cluster["repair_mode"] == "SCENE_REWRITE"
    assert cluster["paragraph_start"] == 72
    assert cluster["paragraph_end"] == 78
    assert cluster["start_span_id"] == "S159"
    assert cluster["end_span_id"] == "S177"
    assert cluster["entry_boundary_span_id"] == "S158"
    assert cluster["exit_boundary_span_id"] == "S178"
    assert 1 < cluster["span_count"] <= 40
    assert cluster["blocking_finding_indexes"] == [0, 1, 2, 4]


def test_minor_language_findings_never_trigger_repair():
    findings = [
        {
            "family": "language_naturalness",
            "severity": "minor",
            "repair_scope": "LOCAL_REPAIR",
            "span_ids": ["S010"],
            "exact_text": "slightly awkward",
            "reason": "Could be smoother.",
        }
    ]
    segments = [
        {
            "span_id": "S010",
            "paragraph_id": "P004",
            "paragraph_index": 4,
            "repaired_text": "slightly awkward",
        }
    ]

    result = build_scene_repair_cluster(
        findings=findings,
        story_segments=segments,
    )
    assert result["repair_required"] is False
    assert result["blocking_findings"] == []
    assert len(result["advisory_findings"]) == 1


def test_bounded_state_machine_accepts_clean_initial_audit():
    assert (
        next_quality_action(
            audit_phase="INITIAL",
            blocking_finding_count=0,
            repair_count=0,
        )
        == "ACCEPT"
    )


def test_bounded_state_machine_allows_exactly_one_scene_repair():
    assert (
        next_quality_action(
            audit_phase="INITIAL",
            blocking_finding_count=3,
            repair_count=0,
        )
        == "SCENE_REPAIR"
    )


def test_bounded_state_machine_rejects_nonconvergent_final_audit():
    assert (
        next_quality_action(
            audit_phase="FINAL",
            blocking_finding_count=1,
            repair_count=1,
        )
        == "REJECT_NON_CONVERGENT"
    )


def test_bounded_state_machine_accepts_clean_final_audit():
    assert (
        next_quality_action(
            audit_phase="FINAL",
            blocking_finding_count=0,
            repair_count=1,
        )
        == "ACCEPT"
    )


def test_final_audit_cannot_run_before_scene_repair():
    with pytest.raises(RuntimeError, match="exactly one"):
        next_quality_action(
            audit_phase="FINAL",
            blocking_finding_count=1,
            repair_count=0,
        )


def test_scene_rewrite_can_change_sentence_count_and_preserve_outside_text():
    from src.spineforge_v21_bounded_quality import apply_scene_rewrite

    findings, segments = _bridge_case()
    plan = build_scene_repair_cluster(
        findings=findings,
        story_segments=segments,
    )
    artifact = json.loads(V20_REPAIRED_STORY.read_text(encoding="utf-8"))
    source_story = Path(artifact["repaired_story_path"]).read_text(encoding="utf-8")
    if source_story.endswith("\n"):
        source_story = source_story[:-1]

    replacement = (
        "They reached the broken root bridge at a run. "
        "Arda anchored the route line to the living trunk, clipped himself in, "
        "and crossed while Nisa belayed from solid ground. "
        "When the bridge tore free and snagged the line, the falling roots pulled "
        "Arda toward the drop. He cut himself free from the loaded line, lunged "
        "for the ledge, and Nisa caught his wrist and hauled him up."
    )
    result = apply_scene_rewrite(
        source_story=source_story,
        story_segments=segments,
        cluster=plan["cluster"],
        replacement_scene=replacement,
    )

    assert result["source_span_count"] == 199
    assert result["repaired_span_count"] != 199
    assert result["outside_cluster_unchanged"] is True
    assert result["source_mutated"] is False
    assert result["lineage"]["fresh_segmentation_after_rewrite"] is True
    assert result["lineage"]["stable_span_identity_across_rewrite_required"] is False
    assert "He cut himself free from the loaded line" in result["repaired_story"]


def test_scene_repair_handoff_is_non_authorizing_and_bounded():
    from src.spineforge_v21_bounded_quality import build_scene_repair_handoff

    findings, segments = _bridge_case()
    artifact = json.loads(V20_REPAIRED_STORY.read_text(encoding="utf-8"))
    handoff = build_scene_repair_handoff(
        source_story_artifact_id=artifact["artifact_id"],
        source_story_sha256=artifact["repaired_story_text_sha256"],
        findings=findings,
        story_segments=segments,
        approved_spine_hash="frozen-spine-hash",
        canon_invariants=[
            "Arda performs the decisive cut.",
            "The cut must physically release Arda from the falling bridge event.",
        ],
    )

    assert handoff["status"] == "READY_NOT_AUTHORIZED"
    assert handoff["paid_execution_authorized"] is False
    assert len(handoff["blocking_findings"]) == 4
    assert len(handoff["editorial_advisories"]) == 9
    assert handoff["scene_cluster"]["start_span_id"] == "S159"
    assert handoff["scene_cluster"]["end_span_id"] == "S177"
    assert handoff["entry_boundary"]["span_id"] == "S158"
    assert handoff["exit_boundary"]["span_id"] == "S178"
    assert handoff["repair_policy"]["max_scene_repairs"] == 1
    assert handoff["repair_policy"]["same_sentence_count_required"] is False
    assert handoff["repair_policy"]["final_audit_may_request_another_repair"] is False
