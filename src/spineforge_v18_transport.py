from __future__ import annotations

import json
from typing import Any

from src.spineforge_v11_contract import AUDIT_DIMENSIONS, SpineAuditV11


DIMENSION_ORDER = [
    "STORY_DESIRE",
    "ROLEPLAY_POTENTIAL",
    "SCENE_POTENTIAL",
    "CHARACTER_DRIVENNESS",
    "WORLD_SPECIFICITY",
    "WONDER_OR_INTRIGUE",
    "AGE_MATURITY",
    "CAUSAL_COHERENCE",
    "ESCALATION",
    "REVERSAL_QUALITY",
    "AGENCY",
    "BRANCH_EXECUTABILITY",
    "CLIMAX_PAYOFF",
    "LOCAL_SATISFACTION",
    "SAGA_ALIGNMENT",
    "AUTHORITY_SAFETY",
    "WRITER_EXECUTABILITY",
    "FRESHNESS",
]


def build_strict_audit_transport_schema() -> dict[str, Any]:
    dimension_ref = {"$ref": "#/$defs/dimension"}
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "decision": {"type": "string"},
            "dimensions": {
                "type": "object",
                "additionalProperties": False,
                "properties": {name: dimension_ref for name in DIMENSION_ORDER},
                "required": DIMENSION_ORDER,
            },
            "blocking_defects": {"type": "array", "items": {"type": "string"}},
            "repair_targets": {
                "type": "array",
                "items": {"$ref": "#/$defs/repair_target"},
            },
            "preserve": {"type": "array", "items": {"type": "string"}},
            "decision_reason": {"type": "string"},
        },
        "required": [
            "decision",
            "dimensions",
            "blocking_defects",
            "repair_targets",
            "preserve",
            "decision_reason",
        ],
        "$defs": {
            "dimension": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "score": {"type": "integer"},
                    "blocking_failure": {"type": "boolean"},
                    "evidence": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["score", "blocking_failure", "evidence", "reason"],
            },
            "repair_target": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "path": {"type": "string"},
                    "defect_class": {"type": "string"},
                    "problem": {"type": "string"},
                    "required_change": {"type": "string"},
                    "preserve": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "path",
                    "defect_class",
                    "problem",
                    "required_change",
                    "preserve",
                ],
            },
        },
    }


def schema_size_bytes(schema: dict[str, Any] | None = None) -> int:
    value = schema or build_strict_audit_transport_schema()
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def transport_to_typed_audit(raw: dict[str, Any]) -> SpineAuditV11:
    dimensions = raw.get("dimensions")
    if not isinstance(dimensions, dict):
        raise ValueError("strict audit transport dimensions must be an object")

    if set(dimensions) != set(DIMENSION_ORDER):
        missing = sorted(set(DIMENSION_ORDER) - set(dimensions))
        extra = sorted(set(dimensions) - set(DIMENSION_ORDER))
        raise ValueError(f"strict audit dimension set mismatch missing={missing} extra={extra}")

    payload = {
        "schema": "spineforge-v11-audit.v1",
        "decision": raw.get("decision"),
        "dimensions": [
            {
                "name": name,
                "score": dimensions[name].get("score"),
                "blocking_failure": dimensions[name].get("blocking_failure"),
                "evidence": [dimensions[name].get("evidence")],
                "reason": dimensions[name].get("reason"),
            }
            for name in DIMENSION_ORDER
        ],
        "blocking_defects": raw.get("blocking_defects") or [],
        "repair_targets": raw.get("repair_targets") or [],
        "preserve": raw.get("preserve") or [],
        "decision_reason": raw.get("decision_reason"),
    }
    return SpineAuditV11.model_validate(payload)


def protected_dimension_set_is_exact() -> bool:
    return set(DIMENSION_ORDER) == AUDIT_DIMENSIONS and len(DIMENSION_ORDER) == len(AUDIT_DIMENSIONS)
