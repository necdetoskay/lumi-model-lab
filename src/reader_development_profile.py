from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SCHEMA_ID = "reader-development-profile.v1"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DimensionBand(StrictModel):
    floor: int = Field(ge=1, le=5)
    target: int = Field(ge=1, le=5)
    ceiling: int = Field(ge=1, le=5)
    guidance: list[str]

    @model_validator(mode="after")
    def validate_order(self) -> "DimensionBand":
        if not (self.floor <= self.target <= self.ceiling):
            raise ValueError("dimension band must satisfy floor <= target <= ceiling")
        return self


class HardFailSignal(StrictModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    description: str
    applies_to_modes: list[str]
    severity: Literal["REPLAN"]


class ReaderDevelopmentProfileV1(StrictModel):
    schema_id: Literal[SCHEMA_ID] = Field(alias="schema")
    profile_id: str = Field(pattern=r"^[a-z][a-z0-9_\-]*$")
    exact_age: int = Field(ge=1, le=120)
    narrative_age_tier: str
    reading_mode: str
    target_modes: list[str]

    premise_maturity: DimensionBand
    narrative_complexity: DimensionBand
    conceptual_complexity: DimensionBand
    interest_fit: DimensionBand
    language_readability: DimensionBand
    agency_expectation: DimensionBand
    inference_causality: DimensionBand
    stakes_complexity: DimensionBand
    wonder_discovery: DimensionBand
    social_emotional_complexity: DimensionBand

    predictability_rule: str
    safety_content_envelope: list[str]
    positive_signals: list[str]
    hard_fail_signals: list[HardFailSignal]
    notes: list[str]

    @model_validator(mode="after")
    def validate_profile(self) -> "ReaderDevelopmentProfileV1":
        if not self.target_modes:
            raise ValueError("target_modes cannot be empty")
        if not self.hard_fail_signals:
            raise ValueError("hard_fail_signals cannot be empty")

        keys = [row.key for row in self.hard_fail_signals]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate hard_fail_signals")

        if self.exact_age >= 10 and self.language_readability.target > self.premise_maturity.target + 2:
            raise ValueError(
                "language_readability cannot mask a materially lower premise maturity target"
            )

        return self


def validate_capability_bridge(profile: ReaderDevelopmentProfileV1) -> None:
    from src.capability_cube import (
        default_reading_mode_for_age_tier,
        narrative_age_tier_for_range,
    )

    expected_tier = narrative_age_tier_for_range(profile.exact_age, profile.exact_age)
    if profile.narrative_age_tier != expected_tier:
        raise ValueError(
            f"exact_age {profile.exact_age} maps to {expected_tier}, "
            f"not {profile.narrative_age_tier}"
        )

    expected_mode = default_reading_mode_for_age_tier(profile.narrative_age_tier)
    if profile.reading_mode != expected_mode:
        raise ValueError(
            f"{profile.narrative_age_tier} reading_mode must be {expected_mode}, "
            f"got {profile.reading_mode}"
        )
