from __future__ import annotations

import copy
import json
from pathlib import Path

from src.spine_context_pack_v1 import write_spine_context_pack
from src.spineforge_v11_contract import AUDIT_DIMENSIONS
from src.spineforge_v12 import run


RESULT = Path("experiments/results/spineforge-v11/36746646152/result.json")
SOURCE = Path("data/specifications/story_lab/age18_forbidden_cartographer_mock_canonical_state_v1.json")


def _accept_audit() -> dict:
    return {
        "schema": "spineforge-v11-audit.v1",
        "decision": "ACCEPT",
        "dimensions": [
            {
                "name": name,
                "score": 5,
                "blocking_failure": False,
                "evidence": ["Specific evidence from the proposed spine."],
                "reason": "Protected in zero-cost control-flow verification.",
            }
            for name in sorted(AUDIT_DIMENSIONS)
        ],
        "blocking_defects": [],
        "repair_targets": [],
        "preserve": ["active protagonist", "evidence discipline"],
        "decision_reason": "Mock audit accepts the validated product.",
    }


def test_v12_real_v11_product_normalizes_then_reaches_auditor(tmp_path: Path):
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))
    architect_raw = copy.deepcopy(evidence["architect_raw"])
    pack_path = tmp_path / "pack.json"
    write_spine_context_pack(source_path=SOURCE, out_path=pack_path)

    outputs = [architect_raw, _accept_audit()]
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
        request = {
            "response_format": {"type": "json_object"},
            "provider": {"order": ["anthropic"]},
        }
        return raw, body, request, []

    result = run(
        context_pack_path=pack_path,
        out_path=tmp_path / "result.json",
        api_key="zero-cost-test",
        call_fn=fake_call,
    )

    assert result["status"] == "awaiting_human_review"
    assert len(calls) == 2
    assert result["mechanical_normalization"]["changed"] is True
    assert result["mechanical_normalization"]["changes"][0]["path"] == (
        "logistics_plan.location_sequence"
    )
    assert result["episode_spine"]["logistics_plan"]["location_sequence"] == [
        "vellum_hall", "greyfen", "ashen_gate", "greyfen"
    ]
    assert result["deterministic_checks"]["mechanical_normalization_valid"] is True
    assert result["deterministic_checks"]["episode_spine_contract_valid"] is True
    assert result["deterministic_checks"]["context_pack_authority_valid"] is True
    assert result["audit"]["decision"] == "ACCEPT"
    assert result["automatic_repair_enabled"] is False
    assert result["writer_authorized"] is False


def test_v12_semantic_failure_stops_before_auditor(tmp_path: Path):
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))
    architect_raw = copy.deepcopy(evidence["architect_raw"])
    architect_raw["reversal"]["evidence"][0]["certainty"] = "CERTAIN"
    pack_path = tmp_path / "pack.json"
    write_spine_context_pack(source_path=SOURCE, out_path=pack_path)
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        body = {
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 500,
                "total_tokens": 1500,
                "cost": 0.007,
            }
        }
        request = {"response_format": {"type": "json_object"}}
        return architect_raw, body, request, []

    result = run(
        context_pack_path=pack_path,
        out_path=tmp_path / "result.json",
        api_key="zero-cost-test",
        call_fn=fake_call,
    )

    assert result["status"] == "architect_contract_or_authority_rejected"
    assert len(calls) == 1
    assert result["automatic_repair_enabled"] is False
    assert result["writer_authorized"] is False
