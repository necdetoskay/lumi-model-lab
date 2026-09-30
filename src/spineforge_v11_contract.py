from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


AUDIT_DIMENSIONS = {
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
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SpineAuditDimensionV11(StrictModel):
    name: Literal[
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
    score: int = Field(ge=1, le=5)
    blocking_failure: bool
    evidence: list[str] = Field(min_length=1, max_length=4)
    reason: str


class SpineRepairTargetV11(StrictModel):
    path: str
    defect_class: Literal[
        "STORY_DRIVE",
        "ROLEPLAY",
        "CHARACTER_AGENCY",
        "WORLD_SPECIFICITY",
        "AGE_MATURITY",
        "CAUSALITY",
        "ESCALATION",
        "REVERSAL",
        "DECISION",
        "CLIMAX",
        "PAYOFF",
        "SAGA",
        "AUTHORITY",
        "EXECUTABILITY",
        "FRESHNESS",
    ]
    problem: str
    required_change: str
    preserve: list[str] = Field(default_factory=list, max_length=5)


class SpineAuditV11(StrictModel):
    schema_id: Literal["spineforge-v11-audit.v1"] = Field(alias="schema")
    decision: Literal["ACCEPT", "REPAIR"]
    dimensions: list[SpineAuditDimensionV11]
    blocking_defects: list[str] = Field(default_factory=list, max_length=12)
    repair_targets: list[SpineRepairTargetV11] = Field(default_factory=list, max_length=12)
    preserve: list[str] = Field(default_factory=list, max_length=12)
    decision_reason: str

    @model_validator(mode="after")
    def validate_audit(self) -> "SpineAuditV11":
        names = [row.name for row in self.dimensions]
        if len(names) != len(set(names)) or set(names) != AUDIT_DIMENSIONS:
            raise ValueError("v11 audit must cover every protected dimension exactly once")

        minimums = {name: 4 for name in AUDIT_DIMENSIONS}
        minimums["REVERSAL_QUALITY"] = 3

        threshold_failures = [
            row.name for row in self.dimensions if row.score < minimums[row.name]
        ]
        blockers = [row.name for row in self.dimensions if row.blocking_failure]

        if self.decision == "ACCEPT":
            if threshold_failures or blockers:
                raise ValueError(
                    "ACCEPT misses protected thresholds: "
                    + ", ".join(sorted(set(threshold_failures + blockers)))
                )
            if self.blocking_defects or self.repair_targets:
                raise ValueError("ACCEPT cannot contain blocking defects or repair targets")
        else:
            if not (threshold_failures or blockers or self.blocking_defects):
                raise ValueError("REPAIR requires a concrete defect")
            if not self.repair_targets:
                raise ValueError("REPAIR requires targeted repair instructions")
        return self
