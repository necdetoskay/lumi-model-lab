import json
from src.spineforge_relay_v1_q5sg import (
    AUTH_SCOPE, MAX_COST_USD, build_inputs, decide, execute_once, prepare, request_payload,
)

def pass_report():
    return {
        "schema_name":"spineforge-relay.semantic-guard.v1",
        "decision":"PASS",
        "findings":[],
        "summary":"No blocking semantic defects."
    }

def rewrite_report(prose):
    anchor='"That weed only grows around the headland."'
    assert anchor in prose
    return {
        "schema_name":"spineforge-relay.semantic-guard.v1",
        "decision":"REWRITE",
        "findings":[{
            "code":"UNSUPPORTED_DURU_KNOWLEDGE",
            "family":"epistemic",
            "severity":"BLOCKING",
            "exact_text":anchor,
            "reason":"Duru does not have this botanical fact in StoryState and it is not directly established.",
            "repair_instruction":"Use only authorized coastal-route/lighthouse knowledge or directly observable evidence."
        }],
        "summary":"One unsupported epistemic claim."
    }

def auth(p):
    return {
        "paid_execution_authorized":True,
        "scope":AUTH_SCOPE,
        "preflight_sha256":p["artifact_sha256"],
        "max_cost_usd":MAX_COST_USD,
        "max_guard_calls":1,
        "automatic_retry":False,
        "state_application_authorized":False,
        "explicit_user_message":"FAKE TEST AUTHORIZATION",
    }

def test_q5sg_input_has_no_deterministic_word_error():
    guard_input, _state, contract, prose, deterministic = build_inputs()
    assert contract.target_words_min <= len(prose.split()) <= contract.target_words_max
    assert deterministic == []
    assert guard_input["candidate_prose"] == prose

def test_q5sg_preflight_is_bounded(tmp_path):
    p=prepare(tmp_path)
    assert p["max_guard_calls"] == 1
    assert p["automatic_retry"] is False
    assert p["rewrite_authorized"] is False
    assert p["state_application_authorized"] is False
    assert p["planned_uncached_cost_usd"] < MAX_COST_USD

def test_q5sg_pass_becomes_accept():
    guard_input, _state, contract, prose, deterministic = build_inputs()
    out=decide(pass_report(),prose,deterministic,contract.scene_id)
    assert out["decision"] == "ACCEPT"
    assert out["publication_ready"] is True

def test_q5sg_blocking_becomes_single_rewrite():
    guard_input, _state, contract, prose, deterministic = build_inputs()
    out=decide(rewrite_report(prose),prose,deterministic,contract.scene_id)
    assert out["decision"] == "REWRITE"
    assert out["rewrite_authorized"] is True
    assert out["state_application_authorized"] is False

def test_q5sg_fake_call_is_one_shot(tmp_path):
    p=prepare(tmp_path/"pre")
    guard_input=json.loads((tmp_path/"pre"/"guard-input.json").read_text())
    req=request_payload(guard_input)
    calls={"n":0}
    def fake(**kwargs):
        calls["n"] += 1
        return pass_report(), {
            "choices":[{"finish_reason":"stop"}],
            "usage":{"prompt_tokens":1800,"completion_tokens":500,"total_tokens":2300,"cost":0.008}
        }, req, []
    out=execute_once(
        api_key="x",run_id="ok",authorization=auth(p),
        preflight_path=tmp_path/"pre"/"preflight.json",
        guard_input_path=tmp_path/"pre"/"guard-input.json",
        output_root=tmp_path/"runs",call_fn=fake,
    )
    assert calls["n"] == 1
    assert out["status"] == "GUARD_COMPLETED_ACCEPT"
