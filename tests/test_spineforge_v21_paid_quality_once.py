from __future__ import annotations

import json
from pathlib import Path
import pytest
from src.spineforge_v21_freeze import PROFILE, seal
from src.spineforge_v21_paid_quality_once import execute_paid_quality_once


def test_paid_wrapper_rejects_before_any_model_call_when_not_authorized(tmp_path):
    with pytest.raises(RuntimeError, match="not authorized"):
        execute_paid_quality_once(api_key="not-used", run_id="denied", output_root=tmp_path)


def test_paid_wrapper_requires_commit_marker(tmp_path):
    profile = json.loads(PROFILE.read_text())
    profile["paid_boundary"].update(paid_execution_authorized=True, authorization_consumed=False)
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(seal(profile)))
    with pytest.raises(RuntimeError, match="marker missing"):
        execute_paid_quality_once(api_key="not-used", run_id="denied", profile_path=path,
                                  output_root=tmp_path / "out", commit_message="ordinary commit")


def test_paid_wrapper_clean_path_is_one_call_and_writes_evidence(tmp_path):
    def forbidden(_):
        pytest.fail("No downstream callback on clean path")
    result, envelope = execute_paid_quality_once(
        api_key="", run_id="clean", output_root=tmp_path / "out", simulation=True,
        initial_audit_fn=lambda _: {"findings": [], "usage": {
            "api_calls": 1, "input_tokens": 100, "output_tokens": 10,
            "reasoning_tokens": 0, "total_tokens": 110, "cost_usd": 0.01, "latency_seconds": 1.2}},
        scene_repair_fn=forbidden, final_audit_fn=forbidden)
    assert result["status"] == "ACCEPT"
    assert result["quality_model_calls"] == envelope["quality_model_calls"] == 1
    assert envelope["simulation"] is True
    assert envelope["explicit_paid_authorization"] is False
    assert Path(envelope["accepted_story_path"]).is_file()
    events = [json.loads(s) for s in Path(envelope["call_ledger_path"]).read_text().splitlines()]
    assert [e["status"] for e in events] == ["STARTED", "COMPLETED"]
    from src.spineforge_v21_constraints import digest_json
    assert events[0]["input_sha256"] == digest_json(events[0]["input"])
    assert events[1]["response_sha256"] == digest_json(events[1]["response"])
    assert events[1]["response"]["findings"] == []


def test_simulation_cannot_fall_back_to_real_transport(tmp_path):
    with pytest.raises(RuntimeError, match="all fake callbacks"):
        execute_paid_quality_once(api_key="", run_id="bad", simulation=True,
                                  initial_audit_fn=lambda _: {}, output_root=tmp_path)
