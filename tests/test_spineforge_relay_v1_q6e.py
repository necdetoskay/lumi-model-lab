import json

import pytest

from src.spineforge_relay_v1_contracts import canonical_sha256
from src.spineforge_relay_v1_q6e import (
    MAX_TOTAL_COST,
    authorization_for,
    build_inputs,
    execute,
    prepare,
)


def test_q6e_binds_revised_sc03_to_accepted_sc02_state():
    _intent, _route, state, plan, contract = build_inputs()
    assert state.revision == 2
    assert state.next_spine_beat == "SC03"
    assert plan.scene_id == "SC03"
    assert contract.story_state_revision == 2
    assert contract.story_state_sha256 == canonical_sha256(state)
    assert contract.required_exit_state["/world/mother_dragon_location"] == "lighthouse_upper_room"
    event = next(e for e in contract.required_events if e.id == "SC03-E05")
    assert event.actor == "sea_dragon"
    assert event.action == "OCCUPY"
    assert event.target == "lighthouse_upper_room"
    assert event.resulting_state == {"/world/mother_dragon_location": "lighthouse_upper_room"}


def test_q6e_preflight_is_one_scene_bounded_and_shares_qualified_context():
    p = prepare()
    assert p["writer"] == "openai/gpt-5.6-sol"
    assert p["guard"] == "anthropic/claude-sonnet-5.5"
    assert p["max_rewrites"] == 1
    assert p["automatic_retry"] is False
    assert p["state_application_on_accept"] is True
    assert p["max_total_cost_usd"] == MAX_TOTAL_COST == 0.30
    assert p["expected_revision"] == 3
    assert p["expected_next_spine_beat"] == "SC04"
    assert p["expected_mother_dragon_location"] == "lighthouse_upper_room"
    assert p["prop_authorization_policy"]["authorized_actionable_props"] == ["compass", "Ekin_jacket"]
    assert p["relevant_character_canon"]["Duru"]["pronouns"] == ["she", "her"]


def test_q6e_authorization_is_exact():
    p = prepare()
    a = authorization_for(p)
    assert a["preflight_sha256"] == canonical_sha256(p)
    assert a["paid_execution_authorized"] is True
    assert a["scene"] == "SC03"
    assert a["max_rewrites"] == 1
    assert a["automatic_retry"] is False
    assert a["max_total_cost_usd"] == 0.30


def test_q6e_missing_credential_fails_before_claim(tmp_path):
    p = prepare()
    a = authorization_for(p)
    with pytest.raises(RuntimeError, match="Missing credential"):
        execute(api_key="", preflight=p, authorization=a, output=tmp_path / "q6e")
    assert not (tmp_path / "q6e").exists()


def test_q6e_tampered_preflight_fails_before_claim(tmp_path):
    p = prepare()
    a = authorization_for(p)
    tampered = json.loads(json.dumps(p))
    tampered["expected_mother_dragon_location"] = "outside"
    with pytest.raises(RuntimeError, match="preflight drift"):
        execute(api_key="fake", preflight=tampered, authorization=a, output=tmp_path / "q6e")
    assert not (tmp_path / "q6e").exists()
