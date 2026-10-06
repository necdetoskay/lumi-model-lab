import json

import pytest

from src.spineforge_relay_v1_guard_paid import (
    AUTH_SCOPE,
    MAX_COST_USD,
    MODEL,
    build_inputs,
    execute_once,
    prepare,
    qualify_report,
    request_payload,
)


def gold_raw():
    return {
        "schema_name": "spineforge-relay.semantic-guard.v1",
        "decision": "REWRITE",
        "findings": [
            {
                "code": "DURU_UNSUPPORTED_DRAGON_RULE",
                "family": "epistemic",
                "severity": "BLOCKING",
                "exact_text": "They always carry their treasure to the tower before a storm.",
                "reason": "Duru lacks provenance for this general dragon behavior.",
                "repair_instruction": "Remove the unsupported generalization and use only observable evidence.",
            },
            {
                "code": "DURU_UNSUPPORTED_MOTHER_RULE",
                "family": "epistemic",
                "severity": "BLOCKING",
                "exact_text": "That one's a mother. Mothers nest up high.",
                "reason": "Duru has no established knowledge of the dragon's maternal status.",
                "repair_instruction": "Remove the unsupported maternal claim.",
            },
        ],
        "summary": "Two blocking epistemic leaks.",
    }


def authorization(preflight):
    return {
        "paid_execution_authorized": True,
        "scope": AUTH_SCOPE,
        "preflight_sha256": preflight["artifact_sha256"],
        "max_cost_usd": MAX_COST_USD,
        "max_guard_calls": 1,
        "automatic_retry": False,
        "rewrite_authorized": False,
        "state_application_authorized": False,
        "explicit_user_message": "FAKE TEST AUTHORIZATION",
    }


def fake_call(**kwargs):
    guard_input, *_ = build_inputs()
    request = request_payload(guard_input)
    body = {
        "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(gold_raw())}}],
        "usage": {
            "prompt_tokens": 1400,
            "completion_tokens": 500,
            "total_tokens": 1900,
            "cost": 0.0078,
            "completion_tokens_details": {"reasoning_tokens": 200},
        },
    }
    return gold_raw(), body, request, []


def test_q5g_guard_input_contains_real_q5b_candidate_and_word_finding():
    guard_input, _state, _contract, prose = build_inputs()
    assert "They always carry their treasure to the tower before a storm." in prose
    assert guard_input["deterministic_findings"][0]["code"] == "WORD_BUDGET_OUTSIDE_CONTRACT"


def test_q5g_request_is_bounded_structured_sonnet():
    guard_input, *_ = build_inputs()
    request = request_payload(guard_input)
    assert request["model"] == MODEL == "anthropic/claude-sonnet-5.5"
    assert request["max_tokens"] == 2500
    assert request["reasoning"] == {"effort": "low", "exclude": True}
    assert request["response_format"]["type"] == "json_schema"
    assert request["provider"]["require_parameters"] is True


def test_q5g_gold_requires_both_epistemic_targets():
    _guard_input, _state, _contract, prose = build_inputs()
    result = qualify_report(gold_raw(), prose)
    assert result["qualification_pass"] is True
    assert result["decision"] == "REWRITE"
    assert all(x["matched"] for x in result["targets"])


def test_q5g_preflight_is_zero_cost_and_bounded(tmp_path):
    report = prepare(tmp_path)
    assert report["paid_execution_authorized"] is False
    assert report["max_guard_calls"] == 1
    assert report["automatic_retry"] is False
    assert report["planned_uncached_cost_usd"] < MAX_COST_USD


def test_q5g_unauthorized_execution_makes_no_call(tmp_path):
    preflight = prepare(tmp_path / "preflight")
    calls = {"n": 0}

    def no_call(**kwargs):
        calls["n"] += 1
        raise AssertionError("provider call forbidden")

    with pytest.raises(RuntimeError, match="Q5G guard authorization"):
        execute_once(
            api_key="fake",
            run_id="no",
            authorization={},
            preflight_path=tmp_path / "preflight" / "preflight.json",
            guard_input_path=tmp_path / "preflight" / "guard-input.json",
            output_root=tmp_path / "runs",
            call_fn=no_call,
        )
    assert calls["n"] == 0


def test_q5g_fake_paid_call_qualifies_guard_without_rewrite(tmp_path):
    preflight = prepare(tmp_path / "preflight")
    out = execute_once(
        api_key="fake",
        run_id="ok",
        authorization=authorization(preflight),
        preflight_path=tmp_path / "preflight" / "preflight.json",
        guard_input_path=tmp_path / "preflight" / "guard-input.json",
        output_root=tmp_path / "runs",
        call_fn=fake_call,
    )
    assert out["api_calls"] == 1
    assert out["status"] == "GUARD_QUALIFIED_REWRITE"
    assert out["rewrite_authorized"] is False
    assert out["state_application_authorized"] is False
