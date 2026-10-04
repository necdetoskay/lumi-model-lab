from __future__ import annotations

import json

from src.spineforge_v19_transport import STRICT_SCHEMA_MAX_BYTES, schema_size_bytes
from src.spineforge_v21_model_adapter import (
    AUDIT_RESPONSE_SCHEMA,
    BASELINE_MODEL,
    FINAL_AUDIT_REQUEST_CLASS,
    FINAL_MAX_TOKENS,
    INITIAL_AUDIT_REQUEST_CLASS,
    INITIAL_MAX_TOKENS,
    REPAIR_MAX_TOKENS,
    SCENE_REPAIR_REQUEST_CLASS,
    REPAIR_RESPONSE_SCHEMA,
    execute_final_audit_call,
    execute_initial_audit_call,
    execute_scene_repair_call,
)


def _body():
    return {
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
            "cost": 0.005,
        }
    }


def _request(max_tokens):
    return {
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_schema"},
    }


def test_v21_schemas_fit_strict_transport_budget():
    assert schema_size_bytes(AUDIT_RESPONSE_SCHEMA) <= STRICT_SCHEMA_MAX_BYTES
    assert schema_size_bytes(REPAIR_RESPONSE_SCHEMA) <= STRICT_SCHEMA_MAX_BYTES


def test_initial_audit_adapter_is_exactly_one_sonnet_call():
    captured = {}

    def fake_call(**kwargs):
        captured.update(kwargs)
        return {"findings": [], "summary": "clean"}, _body(), _request(INITIAL_MAX_TOKENS), []

    result = execute_initial_audit_call(
        api_key="not-used",
        payload={"full_story": "story"},
        call_fn=fake_call,
    )

    assert captured["model"] == BASELINE_MODEL
    assert captured["request_class"] == INITIAL_AUDIT_REQUEST_CLASS
    assert captured["max_tokens"] == INITIAL_MAX_TOKENS
    assert result["usage"]["api_calls"] == 1
    assert result["automatic_retry_executed"] is False


def test_scene_repair_adapter_returns_whole_scene_not_patches():
    captured = {}

    def fake_call(**kwargs):
        captured.update(kwargs)
        return (
            {
                "replacement_scene": "A coherent repaired scene.",
                "resolved_blocking_finding_indexes": [0, 1],
                "preserved_invariants": ["Arda cuts the line."],
                "summary": "scene repaired",
            },
            _body(),
            _request(REPAIR_MAX_TOKENS),
            [],
        )

    result = execute_scene_repair_call(
        api_key="not-used",
        payload={"scene_cluster": {"span_ids": ["S010", "S011"]}},
        call_fn=fake_call,
    )

    assert captured["model"] == BASELINE_MODEL
    assert captured["request_class"] == SCENE_REPAIR_REQUEST_CLASS
    assert captured["max_tokens"] == REPAIR_MAX_TOKENS
    assert "patches" not in result
    assert result["replacement_scene"] == "A coherent repaired scene."
    assert result["usage"]["api_calls"] == 1


def test_final_audit_adapter_receives_targeted_payload():
    captured = {}

    def fake_call(**kwargs):
        captured.update(kwargs)
        return {"findings": [], "summary": "clean"}, _body(), _request(FINAL_MAX_TOKENS), []

    payload = {
        "replacement_scene": "short scene",
        "entry_boundary": {"span_id": "S001", "text": "before"},
        "exit_boundary": {"span_id": "S010", "text": "after"},
    }
    result = execute_final_audit_call(
        api_key="not-used",
        payload=payload,
        call_fn=fake_call,
    )

    sent = json.loads(captured["user_prompt"])
    assert captured["model"] == BASELINE_MODEL
    assert captured["request_class"] == FINAL_AUDIT_REQUEST_CLASS
    assert captured["max_tokens"] == FINAL_MAX_TOKENS
    assert sent["replacement_scene"] == "short scene"
    assert "full_story" not in sent
    assert result["usage"]["api_calls"] == 1
