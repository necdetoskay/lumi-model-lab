from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.spineforge_v11_contract import AUDIT_DIMENSIONS, SpineAuditV11


def _dimensions(score: int = 5):
    return [
        {
            "name": name,
            "score": score,
            "blocking_failure": False,
            "evidence": ["Specific evidence from the proposed spine."],
            "reason": "Audited against the protected dimension.",
        }
        for name in sorted(AUDIT_DIMENSIONS)
    ]


def test_v11_accept_requires_all_protected_dimensions():
    value = SpineAuditV11.model_validate({
        "schema": "spineforge-v11-audit.v1",
        "decision": "ACCEPT",
        "dimensions": _dimensions(),
        "blocking_defects": [],
        "repair_targets": [],
        "preserve": ["dramatic engine"],
        "decision_reason": "No protected defect remains.",
    })
    assert value.decision == "ACCEPT"
    assert {x.name for x in value.dimensions} == AUDIT_DIMENSIONS


def test_v11_accept_rejects_weak_roleplay():
    rows = _dimensions()
    for row in rows:
        if row["name"] == "ROLEPLAY_POTENTIAL":
            row["score"] = 3
    with pytest.raises(ValidationError):
        SpineAuditV11.model_validate({
            "schema": "spineforge-v11-audit.v1",
            "decision": "ACCEPT",
            "dimensions": rows,
            "blocking_defects": [],
            "repair_targets": [],
            "preserve": [],
            "decision_reason": "Should fail.",
        })


def test_v11_repair_requires_targeted_change():
    with pytest.raises(ValidationError):
        SpineAuditV11.model_validate({
            "schema": "spineforge-v11-audit.v1",
            "decision": "REPAIR",
            "dimensions": _dimensions(3),
            "blocking_defects": ["Weak episode."],
            "repair_targets": [],
            "preserve": [],
            "decision_reason": "Repair requested without target.",
        })
