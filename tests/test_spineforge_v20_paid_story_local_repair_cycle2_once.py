from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spineforge_v20_paid_story_local_repair_cycle2_once import (
    AUTHORIZATION_MARKER,
    HANDOFF_PATH,
    execute_paid_story_local_repair_cycle2_once,
)


PROFILE = Path(
    "data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json"
)


def _profile(tmp_path: Path, *, authorized: bool) -> Path:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    stage8 = profile["stage8_story_local_repair"]
    stage8["paid_execution_authorized"] = authorized
    stage8["authorization_consumed"] = not authorized
    stage8["authorization_marker"] = AUTHORIZATION_MARKER
    stage8["paid_attempt_index"] = 3
    p = tmp_path / "profile.json"
    p.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def test_paid_stage8_wrapper_rejects_unapproved_profile(tmp_path: Path):
    called = False

    def fake_run(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("paid inference must not execute")

    with pytest.raises(RuntimeError, match="not authorized"):
        execute_paid_story_local_repair_cycle2_once(
            api_key="not-used",
            run_id="unit",
            output_root=tmp_path,
            run_fn=fake_run,
            profile_path=_profile(tmp_path, authorized=False),
        )
    assert called is False


def test_paid_stage8_wrapper_executes_one_authorized_repair(tmp_path: Path):
    calls = 0
    handoff = json.loads(HANDOFF_PATH.read_text(encoding="utf-8"))

    def fake_run(**kwargs):
        nonlocal calls
        calls += 1
        assert kwargs["handoff"]["artifact_id"] == handoff["artifact_id"]
        return {
            "schema": "spineforge-v20-story-local-repair-cycle2-execution.v1",
            "status": "repair_generated",
            "stage": 8,
            "source_stage7_product_artifact_id": handoff[
                "source_stage7_product_artifact_id"
            ],
            "source_story_sha256": handoff["source_story_sha256"],
            "patches": [],
            "no_change_resolutions": [],
            "changed_span_ids": [],
            "patch_count": 0,
            "no_change_resolution_count": 0,
            "repaired_story": "Synthetic repaired story.",
            "repaired_story_sha256": "synthetic",
            "repair_usage_rollup": {"totals": {"api_calls": 1}},
            "automatic_retry_executed": False,
            "reaudit_executed": False,
            "translation_executed": False,
            "state_commit_executed": False,
            "next_stage": "STORY_REAUDIT",
        }

    result, envelope = execute_paid_story_local_repair_cycle2_once(
        api_key="not-used",
        run_id="123",
        output_root=tmp_path,
        run_fn=fake_run,
        profile_path=_profile(tmp_path, authorized=True),
    )
    assert calls == 1
    assert result["status"] == "repair_generated"
    assert envelope["stage"] == 8
    assert envelope["paid_attempt_index"] == 3
    assert envelope["authorization_marker"] == AUTHORIZATION_MARKER
    assert envelope["automatic_retry_executed"] is False
    assert (tmp_path / "123" / "age12-island-v20-story-local-repair3-result.json").exists()
    assert (tmp_path / "123" / "age12-island-v20-story-local-repair3-story.txt").exists()
    assert (tmp_path / "123" / "age12-island-v20-story-local-repair3-envelope.json").exists()
