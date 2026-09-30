from __future__ import annotations
import json
from pathlib import Path

LEDGER=Path("data/specifications/story_lab/age18_forbidden_cartographer_cost_ledger_v1.json")
FEEDBACK=Path("data/specifications/story_lab/age18_forbidden_cartographer_f11_revision_feedback.json")

def test_f1_replan_cost_is_qualification_waste() -> None:
    j=json.loads(LEDGER.read_text())
    assert j["status"]=="F1_REPLAN_F1_1_READY"
    assert j["product_path"]["api_calls"]==0
    assert j["product_path"]["cost_usd"]==0.0
    q=j["qualification_waste"]
    assert q["api_calls"]==2
    assert q["total_tokens"]==30093
    assert q["cost_usd"]==0.09225655
    assert q["latency_seconds"]==57.531
    assert j["paid_boundary"]["next_scope"]=="F1_1_SONNET55_SPINE_REVISION_PLUS_LUNA_GATE_ONLY"
    assert j["paid_boundary"]["authorized"] is False
    assert j["paid_boundary"]["writer_authorized"] is False

def test_f11_feedback_has_all_four_blocking_roots_and_freezes() -> None:
    j=json.loads(FEEDBACK.read_text())
    assert j["decision"]=="REPLAN"
    assert {x["id"] for x in j["blocking_reasons"]}=={
        "reversal_overclaim",
        "bounded_report_mentor_logistics",
        "extend_testing_greyfen_contradiction",
        "branch_executability",
    }
    freezes=" ".join(j["hard_freezes"]).lower()
    assert "does not cross" in freezes
    assert "nameless vale" in freezes
    assert "only intended main saga milestone" in freezes
    assert j["paid_next_stage_authorized"] is False
