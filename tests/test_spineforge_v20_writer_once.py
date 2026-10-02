from __future__ import annotations

from copy import deepcopy

import pytest

from src.model_registry import normalize_openrouter_request
from src.spineforge_v20_writer_once import execute_writer_once, validate_writer_handoff


BASE_HANDOFF = {
    "schema": "spineforge-v20-writer-handoff.v1",
    "status": "WRITER_READY",
    "writer_model": "aion-labs/aion-3.5-mini",
    "approval_id": "a" * 64,
    "context_pack_id": "ctx",
    "context_fingerprint": "b" * 64,
    "spine_hash": "c" * 64,
    "exact_age": 12,
    "target_words_min": 1600,
    "target_words_max": 2500,
    "preferred_words_min": 2000,
    "preferred_words_max": 2200,
    "human_review": {
        "verdict": "APPROVE",
        "story_writer_authorized": True,
    },
    "paid_writer_execution_authorized": False,
    "writer_input": {"task": "write"},
}


def test_writer_handoff_validation_accepts_exact_writer_ready_shape():
    validate_writer_handoff(BASE_HANDOFF)


def test_writer_handoff_validation_rejects_missing_human_approval():
    bad = deepcopy(BASE_HANDOFF)
    bad["human_review"]["story_writer_authorized"] = False
    with pytest.raises(RuntimeError, match="not authorized"):
        validate_writer_handoff(bad)


def test_writer_once_uses_one_aion_call_and_blocks_all_downstream_stages():
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        story = "The Island That Wasn't on Any Map\n" + ("word " * 1999)
        body = {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 2000,
                "total_tokens": 2100,
            },
            "cost": 0.01,
        }
        request = {
            "temperature": kwargs["temperature"],
            "max_tokens": kwargs["max_tokens"],
            "reasoning": None,
            "response_format": None,
        }
        return story, body, request

    result = execute_writer_once(
        handoff=BASE_HANDOFF,
        api_key="fake",
        system_prompt="writer prompt",
        call_fn=fake_call,
    )
    assert len(calls) == 1
    assert calls[0]["model"] == "aion-labs/aion-3.5-mini"
    assert calls[0]["max_tokens"] == 7000
    assert calls[0]["request_class"] == "spineforge_v20_story_writer"
    assert result["status"] == "writer_generated"
    assert result["deterministic_checks"]["length_pass"] is True
    assert result["automatic_retry_executed"] is False
    assert result["editor_authorized"] is False
    assert result["judge_authorized"] is False
    assert result["repair_authorized"] is False
    assert result["translation_authorized"] is False
    assert result["state_commit_authorized"] is False


def test_writer_once_rejects_out_of_range_story_without_second_call():
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        story = "Title\n" + ("short " * 500)
        body = {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 500,
                "total_tokens": 600,
            },
            "cost": 0.005,
        }
        return story, body, {"temperature": 0.76}

    result = execute_writer_once(
        handoff=BASE_HANDOFF,
        api_key="fake",
        system_prompt="writer prompt",
        call_fn=fake_call,
    )
    assert len(calls) == 1
    assert result["status"] == "writer_generated_deterministic_check_failed"
    assert result["deterministic_checks"]["length_pass"] is False
    assert result["automatic_retry_executed"] is False


def test_v20_writer_request_class_bounds_mandatory_reasoning_and_caps_completion():
    payload = normalize_openrouter_request(
        "aion-labs/aion-3.5-mini",
        {
            "model": "aion-labs/aion-3.5-mini",
            "messages": [{"role": "user", "content": "write"}],
            "temperature": 0.76,
            "max_tokens": 9000,
        },
        request_class="spineforge_v20_story_writer",
        structured_output=False,
    )
    assert payload["max_tokens"] == 7000
    assert payload["reasoning"] == {"effort": "low", "exclude": True}
    assert "seed" not in payload
    assert "stream" not in payload
