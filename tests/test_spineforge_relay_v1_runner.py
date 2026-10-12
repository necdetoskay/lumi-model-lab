import json
from pathlib import Path

from src.spineforge_relay_v1_q6d import request_for
from src.spineforge_relay_v1_runner import build_chain, execute_story, prepare

GREENHOUSE = Path("tests/fixtures/spineforge_relay_v1/q8_greenhouse_notebook.json")
KITE = Path("tests/fixtures/spineforge_relay_v1/q8_hill_kite.json")


def _prose(words=210):
    return " ".join(["clear"] * words)


def _guard(payload, prose, *, block=False):
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
                "reason": "Synthetic zero-cost evidence for runner qualification.",
            })
    residual = {
        "schema_name": "spineforge-relay.semantic-guard.v1",
        "decision": "PASS",
        "findings": [],
        "summary": "No blockers.",
    }
    if block:
        residual = {
            "schema_name": "spineforge-relay.semantic-guard.v1",
            "decision": "REWRITE",
            "findings": [{
                "code": "FORCED_BLOCK",
                "family": "narrative",
                "severity": "BLOCKING",
                "exact_text": prose,
                "reason": "Synthetic forced failure.",
                "repair_instruction": "Repair the scene.",
            }],
            "summary": "Forced blocker.",
        }
    return {"event_evidence": evidence, "residual": residual}


def _fake_call(calls, *, always_block=False):
    def fake(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        scene = payload["scene_contract"]["scene_id"]
        writer = "gpt-5.6-sol" in kwargs["model"]
        stage = "writer" if writer else "guard"
        calls.append((scene, stage))
        if writer:
            text = _prose(210)
        else:
            text = json.dumps(_guard(payload, payload["candidate_prose"], block=always_block))
        _, actual = request_for(stage, payload)
        return text, {
            "choices": [{"finish_reason": "stop", "message": {"content": text}}],
            "usage": {
                "prompt_tokens": 1200,
                "completion_tokens": 450,
                "total_tokens": 1650,
                "cost": 0.01,
            },
        }, actual
    return fake


def test_generic_runner_has_no_lighthouse_story_specific_branches():
    source = Path("src/spineforge_relay_v1_runner.py").read_text(encoding="utf-8")
    for forbidden in ("lighthouse", "mother_dragon", "dragon_hatchling", "compass", "Ekin", "Duru"):
        assert forbidden not in source


def test_unrelated_fixtures_compile_to_terminal_expected_states():
    _f, _i, _r, start_a, rows_a, final_a = build_chain(GREENHOUSE)
    assert start_a.story_id == "q8-greenhouse-notebook"
    assert [p.scene_id for p, _c, _s in rows_a] == ["A1", "A2"]
    assert final_a.revision == 2
    assert final_a.next_spine_beat is None
    assert final_a.objects["notebook"].location == "Selin_hands"
    assert final_a.characters["Selin"].relationships["Bora"]["trust"] == "earned_initial"
    assert final_a.open_threads == []
    assert final_a.resolved_threads == ["recover_notebook"]

    _f, _i, _r, start_b, rows_b, final_b = build_chain(KITE)
    assert start_b.story_id == "q8-hill-kite"
    assert [p.scene_id for p, _c, _s in rows_b] == ["B1", "B2"]
    assert final_b.revision == 2
    assert final_b.next_spine_beat is None
    assert final_b.objects["kite"].location == "Deniz_hands"
    assert final_b.objects["Ece_scarf"].location == "Ece_hands"
    assert final_b.characters["Deniz"].relationships["Ece"]["trust"] == "earned"
    assert final_b.open_threads == []
    assert final_b.resolved_threads == ["recover_kite"]


def test_preflights_are_distinct_but_share_models_and_bounds():
    a = prepare(GREENHOUSE)
    b = prepare(KITE)
    assert a["story_id"] != b["story_id"]
    assert a["fixture_sha256"] != b["fixture_sha256"]
    assert a["writer"] == b["writer"] == "openai/gpt-5.6-sol"
    assert a["guard"] == b["guard"] == "anthropic/claude-sonnet-5.5"
    assert a["max_rewrites_per_scene"] == b["max_rewrites_per_scene"] == 1
    assert a["automatic_retry"] is b["automatic_retry"] is False
    assert a["max_story_cost_usd"] == b["max_story_cost_usd"] == 0.50


def test_same_runner_completes_two_unrelated_stories_with_fake_provider(tmp_path):
    calls_a = []
    out_a = execute_story(
        fixture_path=GREENHOUSE,
        api_key="fake",
        preflight=prepare(GREENHOUSE),
        output=tmp_path / "greenhouse",
        call_fn=_fake_call(calls_a),
    )
    assert out_a["status"] == "ACCEPT"
    assert out_a["accepted_scenes"] == ["A1", "A2"]
    assert len(calls_a) == 4

    calls_b = []
    out_b = execute_story(
        fixture_path=KITE,
        api_key="fake",
        preflight=prepare(KITE),
        output=tmp_path / "kite",
        call_fn=_fake_call(calls_b),
    )
    assert out_b["status"] == "ACCEPT"
    assert out_b["accepted_scenes"] == ["B1", "B2"]
    assert len(calls_b) == 4


def test_failed_first_scene_stops_before_second_scene(tmp_path):
    calls = []
    out = execute_story(
        fixture_path=GREENHOUSE,
        api_key="fake",
        preflight=prepare(GREENHOUSE),
        output=tmp_path / "blocked",
        call_fn=_fake_call(calls, always_block=True),
    )
    assert out["status"] == "REJECT_NON_CONVERGENT"
    assert out["state_advanced_to_revision"] == 0
    assert all(scene == "A1" for scene, _stage in calls)
    assert len(calls) == 4
