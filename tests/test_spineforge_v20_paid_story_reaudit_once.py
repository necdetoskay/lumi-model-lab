from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spineforge_v20_paid_story_reaudit_once import (
    AUTHORIZATION_MARKER,
    HANDOFF_PATH,
    execute_paid_story_reaudit_once,
)


PROFILE = Path(
    "data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json"
)


def _temp_profile(tmp_path: Path, *, authorized: bool) -> Path:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    stage7 = profile["stage7_story_reaudit"]
    stage7["paid_execution_authorized"] = authorized
    stage7["authorization_consumed"] = not authorized
    stage7["authorization_marker"] = AUTHORIZATION_MARKER
    stage7["reaudit_attempt_index"] = 1
    p = tmp_path / "profile.json"
    p.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def test_paid_stage7_wrapper_rejects_unapproved_profile(tmp_path: Path):
    called = False

    def fake_run(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("paid inference must not execute")

    with pytest.raises(RuntimeError, match="not authorized"):
        execute_paid_story_reaudit_once(
            api_key="not-used",
            run_id="unit",
            output_root=tmp_path,
            run_fn=fake_run,
            profile_path=_temp_profile(tmp_path, authorized=False),
        )
    assert called is False


def test_paid_stage7_wrapper_executes_one_authorized_reaudit_boundary(tmp_path: Path):
    calls = 0
    handoff = json.loads(HANDOFF_PATH.read_text(encoding="utf-8"))

    def fake_run(**kwargs):
        nonlocal calls
        calls += 1
        assert kwargs["handoff_path"] == HANDOFF_PATH
        return {
            "schema": "spineforge-v20-story-reaudit-execution.v1",
            "status": "reaudit_completed",
            "source_stage6_artifact_id": handoff["source_stage6_artifact_id"],
            "source_repaired_story_sha256": handoff["repaired_story_text_sha256"],
            "reaudit_artifact": {
                "artifact_id": "story-reaudit:synthetic",
                "decision": "ACCEPT",
                "next_stage": "ENGLISH_MASTER_SEAL",
            },
            "reaudit_usage_rollup": {
                "totals": {
                    "api_calls": 2,
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "reasoning_tokens": 0,
                    "total_tokens": 120,
                    "cost_usd": 0.01,
                    "latency_seconds": 1.0,
                }
            },
            "automatic_retry_executed": False,
            "repair_executed": False,
            "translation_executed": False,
            "state_commit_executed": False,
        }

    result, envelope = execute_paid_story_reaudit_once(
        api_key="not-used",
        run_id="123",
        output_root=tmp_path,
        run_fn=fake_run,
        profile_path=_temp_profile(tmp_path, authorized=True),
    )
    assert calls == 1
    assert result["status"] == "reaudit_completed"
    assert envelope["stage"] == 7
    assert envelope["attempt_index"] == 1
    assert envelope["authorization_marker"] == AUTHORIZATION_MARKER
    assert envelope["automatic_retry_executed"] is False
    assert (tmp_path / "123" / "age12-island-v20-story-reaudit1-result.json").exists()
    assert (tmp_path / "123" / "age12-island-v20-story-reaudit1-envelope.json").exists()


def test_paid_stage7_wrapper_preserves_failure_without_retry(tmp_path: Path):
    calls = 0

    def failing_run(**kwargs):
        nonlocal calls
        calls += 1
        raise RuntimeError("synthetic re-audit failure")

    result, envelope = execute_paid_story_reaudit_once(
        api_key="not-used",
        run_id="456",
        output_root=tmp_path,
        run_fn=failing_run,
        profile_path=_temp_profile(tmp_path, authorized=True),
    )
    assert calls == 1
    assert result["status"] == "unhandled_story_reaudit_runtime_failure"
    assert result["automatic_retry_executed"] is False
    assert result["repair_executed"] is False
    assert result["translation_executed"] is False
    assert result["state_commit_executed"] is False
    assert envelope["automatic_retry_executed"] is False
