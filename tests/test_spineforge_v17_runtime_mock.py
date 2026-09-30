from __future__ import annotations

import json
from pathlib import Path

from src.english_story_pipeline import StructuredJsonCallError
from src.spineforge_v11_contract import AUDIT_DIMENSIONS
from src.spineforge_v17 import run


SOURCE = Path("experiments/results/spineforge-v16/36760550050/result.json")


def _accept():
    return {
        "schema": "spineforge-v11-audit.v1",
        "decision": "ACCEPT",
        "dimensions": [
            {
                "name": name,
                "score": 4,
                "blocking_failure": False,
                "evidence": ["One concise control evidence item."],
                "reason": "Control fixture passes this dimension.",
            }
            for name in sorted(AUDIT_DIMENSIONS)
        ],
        "blocking_defects": [],
        "repair_targets": [],
        "preserve": ["validated v16 spine"],
        "decision_reason": "Complete zero-cost control audit.",
    }


def test_v17_is_audit_only_and_reuses_v16_validated_spine(tmp_path: Path):
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        body = {"usage": {"prompt_tokens": 1000, "completion_tokens": 700, "total_tokens": 1700, "cost": 0.009}}
        return _accept(), body, {"response_format": {"type": "json_object"}}, []

    result = run(
        source_evidence_path=SOURCE,
        out_path=tmp_path / "result.json",
        api_key="zero-cost-test",
        call_fn=fake_call,
    )

    assert len(calls) == 1
    req = json.loads(calls[0]["user_prompt"])
    assert req["validated_episode_spine"] == source["repaired_episode_spine"]
    assert "previous_audit" not in req
    assert len(req["mandatory_audit_dimensions"]) == 18
    assert calls[0]["max_tokens"] == 8000
    assert result["status"] == "awaiting_human_review"
    assert result["audit_completeness"]["complete"] is True
    assert result["repair_called"] is False
    assert result["architect_recalled"] is False
    assert result["writer_authorized"] is False


def test_v17_checkpoints_usage_from_truncated_structured_error(tmp_path: Path):
    def fake_call(**kwargs):
        trace = {
            "body": {
                "usage": {
                    "prompt_tokens": 22000,
                    "completion_tokens": 8000,
                    "total_tokens": 30000,
                    "cost": 0.124,
                }
            },
            "raw_usage": {
                "prompt_tokens": 22000,
                "completion_tokens": 8000,
                "total_tokens": 30000,
                "cost": 0.124,
            },
            "cost": {"usd": 0.124, "try_amount": None, "usd_try_rate": None},
            "retry_suppressed": True,
            "retry_suppressed_reason": "finish_reason_length",
        }
        raise StructuredJsonCallError("STRUCTURED_JSON_RESPONSE_TRUNCATED", trace)

    result = run(
        source_evidence_path=SOURCE,
        out_path=tmp_path / "result.json",
        api_key="zero-cost-test",
        call_fn=fake_call,
    )

    assert result["status"] == "audit_structured_output_failed"
    assert result["pipeline_usage_rollup"]["totals"]["api_calls"] == 1
    assert result["pipeline_usage_rollup"]["totals"]["total_tokens"] == 30000
    assert result["pipeline_usage_rollup"]["totals"]["cost_usd"] == 0.124
    assert result["pipeline_usage_rollup"]["calls"][0]["status"] == "failed_structured_output"
    assert result["failure"]["trace"]["retry_suppressed_reason"] == "finish_reason_length"


def test_v17_incomplete_audit_cannot_reach_human_review(tmp_path: Path):
    raw = _accept()
    raw["decision"] = "REPAIR"
    raw["dimensions"] = [x for x in raw["dimensions"] if x["name"] != "FRESHNESS"]
    raw["blocking_defects"] = ["Missing freshness assessment."]
    raw["repair_targets"] = [{
        "path": "beats",
        "defect_class": "FRESHNESS",
        "problem": "Incomplete audit control fixture.",
        "required_change": "Return complete audit coverage.",
        "preserve": [],
    }]

    def fake_call(**kwargs):
        body = {"usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2, "cost": 0.0}}
        return raw, body, {"response_format": {"type": "json_object"}}, []

    result = run(
        source_evidence_path=SOURCE,
        out_path=tmp_path / "result.json",
        api_key="zero-cost-test",
        call_fn=fake_call,
    )
    assert result["status"] == "audit_contract_rejected"
    assert result["writer_authorized"] is False
