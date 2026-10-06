import pytest

from src.spineforge_relay_v1_contracts import (
    CharacterState,
    SceneContractV1,
    SceneDeltaV1,
    ScenePlanV1,
    StateMutation,
    StoryStateV1,
    canonical_sha256,
)
from src.spineforge_relay_v1_state import (
    InvalidRelayTransition,
    StaleRelayInput,
    apply_scene_delta,
)


H = "a" * 64
H2 = "b" * 64


def base_state() -> StoryStateV1:
    return StoryStateV1(
        story_id="relay-q2",
        revision=1,
        global_spine_sha256=H,
        story_intent_sha256=H2,
        characters={
            "Leyra": CharacterState(
                location="tower_ground",
                inventory={"rope": True},
                knowledge=["tower_looks_abandoned"],
            )
        },
        open_threads=["find_sound_source"],
        completed_spine_beats=["S1"],
        next_spine_beat="S2",
    )


def bound_contract(state: StoryStateV1) -> SceneContractV1:
    plan = ScenePlanV1(
        scene_id="SC02",
        spine_beats=["S2"],
        narrative_purpose="Move the search upstairs.",
        objective="Investigate the sound.",
        turn="The sound is clearly above Leyra.",
    )
    return SceneContractV1(
        scene_id="SC02",
        scene_plan_sha256=canonical_sha256(plan),
        story_state_revision=state.revision,
        story_state_sha256=canonical_sha256(state),
        global_spine_sha256=state.global_spine_sha256,
        story_intent_sha256=state.story_intent_sha256,
        required_events=["Leyra climbs upstairs"],
        entry_state={"Leyra.location": "tower_ground"},
        required_exit_state={"Leyra.location": "tower_floor_2"},
        immutable_facts=["Leyra still owns the rope"],
        forbidden=["The rope cannot disappear"],
    )


def delta_for(state: StoryStateV1, contract: SceneContractV1, mutations: list[StateMutation]) -> SceneDeltaV1:
    return SceneDeltaV1(
        scene_id=contract.scene_id,
        source_state_revision=state.revision,
        source_state_sha256=canonical_sha256(state),
        contract_sha256=canonical_sha256(contract),
        mutations=mutations,
    )


def test_location_transition_updates_only_declared_state_and_increments_revision():
    state = base_state()
    contract = bound_contract(state)
    delta = delta_for(
        state,
        contract,
        [
            StateMutation(
                path="/characters/Leyra/location",
                op="SET",
                before="tower_ground",
                after="tower_floor_2",
            )
        ],
    )

    result = apply_scene_delta(state, delta, contract)

    assert result.revision == 2
    assert result.characters["Leyra"].location == "tower_floor_2"
    assert result.characters["Leyra"].inventory["rope"] is True
    assert state.characters["Leyra"].location == "tower_ground"


def test_stale_state_fingerprint_fails_before_mutation():
    state = base_state()
    contract = bound_contract(state)
    delta = delta_for(state, contract, [])
    changed = state.model_copy(update={"next_spine_beat": "S99"})

    with pytest.raises(StaleRelayInput):
        apply_scene_delta(changed, delta, contract)


def test_before_value_mismatch_fails_closed():
    state = base_state()
    contract = bound_contract(state)
    delta = delta_for(
        state,
        contract,
        [
            StateMutation(
                path="/characters/Leyra/location",
                op="SET",
                before="forest",
                after="tower_floor_2",
            )
        ],
    )

    with pytest.raises(InvalidRelayTransition):
        apply_scene_delta(state, delta, contract)


def test_protected_identity_fields_cannot_be_mutated():
    state = base_state()
    contract = bound_contract(state)
    delta = delta_for(
        state,
        contract,
        [
            StateMutation(
                path="/global_spine_sha256",
                op="SET",
                before=H,
                after="c" * 64,
            )
        ],
    )

    with pytest.raises(InvalidRelayTransition):
        apply_scene_delta(state, delta, contract)


def test_contract_binding_mismatch_is_stale_input():
    state = base_state()
    contract = bound_contract(state)
    stale_payload = contract.model_dump()
    stale_payload["story_state_sha256"] = "c" * 64
    stale_contract = SceneContractV1.model_validate(stale_payload)
    delta = SceneDeltaV1(
        scene_id=stale_contract.scene_id,
        source_state_revision=state.revision,
        source_state_sha256=canonical_sha256(state),
        contract_sha256=canonical_sha256(stale_contract),
        mutations=[],
    )

    with pytest.raises(StaleRelayInput):
        apply_scene_delta(state, delta, stale_contract)


def test_resulting_invalid_thread_state_is_rejected():
    state = base_state()
    contract = bound_contract(state)
    delta = delta_for(
        state,
        contract,
        [
            StateMutation(
                path="/resolved_threads",
                op="SET",
                before=[],
                after=["find_sound_source"],
            )
        ],
    )

    with pytest.raises(InvalidRelayTransition):
        apply_scene_delta(state, delta, contract)


def test_add_and_remove_are_exact_not_best_effort():
    state = base_state()
    contract = bound_contract(state)
    delta = delta_for(
        state,
        contract,
        [
            StateMutation(
                path="/objects/lantern",
                op="ADD",
                after={"owner": "Leyra", "location": None, "state": {"lit": True}},
            )
        ],
    )
    result = apply_scene_delta(state, delta, contract)
    assert result.objects["lantern"].owner == "Leyra"

    next_contract = bound_contract(result)
    bad_remove = delta_for(
        result,
        next_contract,
        [
            StateMutation(
                path="/objects/lantern",
                op="REMOVE",
                before={"owner": "Duru", "location": None, "state": {"lit": True}},
            )
        ],
    )
    with pytest.raises(InvalidRelayTransition):
        apply_scene_delta(result, bad_remove, next_contract)
