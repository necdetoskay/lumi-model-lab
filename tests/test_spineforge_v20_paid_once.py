from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_v20_paid_once import execute_paid_once


def test_paid_runner_persists_result_and_envelope_on_typed_success(tmp_path: Path):
    def fake_run(**kwargs):
        return {
            "schema": "spineforge-v20-evidence.v1",
            "status": "repair_required",
            "writer_authorized": False,
            "pipeline_usage_rollup": {"totals": {"api_calls": 2}},
        }

    result, envelope = execute_paid_once(
        api_key="fake",
        run_id="123",
        output_root=tmp_path,
        run_fn=fake_run,
    )
    assert result["status"] == "repair_required"
    assert envelope["result_status"] == "repair_required"
    assert envelope["writer_authorized"] is False
    out_dir = tmp_path / "123"
    assert (out_dir / "age12-island-v20-attempt1-result.json").exists()
    assert (out_dir / "age12-island-v20-attempt1-envelope.json").exists()


def test_paid_runner_persists_failure_artifact_on_unhandled_exception(tmp_path: Path):
    def boom(**kwargs):
        raise RuntimeError("synthetic provider failure")

    result, envelope = execute_paid_once(
        api_key="fake",
        run_id="456",
        output_root=tmp_path,
        run_fn=boom,
    )
    assert result["status"] == "unhandled_runtime_failure"
    assert result["writer_authorized"] is False
    assert envelope["result_status"] == "unhandled_runtime_failure"
    persisted = json.loads(
        (tmp_path / "456" / "age12-island-v20-attempt1-result.json").read_text()
    )
    assert persisted["failure"]["type"] == "RuntimeError"
