import json

import pytest

from src.spineforge_relay_v1_contracts import canonical_sha256
from src.spineforge_relay_v1_q7 import (
    MAX_TOTAL_COST,
    authorization_for,
    build_chain,
    execute,
    prepare,
)


def test_q7_chain_starts_from_frozen_q6d_revision_three_and_finishes_revision_six():
    fixture, _intent, _route, start, rows, final = build_chain()

    assert fixture["qualification_id"] == "SFR-V1-Q7-SC04-SC06-20261007"
    assert start.revision == 3
    assert start.next_spine_beat == "SC04"
    assert [plan.scene_id for plan, _contract, _before in rows] == ["SC04", "SC05", "SC06"]
    assert [contract.story_state_revision for _plan, contract, _before in rows] == [3, 4, 5]

    assert final.revision == 6
    assert final.next_spine_beat is None
    assert final.completed_spine_beats == ["SC01", "SC02", "SC03", "SC04", "SC05", "SC06"]


def test_q7_terminal_state_closes_story_without_restoring_compass():
    _fixture, _intent, _route, _start, _rows, final = build_chain()

    assert final.objects["compass"].location == "lost_at_sea"
    assert final.objects["dragon_hatchling"].location == "lighthouse_upper_room"
    assert final.characters["Ekin"].location == "harbor"
    assert final.characters["Duru"].location == "harbor"
    assert final.characters["Ekin"].relationships["Duru"]["trust"] == "earned"
    assert final.characters["Duru"].relationships["Ekin"]["trust"] == "earned"
    assert final.world["weather"] == "storm_active_return_route_passable"
    assert final.open_threads == []
    assert final.resolved_threads == ["recover_compass"]
    assert {o.id: o.status for o in final.narrative_obligations} == {
        "ekin_duru_trust": "SATISFIED",
        "compass_loss": "SATISFIED",
    }


def test_q7_sc04_and_sc05_intermediate_state_are_explicit():
    _fixture, _intent, _route, start, rows, _final = build_chain()
    sc04_before = rows[0][2]
    sc05_before = rows[1][2]
    sc06_before = rows[2][2]

    assert canonical_sha256(sc04_before) == canonical_sha256(start)
    assert sc05_before.revision == 4
    assert sc05_before.objects["compass"].location == "lost_at_sea"
    assert sc05_before.objects["dragon_hatchling"].location == "lower_room_dry_ledge"
    assert sc05_before.characters["Ekin"].location == "lighthouse_stair_dry_section"
    assert sc05_before.world["mother_blocked_by_narrow_stair"] is True

    assert sc06_before.revision == 5
    assert sc06_before.objects["dragon_hatchling"].location == "lighthouse_upper_room"
    assert sc06_before.characters["Ekin"].relationships["Duru"]["trust"] == "earned_initial"
    assert sc06_before.characters["Duru"].relationships["Ekin"]["trust"] == "earned_initial"


def test_q7_preflight_is_bounded_and_binds_canon_prop_policy_and_source():
    p = prepare()
    assert p["writer"] == "openai/gpt-5.6-sol"
    assert p["guard"] == "anthropic/claude-sonnet-5.5"
    assert p["max_rewrites_per_scene"] == 1
    assert p["automatic_retry"] is False
    assert p["stop_chain_on_scene_failure"] is True
    assert p["production_write"] is False
    assert p["max_total_cost_usd"] == MAX_TOTAL_COST == 0.90
    assert list(p["relevant_character_canon"]) == ["Ekin", "Duru"]
    assert p["prop_authorization_policy"]["authorized_actionable_props"] == ["compass", "Ekin_jacket"]
    assert [x["scene_id"] for x in p["scene_contracts"]] == ["SC04", "SC05", "SC06"]


def test_q7_authorization_is_exact_and_no_automatic_retry():
    p = prepare()
    a = authorization_for(p)
    assert a["preflight_sha256"] == canonical_sha256(p)
    assert a["paid_execution_authorized"] is True
    assert a["scenes"] == ["SC04", "SC05", "SC06"]
    assert a["max_rewrites_per_scene"] == 1
    assert a["automatic_retry"] is False
    assert a["stop_chain_on_scene_failure"] is True
    assert a["max_total_cost_usd"] == 0.90


def test_q7_missing_credential_fails_before_claim(tmp_path):
    p = prepare()
    a = authorization_for(p)
    with pytest.raises(RuntimeError, match="Missing credential"):
        execute(
            api_key="",
            preflight=p,
            authorization=a,
            output=tmp_path / "q7",
        )
    assert not (tmp_path / "q7").exists()


def test_q7_tampered_preflight_fails_before_claim(tmp_path):
    p = prepare()
    a = authorization_for(p)
    tampered = json.loads(json.dumps(p))
    tampered["max_total_cost_usd"] = 9.0
    with pytest.raises(RuntimeError, match="preflight drift"):
        execute(
            api_key="fake",
            preflight=tampered,
            authorization=a,
            output=tmp_path / "q7",
        )
    assert not (tmp_path / "q7").exists()
