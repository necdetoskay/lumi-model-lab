from __future__ import annotations

from typing import Any


def build_json_schema_response_format(
    *,
    name: str,
    schema: dict[str, Any],
) -> dict[str, Any]:
    if not name or not name.replace("_", "").isalnum():
        raise ValueError("JSON-schema response name must be a non-empty identifier-like string")
    if schema.get("type") != "object":
        raise ValueError("Strict structured output root schema must be an object")
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": True,
            "schema": schema,
        },
    }


def require_schema_capable_provider(
    provider: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = dict(provider or {})
    result["require_parameters"] = True
    return result


def build_json_schema_request_overlay(
    *,
    name: str,
    schema: dict[str, Any],
    provider: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "response_format": build_json_schema_response_format(name=name, schema=schema),
        "provider": require_schema_capable_provider(provider),
    }
