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


def _q7_fake_prose(scene_id: str) -> str:
    base = {
        "SC04": "Ekin moved too quickly in the lighthouse while Duru watched. The hatchling fled down the narrow stair, the mother tried to follow and could not make the turn, and the compass was washed through the lower grate into the sea. Both girls stayed on the dry stair section and saw that the compass was gone.",
        "SC05": "Ekin watched the frightened hatchling retreat as water rose below. She admitted to Duru that her rush had caused the danger and asked for help. Using only the jacket Ekin already wore, they worked together from the dry stair and brought the hatchling safely back to the upper room.",
        "SC06": "The mother sheltered the hatchling in the dry upper room while Ekin and Duru watched. Ekin accepted that her grandfather's compass was gone and would not be replaced. They returned together by the known coastal route while the storm continued, and Ekin decided she would tell the truth about the loss.",
    }[scene_id]
    # Deterministic runtime tests need contract-valid length; semantic content is
    # supplied by the fake structured guard, not inferred from these filler words.
    words = base.split()
    while len(words) < 270:
        words.extend("Wind rain stone sea step breath careful together onward".split())
    return " ".join(words[:270])


def _q7_fake_guard(payload, prose, *, block=False):
    rows = []
    for event in payload["scene_contract"]["required_events"]:
        for pred in event["predicates"]:
            rows.append({
                "event_id": event["id"],
                "predicate_id": pred["id"],
                "subject": pred["subject"],
                "action": pred["action"],
                "target": pred["target"],
                "verdict": "SUPPORTED",
                "provenance": "DIRECT_OBSERVATION",
                "exact_text": prose,
                "evidence_subject": pred["target"],
                "state_pointer": None,
                "reason": "Fake provider supplies explicit structured support.",
            })
    residual = {
        "schema_name": "spineforge-relay.semantic-guard.v1",
        "decision": "PASS",
        "findings": [],
        "summary": "No residual blockers.",
    }
    if block:
        residual = {
            "schema_name": "spineforge-relay.semantic-guard.v1",
            "decision": "REWRITE",
            "findings": [{
                "code": "FAKE_BLOCK",
                "family": "spine",
                "severity": "BLOCKING",
                "exact_text": prose,
                "reason": "Forced non-convergence for stop-chain testing.",
                "repair_instruction": "Repair the blocked scene.",
            }],
            "summary": "Forced blocker.",
        }
    return {"event_evidence": rows, "residual": residual}


def _q7_fake_call_factory(*, fail_scene=None):
    from src.spineforge_relay_v1_q6d import request_for
    calls = []

    def fake_call(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        scene = payload["scene_contract"]["scene_id"]
        is_writer = "gpt-5.6-sol" in kwargs["model"]
        stage = "writer" if is_writer else "guard"
        calls.append((scene, stage, payload.get("attempt")))
        if is_writer:
            text = _q7_fake_prose(scene)
        else:
            text = json.dumps(
                _q7_fake_guard(
                    payload,
                    payload["candidate_prose"],
                    block=(scene == fail_scene),
                )
            )
        _, actual = request_for(stage, payload)
        body = {
            "choices": [{"finish_reason": "stop", "message": {"content": text}}],
            "usage": {
                "prompt_tokens": 1800,
                "completion_tokens": 600,
                "total_tokens": 2400,
                "cost": 0.01,
            },
        }
        return text, body, actual

    return calls, fake_call


def test_q7_fake_full_run_accepts_all_three_scenes_and_closes_story(tmp_path):
    p = prepare()
    a = authorization_for(p)
    calls, fake = _q7_fake_call_factory()
    out = execute(
        api_key="fake",
        preflight=p,
        authorization=a,
        output=tmp_path / "q7",
        call_fn=fake,
    )
    assert out["status"] == "ACCEPT"
    assert out["accepted_scenes"] == ["SC04", "SC05", "SC06"]
    assert out["state_advanced_to_revision"] == 6
    assert out["next_spine_beat"] is None
    assert len(calls) == 6
    final = json.loads((tmp_path / "q7/SC06-accepted.json").read_text())["state_after"]
    assert final["open_threads"] == []
    assert final["resolved_threads"] == ["recover_compass"]
    assert final["objects"]["compass"]["location"] == "lost_at_sea"
    assert all(x["status"] == "SATISFIED" for x in final["narrative_obligations"])


@pytest.mark.parametrize(
    ("fail_scene", "forbidden_later"),
    [("SC04", {"SC05", "SC06"}), ("SC05", {"SC06"})],
)
def test_q7_nonconvergent_scene_stops_before_later_provider_calls(
    tmp_path, fail_scene, forbidden_later
):
    p = prepare()
    a = authorization_for(p)
    calls, fake = _q7_fake_call_factory(fail_scene=fail_scene)
    out = execute(
        api_key="fake",
        preflight=p,
        authorization=a,
        output=tmp_path / ("q7-" + fail_scene),
        call_fn=fake,
    )
    assert out["status"] == "REJECT_NON_CONVERGENT"
    assert not any(scene in forbidden_later for scene, _stage, _attempt in calls)
    attempts = [row for row in calls if row[0] == fail_scene]
    assert attempts == [
        (fail_scene, "writer", 1),
        (fail_scene, "guard", None),
        (fail_scene, "writer", 2),
        (fail_scene, "guard", None),
    ]
