from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spineforge_v20_paid_story_quality_loop_once import (
    AUTHORIZATION_MARKER,
    PROFILE_PATH,
    execute_paid_story_quality_loop_once,
)


def _profile(tmp_path: Path, *, authorized: bool, consumed: bool) -> Path:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    loop = profile["story_quality_loop"]
    loop["paid_execution_authorized"] = authorized
    loop["authorization_consumed"] = consumed
    loop["authorization_marker"] = AUTHORIZATION_MARKER
    p = tmp_path / "profile.json"
    p.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def test_generic_paid_wrapper_rejects_unapproved_profile(tmp_path: Path):
    called = False

    def fake_repair(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("paid inference must not execute")

    with pytest.raises(RuntimeError, match="not authorized"):
        execute_paid_story_quality_loop_once(
            api_key="not-used",
            run_id="unit",
            output_root=tmp_path,
            profile_path=_profile(tmp_path, authorized=False, consumed=True),
            repair_run_fn=fake_repair,
        )
    assert called is False


def test_generic_paid_wrapper_rejects_consumed_authorization(tmp_path: Path):
    with pytest.raises(RuntimeError, match="already consumed"):
        execute_paid_story_quality_loop_once(
            api_key="not-used",
            run_id="unit",
            output_root=tmp_path,
            profile_path=_profile(tmp_path, authorized=True, consumed=True),
        )


def test_generic_paid_repair_emits_next_reaudit_state_without_authorizing_it(tmp_path: Path):
    profile_path = _profile(tmp_path, authorized=True, consumed=False)
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    loop = profile["story_quality_loop"]

    repair_handoff_path = Path(
        "evidence/spineforge-v20-story-quality-loop/"
        "37014477600-repair-handoff.json"
    )
    repair_handoff = json.loads(repair_handoff_path.read_text(encoding="utf-8"))
    loop.update({
        "status": "PAID_EXECUTION_AUTHORIZED",
        "current_action": "LOCAL_REPAIR",
        "current_stage": 10,
        "cycle_index": 3,
        "action_authorization_id": (
            "story-quality-loop:stage10:local-repair:cycle3:attempt4"
        ),
        "source_story_artifact_id": repair_handoff[
            "source_story_artifact_id"
        ],
        "source_story_artifact_path": repair_handoff[
            "source_story_artifact_path"
        ],
        "source_story_artifact_sha256": repair_handoff[
            "source_story_artifact_sha256"
        ],
        "source_story_sha256": repair_handoff["source_story_sha256"],
        "source_reaudit_product_artifact_id": repair_handoff[
            "source_reaudit_product_artifact_id"
        ],
        "source_reaudit_product_path": repair_handoff[
            "source_reaudit_product_path"
        ],
        "source_reaudit_product_sha256": repair_handoff[
            "source_reaudit_product_sha256"
        ],
        "handoff_artifact_id": repair_handoff["artifact_id"],
        "handoff_path": str(repair_handoff_path),
        "handoff_sha256": __import__("hashlib").sha256(
            repair_handoff_path.read_bytes()
        ).hexdigest(),
        "paid_attempt_index": 4,
        "paid_execution_authorized": True,
        "authorization_consumed": False,
    })
    profile_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    source_artifact = json.loads(
        Path(loop["source_story_artifact_path"]).read_text(encoding="utf-8")
    )
    source_story = Path(source_artifact["repaired_story_path"]).read_text(encoding="utf-8")
    if source_story.endswith("\n"):
        source_story = source_story[:-1]

    def fake_repair(**kwargs):
        return {
            "schema": "spineforge-v20-story-quality-repair-execution.v1",
            "status": "repair_generated",
            "stage": 10,
            "repair_cycle_index": 3,
            "paid_attempt_index": 4,
            "source_reaudit_product_artifact_id": loop[
                "source_reaudit_product_artifact_id"
            ],
            "source_reaudit_artifact_id": "synthetic",
            "source_story_artifact_id": loop["source_story_artifact_id"],
            "source_story_sha256": loop["source_story_sha256"],
            "repair_model": "anthropic/claude-sonnet-5.5",
            "patches": [],
            "no_change_resolutions": [],
            "changed_span_ids": [],
            "patch_count": 0,
            "no_change_resolution_count": 0,
            "repaired_story": source_story,
            "repaired_story_sha256": loop["source_story_sha256"],
            "source_story_mutated": False,
            "all_findings_addressed": True,
            "changed_spans_subset_of_allowed": True,
            "repair_usage_rollup": {"totals": {"api_calls": 1}},
            "automatic_retry_executed": False,
            "reaudit_executed": False,
            "translation_executed": False,
            "state_commit_executed": False,
            "next_stage": "STORY_REAUDIT",
        }

    result, envelope = execute_paid_story_quality_loop_once(
        api_key="not-used",
        run_id="123",
        output_root=tmp_path,
        profile_path=profile_path,
        repair_run_fn=fake_repair,
    )
    assert result["status"] == "repair_generated"
    assert envelope["action"] == "LOCAL_REPAIR"
    next_state = json.loads(
        (tmp_path / "123" / "story-quality-loop-next-state.json").read_text(
            encoding="utf-8"
        )
    )
    assert next_state["status"] == "NEXT_ACTION_READY_NOT_AUTHORIZED"
    assert next_state["current_action"] == "REAUDIT"
    assert next_state["current_stage"] == 11
    assert next_state["cycle_index"] == 3
    assert next_state["paid_execution_authorized"] is False
    assert next_state["automatic_paid_transition_enabled"] is False
    assert (tmp_path / "123" / "age12-island-v20-story-quality-repair-c3-product.json").exists()
    assert (tmp_path / "123" / "age12-island-v20-story-quality-repair-c3-next-handoff.json").exists()
