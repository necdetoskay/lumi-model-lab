import json
import pytest

from src.spineforge_relay_v1_q6c_prop_guard import (
    AUTH_SCOPE,
    MAX_COST_USD,
    MODEL,
    build_input,
    execute_once,
    prepare,
    qualify,
    request_payload,
)


def fake_raw():
    return {
        "event_evidence": [],
        "residual": {
            "schema_name": "spineforge-relay.semantic-guard.v1",
            "decision": "REWRITE",
            "findings": [
                {
                    "code": "UNAUTHORIZED_ACTIONABLE_PROP",
                    "family": "canon",
                    "severity": "BLOCKING",
                    "exact_text": "she placed the compass in a nest of dry rope and sailcloth beside the wall",
                    "reason": "Rope and sailcloth are portable/action-capable props not authorized by state, contract, canon or policy.",
                    "repair_instruction": "Use non-actionable nest material or omit the unauthorized props.",
                },
                {
                    "code": "UNAUTHORIZED_ACTIONABLE_PROP",
                    "family": "canon",
                    "severity": "BLOCKING",
                    "exact_text": "Something small stirred under a loop of rope.",
                    "reason": "The rope is an unauthorized portable/action-capable prop.",
                    "repair_instruction": "Remove the rope reference and keep the hatchling directly observable.",
                },
            ],
            "summary": "Two unauthorized actionable prop leaks require rewrite.",
        },
    }


def authorization(preflight):
    return {
        "paid_execution_authorized": True,
        "scope": AUTH_SCOPE,
        "preflight_sha256": preflight["artifact_sha256"],
        "max_cost_usd": MAX_COST_USD,
        "max_guard_calls": 1,
        "automatic_retry": False,
        "state_application_authorized": False,
        "explicit_user_message": "FAKE TEST AUTHORIZATION",
    }


def test_q6c_input_contains_prop_policy_and_real_q6b_bad_prose():
    payload, probe = build_input()
    assert "rope" in payload["candidate_prose"]
    assert payload["prop_authorization_policy"]["authorized_actionable_props"] == ["compass", "Ekin_jacket"]
    assert probe["expected_blocking_anchors"] == [
        "nest of dry rope and sailcloth",
        "loop of rope",
    ]


def test_q6c_request_is_single_structured_sonnet_guard():
    payload, _ = build_input()
    request = request_payload(payload)
    assert request["model"] == MODEL == "anthropic/claude-sonnet-5.5"
    assert request["max_tokens"] == 5000
    assert request["response_format"]["type"] == "json_schema"
    assert request["provider"]["require_parameters"] is True


def test_q6c_qualification_requires_both_prop_anchors():
    payload, probe = build_input()
    result = qualify(fake_raw(), payload["candidate_prose"], probe["expected_blocking_anchors"])
    assert result["qualification_pass"] is True
    assert result["decision"] == "REWRITE"
    assert all(row["matched"] for row in result["targets"])


def test_q6c_preflight_is_bounded(tmp_path):
    report = prepare(tmp_path)
    assert report["max_guard_calls"] == 1
    assert report["automatic_retry"] is False
    assert report["state_application_authorized"] is False
    assert report["planned_uncached_cost_usd"] < MAX_COST_USD


def test_q6c_unauthorized_never_calls_provider(tmp_path):
    preflight = prepare(tmp_path / "pre")
    calls = {"n": 0}

    def no_call(**kwargs):
        calls["n"] += 1
        raise AssertionError

    with pytest.raises(RuntimeError, match="Q6C prop guard authorization"):
        execute_once(
            api_key="fake",
            run_id="no",
            authorization={},
            preflight_path=tmp_path / "pre" / "preflight.json",
            input_path=tmp_path / "pre" / "guard-input.json",
            output_root=tmp_path / "runs",
            call_fn=no_call,
        )
    assert calls["n"] == 0


def test_q6c_fake_call_is_one_shot_and_qualifies(tmp_path):
    preflight = prepare(tmp_path / "pre")
    payload = json.loads((tmp_path / "pre" / "guard-input.json").read_text())
    request = request_payload(payload)
    calls = {"n": 0}

    def fake_call(**kwargs):
        calls["n"] += 1
        raw = fake_raw()
        body = {
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(raw)}}],
            "usage": {
                "prompt_tokens": 3500,
                "completion_tokens": 800,
                "total_tokens": 4300,
                "cost": 0.016,
                "completion_tokens_details": {"reasoning_tokens": 0},
            },
        }
        return raw, body, request, []

    out = execute_once(
        api_key="fake",
        run_id="ok",
        authorization=authorization(preflight),
        preflight_path=tmp_path / "pre" / "preflight.json",
        input_path=tmp_path / "pre" / "guard-input.json",
        output_root=tmp_path / "runs",
        call_fn=fake_call,
    )
    assert calls["n"] == 1
    assert out["status"] == "PROP_GUARD_QUALIFIED"
    assert out["qualification_pass"] is True
    assert out["automatic_retry_executed"] is False
