from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.episode_spine_v3_contract import EpisodeSpineV3
from src.spineforge_v3_contract import CreativeSignatureV1

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
