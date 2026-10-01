from __future__ import annotations

import json
from pathlib import Path

import pytest
import requests

from src.narrative_spine_v1_contract import SpineProductGateV19
from src.spineforge_v19_transport import (
    STRICT_SCHEMA_MAX_BYTES,
    call_json_object_once,
    call_strict_json_once,
    schema_size_bytes,
)


class FakeResponse:
    ok = True
    status_code = 200
    text = ""

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _body(content: dict):
    return {
        "choices": [{"message": {"role": "assistant", "content": json.dumps(content)}}],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
            "cost": 0.001,
        },
    }


def test_v19_gate_strict_schema_is_provider_safe_size():
    schema = SpineProductGateV19.model_json_schema(by_alias=True)
    assert schema_size_bytes(schema) < STRICT_SCHEMA_MAX_BYTES


def test_v19_one_shot_transport_makes_exactly_one_http_request(monkeypatch):
    seen = []

    def normalize(model, payload, request_class, structured_output):
        payload = dict(payload)
        if structured_output:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def post(*args, **kwargs):
        seen.append((args, kwargs))
        return FakeResponse(_body({"ok": True}))

    monkeypatch.setattr("src.spineforge_v19_transport.normalize_openrouter_request", normalize)
    monkeypatch.setattr("src.spineforge_v19_transport.requests.post", post)

    parsed, _, request, _ = call_json_object_once(
        api_key="zero-cost-test",
        model="test/model",
        system_prompt="system",
        user_prompt="{}",
        temperature=0.0,
        max_tokens=100,
        seed=None,
        request_class="test",
    )
    assert parsed == {"ok": True}
    assert request["response_format"]["type"] == "json_object"
    assert len(seen) == 1


def test_v19_transient_http_failure_is_not_retried(monkeypatch):
    seen = []

    class RateLimited:
        ok = False
        status_code = 429
        text = "rate limited"

        def json(self):
            return {"error": {"message": "temporarily rate-limited upstream"}}

    def normalize(model, payload, request_class, structured_output):
        return dict(payload)

    def post(*args, **kwargs):
        seen.append((args, kwargs))
        return RateLimited()

    monkeypatch.setattr("src.spineforge_v19_transport.normalize_openrouter_request", normalize)
    monkeypatch.setattr("src.spineforge_v19_transport.requests.post", post)

    with pytest.raises(Exception) as exc:
        call_json_object_once(
            api_key="zero-cost-test",
            model="test/model",
            system_prompt="system",
            user_prompt="{}",
            temperature=0.0,
            max_tokens=100,
            seed=None,
            request_class="test",
        )
    assert len(seen) == 1
    trace = getattr(exc.value, "trace", {})
    assert trace.get("attempts") == 1
    assert trace.get("retry_suppressed") is True


def test_v19_gate_uses_strict_schema_and_requires_parameters(monkeypatch):
    seen = []

    def normalize(model, payload, request_class, structured_output):
        return dict(payload)

    def post(*args, **kwargs):
        seen.append(kwargs["json"])
        return FakeResponse(_body({
            "schema": "spineforge-v19-product-gate.v1",
            "decision": "ACCEPT",
            "blocking_findings": [],
            "summary": "Ready.",
        }))

    monkeypatch.setattr("src.spineforge_v19_transport.normalize_openrouter_request", normalize)
    monkeypatch.setattr("src.spineforge_v19_transport.requests.post", post)

    schema = SpineProductGateV19.model_json_schema(by_alias=True)
    parsed, _, request, _ = call_strict_json_once(
        api_key="zero-cost-test",
        model="test/model",
        system_prompt="system",
        user_prompt="{}",
        temperature=0.0,
        max_tokens=100,
        seed=None,
        request_class="test",
        schema_name="spineforge_v19_product_gate",
        schema=schema,
    )
    assert parsed["decision"] == "ACCEPT"
    assert request["response_format"]["type"] == "json_schema"
    assert request["provider"]["require_parameters"] is True
    assert len(seen) == 1


def test_v19_runtime_does_not_import_shared_retry_transport():
    source = Path("src/spineforge_v19.py").read_text(encoding="utf-8")
    assert "call_structured_json_with_retry" not in source
    transport = Path("src/spineforge_v19_transport.py").read_text(encoding="utf-8")
    assert "while True" not in transport
    assert "time.sleep" not in transport


def test_v19_gate_strict_schema_requires_every_root_property():
    schema = SpineProductGateV19.model_json_schema(by_alias=True)
    assert set(schema["required"]) == set(schema["properties"])
    assert "blocking_findings" in schema["required"]
