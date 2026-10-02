from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.spineforge_v20_story_local_repair_handoff import (
    DEFAULT_AUDIT_RESULT,
    DEFAULT_QUALIFICATION_REPORT,
    DEFAULT_WRITER_MANIFEST,
    build_story_local_repair_handoff,
)


def test_stage6_handoff_uses_qualified_immutable_stage5_product():
    handoff = build_story_local_repair_handoff()

    assert handoff["schema"] == "spineforge-v20-story-local-repair-handoff.v1"
    assert handoff["artifact_type"] == "IMMUTABLE_STAGE6_LOCAL_REPAIR_INPUT"
    assert handoff["stage"] == 6
    assert handoff["status"] == "READY_NOT_AUTHORIZED"
    assert handoff["immutable"] is True
    assert handoff["source_writer_artifact_id"] == (
        "writer-story:f1000691c85665ea6894e45e0318faaf5cdf7c1dac91fa453153e392af8192f3"
    )
    assert handoff["source_story_sha256"] == (
        "e08f686cc06c5c5a65a86f4bd8f5069aabd04e9a818b2abea5305887ec53cf0f"
    )
    assert handoff["source_audit_artifact_id"] == (
        "story-audit:8ed94a19c3b8637df0378dc3ec64eacef97096efaa3013f19231ee4cf73e4876"
    )
    assert handoff["source_audit_decision"] == "LOCAL_REPAIR_REQUIRED"
    assert handoff["source_audit_next_stage"] == "STORY_LOCAL_REPAIR"
    assert handoff["finding_count"] == 25
    assert handoff["allowed_edit_span_count"] == 25
    assert "S006" in handoff["allowed_edit_span_ids"]
    assert handoff["repair_model"] == "anthropic/claude-sonnet-5.5"
    assert handoff["repair_attempt_index"] == 1
    assert handoff["paid_execution_authorized"] is False
    assert handoff["automatic_retry_enabled"] is False
    assert handoff["repair_policy"]["patches_only"] is True
    assert handoff["repair_policy"]["all_findings_must_be_addressed"] is True
    assert handoff["repair_policy"]["unreferenced_span_edit_forbidden"] is True
    assert handoff["output_contract"]["schema"] == (
        "spineforge-v20-story-local-repair-artifact.v1"
    )
    assert handoff["output_contract"]["next_stage"] == "STORY_REAUDIT"
    assert handoff["next_stage_after_success"] == "STORY_REAUDIT"

    s006 = [
        row for row in handoff["target_segments"]
        if row["span_id"] == "S006"
    ]
    assert len(s006) == 1
    assert "arriving at his shoulder" in s006[0]["source_text"]


def test_stage6_handoff_is_deterministic():
    first = build_story_local_repair_handoff()
    second = build_story_local_repair_handoff()
    assert first == second
    assert first["artifact_id"] == (
        "story-local-repair-handoff:6f27c399c81ca3f8137005af4a36d4be6afd93881555e380e07b127eff5f98e1"
    )


def test_stage6_handoff_rejects_failed_qualification(tmp_path: Path):
    report = json.loads(DEFAULT_QUALIFICATION_REPORT.read_text(encoding="utf-8"))
    report["qualification_pass"] = False
    report["status"] = "FAIL_KNOWN_DEFECT_MISSED"
    bad = tmp_path / "qualification.json"
    bad.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(RuntimeError, match="requires qualified Stage 5 evidence"):
        build_story_local_repair_handoff(
            writer_manifest_path=DEFAULT_WRITER_MANIFEST,
            audit_result_path=DEFAULT_AUDIT_RESULT,
            qualification_report_path=bad,
        )


def test_stage6_handoff_rejects_non_local_finding(tmp_path: Path):
    result = json.loads(DEFAULT_AUDIT_RESULT.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(result)
    mutated["audit_artifact"]["findings"][0]["repair_scope"] = "STRUCTURAL_REPAIR"
    bad = tmp_path / "audit.json"
    bad.write_text(json.dumps(mutated), encoding="utf-8")

    with pytest.raises(RuntimeError, match="forbids non-local repair findings"):
        build_story_local_repair_handoff(
            writer_manifest_path=DEFAULT_WRITER_MANIFEST,
            audit_result_path=bad,
            qualification_report_path=DEFAULT_QUALIFICATION_REPORT,
        )
