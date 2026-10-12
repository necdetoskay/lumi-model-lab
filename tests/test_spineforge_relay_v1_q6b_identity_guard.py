import json
import pytest

from src.spineforge_relay_v1_q6b_identity_guard import (
    AUTH_SCOPE,
    MAX_COST_USD,
    MODEL,
    build_input,
    execute_once,
    prepare,
    qualify,
    request_payload,
)


def fake_raw(prose):
    return {
        "event_evidence": [],
        "residual": {
            "schema_name": "spineforge-relay.semantic-guard.v1",
            "decision": "REWRITE",
            "findings": [
                {
                    "code": "DURU_PRONOUN_MISMATCH_1",
                    "family": "canon",
                    "severity": "BLOCKING",
                    "exact_text": "Ekin followed his finger.",
                    "reason": "Duru is canonically she/her; masculine pronoun contradicts immutable identity canon.",
                    "repair_instruction": "Use Duru's canonical pronouns.",
                },
                {
                    "code": "DURU_PRONOUN_MISMATCH_2",
                    "family": "canon",
                    "severity": "BLOCKING",
                    "exact_text": "He was right that the nest was blocked.",
                    "reason": "Duru is canonically she/her; masculine pronoun contradicts immutable identity canon.",
                    "repair_instruction": "Use Duru's canonical pronouns.",
                },
            ],
            "summary": "Two blocking Duru pronoun contradictions.",
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


def test_q6b_identity_input_carries_immutable_character_canon_and_bad_prose():
    payload, probe = build_input()
    assert payload["relevant_character_canon"]["Duru"]["identity"] == "girl"
    assert payload["relevant_character_canon"]["Duru"]["pronouns"] == ["she", "her"]
    assert "Ekin followed his finger." in payload["candidate_prose"]
    assert "He was right that the nest was blocked." in payload["candidate_prose"]
    assert probe["expected_blocking_anchors"] == ["his finger", "He was right"]


def test_q6b_identity_request_is_structured_bounded_sonnet():
    payload, _ = build_input()
    request = request_payload(payload)
    assert request["model"] == MODEL == "anthropic/claude-sonnet-5.5"
    assert request["max_tokens"] == 5000
    assert request["response_format"]["type"] == "json_schema"
    assert request["provider"]["require_parameters"] is True


def test_q6b_identity_qualification_requires_both_pronoun_anchors():
    payload, probe = build_input()
    result = qualify(fake_raw(payload["candidate_prose"]), payload["candidate_prose"], probe["expected_blocking_anchors"])
    assert result["qualification_pass"] is True
    assert result["decision"] == "REWRITE"
    assert all(row["matched"] for row in result["targets"])


def test_q6b_identity_preflight_is_zero_cost_and_bounded(tmp_path):
    report = prepare(tmp_path)
    assert report["max_guard_calls"] == 1
    assert report["automatic_retry"] is False
    assert report["state_application_authorized"] is False
    assert report["planned_uncached_cost_usd"] < MAX_COST_USD


def test_q6b_identity_unauthorized_makes_no_provider_call(tmp_path):
    preflight = prepare(tmp_path / "pre")
    calls = {"n": 0}

    def no_call(**kwargs):
        calls["n"] += 1
        raise AssertionError("provider call forbidden")

    with pytest.raises(RuntimeError, match="identity guard authorization"):
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


def test_q6b_identity_fake_paid_call_is_exactly_one_and_qualifies(tmp_path):
    preflight = prepare(tmp_path / "pre")
    payload = json.loads((tmp_path / "pre" / "guard-input.json").read_text())
    request = request_payload(payload)
    calls = {"n": 0}

    def fake_call(**kwargs):
        calls["n"] += 1
        raw = fake_raw(payload["candidate_prose"])
        body = {
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(raw)}}],
            "usage": {
                "prompt_tokens": 3000,
                "completion_tokens": 700,
                "total_tokens": 3700,
                "cost": 0.013,
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
    assert out["status"] == "IDENTITY_GUARD_QUALIFIED"
    assert out["qualification_pass"] is True
    assert out["automatic_retry_executed"] is False
    assert out["state_application_authorized"] is False
