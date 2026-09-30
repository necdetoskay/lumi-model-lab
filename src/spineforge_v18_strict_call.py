from __future__ import annotations

import json
from typing import Any

from src.english_story_pipeline import StructuredJsonCallError
from src.generate import parse_cost, parse_usage
from src.spineforge_v6_json_schema import build_json_schema_response_format
from src.spineforge_v6_strict_call import call_openrouter as call_openrouter_strict
from src.spineforge_v18_transport import build_strict_audit_transport_schema, schema_size_bytes


SONNET_MODEL = "anthropic/claude-sonnet-5.5"
STRICT_SCHEMA_MAX_BYTES = 4096


def call_strict_audit_once(
    *,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    request_class: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    schema = build_strict_audit_transport_schema()
    size = schema_size_bytes(schema)
    if size > STRICT_SCHEMA_MAX_BYTES:
        raise RuntimeError(f"v18 strict audit schema too large: {size}>{STRICT_SCHEMA_MAX_BYTES}")

    response_format = build_json_schema_response_format(
        name="spineforge_audit_transport_v18",
        schema=schema,
    )
    text, body, request = call_openrouter_strict(
        api_key=api_key,
        model=SONNET_MODEL,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        seed=None,
        request_class=request_class,
        response_format=response_format,
        require_parameters=True,
    )
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StructuredJsonCallError(
            "STRICT_AUDIT_JSON_INVALID",
            {
                "stage": "strict_audit_parse",
                "model": SONNET_MODEL,
                "request_class": request_class,
                "request": request,
                "raw_response": text,
                "body": body,
                "raw_usage": body.get("usage") or {},
                "usage": parse_usage(body).model_dump(mode="json"),
                "cost": parse_cost(body).model_dump(mode="json"),
                "retry_suppressed": True,
                "retry_suppressed_reason": "provider_strict_schema_call",
            },
        ) from exc
    if not isinstance(parsed, dict):
        raise StructuredJsonCallError(
            "STRICT_AUDIT_ROOT_NOT_OBJECT",
            {
                "stage": "strict_audit_parse",
                "model": SONNET_MODEL,
                "request_class": request_class,
                "request": request,
                "body": body,
                "raw_usage": body.get("usage") or {},
                "usage": parse_usage(body).model_dump(mode="json"),
                "cost": parse_cost(body).model_dump(mode="json"),
                "retry_suppressed": True,
            },
        )
    return parsed, body, request, []
