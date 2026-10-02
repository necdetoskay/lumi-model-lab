from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_v20_paid_writer_once import execute_paid_writer_once


def test_paid_writer_wrapper_persists_story_and_result(tmp_path: Path):
    def fake_run(**kwargs):
        return {
            "schema": "spineforge-v20-writer-evidence.v1",
            "status": "writer_generated",
            "story": "Title\nA finished story.",
            "writer_usage_rollup": {"totals": {"api_calls": 1}},
            "automatic_retry_executed": False,
            "editor_authorized": False,
            "judge_authorized": False,
            "repair_authorized": False,
            "translation_authorized": False,
            "state_commit_authorized": False,
        }

    result, envelope = execute_paid_writer_once(
        api_key="fake",
        run_id="1001",
        output_root=tmp_path,
        run_fn=fake_run,
    )
    assert result["status"] == "writer_generated"
    assert envelope["result_status"] == "writer_generated"
    assert envelope["editor_executed"] is False
    assert envelope["translation_executed"] is False
    assert envelope["attempt_index"] == 3
    assert envelope["authorization_marker"] == "PAID-V20-AGE12-ISLAND-WRITER3"
    out = tmp_path / "1001"
    assert (out / "age12-island-v20-writer3-result.json").exists()
    assert (out / "age12-island-v20-writer3-story.txt").read_text().startswith("Title")


def test_paid_writer_wrapper_persists_unhandled_failure_without_story(tmp_path: Path):
    def boom(**kwargs):
        raise RuntimeError("synthetic writer failure")

    result, envelope = execute_paid_writer_once(
        api_key="fake",
        run_id="1002",
        output_root=tmp_path,
        run_fn=boom,
    )
    assert result["status"] == "unhandled_writer_runtime_failure"
    assert envelope["result_status"] == "unhandled_writer_runtime_failure"
    out = tmp_path / "1002"
    persisted = json.loads((out / "age12-island-v20-writer3-result.json").read_text())
    assert persisted["failure"]["type"] == "RuntimeError"
    assert not (out / "age12-island-v20-writer3-story.txt").exists()


# v20.4 Writer2 paid authorization trigger; no runtime behavior change.

# Paid Writer3 authorization trigger; legacy workflow selector remains WRITER2-only.


def test_paid_ci_dispatch_routes_story_audit_marker_away_from_writer():
    from src.spineforge_v20_paid_writer_once import paid_stage_from_commit_message

    message = (
        "paid story audit "
        "[PAID-V20-AGE12-ISLAND-STORY-AUDIT8] "
        "[PAID-V20-AGE12-ISLAND-WRITER2]"
    )
    assert paid_stage_from_commit_message(message) == "STORY_AUDIT"
    assert paid_stage_from_commit_message(
        "paid writer [PAID-V20-AGE12-ISLAND-WRITER2]"
    ) == "WRITER"


def test_paid_ci_dispatch_routes_story_local_repair_marker_away_from_writer_and_audit():
    from src.spineforge_v20_paid_writer_once import paid_stage_from_commit_message

    message = (
        "paid story local repair "
        "[PAID-V20-AGE12-ISLAND-STORY-LOCAL-REPAIR2] "
        "[PAID-V20-AGE12-ISLAND-WRITER2]"
    )
    assert paid_stage_from_commit_message(message) == "STORY_LOCAL_REPAIR"
