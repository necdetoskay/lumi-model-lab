from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.spineforge_v16_partial_audit import PartialRepairAuditV16, repair_brief_from_partial


SOURCE = Path("experiments/results/spineforge-v15/36757835721/result.json")


def _raw():
    return json.loads(SOURCE.read_text(encoding="utf-8"))["reaudit_raw"]


def test_exact_v15_raw_audit_recovers_as_partial_repair_only():
    audit = PartialRepairAuditV16.model_validate(_raw())
    assert audit.decision == "REPAIR"
    assert len(audit.present_dimensions) == 17
    assert audit.missing_dimensions == ["FRESHNESS"]
    assert len(audit.blocking_defects) == 4
    assert len(audit.repair_targets) == 3
    brief = repair_brief_from_partial(audit)
    assert brief["audit_completeness"]["present_count"] == 17
    assert brief["audit_completeness"]["required_count"] == 18
    assert brief["audit_completeness"]["acceptance_forbidden_from_partial_audit"] is True


def test_partial_audit_can_never_be_accept():
    raw = copy.deepcopy(_raw())
    raw["decision"] = "ACCEPT"
    raw["blocking_defects"] = []
    raw["repair_targets"] = []
    with pytest.raises(ValidationError):
        PartialRepairAuditV16.model_validate(raw)


def test_partial_audit_rejects_duplicate_dimension():
    raw = copy.deepcopy(_raw())
    raw["dimensions"].append(copy.deepcopy(raw["dimensions"][0]))
    with pytest.raises(ValidationError):
        PartialRepairAuditV16.model_validate(raw)
