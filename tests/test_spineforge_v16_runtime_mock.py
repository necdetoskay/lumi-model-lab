from __future__ import annotations

import copy
import json
from pathlib import Path

from src.spineforge_v11_contract import AUDIT_DIMENSIONS
from src.spineforge_v16 import run


SOURCE = Path("experiments/results/spineforge-v15/36757835721/result.json")


def _accept_audit():
    return {
        "schema": "spineforge-v11-audit.v1",
        "decision": "ACCEPT",
        "dimensions": [
            {
                "name": name,
                "score": 5,
                "blocking_failure": False,
                "evidence": ["Complete zero-cost control evidence."],
                "reason": "Full protected dimension supplied.",
            }
            for name in sorted(AUDIT_DIMENSIONS)
        ],
        "blocking_defects": [],
        "repair_targets": [],
        "preserve": ["validated v15 gains"],
        "decision_reason": "Complete control fixture accepts the repaired spine.",
    }


def test_v16_uses_v15_partial_repair_without_treating_it_as_accept(tmp_path: Path):
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    candidate = copy.deepcopy(source["repaired_episode_spine"])
    outputs = [candidate, _accept_audit()]
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        raw = outputs[len(calls) - 1]
        body = {"usage": {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500, "cost": 0.007}}
        return raw, body, {"response_format": {"type": "json_object"}}, []

    result = run(
        source_evidence_path=SOURCE,
        out_path=tmp_path / "result.json",
        api_key="zero-cost-test",
        call_fn=fake_call,
    )

    assert result["status"] == "awaiting_human_review"
    assert result["source_audit_partial_repair_only"] is True
    assert result["source_audit_completeness"]["present_count"] == 17
    assert result["source_audit_completeness"]["missing_dimensions"] == ["FRESHNESS"]
    assert result["source_audit_completeness"]["acceptance_forbidden_from_partial_audit"] is True

    repair_request = json.loads(calls[0]["user_prompt"])
    assert repair_request["repair_brief"]["decision"] == "REPAIR"
    assert len(repair_request["repair_brief"]["blocking_defects"]) == 4
    assert len(repair_request["repair_brief"]["repair_targets"]) == 3

    audit_request = json.loads(calls[1]["user_prompt"])
    assert len(audit_request["mandatory_audit_dimensions"]) == 18
    assert "FRESHNESS" in audit_request["mandatory_audit_dimensions"]
    assert result["reaudit"]["decision"] == "ACCEPT"
    assert result["writer_authorized"] is False


def test_v16_incomplete_final_reaudit_is_rejected_not_accepted(tmp_path: Path):
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    candidate = copy.deepcopy(source["repaired_episode_spine"])
    incomplete = _accept_audit()
    incomplete["decision"] = "REPAIR"
    incomplete["dimensions"] = [row for row in incomplete["dimensions"] if row["name"] != "FRESHNESS"]
    incomplete["blocking_defects"] = ["Control blocker."]
    incomplete["repair_targets"] = [{
        "path": "beats[0]",
        "defect_class": "EXECUTABILITY",
        "problem": "Control problem.",
        "required_change": "Control change.",
        "preserve": [],
    }]
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        raw = candidate if len(calls) == 1 else incomplete
        body = {"usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2, "cost": 0.0}}
        return raw, body, {"response_format": {"type": "json_object"}}, []

    result = run(
        source_evidence_path=SOURCE,
        out_path=tmp_path / "result.json",
        api_key="zero-cost-test",
        call_fn=fake_call,
    )
    assert result["status"] == "reaudit_contract_rejected"
    assert result["writer_authorized"] is False
