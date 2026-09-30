from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.spineforge_v11_contract import AUDIT_DIMENSIONS, SpineAuditDimensionV11, SpineRepairTargetV11


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PartialRepairAuditV16(StrictModel):
    schema_id: Literal["spineforge-v11-audit.v1"] = Field(alias="schema")
    decision: Literal["REPAIR"]
    dimensions: list[SpineAuditDimensionV11] = Field(min_length=1)
    blocking_defects: list[str] = Field(min_length=1, max_length=12)
    repair_targets: list[SpineRepairTargetV11] = Field(min_length=1, max_length=12)
    preserve: list[str] = Field(default_factory=list, max_length=12)
    decision_reason: str

    @model_validator(mode="after")
    def validate_partial_repair(self) -> "PartialRepairAuditV16":
        names = [row.name for row in self.dimensions]
        if len(names) != len(set(names)):
            raise ValueError("partial REPAIR audit cannot duplicate protected dimensions")
        if not set(names).issubset(AUDIT_DIMENSIONS):
            raise ValueError("partial REPAIR audit contains unknown protected dimension")
        return self

    @property
    def present_dimensions(self) -> list[str]:
        return sorted(row.name for row in self.dimensions)

    @property
    def missing_dimensions(self) -> list[str]:
        return sorted(AUDIT_DIMENSIONS - set(self.present_dimensions))


def repair_brief_from_partial(audit: PartialRepairAuditV16) -> dict:
    return {
        "decision": "REPAIR",
        "audit_completeness": {
            "present_count": len(audit.present_dimensions),
            "required_count": len(AUDIT_DIMENSIONS),
            "present_dimensions": audit.present_dimensions,
            "missing_dimensions": audit.missing_dimensions,
            "acceptance_forbidden_from_partial_audit": True,
        },
        "blocking_defects": list(audit.blocking_defects),
        "repair_targets": [row.model_dump(mode="json") for row in audit.repair_targets],
        "preserve": list(audit.preserve),
        "decision_reason": audit.decision_reason,
        "weak_dimensions": [
            {
                "name": row.name,
                "score": row.score,
                "blocking_failure": row.blocking_failure,
                "reason": row.reason,
            }
            for row in audit.dimensions
            if row.score < 4 or row.blocking_failure
        ],
    }
