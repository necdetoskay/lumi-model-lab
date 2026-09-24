from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class StorySpec(BaseModel):
    title_hint: str | None = None
    age_min: int = Field(default=6, ge=3, le=120)
    age_max: int = Field(default=8, ge=3, le=120)
    language: str = "tr"
    target_words: int = Field(default=2000, ge=300, le=5000)
    narrative_family: str | None = None
    reading_mode: str | None = None
    relative_length_class: str | None = None
    protagonist: str
    setting: str
    theme: str
    premise: str
    constraints: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_age_range(self) -> "StorySpec":
        if self.age_min > self.age_max:
            raise ValueError("age_min must be less than or equal to age_max")
        return self


class TokenUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class CostInfo(BaseModel):
    usd: float | None = None
    try_amount: float | None = None
    usd_try_rate: float | None = None


class TechnicalValidation(BaseModel):
    status: str
    eligible_for_judge: bool
    word_count: int
    target_words: int
    min_words: int
    max_words: int
    finish_reason: str | None = None
    reasons: list[str] = Field(default_factory=list)


class GenerationRecord(BaseModel):
    id: str
    created_at: datetime
    teacher_model: str
    provider: str = "openrouter"
    prompt_version: str
    spec: StorySpec
    story: str
    usage: TokenUsage
    cost: CostInfo
    technical_validation: TechnicalValidation
    request: dict[str, Any]
    response_meta: dict[str, Any] = Field(default_factory=dict)


JUDGE_CRITERIA = (
    "instruction_following",
    "coherence",
    "character_consistency",
    "age_appropriateness",
    "creativity",
    "style_quality",
)


class JudgePayload(BaseModel):
    scores: dict[str, int]
    reasons: dict[str, str]
    critical_failures: list[str] = Field(default_factory=list)


class JudgeDecision(BaseModel):
    accepted: bool
    average_score: float
    minimum_score: int
    acceptance_threshold: float
    minimum_criterion_score: int
    reasons: list[str] = Field(default_factory=list)


class JudgeRecord(BaseModel):
    id: str
    created_at: datetime
    source_story_id: str
    source_path: str
    teacher_model: str
    judge_model: str
    judge_prompt_version: str
    result: JudgePayload
    decision: JudgeDecision
    usage: TokenUsage
    cost: CostInfo
    response_meta: dict[str, Any] = Field(default_factory=dict)
