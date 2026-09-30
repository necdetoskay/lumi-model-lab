from __future__ import annotations

from src.openrouter_json_schema import (
    build_json_schema_request_overlay,
    build_json_schema_response_format,
    require_schema_capable_provider,
)


def test_response_format_is_strict_json_schema() -> None:
    schema = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
        "additionalProperties": False,
    }
    value = build_json_schema_response_format(name="spine_compile", schema=schema)
    assert value == {
        "type": "json_schema",
        "json_schema": {
            "name": "spine_compile",
            "strict": True,
            "schema": schema,
        },
    }


def test_provider_requires_parameter_support() -> None:
    assert require_schema_capable_provider({"order": ["anthropic"]}) == {
        "order": ["anthropic"],
        "require_parameters": True,
    }


def test_overlay_contains_schema_and_provider_guard() -> None:
    schema = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
    overlay = build_json_schema_request_overlay(
        name="spine_compile",
        schema=schema,
        provider={"allow_fallbacks": False},
    )
    assert overlay["response_format"]["type"] == "json_schema"
    assert overlay["response_format"]["json_schema"]["strict"] is True
    assert overlay["provider"]["require_parameters"] is True
    assert overlay["provider"]["allow_fallbacks"] is False
