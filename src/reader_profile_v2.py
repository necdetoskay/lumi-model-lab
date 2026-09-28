from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SCHEMA_ID = "reader-development-profile.v2"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReadingSessionBand(StrictModel):
    name: Literal["QUICK", "STANDARD", "LONG", "SPECIAL"]
    target_minutes_min: int = Field(ge=1)
    target_minutes_max: int = Field(ge=1)
    target_words_min: int = Field(ge=100)
    target_words_max: int = Field(ge=100)

    @model_validator(mode="after")
    def validate_ranges(self) -> "ReadingSessionBand":
        if self.target_minutes_min > self.target_minutes_max:
            raise ValueError("minutes min cannot exceed max")
        if self.target_words_min > self.target_words_max:
            raise ValueError("words min cannot exceed max")
        return self


class DevelopmentDimension(StrictModel):
    name: Literal[
        "PREMISE_MATURITY",
        "NARRATIVE_COMPLEXITY",
        "CONCEPTUAL_COMPLEXITY",
        "CAUSAL_DEPTH",
        "INFERENCE_DEMAND",
        "AGENCY_COMPLEXITY",
        "STAKES_CONSEQUENCE_COMPLEXITY",
        "SOCIAL_RELATIONSHIP_COMPLEXITY",
        "PREDICTABILITY_CHALLENGE",
        "WONDER_DISCOVERY",
        "LANGUAGE_READABILITY",
    ]
    target_level: int = Field(ge=1, le=5)
    description: str


class ReaderDevelopmentProfileV2(StrictModel):
    schema_id: Literal[SCHEMA_ID] = Field(alias="schema")
    profile_id: str
    exact_age: int = Field(ge=3, le=120)
    audience_band: Literal[
        "YOUNG_CHILD",
        "MIDDLE_CHILD",
        "OLDER_CHILD",
        "TEEN",
        "ADULT",
        "MATURE_ADULT",
    ]
    developmental_stage: str
    dimensions: list[DevelopmentDimension]
    standard_session: ReadingSessionBand
    optional_sessions: list[ReadingSessionBand]
    required_story_capabilities: list[str]
    reject_signals: list[str]
    language_rules: list[str]
    safety_rules: list[str]
    calibration_notes: list[str]

    @model_validator(mode="after")
    def validate_profile(self) -> "ReaderDevelopmentProfileV2":
        names = [item.name for item in self.dimensions]
        if len(names) != len(set(names)):
            raise ValueError("duplicate development dimension")
        required = {
            "PREMISE_MATURITY",
            "NARRATIVE_COMPLEXITY",
            "CONCEPTUAL_COMPLEXITY",
            "CAUSAL_DEPTH",
            "INFERENCE_DEMAND",
            "AGENCY_COMPLEXITY",
            "STAKES_CONSEQUENCE_COMPLEXITY",
            "SOCIAL_RELATIONSHIP_COMPLEXITY",
            "PREDICTABILITY_CHALLENGE",
            "WONDER_DISCOVERY",
            "LANGUAGE_READABILITY",
        }
        if set(names) != required:
            missing = sorted(required - set(names))
            extra = sorted(set(names) - required)
            raise ValueError(
                f"development dimensions must be complete; missing={missing}, extra={extra}"
            )

        if self.standard_session.name != "STANDARD":
            raise ValueError("standard_session must use STANDARD name")

        optional_names = [item.name for item in self.optional_sessions]
        if "STANDARD" in optional_names:
            raise ValueError("STANDARD belongs only in standard_session")
        if len(optional_names) != len(set(optional_names)):
            raise ValueError("duplicate optional session band")

        if not self.required_story_capabilities:
            raise ValueError("required_story_capabilities cannot be empty")
        if not self.reject_signals:
            raise ValueError("reject_signals cannot be empty")
        return self
