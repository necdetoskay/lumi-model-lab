import json

import pytest

from src.spineforge_relay_v1_contracts import canonical_sha256
from src.spineforge_relay_v1_q7b import (
    MAX_TOTAL_COST,
    authorization_for,
    build_chain,
    execute,
    prepare,
)


def test_q7b_starts_from_q6e_state_with_mother_location():
    _fixture, _intent, _route, start, rows, final = build_chain()
    assert start.revision == 3
    assert start.next_spine_beat == "SC04"
    assert start.world["mother_dragon_location"] == "lighthouse_upper_room"
    assert [p.scene_id for p, _c, _s in rows] == ["SC04", "SC05", "SC06"]
    assert [c.story_state_revision for _p, c, _s in rows] == [3, 4, 5]
    assert final.revision == 6
    assert final.next_spine_beat is None
    assert final.world["mother_dragon_location"] == "lighthouse_upper_room"


def test_q7b_every_contract_binds_mother_location_entry_and_exit():
    _fixture, _intent, _route, _start, rows, _final = build_chain()
    for plan, contract, before in rows:
        assert before.world["mother_dragon_location"] == "lighthouse_upper_room"
        assert contract.entry_state["/world/mother_dragon_location"] == "lighthouse_upper_room"
        assert contract.required_exit_state["/world/mother_dragon_location"] == "lighthouse_upper_room"
        assert any("already inside the lighthouse upper room" in fact for fact in contract.immutable_facts)

    sc04 = rows[0][1]
    sc04_event = next(e for e in sc04.required_events if e.id == "SC04-E03")
    assert sc04_event.resulting_state["/world/mother_dragon_location"] == "lighthouse_upper_room"

    sc06 = rows[2][1]
    sc06_event = next(e for e in sc06.required_events if e.id == "SC06-E01")
    assert sc06_event.resulting_state["/world/mother_dragon_location"] == "lighthouse_upper_room"
    assert any("Do not make the mother sea dragon arrive" in rule for rule in sc06.forbidden)


def test_q7b_terminal_closure_still_holds():
    _fixture, _intent, _route, _start, _rows, final = build_chain()
    assert final.objects["compass"].location == "lost_at_sea"
    assert final.objects["dragon_hatchling"].location == "lighthouse_upper_room"
    assert final.characters["Ekin"].location == "harbor"
    assert final.characters["Duru"].location == "harbor"
    assert final.open_threads == []
    assert final.resolved_threads == ["recover_compass"]
    assert {o.id: o.status for o in final.narrative_obligations} == {
        "ekin_duru_trust": "SATISFIED",
        "compass_loss": "SATISFIED",
    }


def test_q7b_preflight_is_bounded_and_uses_q6e_source():
    p = prepare()
    assert p["qualification_id"] == "SFR-V1-Q7B-SC04-SC06-20261007"
    assert p["writer"] == "openai/gpt-5.6-sol"
    assert p["guard"] == "anthropic/claude-sonnet-5.5"
    assert p["max_rewrites_per_scene"] == 1
    assert p["automatic_retry"] is False
    assert p["stop_chain_on_scene_failure"] is True
    assert p["max_total_cost_usd"] == MAX_TOTAL_COST == 0.90
    assert [x["scene_id"] for x in p["scene_contracts"]] == ["SC04", "SC05", "SC06"]


def test_q7b_authorization_is_exact():
    p = prepare()
    a = authorization_for(p)
    assert a["preflight_sha256"] == canonical_sha256(p)
    assert a["paid_execution_authorized"] is True
    assert a["scenes"] == ["SC04", "SC05", "SC06"]
    assert a["automatic_retry"] is False


def test_q7b_missing_credential_fails_before_claim(tmp_path):
    p = prepare()
    a = authorization_for(p)
    with pytest.raises(RuntimeError, match="Missing credential"):
        execute(api_key="", preflight=p, authorization=a, output=tmp_path / "q7b")
    assert not (tmp_path / "q7b").exists()


def test_q7b_tampered_preflight_fails_before_claim(tmp_path):
    p = prepare()
    a = authorization_for(p)
    tampered = json.loads(json.dumps(p))
    tampered["max_total_cost_usd"] = 9.0
    with pytest.raises(RuntimeError, match="preflight drift"):
        execute(api_key="fake", preflight=tampered, authorization=a, output=tmp_path / "q7b")
    assert not (tmp_path / "q7b").exists()
