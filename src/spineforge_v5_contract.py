from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.episode_spine_v3_contract import EpisodeSpineV3
from src.spineforge_v3_contract import CreativeSignatureV1, SpineProductGateV1

KEY_PATTERN = r"^[a-z][a-z0-9_]*$"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreativeEpisodeIntentV2(StrictModel):
    title: str
    story_promise: str
    protagonist_role: str
    immediate_objective: str
    central_question: str
    stakes: str
    opening_hook: str
    decision_pressure: str
    climax_idea: str
    local_payoff: str
    forward_hook: str
    unresolved_question: str
    constraints: list[str] = Field(default_factory=list, max_length=8)


class CreativeBeatV2(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    location_ref: str
    dramatic_function: str
    character_action: str
    external_pressure_or_event: str
    discovery_or_change: str
    causal_dependency_keys: list[str] = Field(default_factory=list)


class SpineCreativeBlueprintV2(StrictModel):
    schema_id: Literal["spineforge-creative-blueprint.v2"] = Field(alias="schema")
    creative_model: str
    creative_signature: CreativeSignatureV1
    episode_intent: CreativeEpisodeIntentV2
    creative_beats: list[CreativeBeatV2] = Field(min_length=5, max_length=14)
    roleplay_threads: list[str] = Field(default_factory=list, max_length=8)
    self_check_notes: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_blueprint(self) -> "SpineCreativeBlueprintV2":
        keys = [beat.key for beat in self.creative_beats]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate creative beat key")

        seen: set[str] = set()
        for beat in self.creative_beats:
            invalid = [
                ref for ref in beat.causal_dependency_keys
                if ref not in seen
            ]
            if invalid:
                raise ValueError(
                    f"{beat.key}: creative dependencies must reference earlier beats: "
                    + ", ".join(invalid)
                )
            seen.add(beat.key)
        return self


class SpineStructuralAssemblyV1(StrictModel):
    schema_id: Literal["spineforge-structural-assembly.v1"] = Field(alias="schema")
    structural_model: str
    preserved_creative_strengths: list[str] = Field(min_length=2, max_length=10)
    episode_spine: EpisodeSpineV3
    compilation_notes: list[str] = Field(default_factory=list, max_length=12)
    creative_deviations: list[str] = Field(default_factory=list, max_length=8)


class SpineForgeRevisionFeedbackV5(StrictModel):
    schema_id: Literal["spineforge-revision-feedback.v5"] = Field(alias="schema")
    context_pack_id: str
    context_fingerprint: str
    source_attempt: int = Field(ge=1)
    next_attempt: int = Field(ge=2)
    source_status: Literal[
        "creative_blueprint_contract_rejected",
        "structural_assembly_contract_rejected",
        "product_replan_required",
        "human_revise",
    ]
    retry_stage: Literal["CREATIVE_ARCHITECT", "STRUCTURAL_COMPILER"]
    must_preserve: list[str] = Field(min_length=1, max_length=12)
    must_change: list[str] = Field(min_length=1, max_length=12)
    creative_feedback: list[str] = Field(default_factory=list, max_length=12)
    structural_feedback: list[str] = Field(default_factory=list, max_length=12)
    preserved_blueprint: dict[str, Any] | None = None
    validation_errors: list[str] = Field(default_factory=list, max_length=12)
    authority_freezes: list[str] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_feedback(self) -> "SpineForgeRevisionFeedbackV5":
        if self.next_attempt != self.source_attempt + 1:
            raise ValueError("next_attempt must equal source_attempt + 1")
        if self.retry_stage == "STRUCTURAL_COMPILER" and self.preserved_blueprint is None:
            raise ValueError("STRUCTURAL_COMPILER retry requires preserved_blueprint")
        return self


class SpineForgeProductV5(StrictModel):
    schema_id: Literal["spineforge-product.v5"] = Field(alias="schema")
    status: Literal["AWAITING_HUMAN_REVIEW", "HUMAN_APPROVED", "REPLAN_REQUIRED"]
    context_pack_id: str
    context_fingerprint: str
    creative_blueprint: SpineCreativeBlueprintV2
    structural_assembly: SpineStructuralAssemblyV1
    product_gate: SpineProductGateV1
    deterministic_checks: dict[str, Any]
    lineage: dict[str, Any]
    human_review: dict[str, Any]
