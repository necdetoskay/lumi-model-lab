"""Fail-closed data contracts for SpineForge Relay v1.

Q1/Q2 scope: schemas, cross-field invariants, state-transition authorization
and canonical fingerprints. No model calls live in this module.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


_SHA256_LEN = 64


def _unique(values: list[str], field_name: str) -> list[str]:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return values


def _sha(value: str, field_name: str) -> str:
    if len(value) != _SHA256_LEN or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hex digest")
    return value


def _pointer(value: str, field_name: str) -> str:
    if not value.startswith("/") or value == "/":
        raise ValueError(f"{field_name} must contain absolute non-root JSON pointers")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CharacterState(StrictModel):
    location: str | None = None
    condition: dict[str, Any] = Field(default_factory=dict)
    inventory: dict[str, Any] = Field(default_factory=dict)
    knowledge: list[str] = Field(default_factory=list)
    relationships: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_lists(self) -> "CharacterState":
        _unique(self.knowledge, "knowledge")
        return self


class ObjectState(StrictModel):
    owner: str | None = None
    location: str | None = None
    state: dict[str, Any] = Field(default_factory=dict)


class NarrativeObligation(StrictModel):
    id: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    status: Literal["OPEN", "SATISFIED", "FAILED"] = "OPEN"
    target_scene_id: str | None = None


class StoryStateV1(StrictModel):
    schema_name: Literal["spineforge-relay.story-state.v1"] = "spineforge-relay.story-state.v1"
    story_id: str = Field(min_length=1)
    revision: int = Field(ge=0)
    global_spine_sha256: str
    story_intent_sha256: str
    characters: dict[str, CharacterState] = Field(default_factory=dict)
    world: dict[str, Any] = Field(default_factory=dict)
    objects: dict[str, ObjectState] = Field(default_factory=dict)
    open_threads: list[str] = Field(default_factory=list)
    resolved_threads: list[str] = Field(default_factory=list)
    completed_spine_beats: list[str] = Field(default_factory=list)
    next_spine_beat: str | None = None
    narrative_obligations: list[NarrativeObligation] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_state(self) -> "StoryStateV1":
        _sha(self.global_spine_sha256, "global_spine_sha256")
        _sha(self.story_intent_sha256, "story_intent_sha256")
        _unique(self.open_threads, "open_threads")
        _unique(self.resolved_threads, "resolved_threads")
        _unique(self.completed_spine_beats, "completed_spine_beats")
        if set(self.open_threads) & set(self.resolved_threads):
            raise ValueError("open_threads and resolved_threads must be disjoint")
        obligation_ids = [x.id for x in self.narrative_obligations]
        _unique(obligation_ids, "narrative_obligations.id")
        return self


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


class StateMutation(StrictModel):
    path: str = Field(min_length=1)
    op: Literal["SET", "ADD", "REMOVE"]
    before: Any | None = None
    after: Any | None = None

    @model_validator(mode="after")
    def validate_mutation(self) -> "StateMutation":
        _pointer(self.path, "mutation path")
        if self.op == "ADD" and self.after is None:
            raise ValueError("ADD requires after")
        if self.op == "REMOVE" and self.before is None:
            raise ValueError("REMOVE requires before")
        if self.op == "REMOVE" and self.after is not None:
            raise ValueError("REMOVE requires after=None")
        if self.op == "SET" and self.before == self.after:
            raise ValueError("SET must change the value")
        return self


class SceneDeltaV1(StrictModel):
    schema_name: Literal["spineforge-relay.scene-delta.v1"] = "spineforge-relay.scene-delta.v1"
    scene_id: str = Field(min_length=1)
    source_state_revision: int = Field(ge=0)
    source_state_sha256: str
    contract_sha256: str
    mutations: list[StateMutation] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_delta(self) -> "SceneDeltaV1":
        _sha(self.source_state_sha256, "source_state_sha256")
        _sha(self.contract_sha256, "contract_sha256")
        paths = [x.path for x in self.mutations]
        _unique(paths, "mutations.path")
        return self


class ValidationFinding(StrictModel):
    code: str = Field(min_length=1)
    family: Literal[
        "physical",
        "causal",
        "state",
        "spatial",
        "temporal",
        "epistemic",
        "response",
        "closure",
        "canon",
        "age",
        "spine",
        "narrative",
        "contract",
        "stale_input",
    ]
    severity: Literal["BLOCKING", "WARN"]
    message: str = Field(min_length=1)
    evidence: list[str] = Field(default_factory=list)


class SceneValidationV1(StrictModel):
    schema_name: Literal["spineforge-relay.scene-validation.v1"] = "spineforge-relay.scene-validation.v1"
    scene_id: str = Field(min_length=1)
    attempt: Literal[1, 2]
    deterministic_pass: bool
    semantic_guard_used: bool = False
    decision: Literal["ACCEPT", "REWRITE", "REJECT_NON_CONVERGENT"]
    findings: list[ValidationFinding] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_decision(self) -> "SceneValidationV1":
        blocking = [f for f in self.findings if f.severity == "BLOCKING"]
        if self.decision == "ACCEPT" and (not self.deterministic_pass or blocking):
            raise ValueError("ACCEPT requires deterministic_pass and no blocking findings")
        if self.decision == "REWRITE" and self.attempt != 1:
            raise ValueError("REWRITE is only valid after attempt 1")
        if self.decision in {"REWRITE", "REJECT_NON_CONVERGENT"} and not blocking:
            raise ValueError(f"{self.decision} requires at least one blocking finding")
        if self.decision == "REJECT_NON_CONVERGENT" and self.attempt != 2:
            raise ValueError("REJECT_NON_CONVERGENT is only valid after attempt 2")
        return self


class SceneArtifactV1(StrictModel):
    schema_name: Literal["spineforge-relay.scene-artifact.v1"] = "spineforge-relay.scene-artifact.v1"
    scene_id: str = Field(min_length=1)
    attempt: Literal[1, 2]
    status: Literal["ACCEPTED", "REJECTED"]
    prose: str = Field(min_length=1)
    word_count: int = Field(ge=1)
    contract_sha256: str
    state_before_sha256: str
    validation_sha256: str
    state_after_sha256: str | None = None

    @model_validator(mode="after")
    def validate_artifact(self) -> "SceneArtifactV1":
        for name in ("contract_sha256", "state_before_sha256", "validation_sha256"):
            _sha(getattr(self, name), name)
        if self.state_after_sha256 is not None:
            _sha(self.state_after_sha256, "state_after_sha256")
        if self.status == "ACCEPTED" and self.state_after_sha256 is None:
            raise ValueError("ACCEPTED artifact requires state_after_sha256")
        if self.status == "REJECTED" and self.state_after_sha256 is not None:
            raise ValueError("REJECTED artifact cannot advance story state")
        return self


def canonical_sha256(value: BaseModel | dict[str, Any]) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
