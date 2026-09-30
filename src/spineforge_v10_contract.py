from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.episode_spine_v3_contract import EpisodeBeatV2, KEY_PATTERN


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


EpisodeRoleV10 = Literal[
    "MAIN_SAGA_ENTRY",
    "MAIN_SAGA_PROGRESS",
    "SIDE_SAGA",
    "WORLD_EXPLORATION",
    "RELATIONSHIP",
    "SAGA_FREE",
    "MIXED",
]

ReversalCertaintyV10 = Literal["OBSERVED", "INFERRED", "HYPOTHESIS"]

PersistentOutcomeTypeV10 = Literal[
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


class LogisticsDraftV10(StrictModel):
    time_window: str
    movement_constraints: list[str]
    feasibility_rationale: str


class StructuralFrameV10(StrictModel):
    schema_id: Literal["spineforge-structural-frame.v1"] = Field(alias="schema")
    preserved_creative_strengths: list[str] = Field(min_length=2, max_length=10)
    title: str
    episode_role: EpisodeRoleV10
    story_promise: str
    protagonist_role: str
    immediate_objective: str
    central_question: str
    stakes: str
    constraints: list[str]
    opening_hook: str
    logistics: LogisticsDraftV10
    escalation_ladder: list[str]
    climax: str
    local_payoff: str
    forward_hook: str
    writer_rules: list[str]
    compilation_notes: list[str] = Field(default_factory=list, max_length=12)
    creative_deviations: list[str] = Field(default_factory=list, max_length=8)


class StructuralBeatsV10(StrictModel):
    schema_id: Literal["spineforge-structural-beats.v1"] = Field(alias="schema")
    beats: list[EpisodeBeatV2] = Field(min_length=8, max_length=12)

    @model_validator(mode="after")
    def validate_dependencies(self) -> "StructuralBeatsV10":
        keys = [beat.key for beat in self.beats]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate beat key")
        seen: set[str] = set()
        for index, beat in enumerate(self.beats):
            if index > 0 and not beat.causal_dependency_keys:
                raise ValueError(f"{beat.key}: non-opening beat needs a causal dependency")
            invalid = [ref for ref in beat.causal_dependency_keys if ref not in seen]
            if invalid:
                raise ValueError(
                    f"{beat.key}: dependencies must reference earlier beats: "
                    + ", ".join(invalid)
                )
            seen.add(beat.key)
        return self


class ReversalEvidenceDraftV10(StrictModel):
    claim: str
    supporting_beat_keys: list[str]
    certainty: ReversalCertaintyV10


class ReversalDraftV10(StrictModel):
    prior_belief: str
    evidence: list[ReversalEvidenceDraftV10]
    reinterpretation: str
    inference_ceiling: str
    unresolved_after_reversal: str


class DecisionBranchDraftV10(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    option: str
    immediate_action: str
    evidence_state_after_choice: str
    cost_or_risk: str
    relationship_or_access_effect: str
    climax_requirement: str
    local_payoff_if_earned: str


class DecisionDraftV10(StrictModel):
    pressure: str
    branches: list[DecisionBranchDraftV10]
    what_is_unknown: str

    @model_validator(mode="after")
    def validate_branches(self) -> "DecisionDraftV10":
        if len(self.branches) < 2:
            raise ValueError("decision point requires at least two credible branches")
        keys = [branch.key for branch in self.branches]
        if len(keys) != len(set(keys)):
            raise ValueError("decision branch keys must be unique")
        return self


class PersistentOutcomeDraftV10(StrictModel):
    type: PersistentOutcomeTypeV10
    description: str
    commit_condition: str


class SagaProgressionDraftV10(StrictModel):
    completion_evidence: list[str]


class AntiRepetitionDraftV10(StrictModel):
    core_problem_shape: str
    primary_activity: str
    main_location_pattern: str
    climax_shape: str
    distinct_from_recent_episodes_because: str


class StructuralResolutionV10(StrictModel):
    schema_id: Literal["spineforge-structural-resolution.v1"] = Field(alias="schema")
    reversal: ReversalDraftV10
    decision_point: DecisionDraftV10
    persistent_outcome_candidates: list[PersistentOutcomeDraftV10]
    saga_progression: SagaProgressionDraftV10
    anti_repetition_signature: AntiRepetitionDraftV10
