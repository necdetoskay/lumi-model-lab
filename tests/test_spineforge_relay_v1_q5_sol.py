import json
import pytest

from src.spineforge_relay_v1_q5_sol import (
    AUTH_SCOPE, MAX_COST_USD, MAX_TOKENS, MODEL,
    build_inputs, execute_once, prepare, request_payload, validate_candidate,
)

def good_scene():
    return " ".join([
        "Ekin was turning her grandfather's brass compass in her palm when the harbor water burst beside the dock.",
        "A scarred sea dragon rose through the spray, hooked the compass away with one webbed claw, and dropped back into the chop.",
        "Ekin shouted and sprinted after it along the planks as the dragon surfaced farther out, brass flashing between its claws.",
        "It angled toward the headland while Ekin raced for the cliff lane.",
        "Stop, someone called behind her.",
        "Ekin turned on a girl standing near the gangplank.",
        "The girl pointed to wet scales on the boards and then to a brief glint near the old lighthouse.",
        "I'm Duru, she said. The coastal path reaches the lighthouse faster than that lane.",
        "Ekin looked from the stranger to the distant flash.",
        "Every part of her wanted to keep chasing alone, but the compass was already getting farther away.",
        "Fine, she said. Show me the path. But don't slow me down.",
        "Duru shrugged and headed toward the coastal trail.",
        "Ekin fell into step beside her, still wary and still angry, while the dragon carried the compass toward the headland.",
        "They were not friends, but for the moment they were going the same way."
    ])

def auth(p):
    return {
        "paid_execution_authorized": True,
        "scope": AUTH_SCOPE,
        "preflight_sha256": p["artifact_sha256"],
        "max_cost_usd": MAX_COST_USD,
        "max_writer_calls": 1,
        "automatic_retry": False,
        "state_application_authorized": False,
        "explicit_user_message": "FAKE TEST AUTHORIZATION",
    }

def test_q5s_keeps_frozen_scene_contract():
    payload, state, plan, route, contract = build_inputs()
    assert state.next_spine_beat == "SC01"
    assert route.beat_ids[0] == "SC01"
    assert plan.spine_beats == ["SC01"]
    assert contract.consumed_spine_beats == ["SC01"]
    assert payload["scene_contract"]["required_exit_state"]["/objects/compass/location"] == "mother_dragon"

def test_q5s_request_is_sol_low_reasoning_plain_text():
    payload, *_ = build_inputs()
    req = request_payload(payload)
    assert req["model"] == MODEL == "openai/gpt-5.6-sol"
    assert req["max_tokens"] == MAX_TOKENS == 3500
    assert req["reasoning"] == {"effort":"low","exclude":True}
    assert req["response_format"] == {"type":"text"}
    assert "temperature" not in req
    assert req["provider"] == {"order":["openai"],"allow_fallbacks":False,"require_parameters":True}

def test_q5s_preflight_is_one_call_and_bounded(tmp_path):
    p=prepare(tmp_path)
    assert p["max_writer_calls"] == 1
    assert p["automatic_retry"] is False
    assert p["semantic_guard_required"] is True
    assert p["state_application_authorized"] is False
    assert p["planned_uncached_cost_usd"] < MAX_COST_USD

def test_q5s_validator_accepts_clean_scene():
    payload,*_=build_inputs()
    a=validate_candidate(good_scene(),payload)
    assert a["status"] == "WRITER_GENERATED_PENDING_SCENE_GUARD"
    assert a["state_application_authorized"] is False
    assert 180 <= a["word_count"] <= 280

def test_q5s_unauthorized_never_calls_provider(tmp_path):
    p=prepare(tmp_path/"pre")
    calls={"n":0}
    def no_call(**kwargs):
        calls["n"] += 1
        raise AssertionError
    with pytest.raises(RuntimeError,match="Q5S paid authorization"):
        execute_once(
            api_key="x",run_id="no",authorization={},
            preflight_path=tmp_path/"pre"/"preflight.json",
            writer_input_path=tmp_path/"pre"/"writer-input.json",
            output_root=tmp_path/"runs",call_fn=no_call,
        )
    assert calls["n"] == 0

def test_q5s_fake_call_is_one_shot_pending_guard(tmp_path):
    p=prepare(tmp_path/"pre")
    writer_input=json.loads((tmp_path/"pre"/"writer-input.json").read_text())
    req=request_payload(writer_input)
    calls={"n":0}
    def fake(**kwargs):
        calls["n"] += 1
        return good_scene(), {
            "choices":[{"finish_reason":"stop","message":{"content":good_scene()}}],
            "usage":{"prompt_tokens":1500,"completion_tokens":900,"total_tokens":2400,"cost":0.012,
                     "completion_tokens_details":{"reasoning_tokens":300}},
        }, req
    out=execute_once(
        api_key="x",run_id="ok",authorization=auth(p),
        preflight_path=tmp_path/"pre"/"preflight.json",
        writer_input_path=tmp_path/"pre"/"writer-input.json",
        output_root=tmp_path/"runs",call_fn=fake,
    )
    assert calls["n"] == 1
    assert out["status"] == "WRITER_GENERATED_PENDING_SCENE_GUARD"
    assert out["automatic_retry_executed"] is False
