from __future__ import annotations

import copy
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.episode_spine_v3_contract import EpisodeSpineV3
from src.spineforge_v3_contract import CreativeSignatureV1, SpineProductDimensionV1

AION_MODEL = "aion-labs/aion-3.5-mini"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SpineCreativeIntentV1(StrictModel):
    schema_id: Literal["spineforge-creative-intent.v1"] = Field(alias="schema")
    creative_model: str
    creative_signature: CreativeSignatureV1
    episode_spine: dict[str, Any]
    self_check_notes: list[str] = Field(default_factory=list, max_length=8)


class SpineStructuralCompilationV1(StrictModel):
    schema_id: Literal["spineforge-structural-compilation.v1"] = Field(alias="schema")
    decision: Literal["COMPILE", "REPLAN"]
    assessment_summary: str
    preserved_creative_strengths: list[str] = Field(min_length=2, max_length=8)
    compiled_spine: EpisodeSpineV3 | None
    replan_feedback: list[str] = Field(max_length=10)

    @model_validator(mode="after")
    def validate_decision(self) -> "SpineStructuralCompilationV1":
        if self.decision == "COMPILE":
            if self.compiled_spine is None:
                raise ValueError("COMPILE requires compiled_spine")
            if self.replan_feedback:
                raise ValueError("COMPILE cannot include replan_feedback")
        else:
            if self.compiled_spine is not None:
                raise ValueError("REPLAN cannot include compiled_spine")
            if not self.replan_feedback:
                raise ValueError("REPLAN requires concrete feedback")
        return self


class SpineProductGateV5(StrictModel):
    schema_id: Literal["spineforge-product-gate.v5"] = Field(alias="schema")
    dimensions: list[SpineProductDimensionV1]
    decision: Literal["ACCEPT", "REPLAN"]
    replan_target: Literal["AION_CREATIVE", "SONNET_STRUCTURAL"] | None
    blocking_reasons: list[str]
    decision_reason: str

    @model_validator(mode="after")
    def validate_gate(self) -> "SpineProductGateV5":
        expected = {
            "STORY_DESIRE","ROLEPLAY_POTENTIAL","SCENE_POTENTIAL",
            "CHARACTER_DRIVENNESS","WORLD_SPECIFICITY","WONDER_OR_INTRIGUE",
            "AGE_MATURITY","CAUSAL_COHERENCE","ESCALATION","REVERSAL_QUALITY",
            "AGENCY","BRANCH_EXECUTABILITY","CLIMAX_PAYOFF","LOCAL_SATISFACTION",
            "SAGA_ALIGNMENT","WRITER_EXECUTABILITY","FRESHNESS",
        }
        names = [row.name for row in self.dimensions]
        if len(names) != len(set(names)) or set(names) != expected:
            raise ValueError("Spine Product Gate must cover every dimension exactly once")
        if any(x.blocking_failure for x in self.dimensions) and self.decision != "REPLAN":
            raise ValueError("Any blocking failure requires REPLAN")
        if self.decision == "ACCEPT":
            if self.replan_target is not None or self.blocking_reasons:
                raise ValueError("ACCEPT cannot include replan target/blocking reasons")
            scores = {x.name: x.score for x in self.dimensions}
            minimums = {
                "STORY_DESIRE":4,"ROLEPLAY_POTENTIAL":4,"SCENE_POTENTIAL":4,
                "CHARACTER_DRIVENNESS":4,"WORLD_SPECIFICITY":4,"WONDER_OR_INTRIGUE":4,
                "AGE_MATURITY":4,"CAUSAL_COHERENCE":4,"ESCALATION":4,
                "REVERSAL_QUALITY":3,"AGENCY":4,"BRANCH_EXECUTABILITY":4,
                "CLIMAX_PAYOFF":4,"LOCAL_SATISFACTION":4,"SAGA_ALIGNMENT":4,
                "WRITER_EXECUTABILITY":4,"FRESHNESS":4,
            }
            misses = [f"{name}:{scores[name]}<{minimum}" for name, minimum in minimums.items()
                      if scores[name] < minimum]
            if misses:
                raise ValueError("ACCEPT misses protected product thresholds: " + ", ".join(misses))
        else:
            if self.replan_target is None:
                raise ValueError("REPLAN requires replan_target")
            if not self.blocking_reasons:
                raise ValueError("REPLAN requires blocking reasons")
        return self


class SpineForgeRevisionFeedbackV5(StrictModel):
    schema_id: Literal["spineforge-revision-feedback.v5"] = Field(alias="schema")
    context_pack_id: str
    context_fingerprint: str
    source_attempt: int = Field(ge=1)
    next_attempt: int = Field(ge=2)
    target_stage: Literal["AION_CREATIVE", "SONNET_STRUCTURAL"]
    source_status: Literal[
        "creative_intent_rejected",
        "structural_replan_required",
        "structural_compile_rejected",
        "product_replan_required",
        "human_revise",
    ]
    must_preserve: list[str] = Field(min_length=2, max_length=12)
    must_change: list[str] = Field(min_length=1, max_length=12)
    creative_feedback: list[str] = Field(max_length=12)
    structural_feedback: list[str] = Field(max_length=12)
    previous_creative_intent: dict[str, Any] | None
    previous_compiled_spine: dict[str, Any] | None
    validation_errors: list[str] = Field(max_length=12)
    authority_freezes: list[str] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_attempts(self) -> "SpineForgeRevisionFeedbackV5":
        if self.next_attempt != self.source_attempt + 1:
            raise ValueError("next_attempt must equal source_attempt + 1")
        if self.target_stage == "SONNET_STRUCTURAL" and self.previous_creative_intent is None:
            raise ValueError("SONNET_STRUCTURAL resume requires previous_creative_intent")
        return self


class SpineForgeProductV5(StrictModel):
    schema_id: Literal["spineforge-product.v5"] = Field(alias="schema")
    status: Literal["AWAITING_HUMAN_REVIEW"]
    context_pack_id: str
    context_fingerprint: str
    creative_intent: SpineCreativeIntentV1
    structural_compilation: SpineStructuralCompilationV1
    compiled_spine: EpisodeSpineV3
    product_gate: SpineProductGateV5
    deterministic_checks: dict[str, Any]
    lineage: dict[str, Any]
    human_review: dict[str, Any]


def migrate_v4_raw_to_v5_intent(raw: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(raw)
    value["schema"] = "spineforge-creative-intent.v1"
    value["creative_model"] = AION_MODEL
    return value
