import json
import pytest

from src.spineforge_relay_v1_rewrite_paid import (
    AUTH_SCOPE, MAX_COST_USD, MAX_TOKENS, MODEL,
    build_rewrite_input, execute_once, prepare, request_payload, validate_rewrite,
)

def good_scene():
    return " ".join([
        "Ekin turned the brass compass in her hands as wind worried the harbor ropes.",
        "A shadow swept over the dock and a scarred sea dragon surged from the water, snatching the compass from her palm.",
        "Ekin shouted and ran after it, boots pounding the planks until the creature lifted beyond the warehouses.",
        "She nearly chose the steep cliff lane when a girl at the gangplank called for her to stop.",
        "Ekin spun on her. The girl pointed to several wet scales scattered along the boards and then toward the old lighthouse on the headland.",
        "A brass flash winked high against the grey stone.",
        "I'm Duru, the girl said. The coastal path reaches the lighthouse faster than that lane.",
        "Ekin hated that the stranger had a point. The compass was her grandfather's, and every second mattered.",
        "Fine, Ekin said. Show me the path. But don't slow me down.",
        "Duru answered with a shrug and headed for the coastal trail.",
        "Ekin fell into step beside her, still wary, while the dragon disappeared toward the headland with the compass.",
        "Neither girl called it trust, but for the moment they were going the same way."
    ])

def auth(p):
    return {
        "paid_execution_authorized": True,
        "scope": AUTH_SCOPE,
        "preflight_sha256": p["artifact_sha256"],
        "max_cost_usd": MAX_COST_USD,
        "max_rewrite_calls": 1,
        "automatic_retry": False,
        "state_application_authorized": False,
        "explicit_user_message": "FAKE TEST AUTHORIZATION",
    }

def test_rewrite_input_is_attempt_two_and_contains_qualified_findings():
    payload, guard = build_rewrite_input()
    assert payload["attempt"] == 2
    assert guard["qualification_pass"] is True
    assert len(payload["blocking_findings"]) >= 4
    assert "Sea dragons don't come back" in payload["source_scene"]
    assert payload["rewrite_policy"]["state_application_authorized"] is False

def test_rewrite_request_is_bounded_aion_plain_text():
    payload, _ = build_rewrite_input()
    req = request_payload(payload)
    assert req["model"] == MODEL == "aion-labs/aion-3.5-mini"
    assert req["max_tokens"] == MAX_TOKENS == 5000
    assert req["reasoning"] == {"effort":"low","exclude":True}
    assert req["response_format"] == {"type":"text"}

def test_rewrite_preflight_is_bounded_and_zero_cost(tmp_path):
    p = prepare(tmp_path)
    assert p["max_rewrite_calls"] == 1
    assert p["automatic_retry"] is False
    assert p["attempt"] == 2
    assert p["final_guard_required"] is True
    assert p["planned_uncached_cost_usd"] < MAX_COST_USD

def test_rewrite_validator_accepts_targeted_clean_candidate():
    payload, _ = build_rewrite_input()
    a = validate_rewrite(good_scene(), payload)
    assert a["status"] == "REWRITE_GENERATED_PENDING_FINAL_GUARD"
    assert a["attempt"] == 2
    assert a["state_application_authorized"] is False

def test_rewrite_unauthorized_makes_no_call(tmp_path):
    p = prepare(tmp_path / "pre")
    calls = {"n":0}
    def no_call(**kwargs):
        calls["n"] += 1
        raise AssertionError
    with pytest.raises(RuntimeError, match="Q5R paid authorization"):
        execute_once(
            api_key="x", run_id="no", authorization={},
            preflight_path=tmp_path/"pre"/"preflight.json",
            rewrite_input_path=tmp_path/"pre"/"rewrite-input.json",
            output_root=tmp_path/"runs", call_fn=no_call,
        )
    assert calls["n"] == 0

def test_rewrite_fake_call_is_one_shot_pending_final_guard(tmp_path):
    p = prepare(tmp_path / "pre")
    payload = json.loads((tmp_path/"pre"/"rewrite-input.json").read_text())
    req = request_payload(payload)
    calls={"n":0}
    def fake(**kwargs):
        calls["n"] += 1
        return good_scene(), {
            "choices":[{"finish_reason":"stop","message":{"content":good_scene()}}],
            "usage":{"prompt_tokens":2200,"completion_tokens":900,"total_tokens":3100,"cost":0.0028,
                     "completion_tokens_details":{"reasoning_tokens":400}},
        }, req
    out = execute_once(
        api_key="x",run_id="ok",authorization=auth(p),
        preflight_path=tmp_path/"pre"/"preflight.json",
        rewrite_input_path=tmp_path/"pre"/"rewrite-input.json",
        output_root=tmp_path/"runs",call_fn=fake,
    )
    assert calls["n"] == 1
    assert out["status"] == "REWRITE_GENERATED_PENDING_FINAL_GUARD"
    assert out["automatic_retry_executed"] is False
    artifact=json.loads((tmp_path/"runs/ok/rewrite-artifact.json").read_text())
    assert artifact["publication_ready"] is False
