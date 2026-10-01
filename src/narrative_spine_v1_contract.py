from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


NARRATIVE_SPINE_SCHEMA = "narrative-spine.v1"
GATE_SCHEMA = "spineforge-v19-product-gate.v1"
KEY_PATTERN = r"^[a-z][a-z0-9_]*$"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EpisodeConceptV1(StrictModel):
    story_promise: str = Field(min_length=1)
    story_family: str = Field(min_length=1)
    tone: str = Field(min_length=1)
    target_reader_effect: str = Field(min_length=1)


class ProtagonistIntentV1(StrictModel):
    role: str = Field(min_length=1)
    immediate_goal: str = Field(min_length=1)
    pressure: str = Field(min_length=1)


class WorldSpecificElementV1(StrictModel):
    context_ref: str = Field(min_length=1)
    narrative_use: str = Field(min_length=1)


class NarrativeBeatV1(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    location_ref: str = Field(min_length=1)
    character_action: str = Field(min_length=1)
    external_change: str = Field(min_length=1)
    new_information: str = Field(min_length=1)
    consequence: str = Field(min_length=1)
    escalation: str = Field(min_length=1)


class DecisionOptionV1(StrictModel):
    option: str = Field(min_length=1)
    immediate_cost: str = Field(min_length=1)
    possible_consequence: str = Field(min_length=1)


class NarrativeDecisionV1(StrictModel):
    required: bool
    pressure: str = ""
    options: list[DecisionOptionV1] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def validate_decision(self) -> "NarrativeDecisionV1":
        if self.required:
            if not self.pressure.strip():
                raise ValueError("required decision needs pressure")
            if len(self.options) < 2:
                raise ValueError("required decision needs at least two credible options")
        elif self.options and len(self.options) < 2:
            raise ValueError("optional decision with options still needs at least two options")
        return self


class PersistentOutcomeCandidateV1(StrictModel):
    type: Literal[
        "KNOWLEDGE",
        "RELATIONSHIP",
        "REPUTATION",
        "ACCESS",
        "ITEM",
        "RUMOR",
        "OPPORTUNITY",
        "LOCATION_STATE",
        "SAGA_STATE",
    ]
    description: str = Field(min_length=1)
    commit_condition: str = Field(min_length=1)


class NarrativeSpineV1(StrictModel):
    schema_id: Literal[NARRATIVE_SPINE_SCHEMA] = Field(alias="schema")
    title: str = Field(min_length=1)
    episode_concept: EpisodeConceptV1
    protagonist: ProtagonistIntentV1
    central_question: str = Field(min_length=1)
    stakes: str = Field(min_length=1)
    world_specific_elements: list[WorldSpecificElementV1] = Field(min_length=1, max_length=12)
    beats: list[NarrativeBeatV1] = Field(min_length=3, max_length=14)
    decision: NarrativeDecisionV1
    climax: str = Field(min_length=1)
    local_payoff: str = Field(min_length=1)
    unresolved_hooks: list[str] = Field(default_factory=list, max_length=8)
    reveal_limits: list[str] = Field(default_factory=list, min_length=1, max_length=12)
    persistent_outcome_candidates: list[PersistentOutcomeCandidateV1] = Field(
        default_factory=list, min_length=1, max_length=10
    )
    writer_rules: list[str] = Field(default_factory=list, min_length=1, max_length=16)

    @model_validator(mode="after")
    def validate_spine(self) -> "NarrativeSpineV1":
        keys = [beat.key for beat in self.beats]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate beat key")
        return self


class GateFindingV1(StrictModel):
    dimension: Literal[
        "PREMISE_MATURITY",
        "ROLEPLAY",
        "AGENCY",
        "CAUSALITY",
        "DISCOVERY",
        "STAKES",
        "WORLD_SPECIFICITY",
        "DECISION_QUALITY",
        "CLIMAX_PAYOFF",
        "AGE_FIT",
        "CANON_REVEAL",
        "WRITER_EXECUTABILITY",
        "FRESHNESS",
    ]
    severity: Literal["BLOCKER", "MAJOR"]
    repairability: Literal["LOCAL", "STRUCTURAL", "PREMISE"]
    target_path: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    evidence: str = Field(min_length=1)


class SpineProductGateV19(StrictModel):
    schema_id: Literal[GATE_SCHEMA] = Field(alias="schema")
    decision: Literal["ACCEPT", "REPAIR", "REPLAN"]
    blocking_findings: list[GateFindingV1] = Field(max_length=12)
    summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_gate(self) -> "SpineProductGateV19":
        if self.decision == "ACCEPT" and self.blocking_findings:
            raise ValueError("ACCEPT cannot contain blocking findings")
        if self.decision != "ACCEPT" and not self.blocking_findings:
            raise ValueError(f"{self.decision} requires concrete blocking findings")
        if self.decision == "REPAIR":
            if any(row.repairability != "LOCAL" for row in self.blocking_findings):
                raise ValueError("REPAIR may contain only LOCAL findings")
        if self.decision == "REPLAN":
            if not any(
                row.repairability in {"STRUCTURAL", "PREMISE"}
                for row in self.blocking_findings
            ):
                raise ValueError("REPLAN requires STRUCTURAL or PREMISE finding")
        return self
