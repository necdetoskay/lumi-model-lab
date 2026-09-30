from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spineforge_cost_ledger import build_spineforge_cost_ledger
from src.spineforge_stage import run as run_stage


def test_paid_stage_requires_explicit_authorization(tmp_path:Path):
    trigger=tmp_path/"trigger.json"
    trigger.write_text(json.dumps({
        "schema_version":"spineforge-trigger.v1",
        "paid_authorized":False,
        "scope":"SPINEFORGE_ATTEMPT",
        "case_manifest":"unused.json",
        "attempt_index":1,
    }))
    with pytest.raises(RuntimeError,match="not explicitly authorized"):
        run_stage(trigger_path=trigger,out_dir=tmp_path/"out")


def test_cost_ledger_separates_replan_waste_from_accepted_attempt(tmp_path:Path):
    a1=tmp_path/"a1.json"
    a2=tmp_path/"a2.json"
    a1.write_text(json.dumps({
        "attempt_index":1,
        "status":"creative_replan_required",
        "pipeline_usage_rollup":{"totals":{
            "api_calls":2,"total_tokens":1000,"cost_usd":0.02,"latency_seconds":10
        }}
    }))
    a2.write_text(json.dumps({
        "attempt_index":2,
        "status":"awaiting_human_review",
        "pipeline_usage_rollup":{"totals":{
            "api_calls":3,"total_tokens":2000,"cost_usd":0.03,"latency_seconds":20
        }}
    }))
    ledger=build_spineforge_cost_ledger(
        case_id="case",runtime_id="runtime",attempt_paths=[a1,a2]
    )
    assert ledger["qualification_revision_waste"]["cost_usd"]==0.02
    assert ledger["accepted_attempt"]["cost_usd"]==0.03
    assert ledger["actual_spend"]["cost_usd"]==0.05
    assert ledger["actual_spend"]["api_calls"]==5
