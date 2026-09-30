from __future__ import annotations

import json
from pathlib import Path

from src.premise_architect_v2_contract import PremiseLabStateV1, PremiseCandidateV2, build_reveal_safe_premise_projection
from src.reader_profile_v2 import ReaderDevelopmentProfileV2
from src.saga_blueprint_contract import NarrativeFixture
from src.saga_spine_v2_contract import CharacterSagaSpineV2

READER=Path("data/specifications/reader_profiles/age18_adventure_v2.json")
FIXTURE=Path("data/specifications/saga_lab/age18_forbidden_cartographer_fixture_v1.json")
SAGA=Path("data/specifications/saga_lab/age18_forbidden_cartographer_saga_v1.json")
STATE=Path("data/specifications/story_lab/age18_forbidden_cartographer_initial_state_v1.json")
PREMISE=Path("data/specifications/story_lab/age18_forbidden_cartographer_controlled_premise_v1.json")


def _load():
    reader=ReaderDevelopmentProfileV2.model_validate_json(READER.read_text())
    fixture=NarrativeFixture.model_validate_json(FIXTURE.read_text())
    saga=CharacterSagaSpineV2.model_validate_json(SAGA.read_text())
    state=PremiseLabStateV1.model_validate_json(STATE.read_text())
    premise_artifact=json.loads(PREMISE.read_text())
    premise=PremiseCandidateV2.model_validate(premise_artifact["premise"])
    projection=build_reveal_safe_premise_projection(
        spine=saga,reader=reader,fixture=fixture,state=state
    )
    return reader,fixture,saga,state,premise_artifact,premise,projection


def test_forbidden_cartographer_authority_is_strictly_valid() -> None:
    reader,fixture,_,_,premise_artifact,premise,projection=_load()
    assert reader.exact_age==fixture.character.age==18
    assert fixture.world.world_type=="HIGH_FANTASY"
    assert fixture.story_mode=="MYSTERY"
    assert premise_artifact["authority_mode"]=="FIXED_QUALIFICATION_FIXTURE"
    assert premise_artifact["human_creative_approval_required_before_writer"] is True
    assert premise.expected_session=="STANDARD"
    assert projection["session_target"]["target_words_min"]==1600
    assert projection["session_target"]["target_words_max"]==2500


def test_first_fantasy_episode_has_safe_milestone_and_location_authority() -> None:
    *_,premise_artifact,premise,projection=_load()
    eligible={row["key"] for row in projection["eligible_main_saga_milestones"]}
    assert "forbidden_passage_observed" in eligible
    assert "forbidden_passage_observed" in premise.target_refs
    accessible={
        row["key"]
        for row in projection["world"]["location_access"]
        if row["status"]=="AVAILABLE" and row["premise_usage"]=="FULL"
    }
    assert set(premise.location_refs)<=accessible
    assert {"vellum_hall","greyfen","ashen_gate"}<=accessible


def test_hidden_truths_do_not_precommit_first_episode() -> None:
    _,_,saga,_,_,premise,_=_load()
    hidden={row.key:row for row in saga.main_saga.hidden_truths}
    assert hidden["boundary_return_rule"].mode=="FIXED_HIDDEN"
    assert hidden["ilyan_prior_findings"].mode=="FIXED_HIDDEN"
    assert hidden["nameless_vale_purpose"].mode=="UNRESOLVED_BY_DESIGN"
    text=" ".join([
        premise.central_problem,
        premise.wonder_or_discovery,
        premise.local_payoff,
        *premise.constraints,
    ]).lower()
    assert "must leave cause" in premise.local_payoff.lower()
    assert "cannot prove motive" in text
    assert "nameless vale" in text


def test_no_auto_writer_authorization_or_paid_call() -> None:
    artifact=json.loads(PREMISE.read_text())
    assert artifact["human_creative_approval_required_before_writer"] is True
