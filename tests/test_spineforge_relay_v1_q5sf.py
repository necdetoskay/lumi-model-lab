import json
from src.spineforge_relay_v1_q5sf import (
    AUTH_SCOPE, AUTHORIZATION_SCHEMA_VERSION, MAX_COST_USD, build_inputs, decide, execute_once, prepare, request_payload,
)

def pass_report():
    return {
        "schema_name":"spineforge-relay.semantic-guard.v1",
        "decision":"PASS",
        "findings":[],
        "summary":"No blocking defects."
    }

def blocking_report(prose):
    anchor="It’s going toward the lighthouse"
    assert anchor in prose
    return {
        "schema_name":"spineforge-relay.semantic-guard.v1",
        "decision":"REWRITE",
        "findings":[{
            "code":"FINAL_BLOCKER",
            "family":"epistemic",
            "severity":"BLOCKING",
            "exact_text":anchor,
            "reason":"Synthetic final-guard blocker.",
            "repair_instruction":"No further automatic rewrite is permitted."
        }],
        "summary":"Blocking defect remains."
    }

def auth(p):
    return {
        "paid_execution_authorized":True,
        "scope":AUTH_SCOPE,
        "preflight_sha256":p["artifact_sha256"],
        "max_cost_usd":MAX_COST_USD,
        "max_guard_calls":1,
        "authorization_schema_version":AUTHORIZATION_SCHEMA_VERSION,
        "automatic_retry":False,
        "rewrite_authorized":False,
        "state_application_authorized":False,
        "explicit_user_message":"FAKE TEST AUTHORIZATION",
    }

def test_q5sf_uses_attempt_two_candidate():
    guard_input, _state, contract, prose, deterministic=build_inputs()
    assert contract.scene_id == "SC01"
    assert 180 <= len(prose.split()) <= 280
    assert deterministic == []

def test_q5sf_pass_means_accept_and_state_may_advance():
    _i,_s,c,p,d=build_inputs()
    out=decide(pass_report(),p,d,c.scene_id)
    assert out["decision"] == "ACCEPT"
    assert out["state_application_authorized"] is True
    assert out["publication_ready"] is False

def test_q5sf_blocker_means_non_convergent_no_third_rewrite():
    _i,_s,c,p,d=build_inputs()
    out=decide(blocking_report(p),p,d,c.scene_id)
    assert out["decision"] == "REJECT_NON_CONVERGENT"
    assert out["state_application_authorized"] is False

def test_q5sf_preflight_is_one_call(tmp_path):
    p=prepare(tmp_path)
    assert p["attempt"] == 2
    assert p["max_guard_calls"] == 1
    assert p["authorization_schema_version"] == 2
    assert p["automatic_retry"] is False
    assert p["rewrite_authorized"] is False
    assert p["planned_uncached_cost_usd"] < MAX_COST_USD

def test_q5sf_fake_pass_call(tmp_path):
    p=prepare(tmp_path/"pre")
    gi=json.loads((tmp_path/"pre"/"guard-input.json").read_text())
    req=request_payload(gi)
    calls={"n":0}
    def fake(**kwargs):
        calls["n"] += 1
        return pass_report(), {
            "choices":[{"finish_reason":"stop"}],
            "usage":{"prompt_tokens":1800,"completion_tokens":300,"total_tokens":2100,"cost":0.007}
        }, req, []
    out=execute_once(
        api_key="x",run_id="ok",authorization=auth(p),
        preflight_path=tmp_path/"pre"/"preflight.json",
        guard_input_path=tmp_path/"pre"/"guard-input.json",
        output_root=tmp_path/"runs",call_fn=fake,
    )
    assert calls["n"] == 1
    assert out["status"] == "FINAL_GUARD_ACCEPT"
    assert out["state_application_authorized"] is True
