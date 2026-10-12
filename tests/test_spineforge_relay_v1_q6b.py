import json

from src.spineforge_relay_v1_q6b import (
    authorization_for,
    execute,
    prepare,
    relevant_character_canon,
    request_for,
)


def test_q6b_character_canon_is_explicit_and_immutable():
    canon = relevant_character_canon()
    assert canon["Duru"]["identity"] == "girl"
    assert canon["Duru"]["pronouns"] == ["she", "her"]
    assert canon["Ekin"]["pronouns"] == ["she", "her"]


def test_q6b_writer_and_guard_receive_same_character_canon():
    p = prepare()
    canon = p["relevant_character_canon"]
    payload = {
        "story_intent": {},
        "story_state": {},
        "frozen_spine_route": {},
        "scene_contract": {},
        "relevant_character_canon": canon,
        "attempt": 1,
        "rewrite": None,
    }
    _, writer = request_for("writer", payload)
    writer_input = json.loads(writer["messages"][1]["content"])
    assert writer_input["relevant_character_canon"] == canon

    guard_payload = {
        **payload,
        "candidate_prose": "Duru raised her hand.",
        "deterministic_findings": [],
    }
    _, guard = request_for("guard", guard_payload)
    guard_input = json.loads(guard["messages"][1]["content"])
    assert guard_input["relevant_character_canon"] == canon


def test_q6b_preflight_is_fresh_and_bounded():
    p = prepare()
    a = authorization_for(p)
    assert p["qualification_id"] == "SFR-V1-Q6B-SC02-SC03-20261007"
    assert p["max_rewrites_per_scene"] == 1
    assert p["automatic_retry"] is False
    assert p["stop_chain_on_scene_failure"] is True
    assert p["max_total_cost_usd"] == 0.60
    assert a["preflight_sha256"]
    assert a["paid_execution_authorized"] is True
    assert a["scenes"] == ["SC02", "SC03"]
