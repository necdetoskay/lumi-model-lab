from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.spineforge_v11_contract import AUDIT_DIMENSIONS
from src.spineforge_v18 import run
from src.spineforge_v18_transport import (
    DIMENSION_ORDER,
    build_strict_audit_transport_schema,
    protected_dimension_set_is_exact,
    schema_size_bytes,
    transport_to_typed_audit,
)


SOURCE = Path("experiments/results/spineforge-v16/36760550050/result.json")


def _transport(decision="ACCEPT"):
    dims = {
        name: {
            "score": 4 if name != "REVERSAL_QUALITY" else 3,
            "blocking_failure": False,
            "evidence": f"{name} evidence.",
            "reason": f"{name} reason.",
        }
        for name in DIMENSION_ORDER
    }
    return {
        "decision": decision,
        "dimensions": dims,
        "blocking_defects": [],
        "repair_targets": [],
        "preserve": ["validated v16 spine"],
        "decision_reason": "Complete strict transport fixture.",
    }


def test_v18_strict_transport_schema_is_small_and_requires_all_dimensions():
    schema = build_strict_audit_transport_schema()
    assert protected_dimension_set_is_exact() is True
    assert set(schema["properties"]["dimensions"]["required"]) == AUDIT_DIMENSIONS
    assert schema["properties"]["dimensions"]["additionalProperties"] is False
    assert schema_size_bytes(schema) < 4096


def test_v18_transport_converts_to_existing_typed_audit():
    audit = transport_to_typed_audit(_transport())
    assert audit.decision == "ACCEPT"
    assert len(audit.dimensions) == 18
    assert {x.name for x in audit.dimensions} == AUDIT_DIMENSIONS


def test_v18_transport_missing_dimension_is_rejected():
    raw = _transport()
    del raw["dimensions"]["FRESHNESS"]
    with pytest.raises(ValueError):
        transport_to_typed_audit(raw)


def test_v18_runtime_is_single_strict_audit_only_call(tmp_path: Path):
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        body = {"usage": {"prompt_tokens": 1000, "completion_tokens": 600, "total_tokens": 1600, "cost": 0.008}}
        request = {
            "response_format": {"type": "json_schema", "json_schema": {"name": "spineforge_audit_transport_v18", "strict": True}},
            "provider": {"require_parameters": True},
        }
        return _transport(), body, request, []

    result = run(
        source_evidence_path=SOURCE,
        out_path=tmp_path / "result.json",
        api_key="zero-cost-test",
        call_fn=fake_call,
    )

    assert len(calls) == 1
    assert result["status"] == "awaiting_human_review"
    assert result["provider_strict_json_schema"] is True
    assert result["strict_schema_size_bytes"] < 4096
    assert result["audit_completeness"]["complete"] is True
    assert result["repair_called"] is False
    assert result["architect_recalled"] is False
    assert result["writer_authorized"] is False


def test_v18_repair_decision_still_requires_typed_targets():
    raw = _transport(decision="REPAIR")
    raw["dimensions"]["CAUSAL_COHERENCE"]["score"] = 2
    raw["dimensions"]["CAUSAL_COHERENCE"]["blocking_failure"] = True
    raw["blocking_defects"] = ["Causal logic remains unsupported."]
    raw["repair_targets"] = [{
        "path": "beats[5]",
        "defect_class": "CAUSALITY",
        "problem": "Evidence chain is incomplete.",
        "required_change": "Make the causal observation explicit.",
        "preserve": ["authority safety"],
    }]
    audit = transport_to_typed_audit(raw)
    assert audit.decision == "REPAIR"
    assert len(audit.repair_targets) == 1
