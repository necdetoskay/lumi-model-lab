from __future__ import annotations

import copy
import json
from pathlib import Path

from src.spineforge_v11_contract import AUDIT_DIMENSIONS
from src.spineforge_v14 import run


SOURCE = Path("experiments/results/spineforge-v12/36752663853/result.json")


def _accept_audit():
    return {
        "schema": "spineforge-v11-audit.v1",
        "decision": "ACCEPT",
        "dimensions": [
            {
                "name": name,
                "score": 5,
                "blocking_failure": False,
                "evidence": ["Repaired structure is executable in the zero-cost control fixture."],
                "reason": "Control-flow acceptance fixture.",
            }
            for name in sorted(AUDIT_DIMENSIONS)
        ],
        "blocking_defects": [],
        "repair_targets": [],
        "preserve": ["validated repair"],
        "decision_reason": "Zero-cost control fixture accepts repaired spine.",
    }


def test_v14_uses_exact_v12_repair_targets_then_reaudits(tmp_path: Path):
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    repaired = copy.deepcopy(source["episode_spine"])
    calls = []

    outputs = [repaired, _accept_audit()]

    def fake_call(**kwargs):
        calls.append(kwargs)
        raw = outputs[len(calls) - 1]
        body = {
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 500,
                "total_tokens": 1500,
                "cost": 0.007,
            }
        }
        return raw, body, {"response_format": {"type": "json_object"}}, []

    result = run(
        source_evidence_path=SOURCE,
        out_path=tmp_path / "result.json",
        api_key="zero-cost-test",
        call_fn=fake_call,
    )

    assert result["status"] == "awaiting_human_review"
    assert len(calls) == 2
    repair_request = json.loads(calls[0]["user_prompt"])
    brief = repair_request["repair_brief"]
    assert brief["decision"] == "REPAIR"
    assert len(brief["blocking_defects"]) == 6
    assert len(brief["repair_targets"]) == 5
    assert "the opening hook" in brief["preserve"]
    assert calls[0]["model"] == "anthropic/claude-sonnet-5.5"
    assert calls[1]["model"] == "anthropic/claude-sonnet-5.5"
    assert result["deterministic_checks"]["repair_episode_spine_contract_valid"] is True
    assert result["reaudit"]["decision"] == "ACCEPT"
    assert result["automatic_repair_loop_enabled"] is False
    assert result["writer_authorized"] is False


def test_v14_source_audit_is_typed_repair_before_any_model_call(tmp_path: Path):
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    repaired = copy.deepcopy(source["episode_spine"])
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            body = {"usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2, "cost": 0.0}}
            return repaired, body, {"response_format": {"type": "json_object"}}, []
        return _accept_audit(), {"usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2, "cost": 0.0}}, {"response_format": {"type": "json_object"}}, []

    result = run(
        source_evidence_path=SOURCE,
        out_path=tmp_path / "result.json",
        api_key="zero-cost-test",
        call_fn=fake_call,
    )
    assert result["source_audit"]["decision"] == "REPAIR"
    assert result["source_audit_contract_normalization"]["changed"] is True
