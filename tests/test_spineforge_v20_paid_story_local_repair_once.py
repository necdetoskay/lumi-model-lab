from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spineforge_v20_paid_story_local_repair_once import (
    AUTHORIZATION_MARKER,
    HANDOFF_PATH,
    execute_paid_story_local_repair_once,
)


PROFILE = Path(
    "data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json"
)


def test_paid_stage6_wrapper_rejects_unapproved_current_freeze(tmp_path: Path):
    called = False

    def fake_run(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("paid inference must not execute")

    with pytest.raises(RuntimeError, match="not authorized"):
        execute_paid_story_local_repair_once(
            api_key="not-used",
            run_id="unit",
            output_root=tmp_path,
            run_fn=fake_run,
        )
    assert called is False


def test_paid_stage6_wrapper_executes_exactly_one_authorized_repair(tmp_path: Path):
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    profile["stage6_story_local_repair"]["status"] = "PAID_EXECUTION_AUTHORIZED"
    profile["stage6_story_local_repair"]["paid_execution_authorized"] = True
    profile["stage6_story_local_repair"]["authorization_consumed"] = False
    profile["stage6_story_local_repair"]["authorization_marker"] = AUTHORIZATION_MARKER
    temp_profile = tmp_path / "profile.json"
    temp_profile.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    calls = 0
    handoff = json.loads(HANDOFF_PATH.read_text(encoding="utf-8"))
    repaired_story = "Synthetic repaired story.\n"

    def fake_run(**kwargs):
        nonlocal calls
        calls += 1
        assert kwargs["handoff"]["artifact_id"] == handoff["artifact_id"]
        assert "PATCHES ONLY" in kwargs["system_prompt"]
        return {
            "schema": "spineforge-v20-story-local-repair-execution.v1",
            "status": "repair_generated",
            "source_writer_artifact_id": handoff["source_writer_artifact_id"],
            "source_story_sha256": handoff["source_story_sha256"],
            "source_audit_artifact_id": handoff["source_audit_artifact_id"],
            "repair_model": handoff["repair_model"],
            "patches": [],
            "changed_span_ids": [],
            "patch_count": 0,
            "repaired_story": repaired_story,
            "repaired_story_sha256": "synthetic",
            "source_story_mutated": False,
            "all_findings_addressed": True,
            "changed_spans_subset_of_allowed": True,
            "repair_usage_rollup": {
                "totals": {
                    "api_calls": 1,
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "reasoning_tokens": 10,
                    "total_tokens": 150,
                    "cost_usd": 0.01,
                    "latency_seconds": 1.0,
                }
            },
            "incremental_cost_usd": 0.01,
            "incremental_latency_seconds": 1.0,
            "automatic_retry_executed": False,
            "reaudit_executed": False,
            "translation_executed": False,
            "state_commit_executed": False,
            "next_stage": "STORY_REAUDIT",
            "transport_failures": [],
            "request": {},
        }

    result, envelope = execute_paid_story_local_repair_once(
        api_key="not-used",
        run_id="123",
        output_root=tmp_path,
        run_fn=fake_run,
        profile_path=temp_profile,
    )

    assert calls == 1
    assert result["status"] == "repair_generated"
    assert envelope["stage"] == 6
    assert envelope["attempt_index"] == 1
    assert envelope["authorization_marker"] == AUTHORIZATION_MARKER
    assert envelope["automatic_retry_executed"] is False
    assert envelope["reaudit_executed"] is False
    assert envelope["translation_executed"] is False
    assert envelope["state_commit_executed"] is False

    out = tmp_path / "123"
    assert (out / "age12-island-v20-story-local-repair1-result.json").exists()
    assert (out / "age12-island-v20-story-local-repair1-envelope.json").exists()
    story_path = out / "age12-island-v20-story-local-repair1-story.txt"
    assert story_path.exists()
    assert story_path.read_text(encoding="utf-8") == repaired_story


def test_paid_stage6_wrapper_preserves_failure_without_retry(tmp_path: Path):
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    profile["stage6_story_local_repair"]["status"] = "PAID_EXECUTION_AUTHORIZED"
    profile["stage6_story_local_repair"]["paid_execution_authorized"] = True
    profile["stage6_story_local_repair"]["authorization_consumed"] = False
    temp_profile = tmp_path / "profile.json"
    temp_profile.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    calls = 0

    def failing_run(**kwargs):
        nonlocal calls
        calls += 1
        raise RuntimeError("synthetic paid failure")

    result, envelope = execute_paid_story_local_repair_once(
        api_key="not-used",
        run_id="456",
        output_root=tmp_path,
        run_fn=failing_run,
        profile_path=temp_profile,
    )

    assert calls == 1
    assert result["status"] == "unhandled_story_local_repair_runtime_failure"
    assert result["automatic_retry_executed"] is False
    assert result["reaudit_executed"] is False
    assert envelope["automatic_retry_executed"] is False
    assert not (
        tmp_path / "456" / "age12-island-v20-story-local-repair1-story.txt"
    ).exists()
