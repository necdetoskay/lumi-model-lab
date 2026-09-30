from __future__ import annotations

import json

import pytest

import src.spineforge_v7_structured_call as adapter
from src.spineforge_v7_contract import (
    StructuralBeatsV1,
    StructuralFrameV1,
    StructuralResolutionV1,
)


@pytest.mark.parametrize(
    ("task", "contract"),
    [
        ("compile_structural_frame", StructuralFrameV1),
        ("compile_structural_beats", StructuralBeatsV1),
        ("compile_structural_resolution", StructuralResolutionV1),
    ],
)
def test_sonnet_sections_use_small_provider_strict_schema(monkeypatch, task, contract) -> None:
    captured = {}

    def fake_strict(**kwargs):
        captured.update(kwargs)
        return "{}", {"usage": {}}, {
            "response_format": kwargs["response_format"],
            "provider": {"require_parameters": kwargs["require_parameters"]},
        }

    monkeypatch.setattr(adapter, "call_openrouter_strict", fake_strict)
    payload = {
        "task": task,
        "output_contract": contract.model_json_schema(by_alias=True),
    }
    value, _, request, _ = adapter.call_structured_json_once(
        api_key="x",
        model=adapter.SONNET_MODEL,
        system_prompt="system",
        user_prompt=json.dumps(payload),
        temperature=0.0,
        max_tokens=1000,
        seed=None,
        request_class="saga_architect",
    )
    fmt = captured["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["strict"] is True
    assert adapter.schema_size_bytes(fmt["json_schema"]["schema"]) < adapter.SONNET_STRICT_SCHEMA_MAX_BYTES
    assert captured["require_parameters"] is True
    assert request["provider"]["require_parameters"] is True
    assert value == {}


def test_aion_stays_on_legacy_json_object_path(monkeypatch) -> None:
    seen = {}

    def fake_legacy(**kwargs):
        seen.update(kwargs)
        return {"value": "ok"}, {"usage": {}}, {"response_format": {"type": "json_object"}}, []

    monkeypatch.setattr(adapter, "call_legacy_structured", fake_legacy)
    monkeypatch.setattr(
        adapter,
        "call_openrouter_strict",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("strict path forbidden")),
    )
    result, _, request, _ = adapter.call_structured_json_once(
        api_key="x",
        model=adapter.AION_MODEL,
        system_prompt="system",
        user_prompt=json.dumps({"task": "creative", "output_contract": {"type": "object"}}),
        temperature=0.8,
        max_tokens=1000,
        seed=None,
        request_class="teacher_story_medium_reasoning",
    )
    assert result == {"value": "ok"}
    assert request["response_format"]["type"] == "json_object"
    assert seen["max_parse_attempts"] == 1
