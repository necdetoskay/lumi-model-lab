from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.episode_spine_v3_contract import EpisodeBeatV2
from src.spineforge_v3_contract import SpineProductGateV1
from src.spineforge_v5_contract import SpineCreativeBlueprintV2, SpineStructuralAssemblyV1


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LogisticsDraftV1(StrictModel):
    time_window: str
    movement_constraints: list[str]
    feasibility_rationale: str


class StructuralFrameV1(StrictModel):
    schema_id: Literal["spineforge-structural-frame.v1"] = Field(alias="schema")
    preserved_creative_strengths: list[str] = Field(min_length=2, max_length=10)
    title: str
    episode_role: str
    story_promise: str
    protagonist_role: str
    immediate_objective: str
    central_question: str
    stakes: str
    constraints: list[str]
    opening_hook: str
    logistics: LogisticsDraftV1
    escalation_ladder: list[str]
    climax: str
    local_payoff: str
    forward_hook: str
    writer_rules: list[str]
    compilation_notes: list[str] = Field(default_factory=list, max_length=12)
    creative_deviations: list[str] = Field(default_factory=list, max_length=8)


class StructuralBeatsV1(StrictModel):
    schema_id: Literal["spineforge-structural-beats.v1"] = Field(alias="schema")
    beats: list[EpisodeBeatV2] = Field(min_length=8, max_length=12)

    @model_validator(mode="after")
    def validate_dependencies(self) -> "StructuralBeatsV1":
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


class ReversalEvidenceDraftV1(StrictModel):
    claim: str
    supporting_beat_keys: list[str]
    certainty: str


class ReversalDraftV1(StrictModel):
    prior_belief: str
    evidence: list[ReversalEvidenceDraftV1]
    reinterpretation: str
    inference_ceiling: str
    unresolved_after_reversal: str


class DecisionBranchDraftV1(StrictModel):
    key: str
    option: str
    immediate_action: str
    evidence_state_after_choice: str
    cost_or_risk: str
    relationship_or_access_effect: str
    climax_requirement: str
    local_payoff_if_earned: str


class DecisionDraftV1(StrictModel):
    pressure: str
    branches: list[DecisionBranchDraftV1]
    what_is_unknown: str

    @model_validator(mode="after")
    def validate_branches(self) -> "DecisionDraftV1":
        if len(self.branches) < 2:
            raise ValueError("decision point requires at least two credible branches")
        keys = [branch.key for branch in self.branches]
        if len(keys) != len(set(keys)):
            raise ValueError("decision branch keys must be unique")
        return self


class PersistentOutcomeDraftV1(StrictModel):
    type: str
    description: str
    commit_condition: str


class SagaProgressionDraftV1(StrictModel):
    completion_evidence: list[str]


class AntiRepetitionDraftV1(StrictModel):
    core_problem_shape: str
    primary_activity: str
    main_location_pattern: str
    climax_shape: str
    distinct_from_recent_episodes_because: str


class StructuralResolutionV1(StrictModel):
    schema_id: Literal["spineforge-structural-resolution.v1"] = Field(alias="schema")
    reversal: ReversalDraftV1
    decision_point: DecisionDraftV1
    persistent_outcome_candidates: list[PersistentOutcomeDraftV1]
    saga_progression: SagaProgressionDraftV1
    anti_repetition_signature: AntiRepetitionDraftV1


class SpineForgeRevisionFeedbackV7(StrictModel):
    schema_id: Literal["spineforge-revision-feedback.v7"] = Field(alias="schema")
    context_pack_id: str
    context_fingerprint: str
    source_attempt: int = Field(ge=1)
    next_attempt: int = Field(ge=2)
    source_status: str
    retry_stage: Literal[
        "CREATIVE_ARCHITECT",
        "STRUCTURAL_FRAME",
        "STRUCTURAL_BEATS",
        "STRUCTURAL_RESOLUTION",
    ]
    must_preserve: list[str] = Field(min_length=1, max_length=12)
    must_change: list[str] = Field(min_length=1, max_length=12)
    preserved_blueprint: dict[str, Any] | None = None
    preserved_frame: dict[str, Any] | None = None
    preserved_beats: dict[str, Any] | None = None
    validation_errors: list[str] = Field(default_factory=list, max_length=12)
    authority_freezes: list[str] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_feedback(self) -> "SpineForgeRevisionFeedbackV7":
        if self.next_attempt != self.source_attempt + 1:
            raise ValueError("next_attempt must equal source_attempt + 1")
        if self.retry_stage != "CREATIVE_ARCHITECT" and self.preserved_blueprint is None:
            raise ValueError("structural retry requires preserved_blueprint")
        if self.retry_stage in {"STRUCTURAL_BEATS", "STRUCTURAL_RESOLUTION"} and self.preserved_frame is None:
            raise ValueError("late structural retry requires preserved_frame")
        if self.retry_stage == "STRUCTURAL_RESOLUTION" and self.preserved_beats is None:
            raise ValueError("resolution retry requires preserved_beats")
        return self


class SpineForgeProductV7(StrictModel):
    schema_id: Literal["spineforge-product.v7"] = Field(alias="schema")
    status: Literal["AWAITING_HUMAN_REVIEW", "HUMAN_APPROVED", "REPLAN_REQUIRED"]
    context_pack_id: str
    context_fingerprint: str
    creative_blueprint: SpineCreativeBlueprintV2
    structural_frame: StructuralFrameV1
    structural_beats: StructuralBeatsV1
    structural_resolution: StructuralResolutionV1
    structural_assembly: SpineStructuralAssemblyV1
    product_gate: SpineProductGateV1
    deterministic_checks: dict[str, Any]
    lineage: dict[str, Any]
    human_review: dict[str, Any]
