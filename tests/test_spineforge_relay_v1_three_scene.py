from tests.relay_event_fixture import event
import pytest

from src.spineforge_relay_v1_compile import compile_scene_contract
from src.spineforge_relay_v1_contracts import (
    CharacterState,
    FrozenSpineRouteV1,
    ObjectState,
    SceneArtifactV1,
    SceneDeltaV1,
    ScenePlanV1,
    SceneValidationV1,
    StateMutation,
    StoryStateV1,
    canonical_sha256,
)
from src.spineforge_relay_v1_state import StaleRelayInput, apply_scene_delta


H = "a" * 64
H2 = "b" * 64


def make_plan(state, scene_id, beat, next_beat, purpose, entry, exit_state, allowed=None):
    return ScenePlanV1(
        scene_id=scene_id,
        spine_beats=[beat],
        next_spine_beat=next_beat,
        narrative_purpose=purpose,
        objective=purpose,
        turn=f"{scene_id} reaches its intended turn.",
        required_events=[event("ensemble", "ADVANCE", purpose)],
        entry_state=entry,
        required_exit_state=exit_state,
        allowed_state_paths=allowed or [],
    )


def make_delta(state, contract, mutations):
    return SceneDeltaV1(
        scene_id=contract.scene_id,
        source_state_revision=state.revision,
        source_state_sha256=canonical_sha256(state),
        contract_sha256=canonical_sha256(contract),
        mutations=mutations,
    )


def freeze(scene_id, state_before, state_after, contract, prose):
    validation = SceneValidationV1(
        scene_id=scene_id,
        attempt=1,
        deterministic_pass=True,
        decision="ACCEPT",
    )
    return SceneArtifactV1(
        scene_id=scene_id,
        attempt=1,
        status="ACCEPTED",
        prose=prose,
        word_count=len(prose.split()),
        contract_sha256=canonical_sha256(contract),
        state_before_sha256=canonical_sha256(state_before),
        validation_sha256=canonical_sha256(validation),
        state_after_sha256=canonical_sha256(state_after),
    )


def test_three_scene_relay_preserves_state_and_advances_spine_without_prose_memory():
    route = FrozenSpineRouteV1(
        global_spine_sha256=H,
        beat_ids=["S1", "S2", "S3"],
    )

    s0 = StoryStateV1(
        story_id="relay-three-scene-proof",
        revision=0,
        global_spine_sha256=H,
        story_intent_sha256=H2,
        characters={
            "Leyra": CharacterState(location="outside_tower", knowledge=[]),
            "Duru": CharacterState(location="tower_floor_3", knowledge=[]),
        },
        objects={
            "rope": ObjectState(owner="Leyra", location="carried_by_Leyra", state={"usable": True})
        },
        next_spine_beat="S1",
    )

    p1 = make_plan(
        s0, "SC01", "S1", "S2", "Leyra enters the tower.",
        {"/characters/Leyra/location": "outside_tower", "/objects/rope/owner": "Leyra"},
        {"/characters/Leyra/location": "tower_ground"},
    )
    c1 = compile_scene_contract(s0, p1, route)
    d1 = make_delta(s0, c1, [
        StateMutation(
            path="/characters/Leyra/location",
            op="SET",
            before="outside_tower",
            after="tower_ground",
        )
    ])
    s1 = apply_scene_delta(s0, d1, c1)
    a1 = freeze("SC01", s0, s1, c1, "Leyra entered the tower with the rope still over her shoulder.")

    p2 = make_plan(
        s1, "SC02", "S2", "S3", "Leyra climbs to the second floor.",
        {"/characters/Leyra/location": "tower_ground", "/objects/rope/owner": "Leyra"},
        {"/characters/Leyra/location": "tower_floor_2"},
    )
    c2 = compile_scene_contract(s1, p2, route)
    d2 = make_delta(s1, c2, [
        StateMutation(
            path="/characters/Leyra/location",
            op="SET",
            before="tower_ground",
            after="tower_floor_2",
        )
    ])
    s2 = apply_scene_delta(s1, d2, c2)
    a2 = freeze("SC02", s1, s2, c2, "Leyra climbed the worn stairs to the second floor.")

    p3 = make_plan(
        s2, "SC03", "S3", None, "Leyra reaches Duru.",
        {
            "/characters/Leyra/location": "tower_floor_2",
            "/characters/Duru/location": "tower_floor_3",
            "/objects/rope/owner": "Leyra",
        },
        {"/characters/Leyra/location": "tower_floor_3"},
        allowed=["/characters/Leyra/knowledge/-"],
    )
    c3 = compile_scene_contract(s2, p3, route)
    d3 = make_delta(s2, c3, [
        StateMutation(
            path="/characters/Leyra/location",
            op="SET",
            before="tower_floor_2",
            after="tower_floor_3",
        ),
        StateMutation(
            path="/characters/Leyra/knowledge/-",
            op="ADD",
            after="Duru_is_here",
        ),
    ])
    s3 = apply_scene_delta(s2, d3, c3)
    a3 = freeze("SC03", s2, s3, c3, "On the third floor Leyra found Duru and called her name.")

    assert [s0.revision, s1.revision, s2.revision, s3.revision] == [0, 1, 2, 3]
    assert [a1.status, a2.status, a3.status] == ["ACCEPTED", "ACCEPTED", "ACCEPTED"]
    assert s3.completed_spine_beats == ["S1", "S2", "S3"]
    assert s3.next_spine_beat is None
    assert s3.characters["Leyra"].location == "tower_floor_3"
    assert s3.characters["Duru"].location == "tower_floor_3"
    assert "Duru_is_here" in s3.characters["Leyra"].knowledge
    assert s3.objects["rope"].owner == "Leyra"
    assert s3.objects["rope"].location == "carried_by_Leyra"
    assert s3.objects["rope"].state["usable"] is True

    with pytest.raises(StaleRelayInput):
        apply_scene_delta(s2, d1, c1)
