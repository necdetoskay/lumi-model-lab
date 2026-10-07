import json
import pytest
from src.spineforge_relay_v1_q5s_guard_paid import (
    AUTH_SCOPE, MAX_COST_USD, MODEL, build_inputs, execute_once, prepare, request_payload,
)

def auth(p):
    return {
        "paid_execution_authorized": True,
        "scope": AUTH_SCOPE,
        "preflight_sha256": p["artifact_sha256"],
        "max_cost_usd": MAX_COST_USD,
        "max_guard_calls": 1,
        "automatic_retry": False,
        "rewrite_authorized": False,
        "state_application_authorized": False,
        "explicit_user_message": "FAKE TEST AUTHORIZATION",
    }

def fake_raw():
    return {
        "schema_name":"spineforge-relay.semantic-guard.v1",
        "decision":"REWRITE",
        "findings":[{
            "code":"UNSUPPORTED_LOCAL_BOTANY",
            "family":"epistemic",
            "severity":"BLOCKING",
            "exact_text":"That weed only grows around the headland.",
            "reason":"Duru's StoryState does not establish this botanical knowledge.",
            "repair_instruction":"Remove the unsupported botanical claim and use only authorized route/lighthouse knowledge or direct observation."
        }],
        "summary":"One blocking epistemic claim."
    }

def test_q5sg_input_is_sol_candidate_and_has_no_word_blocker():
    payload, _state, _contract, prose, det = build_inputs()
    assert "That weed only grows around the headland." in prose
    assert det == []
    assert payload["candidate_prose"] == prose

def test_q5sg_request_is_bounded_sonnet_structured_guard():
    payload,*_=build_inputs()
    req=request_payload(payload)
    assert req["model"] == MODEL == "anthropic/claude-sonnet-5.5"
    assert req["max_tokens"] == 2500
    assert req["reasoning"] == {"effort":"low","exclude":True}
    assert req["response_format"]["type"] == "json_schema"

def test_q5sg_preflight_is_one_call_and_no_state_apply(tmp_path):
    p=prepare(tmp_path)
    assert p["max_guard_calls"] == 1
    assert p["automatic_retry"] is False
    assert p["rewrite_authorized"] is False
    assert p["state_application_authorized"] is False
    assert p["planned_uncached_cost_usd"] < MAX_COST_USD

def test_q5sg_unauthorized_never_calls_provider(tmp_path):
    p=prepare(tmp_path/"pre")
    calls={"n":0}
    def no_call(**kwargs):
        calls["n"]+=1
        raise AssertionError
    with pytest.raises(RuntimeError,match="Q5SG guard authorization"):
        execute_once(
            api_key="x",run_id="no",authorization={},
            preflight_path=tmp_path/"pre"/"preflight.json",
            guard_input_path=tmp_path/"pre"/"guard-input.json",
            output_root=tmp_path/"runs",call_fn=no_call,
        )
    assert calls["n"]==0

def test_q5sg_fake_call_returns_rewrite_without_applying_state(tmp_path):
    p=prepare(tmp_path/"pre")
    guard_input=json.loads((tmp_path/"pre"/"guard-input.json").read_text())
    req=request_payload(guard_input)
    calls={"n":0}
    def fake(**kwargs):
        calls["n"]+=1
        raw=fake_raw()
        body={
            "choices":[{"finish_reason":"stop","message":{"content":json.dumps(raw)}}],
            "usage":{"prompt_tokens":1900,"completion_tokens":450,"total_tokens":2350,"cost":0.008,
                     "completion_tokens_details":{"reasoning_tokens":0}},
        }
        return raw,body,req,[]
    out=execute_once(
        api_key="x",run_id="ok",authorization=auth(p),
        preflight_path=tmp_path/"pre"/"preflight.json",
        guard_input_path=tmp_path/"pre"/"guard-input.json",
        output_root=tmp_path/"runs",call_fn=fake,
    )
    assert calls["n"]==1
    assert out["status"]=="GUARD_REWRITE_REQUIRED"
    assert out["state_application_authorized"] is False
