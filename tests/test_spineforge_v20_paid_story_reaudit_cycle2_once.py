from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spineforge_v20_paid_story_reaudit_cycle2_once import (
    AUTHORIZATION_MARKER,
    HANDOFF_PATH,
    execute_paid_story_reaudit_cycle2_once,
)


PROFILE = Path(
    "data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json"
)


def _profile(tmp_path: Path, *, authorized: bool) -> Path:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    stage9 = profile["stage9_story_reaudit"]
    stage9["paid_execution_authorized"] = authorized
    stage9["authorization_consumed"] = not authorized
    stage9["authorization_marker"] = AUTHORIZATION_MARKER
    stage9["reaudit_attempt_index"] = 2
    p = tmp_path / "profile.json"
    p.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def test_paid_stage9_wrapper_rejects_unapproved_profile(tmp_path: Path):
    called = False

    def fake_run(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("paid inference must not execute")

    with pytest.raises(RuntimeError, match="not authorized"):
        execute_paid_story_reaudit_cycle2_once(
            api_key="not-used",
            run_id="unit",
            output_root=tmp_path,
            run_fn=fake_run,
            profile_path=_profile(tmp_path, authorized=False),
        )
    assert called is False


def test_paid_stage9_wrapper_executes_one_authorized_reaudit_boundary(tmp_path: Path):
    calls = 0
    handoff = json.loads(HANDOFF_PATH.read_text(encoding="utf-8"))

    def fake_run(**kwargs):
        nonlocal calls
        calls += 1
        assert kwargs["handoff_path"] == HANDOFF_PATH
        return {
            "schema": "spineforge-v20-story-reaudit-cycle2-execution.v1",
            "status": "reaudit_completed",
            "stage": 9,
            "source_stage8_artifact_id": handoff["source_stage8_artifact_id"],
            "source_repaired_story_sha256": handoff["repaired_story_text_sha256"],
            "reaudit_artifact": {
                "artifact_id": "story-reaudit-cycle2:synthetic",
                "decision": "ACCEPT",
                "next_stage": "ENGLISH_MASTER_SEAL",
            },
            "reaudit_usage_rollup": {"totals": {"api_calls": 2}},
            "automatic_retry_executed": False,
            "repair_executed": False,
            "translation_executed": False,
            "state_commit_executed": False,
        }

    result, envelope = execute_paid_story_reaudit_cycle2_once(
        api_key="not-used",
        run_id="123",
        output_root=tmp_path,
        run_fn=fake_run,
        profile_path=_profile(tmp_path, authorized=True),
    )
    assert calls == 1
    assert result["status"] == "reaudit_completed"
    assert envelope["stage"] == 9
    assert envelope["reaudit_attempt_index"] == 2
    assert envelope["authorization_marker"] == AUTHORIZATION_MARKER
    assert envelope["automatic_retry_executed"] is False
    assert (tmp_path / "123" / "age12-island-v20-story-reaudit2-result.json").exists()
    assert (tmp_path / "123" / "age12-island-v20-story-reaudit2-envelope.json").exists()
