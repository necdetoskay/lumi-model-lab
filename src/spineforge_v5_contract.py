from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.episode_spine_v3_contract import EpisodeSpineV3
from src.spineforge_v3_contract import CreativeSignatureV1, SpineProductGateV1


KEY_PATTERN = r"^[a-z][a-z0-9_]*$"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreativeMomentV5(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    location_ref: str
    scene_intent: str
    protagonist_move: str
    pressure_or_event: str
    change_or_discovery: str


class CreativeSpineSeedV5(StrictModel):
    schema_id: Literal["spineforge-creative-seed.v5"] = Field(alias="schema")
    creative_model: str
    creative_signature: CreativeSignatureV1
    working_title: str
    story_promise: str
    protagonist_role: str
    immediate_objective: str
    central_question: str
    stakes: str
    constraints: list[str] = Field(min_length=1, max_length=10)
    moments: list[CreativeMomentV5] = Field(min_length=6, max_length=12)
    decision_pressure: str
    decision_options: list[str] = Field(min_length=2, max_length=4)
    climax_intent: str
    local_payoff: str
    forward_hook: str
    writer_texture: list[str] = Field(min_length=2, max_length=8)

    @model_validator(mode="after")
    def validate_seed(self) -> "CreativeSpineSeedV5":
        keys = [moment.key for moment in self.moments]
        if len(keys) != len(set(keys)):
            raise ValueError("creative seed moment keys must be unique")
        return self


class StructuralCompileV5(StrictModel):
    schema_id: Literal["spineforge-structural-compile.v5"] = Field(alias="schema")
    decision: Literal["COMPILED", "REPLAN"]
    assessment_summary: str
    preserved_creative_strengths: list[str] = Field(min_length=2, max_length=8)
    compiler_notes: list[str] = Field(default_factory=list, max_length=10)
    episode_spine: EpisodeSpineV3 | None = None
    replan_feedback: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_decision(self) -> "StructuralCompileV5":
        if self.decision == "COMPILED":
            if self.episode_spine is None:
                raise ValueError("COMPILED requires episode_spine")
            if self.replan_feedback:
                raise ValueError("COMPILED cannot include replan_feedback")
        else:
            if self.episode_spine is not None:
                raise ValueError("REPLAN cannot include episode_spine")
            if not self.replan_feedback:
                raise ValueError("REPLAN requires concrete feedback")
        return self


class SpineForgeProductV5(StrictModel):
    schema_id: Literal["spineforge-product.v5"] = Field(alias="schema")
    context_pack_id: str
    context_fingerprint: str
    creative_seed: CreativeSpineSeedV5
    structural_compile: StructuralCompileV5
    product_gate: SpineProductGateV1
    deterministic_checks: dict[str, Any]
    lineage: dict[str, Any]
    human_review: dict[str, Any]
