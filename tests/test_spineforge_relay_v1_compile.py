from tests.relay_event_fixture import event
import pytest

from src.spineforge_relay_v1_compile import SceneCompileError, compile_scene_contract
from src.spineforge_relay_v1_contracts import (
    CharacterState,
    FrozenSpineRouteV1,
    ScenePlanV1,
    StoryStateV1,
)

H = "a" * 64
H2 = "b" * 64


def state(next_beat="SC02", completed=None):
    return StoryStateV1(
        story_id="compile-proof",
        revision=2,
        global_spine_sha256=H,
        story_intent_sha256=H2,
        characters={"Ekin": CharacterState(location="coastal_path")},
        completed_spine_beats=completed or ["SC01"],
        next_spine_beat=next_beat,
    )


def route():
    return FrozenSpineRouteV1(
        global_spine_sha256=H,
        beat_ids=["SC01", "SC02", "SC03", "SC04", "SC05", "SC06"],
    )


def plan(beats, next_beat, entry="coastal_path"):
    return ScenePlanV1(
        scene_id="SCENE-X",
        spine_beats=beats,
        next_spine_beat=next_beat,
        narrative_purpose="Advance the frozen lighthouse spine.",
        objective="Advance the scene.",
        required_events=[event("Ekin", "MOVE", "lighthouse_upper")],
        turn="The scene reaches its turn.",
        entry_state={"/characters/Ekin/location": entry},
        required_exit_state={"/characters/Ekin/location": "lighthouse_upper"},
    )


def test_compiler_accepts_exact_contiguous_route_progression():
    contract = compile_scene_contract(
        state(),
        plan(["SC02"], "SC03"),
        route(),
    )
    assert contract.consumed_spine_beats == ["SC02"]
    assert contract.next_spine_beat == "SC03"


def test_compiler_accepts_multiple_contiguous_beats_for_one_scene():
    contract = compile_scene_contract(
        state(),
        plan(["SC02", "SC03"], "SC04"),
        route(),
    )
    assert contract.consumed_spine_beats == ["SC02", "SC03"]


def test_compiler_rejects_skipping_or_inventing_spine_beats():
    with pytest.raises(SceneCompileError, match="contiguous frozen beats"):
        compile_scene_contract(
            state(),
            plan(["SC02", "SC99"], "SC04"),
            route(),
        )


def test_compiler_rejects_wrong_declared_next_beat():
    with pytest.raises(SceneCompileError, match="next beat mismatch"):
        compile_scene_contract(
            state(),
            plan(["SC02"], "SC05"),
            route(),
        )


def test_compiler_rejects_route_bound_to_another_global_spine():
    bad_route = FrozenSpineRouteV1(
        global_spine_sha256="c" * 64,
        beat_ids=["SC01", "SC02"],
    )
    with pytest.raises(SceneCompileError, match="route hash"):
        compile_scene_contract(
            state(),
            plan(["SC02"], None),
            bad_route,
        )


def test_compiler_rejects_stale_entry_state():
    with pytest.raises(SceneCompileError, match="entry state is stale"):
        compile_scene_contract(
            state(),
            plan(["SC02"], "SC03", entry="harbor"),
            route(),
        )


def test_compiler_rejects_consumed_beat_replay():
    replay_state = state(next_beat="SC02", completed=["SC01", "SC02"])
    with pytest.raises(SceneCompileError, match="already completed"):
        compile_scene_contract(
            replay_state,
            plan(["SC02"], "SC03"),
            route(),
        )


def test_route_rejects_duplicate_beat_ids():
    with pytest.raises(ValueError):
        FrozenSpineRouteV1(
            global_spine_sha256=H,
            beat_ids=["SC01", "SC01"],
        )
