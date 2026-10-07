import json

from src.spineforge_relay_v1_q6d import (
    authorization_for,
    prepare,
    prop_authorization_policy,
    relevant_character_canon,
    request_for,
)


def test_q6d_requires_both_identity_and_prop_context():
    p = prepare()
    assert p["qualification_id"] == "SFR-V1-Q6D-SC02-SC03-20261007"
    assert p["relevant_character_canon"]["Duru"]["pronouns"] == ["she", "her"]
    assert p["prop_authorization_policy"]["authorized_actionable_props"] == ["compass", "Ekin_jacket"]
    assert p["prop_guard_result_sha256"]
    assert p["identity_guard_preflight_sha256"]


def test_q6d_writer_and_guard_receive_identical_context_layers():
    canon = relevant_character_canon()
    prop = prop_authorization_policy()
    payload = {
        "story_intent": {},
        "story_state": {},
        "frozen_spine_route": {},
        "scene_contract": {},
        "relevant_character_canon": canon,
        "prop_authorization_policy": prop,
        "attempt": 1,
        "rewrite": None,
    }
    _, writer = request_for("writer", payload)
    writer_input = json.loads(writer["messages"][1]["content"])
    assert writer_input["relevant_character_canon"] == canon
    assert writer_input["prop_authorization_policy"] == prop

    guard_payload = {
        **payload,
        "candidate_prose": "Duru raised her hand.",
        "deterministic_findings": [],
    }
    _, guard = request_for("guard", guard_payload)
    guard_input = json.loads(guard["messages"][1]["content"])
    assert guard_input["relevant_character_canon"] == canon
    assert guard_input["prop_authorization_policy"] == prop


def test_q6d_is_bounded_and_fresh():
    p = prepare()
    a = authorization_for(p)
    assert p["max_rewrites_per_scene"] == 1
    assert p["automatic_retry"] is False
    assert p["stop_chain_on_scene_failure"] is True
    assert p["max_total_cost_usd"] == 0.60
    assert a["paid_execution_authorized"] is True
    assert a["automatic_retry"] is False
    assert a["scenes"] == ["SC02", "SC03"]
