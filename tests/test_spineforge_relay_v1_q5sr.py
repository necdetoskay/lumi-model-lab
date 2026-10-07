import json
import pytest

from src.spineforge_relay_v1_q5sr import (
    AUTH_SCOPE, MAX_COST_USD, MODEL, build_rewrite_input, execute_once, prepare,
    request_payload, validate_rewrite,
)

def clean_scene():
    return " ".join([
        "Ekin rubbed her thumb across her grandfather's brass compass as storm clouds gathered beyond the harbor.",
        "A green shape flashed beneath the water, then a scarred sea dragon lunged over the quay and snapped the compass from her hand.",
        "Ekin yelled and tore after it along the planks.",
        "The dragon surfaced beyond the fishing boats and angled toward the headland, the brass compass flashing between its teeth.",
        "Ekin reached the final mooring post and searched for a way across the water.",
        "Don't jump, a girl called.",
        "Ekin spun toward the stranger.",
        "The girl pointed past the breakwater, where the dragon was still visible cutting toward the headland.",
        "The lighthouse stood there against the darkening sky.",
        "It is heading that way, the girl said. I know the coastal route to the lighthouse. I'm Duru.",
        "Ekin looked from Duru to the shrinking shape in the water.",
        "She hated needing help, but the compass was getting farther away.",
        "Fine, Ekin said. We go together. Until I get it back.",
        "Duru nodded and turned toward the harbor road.",
        "Ekin followed beside her, wary of the stranger but unwilling to lose another second."
    ])

def auth(p):
    return {
        "paid_execution_authorized":True,
        "scope":AUTH_SCOPE,
        "preflight_sha256":p["artifact_sha256"],
        "max_cost_usd":MAX_COST_USD,
        "max_rewrite_calls":1,
        "automatic_retry":False,
        "state_application_authorized":False,
        "explicit_user_message":"FAKE TEST AUTHORIZATION",
    }

def test_q5sr_is_attempt_two_from_q5sg_findings():
    payload, guard=build_rewrite_input()
    assert payload["attempt"] == 2
    assert guard["decision"] == "REWRITE"
    assert len(payload["blocking_findings"]) == 2
    assert payload["rewrite_policy"]["final_guard_required"] is True

def test_q5sr_request_uses_sol_low_reasoning():
    payload,_=build_rewrite_input()
    req=request_payload(payload)
    assert req["model"] == MODEL == "openai/gpt-5.6-sol"
    assert req["reasoning"] == {"effort":"low","exclude":True}
    assert req["response_format"] == {"type":"text"}

def test_q5sr_preflight_is_one_call_bounded(tmp_path):
    p=prepare(tmp_path)
    assert p["attempt"] == 2
    assert p["max_rewrite_calls"] == 1
    assert p["automatic_retry"] is False
    assert p["final_guard_required"] is True
    assert p["planned_uncached_cost_usd"] < MAX_COST_USD

def test_q5sr_clean_rewrite_is_pending_final_guard():
    payload,_=build_rewrite_input()
    a=validate_rewrite(clean_scene(),payload)
    assert a["attempt"] == 2
    assert a["status"] == "REWRITE_GENERATED_PENDING_FINAL_GUARD"
    assert a["state_application_authorized"] is False

def test_q5sr_fake_call_is_one_shot(tmp_path):
    p=prepare(tmp_path/"pre")
    payload=json.loads((tmp_path/"pre"/"rewrite-input.json").read_text())
    req=request_payload(payload)
    calls={"n":0}
    def fake(**kwargs):
        calls["n"] += 1
        return clean_scene(), {
            "choices":[{"finish_reason":"stop"}],
            "usage":{"prompt_tokens":2000,"completion_tokens":600,"total_tokens":2600,"cost":0.01,
                     "completion_tokens_details":{"reasoning_tokens":80}},
        }, req
    out=execute_once(
        api_key="x",run_id="ok",authorization=auth(p),
        preflight_path=tmp_path/"pre"/"preflight.json",
        rewrite_input_path=tmp_path/"pre"/"rewrite-input.json",
        output_root=tmp_path/"runs",call_fn=fake,
    )
    assert calls["n"] == 1
    assert out["status"] == "REWRITE_GENERATED_PENDING_FINAL_GUARD"
