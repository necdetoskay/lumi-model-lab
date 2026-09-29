from __future__ import annotations

import json
from pathlib import Path

from src.premise_architect_v2_contract import PremiseLabStateV1, build_reveal_safe_premise_projection
from src.reader_profile_v2 import ReaderDevelopmentProfileV2
from src.saga_blueprint_contract import NarrativeFixture
from src.saga_spine_v2_contract import CharacterSagaSpineV2


READER = Path("data/specifications/reader_profiles/age18_adventure_v2.json")
FIXTURE = Path("data/specifications/saga_lab/age18_shattered_meridian_fixture_v1.json")
SAGA = Path("data/specifications/saga_lab/age18_shattered_meridian_gate_b_control_v1.json")
STATE = Path("data/specifications/story_lab/age18_shattered_meridian_initial_state_v1.json")
PREMISE = Path("data/specifications/story_lab/age18_shattered_meridian_controlled_premise_v1.json")


def test_age18_control_authority_is_strictly_valid() -> None:
    reader = ReaderDevelopmentProfileV2.model_validate_json(READER.read_text())
    fixture = NarrativeFixture.model_validate_json(FIXTURE.read_text())
    saga = CharacterSagaSpineV2.model_validate_json(SAGA.read_text())
    state = PremiseLabStateV1.model_validate_json(STATE.read_text())
    premise_artifact = json.loads(PREMISE.read_text())

    assert reader.exact_age == fixture.character.age == 18
    assert premise_artifact["authority_mode"] == "FIXED_QUALIFICATION_FIXTURE"
    assert premise_artifact["human_creative_approval_required_before_writer"] is True

    projection = build_reveal_safe_premise_projection(
        spine=saga, reader=reader, fixture=fixture, state=state
    )
    assert projection["session_target"]["target_words_min"] == 1600
    assert projection["session_target"]["target_words_max"] == 2500
    eligible = {row["key"] for row in projection["eligible_main_saga_milestones"]}
    assert "first_discrepancy_logged" in eligible

    premise = premise_artifact["premise"]
    accessible = {
        row["key"]
        for row in projection["world"]["location_access"]
        if row["status"] == "AVAILABLE" and row["premise_usage"] == "FULL"
    }
    assert set(premise["location_refs"]) <= accessible
    assert "first_discrepancy_logged" in premise["target_refs"]
    assert premise["expected_session"] == "STANDARD"
