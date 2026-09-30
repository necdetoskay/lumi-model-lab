from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.spineforge_v11_contract import SpineAuditV11
from src.spineforge_v13_audit_normalizer import normalize_audit_contract_aliases


RESULT = Path("experiments/results/spineforge-v12/36752663853/result.json")


def _raw():
    return json.loads(RESULT.read_text(encoding="utf-8"))["audit_raw"]


def test_exact_v12_audit_fails_before_alias_normalization():
    with pytest.raises(ValidationError) as exc:
        SpineAuditV11.model_validate(_raw())
    assert "CHARACTER_DRIVENESS" in str(exc.value)


def test_exact_v12_audit_passes_after_one_nonsemantic_alias_change():
    raw = _raw()
    normalized, report = normalize_audit_contract_aliases(raw)

    assert report.changed is True
    assert len(report.changes) == 1
    assert report.changes[0].before == "CHARACTER_DRIVENESS"
    assert report.changes[0].after == "CHARACTER_DRIVENNESS"
    assert report.changes[0].semantic_change is False

    audit = SpineAuditV11.model_validate(normalized)
    assert audit.decision == "REPAIR"
    assert len(audit.blocking_defects) == 6
    assert len(audit.repair_targets) == 5


def test_alias_normalization_changes_only_dimension_name():
    raw = _raw()
    normalized, _ = normalize_audit_contract_aliases(raw)

    expected = copy.deepcopy(raw)
    expected["dimensions"][3]["name"] = "CHARACTER_DRIVENNESS"
    assert normalized == expected


def test_alias_normalization_preserves_semantic_audit_payload():
    raw = _raw()
    normalized, report = normalize_audit_contract_aliases(raw)

    assert normalized["decision"] == raw["decision"]
    assert normalized["blocking_defects"] == raw["blocking_defects"]
    assert normalized["repair_targets"] == raw["repair_targets"]
    assert normalized["preserve"] == raw["preserve"]
    assert normalized["decision_reason"] == raw["decision_reason"]

    raw_scores = [(x["score"], x["blocking_failure"]) for x in raw["dimensions"]]
    new_scores = [(x["score"], x["blocking_failure"]) for x in normalized["dimensions"]]
    assert new_scores == raw_scores
    assert report.decision_unchanged is True
    assert report.scores_unchanged is True
    assert report.blockers_unchanged is True
    assert report.repair_targets_unchanged is True


def test_unknown_dimension_is_not_silently_rewritten():
    raw = _raw()
    raw["dimensions"][3]["name"] = "CHARACTER_STUFF"
    normalized, report = normalize_audit_contract_aliases(raw)
    assert report.changed is False
    with pytest.raises(ValidationError):
        SpineAuditV11.model_validate(normalized)
