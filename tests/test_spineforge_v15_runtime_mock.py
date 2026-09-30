from __future__ import annotations

import copy
import json
from pathlib import Path

from src.spineforge_v11_contract import AUDIT_DIMENSIONS
from src.spineforge_v15 import run


SOURCE = Path("experiments/results/spineforge-v14/36755567557/result.json")


def _accept_audit():
    return {
        "schema": "spineforge-v11-audit.v1",
        "decision": "ACCEPT",
        "dimensions": [
            {
                "name": name,
                "score": 5,
                "blocking_failure": False,
                "evidence": ["Convergence repair control fixture resolves the remaining target."],
                "reason": "Zero-cost acceptance fixture.",
            }
            for name in sorted(AUDIT_DIMENSIONS)
        ],
        "blocking_defects": [],
        "repair_targets": [],
        "preserve": ["validated v14 dramatic engine"],
        "decision_reason": "Zero-cost control fixture accepts convergence repair.",
    }


def test_v15_uses_v14_repaired_spine_and_typed_reaudit(tmp_path: Path):
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    candidate = copy.deepcopy(source["repaired_episode_spine"])
    outputs = [candidate, _accept_audit()]
    calls = []

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
    assert result["source_audit_already_typed"] is True
    assert result["source_audit"]["decision"] == "REPAIR"
    assert len(result["source_audit"]["blocking_defects"]) == 5
    assert len(result["source_audit"]["repair_targets"]) == 4

    repair_request = json.loads(calls[0]["user_prompt"])
    assert repair_request["current_episode_spine"] == source["repaired_episode_spine"]
    assert len(repair_request["repair_brief"]["repair_targets"]) == 4
    assert result["reaudit"]["decision"] == "ACCEPT"
    assert result["automatic_repair_loop_enabled"] is False
    assert result["writer_authorized"] is False


def test_v15_does_not_recall_architect(tmp_path: Path):
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    candidate = copy.deepcopy(source["repaired_episode_spine"])
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        raw = candidate if len(calls) == 1 else _accept_audit()
        body = {"usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2, "cost": 0.0}}
        return raw, body, {"response_format": {"type": "json_object"}}, []

    run(
        source_evidence_path=SOURCE,
        out_path=tmp_path / "result.json",
        api_key="zero-cost-test",
        call_fn=fake_call,
    )

    assert [c["model"] for c in calls] == [
        "anthropic/claude-sonnet-5.5",
        "anthropic/claude-sonnet-5.5",
    ]
    assert "convergence_semantic_episode_spine_repair" in calls[0]["user_prompt"]
    assert "spineforge_v15_repair" not in calls[1]["user_prompt"]
