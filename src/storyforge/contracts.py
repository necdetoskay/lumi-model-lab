from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StoryForgeFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    kind: Literal["canon", "state", "guard", "meta"] = "state"


class StoryIntentReferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_fact_ids: list[str] = Field(default_factory=list)
    hard_guard_fact_ids: list[str] = Field(default_factory=list)


class StoryForgeIntent(BaseModel):
    model_config = ConfigDict(extra="allow")

    family: str
    opportunity: str
    stakes: str = "low"
    fantasy_allowed: bool = False
    references: StoryIntentReferences
    hard_constraints: list[str] = Field(default_factory=list)


class StoryForgeGenerationProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exact_age: int
    target_words: int
    preferred_range: tuple[int, int]
    hard_range: tuple[int, int]
    language_of_generation: Literal["en"] = "en"
    delivery_language: Literal["tr"] = "tr"


class StoryForgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["storyforge-request.v1"] = "storyforge-request.v1"
    profile_id: str = "LSF-A4-W500-v1.0-rc1"
    request_id: str
    active_world_id: str
    always_required: list[StoryForgeFact]
    candidate_facts: list[StoryForgeFact]
    forbidden_facts: list[StoryForgeFact] = Field(default_factory=list)
    story_intent: StoryForgeIntent
    generation_profile: StoryForgeGenerationProfile

    @model_validator(mode="after")
    def validate_fact_ids(self) -> "StoryForgeRequest":
        ids = [x.id for x in self.always_required + self.candidate_facts + self.forbidden_facts]
        if len(ids) != len(set(ids)):
            raise ValueError("StoryForge fact ids must be globally unique.")
        candidate_ids = {x.id for x in self.candidate_facts}
        required = set(self.story_intent.references.required_fact_ids)
        guards = set(self.story_intent.references.hard_guard_fact_ids)
        missing = sorted((required | guards) - candidate_ids)
        if missing:
            raise ValueError(f"StoryIntent references missing candidate facts: {missing}")
        return self


class StoryForgeResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: Literal["storyforge-result.v1"] = "storyforge-result.v1"
    profile_id: str
    request_id: str
    status: Literal[
        "publication_ready",
        "plan_rejected",
        "story_rejected",
        "translation_rejected",
        "runtime_error",
    ]
    publication_ready: bool
    context_packet: dict[str, Any] | None = None
    plan: dict[str, Any] | None = None
    english_story: str | None = None
    turkish_story: str | None = None
    proposed_story_outcome: dict[str, Any] | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
