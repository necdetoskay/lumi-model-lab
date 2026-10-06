import json
from pathlib import Path

import pytest

from src.spineforge_relay_v1_contracts import (
    CharacterState,
    ObjectState,
    SceneContractV1,
    SceneDeltaV1,
    ScenePlanV1,
    StateMutation,
    StoryStateV1,
    canonical_sha256,
)
from src.spineforge_relay_v1_state import InvalidRelayTransition, apply_scene_delta


H = "a" * 64
H2 = "b" * 64
FIXTURE = Path("tests/fixtures/spineforge_relay_v1/historical_continuity.json")


def test_historical_continuity_failures_are_encoded_and_blocked():
    data = json.loads(FIXTURE.read_text())
    assert len(data["cases"]) == 2

    state = StoryStateV1(
        story_id="lighthouse-historical-continuity",
        revision=7,
        global_spine_sha256=H,
        story_intent_sha256=H2,
        characters={
            "Ekin": CharacterState(location="lower_stairs"),
            "Duru": CharacterState(location="upper_room"),
        },
        objects={
            "compass_cord": ObjectState(owner=None, location="with_dragon"),
        },
        next_spine_beat="HIST",
    )

    plan = ScenePlanV1(
        scene_id="SC-HIST",
        spine_beats=["HIST"],
        narrative_purpose="Preserve continuity while Ekin returns upward.",
        objective="Return Ekin to the upper room.",
        turn="The rescue succeeds.",
    )
    contract = SceneContractV1(
        scene_id="SC-HIST",
        scene_plan_sha256=canonical_sha256(plan),
        story_state_revision=state.revision,
        story_state_sha256=canonical_sha256(state),
        global_spine_sha256=state.global_spine_sha256,
        story_intent_sha256=state.story_intent_sha256,
        consumed_spine_beats=["HIST"],
        next_spine_beat=None,
        required_events=["Ekin returns to the upper room"],
        entry_state={
            "/characters/Duru/location": "upper_room",
            "/objects/compass_cord/location": "with_dragon",
        },
        required_exit_state={
            "/characters/Ekin/location": "upper_room",
        },
        allowed_state_paths=[],
    )

    for case in data["cases"]:
        mutation = StateMutation.model_validate(case["attempted_mutation"])
        delta = SceneDeltaV1(
            scene_id=contract.scene_id,
            source_state_revision=state.revision,
            source_state_sha256=canonical_sha256(state),
            contract_sha256=canonical_sha256(contract),
            mutations=[mutation],
        )
        with pytest.raises(InvalidRelayTransition, match="Unauthorized persistent state path"):
            apply_scene_delta(state, delta, contract)
