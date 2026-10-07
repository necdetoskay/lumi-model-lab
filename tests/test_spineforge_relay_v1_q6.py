import json

from src.spineforge_relay_v1_q5t import request_for
from src.spineforge_relay_v1_q6 import (
    authorization_for,
    build_chain,
    execute,
    prepare,
)

SC02 = """Duru led Ekin away from the harbor along the coastal route she already knew. Ekin kept glancing back toward the shrinking harbor, as if the stolen compass might somehow reappear behind them. The wind strengthened over the headland, tugging at Ekin's jacket and flattening the grass beside the path.

"This way," Duru said, pointing to the climbing trail.

Ekin frowned. "I can see the lighthouse."

"Seeing it isn't the same as reaching it."

Ekin almost argued, then looked at the steep rocks below and followed. She did not thank Duru. Duru did not ask her to.

The white lighthouse grew larger with every turn. Its upper doorway stood open, dark against the pale wall. Thunder rolled farther out to sea, but the path beneath their feet remained clear.

At the last rise, Ekin hurried ahead. Duru caught up at the threshold.

"Still together?" Duru asked.

"Until I get the compass back."

They crossed the open doorway side by side and entered the dry upper room. Dust moved in the wind from a broken window. Ekin stopped just inside, listening for claws or wings, while Duru stayed close enough to be useful and far enough not to pretend they were friends."""

SC03 = """The upper room smelled of salt, old stone, and dry grass. Wind moved through a broken window and stirred a nest built in the far corner.

The mother sea dragon landed beside it and lowered her head. The brass compass dropped from her teeth into the nest. Ekin saw it at once.

"There," she whispered, taking a step.

Duru caught her sleeve. "Wait."

A small shape shifted behind the nest. Duru pointed. A cat-sized dragon hatchling stepped into view, its wings still too small for flight. Ekin saw it nose one of the dull metal scraps near the compass.

The mother dragon moved between Ekin and the nest. She spread one wing and hissed. Ekin stopped, but her eyes stayed on the compass.

"I'm not leaving without it."

"I'm not telling you to leave," Duru said. "I'm telling you not to rush her."

Near the wall, both girls noticed a narrow turning stair descending from the upper room. Far below, through the stairwell, came the hollow boom of waves against a lower iron grate facing the sea.

Ekin looked from the stair back to the nest. The mother still blocked the approach, the hatchling stayed close behind her, and the compass lay in plain sight.

Duru lowered her voice. "Think first."

Ekin heard the warning as an order. Her jaw tightened. "I am thinking."

But she did not move for the compass yet."""


def fake_guard(payload, prose):
    evidence = []
    for event in payload["scene_contract"]["required_events"]:
        for pred in event["predicates"]:
            evidence.append({
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
                "reason": "Fake provider fixture supplies explicit semantic support.",
            })
    return {
        "event_evidence": evidence,
        "residual": {
            "schema_name": "spineforge-relay.semantic-guard.v1",
            "decision": "PASS",
            "findings": [],
            "summary": "No residual blocking defects.",
        },
    }


def test_q6_chain_binds_sc03_to_expected_revision_two_state():
    _fixture, _intent, _route, start, rows, final = build_chain()
    assert start.revision == 1
    assert start.next_spine_beat == "SC02"
    assert rows[0][1].story_state_revision == 1
    assert rows[1][1].story_state_revision == 2
    assert rows[1][2].characters["Ekin"].location == "lighthouse_upper_room"
    assert final.revision == 3
    assert final.next_spine_beat == "SC04"
    assert final.objects["compass"].location == "lighthouse_nest"
    assert final.objects["dragon_hatchling"].location == "lighthouse_upper_room"
    assert final.world["narrow_stair_to_lower_room"] is True
    assert final.world["lower_room_sea_grate"] is True


def test_q6_preflight_is_bounded_and_derived_from_frozen_q5t_state():
    p = prepare()
    assert [x["scene_id"] for x in p["scene_contracts"]] == ["SC02", "SC03"]
    assert p["max_rewrites_per_scene"] == 1
    assert p["automatic_retry"] is False
    assert p["stop_chain_on_scene_failure"] is True
    assert p["max_total_cost_usd"] == 0.60


def test_q6_fake_end_to_end_accepts_two_scenes_and_advances_to_sc04(tmp_path):
    p = prepare()
    auth = authorization_for(p)
    calls = []

    def fake_call(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        model = kwargs["model"]
        scene = payload["scene_contract"]["scene_id"]
        calls.append((scene, model))
        if "gpt-5.6-sol" in model:
            text = SC02 if scene == "SC02" else SC03
            stage = "writer"
        else:
            prose = payload["candidate_prose"]
            text = json.dumps(fake_guard(payload, prose))
            stage = "guard"
        _, actual = request_for(stage, payload)
        body = {
            "choices": [{"finish_reason": "stop", "message": {"content": text}}],
            "usage": {
                "prompt_tokens": 1500,
                "completion_tokens": 500,
                "total_tokens": 2000,
                "cost": 0.01,
            },
        }
        return text, body, actual

    out = execute(
        api_key="fake",
        preflight=p,
        authorization=auth,
        output=tmp_path / "q6",
        call_fn=fake_call,
    )
    assert out["status"] == "ACCEPT"
    assert out["accepted_scenes"] == ["SC02", "SC03"]
    assert out["state_advanced_to_revision"] == 3
    assert out["next_spine_beat"] == "SC04"
    assert len(calls) == 4

    sc03 = json.loads((tmp_path / "q6/SC03-accepted.json").read_text())
    assert sc03["state_after"]["objects"]["dragon_hatchling"]["state"]["can_fly"] is False


def test_q6_stops_before_sc03_when_sc02_guard_blocks(tmp_path):
    p = prepare()
    auth = authorization_for(p)
    calls = []

    def fake_call(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        model = kwargs["model"]
        scene = payload["scene_contract"]["scene_id"]
        calls.append((scene, model))
        if "gpt-5.6-sol" in model:
            text = SC02
            stage = "writer"
        else:
            prose = payload["candidate_prose"]
            raw = fake_guard(payload, prose)
            raw["residual"] = {
                "schema_name": "spineforge-relay.semantic-guard.v1",
                "decision": "REWRITE",
                "findings": [{
                    "code": "BLOCK",
                    "family": "spine",
                    "severity": "BLOCKING",
                    "exact_text": prose,
                    "reason": "forced failure",
                    "repair_instruction": "fix",
                }],
                "summary": "forced failure",
            }
            text = json.dumps(raw)
            stage = "guard"
        _, actual = request_for(stage, payload)
        body = {
            "choices": [{"finish_reason": "stop", "message": {"content": text}}],
            "usage": {
                "prompt_tokens": 1500,
                "completion_tokens": 500,
                "total_tokens": 2000,
                "cost": 0.01,
            },
        }
        return text, body, actual

    out = execute(
        api_key="fake",
        preflight=p,
        authorization=auth,
        output=tmp_path / "q6fail",
        call_fn=fake_call,
    )
    assert out["status"] == "REJECT_NON_CONVERGENT"
    assert all(scene == "SC02" for scene, _ in calls)
    assert out["state_advanced_to_revision"] == 1
