from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_v20_paid_repair_once import execute_paid_repair_once


def test_paid_repair_wrapper_persists_typed_result(tmp_path: Path):
    def fake_run(**kwargs):
        return {
            "schema": "spineforge-v20-local-repair-evidence.v1",
            "status": "awaiting_human_review",
            "writer_authorized": False,
            "pipeline_usage_rollup": {"totals": {"api_calls": 2}},
        }

    result, envelope = execute_paid_repair_once(
        api_key="fake",
        run_id="901",
        output_root=tmp_path,
        run_fn=fake_run,
    )
    assert result["status"] == "awaiting_human_review"
    assert envelope["result_status"] == "awaiting_human_review"
    assert envelope["writer_authorized"] is False
    assert (tmp_path / "901" / "age12-island-v20-repair1-result.json").exists()
    assert (tmp_path / "901" / "age12-island-v20-repair1-envelope.json").exists()


def test_paid_repair_wrapper_persists_unhandled_failure(tmp_path: Path):
    def boom(**kwargs):
        raise RuntimeError("synthetic repair failure")

    result, envelope = execute_paid_repair_once(
        api_key="fake",
        run_id="902",
        output_root=tmp_path,
        run_fn=boom,
    )
    assert result["status"] == "unhandled_repair_runtime_failure"
    assert result["writer_authorized"] is False
    assert envelope["result_status"] == "unhandled_repair_runtime_failure"
    persisted = json.loads(
        (tmp_path / "902" / "age12-island-v20-repair1-result.json").read_text()
    )
    assert persisted["failure"]["type"] == "RuntimeError"
