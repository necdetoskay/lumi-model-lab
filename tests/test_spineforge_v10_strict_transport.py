from __future__ import annotations

import json

import pytest

import src.spineforge_v10_structured_call as adapter
from src.spineforge_v10_contract import (
    StructuralBeatsV10 as StructuralBeatsV1,
    StructuralFrameV10 as StructuralFrameV1,
    StructuralResolutionV10 as StructuralResolutionV1,
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


def test_v10_sanitizer_preserves_real_property_names_that_match_annotation_keywords() -> None:
    source = {
        "title": "Root schema annotation",
        "description": "Root schema description",
        "type": "object",
        "properties": {
            "title": {"title": "Field annotation", "type": "string", "description": "metadata"},
            "description": {"type": "string", "description": "metadata"},
            "default": {"type": "string", "default": "x"},
            "normal": {"type": "string", "pattern": "^x$"},
        },
        "required": ["title", "description", "default", "normal"],
        "additionalProperties": False,
    }
    got = adapter.build_provider_transport_schema(source)
    assert "title" not in got
    assert "description" not in got
    assert set(got["properties"]) == {"title", "description", "default", "normal"}
    assert got["properties"]["title"] == {"type": "string"}
    assert got["properties"]["description"] == {"type": "string"}
    assert got["properties"]["default"] == {"type": "string"}
    assert got["properties"]["normal"] == {"type": "string"}
    adapter.validate_required_properties(got)


def test_v10_rejects_required_property_missing_from_properties_before_provider(monkeypatch) -> None:
    called = False

    def fake_strict(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("provider must not be called")

    monkeypatch.setattr(adapter, "call_openrouter_strict", fake_strict)
    payload = {
        "task": "compile_structural_frame",
        "output_contract": {
            "type": "object",
            "properties": {"schema": {"type": "string"}},
            "required": ["schema", "title"],
            "additionalProperties": False,
        },
    }
    with pytest.raises(RuntimeError, match="required keys missing from properties: title"):
        adapter.call_structured_json_once(
            api_key="x",
            model=adapter.SONNET_MODEL,
            system_prompt="system",
            user_prompt=json.dumps(payload),
            temperature=0.0,
            max_tokens=1000,
            seed=None,
            request_class="saga_architect",
        )
    assert called is False


def test_v10_real_frame_title_is_present_in_provider_schema(monkeypatch) -> None:
    captured = {}

    def fake_strict(**kwargs):
        captured.update(kwargs)
        return "{}", {"usage": {}}, {
            "response_format": kwargs["response_format"],
            "provider": {"require_parameters": kwargs["require_parameters"]},
        }

    monkeypatch.setattr(adapter, "call_openrouter_strict", fake_strict)
    payload = {
        "task": "compile_structural_frame",
        "output_contract": StructuralFrameV1.model_json_schema(by_alias=True),
    }
    adapter.call_structured_json_once(
        api_key="x",
        model=adapter.SONNET_MODEL,
        system_prompt="system",
        user_prompt=json.dumps(payload),
        temperature=0.0,
        max_tokens=1000,
        seed=None,
        request_class="saga_architect",
    )
    schema = captured["response_format"]["json_schema"]["schema"]
    assert "title" in schema["required"]
    assert "title" in schema["properties"]
    assert schema["properties"]["title"] == {"type": "string"}
    adapter.validate_required_properties(schema)
