"""Explicit historical Q0-Q5S string-event replay. Not used by Q5T."""
from typing import Any, Literal
from pydantic import Field, model_validator
from src.spineforge_relay_v1_contracts import (StrictModel, StoryStateV1, FrozenSpineRouteV1, canonical_sha256, _unique, _sha, _pointer)

class ScenePlanV1(StrictModel):
    schema_name: Literal["spineforge-relay.scene-plan.v1"] = "spineforge-relay.scene-plan.v1"
    scene_id: str = Field(min_length=1)
    spine_beats: list[str] = Field(min_length=1)
    narrative_purpose: str = Field(min_length=1)
    location: str | None = None
    objective: str = Field(min_length=1)
    turn: str = Field(min_length=1)
    entry_requirements: list[str] = Field(default_factory=list)
    exit_requirements: list[str] = Field(default_factory=list)
    required_events: list[str] = Field(default_factory=list)
    entry_state: dict[str, Any] = Field(default_factory=dict)
    required_exit_state: dict[str, Any] = Field(default_factory=dict)
    allowed_state_paths: list[str] = Field(default_factory=list)
    immutable_facts: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    emotional_transition: dict[str, str] | None = None
    next_spine_beat: str | None = None
    target_words_min: int = Field(default=120, ge=40, le=2000)
    target_words_max: int = Field(default=260, ge=40, le=3000)

    @model_validator(mode="after")
    def validate_plan(self) -> "ScenePlanV1":
        _unique(self.spine_beats, "spine_beats")
        _unique(self.entry_requirements, "entry_requirements")
        _unique(self.exit_requirements, "exit_requirements")
        _unique(self.required_events, "required_events")
        _unique(self.allowed_state_paths, "allowed_state_paths")
        _unique(self.immutable_facts, "immutable_facts")
        _unique(self.forbidden, "forbidden")
        for field_name, pointers in (
            ("entry_state", list(self.entry_state)),
            ("required_exit_state", list(self.required_exit_state)),
            ("allowed_state_paths", self.allowed_state_paths),
        ):
            for pointer in pointers:
                _pointer(pointer, field_name)
        if self.target_words_min > self.target_words_max:
            raise ValueError("target_words_min must be <= target_words_max")
        return self


class SceneContractV1(StrictModel):
    schema_name: Literal["spineforge-relay.scene-contract.v1"] = "spineforge-relay.scene-contract.v1"
    scene_id: str = Field(min_length=1)
    scene_plan_sha256: str
    story_state_revision: int = Field(ge=0)
    story_state_sha256: str
    global_spine_sha256: str
    story_intent_sha256: str
    consumed_spine_beats: list[str] = Field(min_length=1)
    next_spine_beat: str | None = None
    required_events: list[str] = Field(min_length=1)
    entry_state: dict[str, Any] = Field(default_factory=dict)
    required_exit_state: dict[str, Any] = Field(default_factory=dict)
    allowed_state_paths: list[str] = Field(default_factory=list)
    immutable_facts: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    emotional_transition: dict[str, str] | None = None
    target_words_min: int = Field(default=120, ge=40, le=2000)
    target_words_max: int = Field(default=260, ge=40, le=3000)
    max_rewrites: Literal[1] = 1

    @model_validator(mode="after")
    def validate_contract(self) -> "SceneContractV1":
        for name in (
            "scene_plan_sha256",
            "story_state_sha256",
            "global_spine_sha256",
            "story_intent_sha256",
        ):
            _sha(getattr(self, name), name)
        _unique(self.consumed_spine_beats, "consumed_spine_beats")
        _unique(self.required_events, "required_events")
        _unique(self.immutable_facts, "immutable_facts")
        _unique(self.forbidden, "forbidden")
        _unique(self.allowed_state_paths, "allowed_state_paths")
        for field_name, pointers in (
            ("entry_state", list(self.entry_state)),
            ("required_exit_state", list(self.required_exit_state)),
            ("allowed_state_paths", self.allowed_state_paths),
        ):
            for pointer in pointers:
                _pointer(pointer, field_name)
        if self.target_words_min > self.target_words_max:
            raise ValueError("target_words_min must be <= target_words_max")
        return self


