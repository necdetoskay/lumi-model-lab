from __future__ import annotations

import copy
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.episode_spine_v3_contract import EpisodeSpineV3
from src.spineforge_v3_contract import CreativeSignatureV1

AION_MODEL = "aion-labs/aion-3.5-mini"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SpineCreativeIntentV1(StrictModel):
    """Creative artifact: rich proposal, not strict structural authority."""

    schema_id: Literal["spineforge-creative-intent.v1"] = Field(alias="schema")
    creative_model: str
    creative_signature: CreativeSignatureV1
    episode_spine: dict[str, Any]
    self_check_notes: list[str] = Field(default_factory=list, max_length=8)


class SpineStructuralCompilationV1(StrictModel):
    """Sonnet-owned strict structural compilation boundary."""

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


def migrate_v4_raw_to_v5_intent(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Envelope-only migration for archived v4 Aion evidence.

    The nested episode_spine proposal is copied byte-for-structure and is not
    normalized into EpisodeSpineV3 here. v5 deliberately moves that strict
    structural responsibility to Sonnet.
    """
    value = copy.deepcopy(raw)
    value["schema"] = "spineforge-creative-intent.v1"
    value["creative_model"] = AION_MODEL
    return value
