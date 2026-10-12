"""Deterministic ScenePlan -> SceneContract compiler for SpineForge Relay v1."""
from __future__ import annotations

from typing import Any

from src.spineforge_relay_v1_legacy_contracts import (
    FrozenSpineRouteV1,
    SceneContractV1,
    ScenePlanV1,
    StoryStateV1,
    canonical_sha256,
)


class SceneCompileError(RuntimeError):
    """Raised when a scene plan cannot be bound to current frozen inputs."""


def _tokens(pointer: str) -> list[str]:
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def _value_at(root: Any, pointer: str) -> tuple[bool, Any]:
    current = root
    parts = _tokens(pointer)
    if not parts:
        return True, current
    for token in parts:
        if isinstance(current, dict):
            if token not in current:
                return False, None
            current = current[token]
        elif isinstance(current, list):
            if token == "-":
                return False, None
            try:
                idx = int(token)
            except ValueError:
                return False, None
            if idx < 0 or idx >= len(current):
                return False, None
            current = current[idx]
        else:
            return False, None
    return True, current


def _assert_spine_progression(
    state: StoryStateV1,
    plan: ScenePlanV1,
    route: FrozenSpineRouteV1,
) -> None:
    if route.global_spine_sha256 != state.global_spine_sha256:
        raise SceneCompileError("Frozen spine route hash does not match StoryState")
    if state.next_spine_beat is None:
        raise SceneCompileError("Story state has no next spine beat")

    try:
        start = route.beat_ids.index(state.next_spine_beat)
    except ValueError as exc:
        raise SceneCompileError("Current next spine beat is absent from frozen route") from exc

    stop = start + len(plan.spine_beats)
    if stop > len(route.beat_ids):
        raise SceneCompileError("Scene plan consumes beyond frozen spine route")

    expected = route.beat_ids[start:stop]
    if plan.spine_beats != expected:
        raise SceneCompileError(
            f"Scene plan must consume contiguous frozen beats: expected {expected}"
        )

    expected_next = route.beat_ids[stop] if stop < len(route.beat_ids) else None
    if plan.next_spine_beat != expected_next:
        raise SceneCompileError(
            f"Scene plan next beat mismatch: expected {expected_next!r}"
        )

    if any(beat in state.completed_spine_beats for beat in plan.spine_beats):
        raise SceneCompileError("Scene plan attempts to consume an already completed spine beat")


def compile_scene_contract(
    state: StoryStateV1,
    plan: ScenePlanV1,
    route: FrozenSpineRouteV1,
) -> SceneContractV1:
    """Bind one structured ScenePlan to exact StoryState and frozen spine route.

    No semantic inference is performed here. Scene planning owns the structured
    proposal; this compiler owns deterministic route, state and fingerprint checks.
    """
    _assert_spine_progression(state, plan, route)

    state_payload = state.model_dump(mode="json")
    for pointer, expected in plan.entry_state.items():
        exists, actual = _value_at(state_payload, pointer)
        if not exists or actual != expected:
            raise SceneCompileError(f"Scene plan entry state is stale: {pointer}")

    required_events = plan.required_events or [plan.objective]

    return SceneContractV1(
        scene_id=plan.scene_id,
        scene_plan_sha256=canonical_sha256(plan),
        story_state_revision=state.revision,
        story_state_sha256=canonical_sha256(state),
        global_spine_sha256=state.global_spine_sha256,
        story_intent_sha256=state.story_intent_sha256,
        consumed_spine_beats=plan.spine_beats,
        next_spine_beat=plan.next_spine_beat,
        required_events=required_events,
        entry_state=plan.entry_state,
        required_exit_state=plan.required_exit_state,
        allowed_state_paths=plan.allowed_state_paths,
        immutable_facts=plan.immutable_facts,
        forbidden=plan.forbidden,
        emotional_transition=plan.emotional_transition,
        target_words_min=plan.target_words_min,
        target_words_max=plan.target_words_max,
        max_rewrites=1,
    )
