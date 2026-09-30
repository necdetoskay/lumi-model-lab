from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spineforge_v12_stage import run as run_stage


CASE = Path("data/specifications/story_lab/spineforge_v12_age18_forbidden_cartographer_case_v1.json")
LEDGER = Path("data/specifications/story_lab/spineforge_v12_age18_forbidden_cartographer_cost_ledger_v1.json")
TRIGGER = Path("experiments/triggers/spineforge-v12.json")
WORKFLOW = Path(".github/workflows/spineforge-v12.yml")


def test_v12_unapproved_trigger_stops_before_runtime(tmp_path: Path):
    trigger = tmp_path / "trigger.json"
    trigger.write_text(
        json.dumps({
            "schema_version": "spineforge-v12-trigger.v1",
            "scope": "SPINEFORGE_V12_ATTEMPT",
            "paid_authorized": False,
            "case_manifest": str(CASE),
            "attempt_index": 1,
        }),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError) as exc:
        run_stage(trigger_path=trigger, out_dir=tmp_path / "out")
    assert "not explicitly authorized" in str(exc.value)
    assert not (tmp_path / "out" / "result.json").exists()


def test_v12_case_and_ledger_are_zero_spend_before_paid_authorization():
    case = json.loads(CASE.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert case["status"] == "ZERO_COST_QUALIFICATION"
    assert ledger["status"] == "ZERO_COST_QUALIFICATION"
    assert ledger["v12_actual_spend"] == {
        "api_calls": 0,
        "total_tokens": 0,
        "cost_usd": 0,
        "latency_seconds": 0,
    }
    assert ledger["paid_boundary"]["authorized"] is False
    assert not TRIGGER.exists()


def test_v12_paid_workflow_is_trigger_path_only():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "experiments/triggers/spineforge-v12.json" in workflow
    assert "workflow_dispatch" not in workflow
    assert "spineforge_v12_stage" in workflow
