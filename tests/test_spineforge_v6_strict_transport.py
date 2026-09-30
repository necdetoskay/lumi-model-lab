from __future__ import annotations

import json
import pytest
import src.spineforge_v6_structured_call as adapter


def _schema() -> dict:
    return {
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
        "additionalProperties": False,
    }


def _user_prompt() -> str:
    return json.dumps({"output_contract": _schema(), "payload": {"x": 1}})


def test_aion_uses_legacy_json_object_path(monkeypatch) -> None:
    seen = {}
    def fake_legacy(**kwargs):
        seen.update(kwargs)
        return {"value": "aion"}, {"usage": {}}, {"response_format": {"type": "json_object"}}, []
    def forbidden_strict(**kwargs):
        raise AssertionError("strict transport must not be used for Aion")
    monkeypatch.setattr(adapter, "call_legacy_structured", fake_legacy)
    monkeypatch.setattr(adapter, "call_openrouter_strict", forbidden_strict)
    value, _, request, failures = adapter.call_structured_json_with_retry(
        api_key="x", model=adapter.AION_MODEL, system_prompt="system",
        user_prompt=_user_prompt(), temperature=0.8, max_tokens=1000,
        seed=None, request_class="teacher_story_medium_reasoning",
        max_parse_attempts=1,
    )
    assert value == {"value": "aion"}
    assert request["response_format"]["type"] == "json_object"
    assert failures == []
    assert seen["model"] == adapter.AION_MODEL


@pytest.mark.parametrize("model", [adapter.SONNET_MODEL, adapter.LUNA_MODEL])
def test_sonnet_and_luna_use_provider_strict_json_schema(monkeypatch, model: str) -> None:
    captured = {}
    def fake_strict(**kwargs):
        captured.update(kwargs)
        request = {
            "response_format": kwargs["response_format"],
            "provider": {"require_parameters": kwargs["require_parameters"]},
        }
        return '{"value":"ok"}', {"usage": {}}, request
    def forbidden_legacy(**kwargs):
        raise AssertionError("legacy json_object path must not be used")
    monkeypatch.setattr(adapter, "call_openrouter_strict", fake_strict)
    monkeypatch.setattr(adapter, "call_legacy_structured", forbidden_legacy)
    value, _, request, failures = adapter.call_structured_json_with_retry(
        api_key="x", model=model, system_prompt="system",
        user_prompt=_user_prompt(), temperature=0.0, max_tokens=5000,
        seed=None,
        request_class="saga_architect" if model == adapter.SONNET_MODEL else "editorial_audit",
        max_parse_attempts=1,
    )
    fmt = captured["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["strict"] is True
    assert fmt["json_schema"]["schema"] == _schema()
    assert captured["require_parameters"] is True
    assert request["provider"]["require_parameters"] is True
    assert value == {"value": "ok"}
    assert failures == []


def test_strict_path_forbids_parse_retry(monkeypatch) -> None:
    monkeypatch.setattr(adapter, "call_openrouter_strict", lambda **kwargs: ('{"value":"ok"}', {"usage": {}}, {}))
    with pytest.raises(RuntimeError, match="forbid parse retries"):
        adapter.call_structured_json_with_retry(
            api_key="x", model=adapter.SONNET_MODEL, system_prompt="system",
            user_prompt=_user_prompt(), temperature=0.0, max_tokens=5000,
            seed=None, request_class="saga_architect", max_parse_attempts=2,
        )


def test_strict_path_requires_output_contract_before_provider_call(monkeypatch) -> None:
    called = []
    monkeypatch.setattr(adapter, "call_openrouter_strict", lambda **kwargs: called.append(kwargs))
    with pytest.raises(RuntimeError, match="requires object output_contract"):
        adapter.call_structured_json_with_retry(
            api_key="x", model=adapter.SONNET_MODEL, system_prompt="system",
            user_prompt=json.dumps({"payload": {}}), temperature=0.0,
            max_tokens=5000, seed=None, request_class="saga_architect",
            max_parse_attempts=1,
        )
    assert called == []
