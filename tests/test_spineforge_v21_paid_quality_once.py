from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spineforge_v21_paid_quality_once import (
    AUTHORIZATION_MARKER,
    execute_paid_quality_once,
)


SOURCE_ARTIFACT = Path(
    "evidence/spineforge-v20-paid-writer/37204419845/"
    "age12-island-v20-story-quality-repair-c10-product.json"
)


def _profile(tmp_path: Path, *, authorized: bool) -> Path:
    artifact = json.loads(SOURCE_ARTIFACT.read_text(encoding="utf-8"))
    profile = {
        "runtime_freeze": {
            "runtime_revision": "TEST-v21",
            "files": [],
        },
        "source_story": {
            "artifact_id": artifact["artifact_id"],
            "artifact_path": str(SOURCE_ARTIFACT),
            "story_sha256": artifact["repaired_story_text_sha256"],
            "approved_spine_hash": "spine",
            "canon_invariants": ["Arda performs the decisive cut."],
        },
        "paid_boundary": {
            "paid_execution_authorized": authorized,
            "authorization_marker": AUTHORIZATION_MARKER,
            "authorization_consumed": False,
        },
        "cost_policy": {
            "quality_stage_limits_usd": {
                "initial_audit": 0.04,
                "scene_repair": 0.035,
                "final_audit": 0.025,
            }
        },
    }
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile), encoding="utf-8")
    return path


def test_paid_wrapper_rejects_before_any_model_call_when_not_authorized(tmp_path):
    profile = _profile(tmp_path, authorized=False)
    called = False

    def audit(_):
        nonlocal called
        called = True
        raise AssertionError

    with pytest.raises(RuntimeError, match="not authorized"):
        execute_paid_quality_once(
            api_key="not-used",
            run_id="test",
            profile_path=profile,
            output_root=tmp_path / "out",
            initial_audit_fn=audit,
            scene_repair_fn=lambda _: {},
            final_audit_fn=lambda _: {},
            verify_fn=lambda _: {"runtime_revision": "TEST-v21", "verified_files": 0},
            require_commit_marker=False,
        )

    assert called is False


def test_paid_wrapper_requires_commit_marker(tmp_path):
    profile = _profile(tmp_path, authorized=True)

    with pytest.raises(RuntimeError, match="marker missing"):
        execute_paid_quality_once(
            api_key="not-used",
            run_id="test",
            profile_path=profile,
            output_root=tmp_path / "out",
            verify_fn=lambda _: {"runtime_revision": "TEST-v21", "verified_files": 0},
            require_commit_marker=True,
            commit_message="ordinary commit",
        )


def test_paid_wrapper_clean_path_is_one_call_and_writes_evidence(tmp_path):
    profile = _profile(tmp_path, authorized=True)

    def audit(_):
        return {
            "findings": [],
            "usage": {
                "api_calls": 1,
                "input_tokens": 100,
                "output_tokens": 10,
                "reasoning_tokens": 0,
                "total_tokens": 110,
                "cost_usd": 0.01,
                "latency_seconds": 1.2,
            },
        }

    result, envelope = execute_paid_quality_once(
        api_key="not-used",
        run_id="123",
        profile_path=profile,
        output_root=tmp_path / "out",
        initial_audit_fn=audit,
        scene_repair_fn=lambda _: (_ for _ in ()).throw(AssertionError()),
        final_audit_fn=lambda _: (_ for _ in ()).throw(AssertionError()),
        verify_fn=lambda _: {"runtime_revision": "TEST-v21", "verified_files": 0},
        require_commit_marker=True,
        commit_message=f"paid [{AUTHORIZATION_MARKER}]",
    )

    assert result["status"] == "ACCEPT"
    assert result["quality_model_calls"] == 1
    assert envelope["quality_model_calls"] == 1
    assert envelope["automatic_retry_executed"] is False
    assert envelope["automatic_second_repair_executed"] is False
    assert Path(envelope["result_path"]).is_file()
    assert Path(envelope["accepted_story_path"]).is_file()
