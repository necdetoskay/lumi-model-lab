import pytest
from pydantic import ValidationError

from src.spineforge_relay_v1_contracts import (
    CharacterState,
    SceneArtifactV1,
    SceneContractV1,
    SceneDeltaV1,
    ScenePlanV1,
    SceneValidationV1,
    StateMutation,
    StoryStateV1,
    ValidationFinding,
    canonical_sha256,
)

H = "a" * 64
H2 = "b" * 64
H3 = "c" * 64
H4 = "d" * 64


def sample_state() -> StoryStateV1:
    return StoryStateV1(
        story_id="relay-fixture-1",
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


def test_story_state_fingerprint_is_canonical_and_stable():
    state = sample_state()
    assert canonical_sha256(state) == canonical_sha256(state.model_dump(mode="json"))
    assert len(canonical_sha256(state)) == 64


def test_story_state_rejects_thread_overlap():
    with pytest.raises(ValidationError):
        StoryStateV1(
            story_id="bad",
            revision=0,
            global_spine_sha256=H,
            story_intent_sha256=H2,
            open_threads=["rescue_duru"],
            resolved_threads=["rescue_duru"],
        )


def test_scene_plan_allows_multiple_spine_beats_but_not_duplicates():
    plan = ScenePlanV1(
        scene_id="SC03",
        spine_beats=["S3", "S4"],
        narrative_purpose="Discovery becomes immediate danger.",
        location="tower_floor_3",
        objective="Find Duru.",
        turn="The tower begins to fail.",
    )
    assert plan.spine_beats == ["S3", "S4"]
    with pytest.raises(ValidationError):
        ScenePlanV1(
            scene_id="SC03",
            spine_beats=["S3", "S3"],
            narrative_purpose="bad",
            objective="bad",
            turn="bad",
        )


def test_scene_contract_uses_pointer_state_and_one_rewrite_maximum():
    state = sample_state()
    plan = ScenePlanV1(
        scene_id="SC02",
        spine_beats=["S2"],
        narrative_purpose="Move the search upstairs.",
        objective="Investigate the sound.",
        turn="The sound is clearly above Leyra.",
    )
    contract = SceneContractV1(
        scene_id="SC02",
        scene_plan_sha256=canonical_sha256(plan),
        story_state_revision=state.revision,
        story_state_sha256=canonical_sha256(state),
        global_spine_sha256=state.global_spine_sha256,
        story_intent_sha256=state.story_intent_sha256,
        required_events=["Leyra climbs upstairs"],
        entry_state={"/characters/Leyra/location": "tower_ground"},
        required_exit_state={"/characters/Leyra/location": "tower_floor_2"},
        immutable_facts=["Leyra owns the rope"],
        forbidden=["The rope cannot disappear"],
        max_rewrites=1,
    )
    assert contract.max_rewrites == 1

    bad = contract.model_dump()
    bad["max_rewrites"] = 2
    with pytest.raises(ValidationError):
        SceneContractV1.model_validate(bad)

    bad_pointer = contract.model_dump()
    bad_pointer["entry_state"] = {"Leyra.location": "tower_ground"}
    with pytest.raises(ValidationError):
        SceneContractV1.model_validate(bad_pointer)


def test_delta_requires_unique_absolute_mutation_paths():
    delta = SceneDeltaV1(
        scene_id="SC02",
        source_state_revision=1,
        source_state_sha256=H,
        contract_sha256=H2,
        mutations=[
            StateMutation(
                path="/characters/Leyra/location",
                op="SET",
                before="tower_ground",
                after="tower_floor_2",
            )
        ],
    )
    assert delta.mutations[0].path == "/characters/Leyra/location"

    with pytest.raises(ValidationError):
        SceneDeltaV1(
            scene_id="SC02",
            source_state_revision=1,
            source_state_sha256=H,
            contract_sha256=H2,
            mutations=[
                StateMutation(path="/characters/Leyra/location", op="SET", before="a", after="b"),
                StateMutation(path="/characters/Leyra/location", op="SET", before="b", after="c"),
            ],
        )


def test_validation_is_fail_closed_and_rewrite_is_bounded():
    finding = ValidationFinding(
        code="LOCATION_JUMP",
        family="spatial",
        severity="BLOCKING",
        message="Leyra cannot move from floor 2 to the forest without a transition.",
    )
    first = SceneValidationV1(
        scene_id="SC04",
        attempt=1,
        deterministic_pass=False,
        decision="REWRITE",
        findings=[finding],
    )
    assert first.decision == "REWRITE"

    with pytest.raises(ValidationError):
        SceneValidationV1(
            scene_id="SC04",
            attempt=2,
            deterministic_pass=False,
            decision="REWRITE",
            findings=[finding],
        )

    second = SceneValidationV1(
        scene_id="SC04",
        attempt=2,
        deterministic_pass=False,
        decision="REJECT_NON_CONVERGENT",
        findings=[finding],
    )
    assert second.decision == "REJECT_NON_CONVERGENT"


def test_accepted_scene_must_advance_to_a_bound_post_state():
    validation = SceneValidationV1(
        scene_id="SC01",
        attempt=1,
        deterministic_pass=True,
        decision="ACCEPT",
    )
    artifact = SceneArtifactV1(
        scene_id="SC01",
        attempt=1,
        status="ACCEPTED",
        prose="Leyra stepped inside the tower with the rope still looped over her shoulder.",
        word_count=13,
        contract_sha256=H,
        state_before_sha256=H2,
        validation_sha256=canonical_sha256(validation),
        state_after_sha256=H3,
    )
    assert artifact.status == "ACCEPTED"

    bad = artifact.model_dump()
    bad["state_after_sha256"] = None
    with pytest.raises(ValidationError):
        SceneArtifactV1.model_validate(bad)


def test_rejected_scene_cannot_advance_story_state():
    with pytest.raises(ValidationError):
        SceneArtifactV1(
            scene_id="SC05",
            attempt=2,
            status="REJECTED",
            prose="Rejected scene text.",
            word_count=3,
            contract_sha256=H,
            state_before_sha256=H2,
            validation_sha256=H4,
            state_after_sha256=H3,
        )
