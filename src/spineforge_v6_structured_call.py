from __future__ import annotations

import json
from typing import Any

from src.english_story_pipeline import (
    StructuredJsonCallError,
    call_structured_json_with_retry as call_legacy_structured,
)
from src.spineforge_v6_json_schema import build_json_schema_response_format
from src.spineforge_v6_strict_call import call_openrouter as call_openrouter_strict


AION_MODEL = "aion-labs/aion-3.5-mini"
SONNET_MODEL = "anthropic/claude-sonnet-5.5"
LUNA_MODEL = "openai/gpt-5.6-luna"

STRICT_MODELS = {SONNET_MODEL, LUNA_MODEL}


def _strict_schema_name(model: str) -> str:
    if model == SONNET_MODEL:
        return "spineforge_structural_assembly_v1"
    if model == LUNA_MODEL:
        return "spineforge_product_gate_v1"
    raise RuntimeError(f"Unsupported strict SpineForge v6 model: {model}")


def call_structured_json_with_retry(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int | None,
    seed: int | None,
    request_class: str,
    max_parse_attempts: int = 1,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """
    Preserve the v5 runtime call interface while changing only the provider
    enforcement boundary:

    - Aion stays on its verified json_object transport because its endpoint
      does not advertise strict JSON-schema enforcement.
    - Sonnet and Luna receive the exact application output_contract as
      provider-level strict JSON Schema, plus provider require_parameters.
    - Application/Pydantic validation still runs after this function.
    - No parse retry is performed on strict calls.
    """
    if model not in STRICT_MODELS:
        return call_legacy_structured(
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed,
            request_class=request_class,
            max_parse_attempts=max_parse_attempts,
        )

    if max_parse_attempts != 1:
        raise RuntimeError("SpineForge v6 strict calls forbid parse retries.")

    try:
        request_payload = json.loads(user_prompt)
    except json.JSONDecodeError as exc:
        raise RuntimeError("SpineForge v6 strict user prompt must be one JSON object.") from exc
    if not isinstance(request_payload, dict):
        raise RuntimeError("SpineForge v6 strict user prompt root must be an object.")

    schema = request_payload.get("output_contract")
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise RuntimeError("SpineForge v6 strict call requires object output_contract.")

    response_format = build_json_schema_response_format(
        name=_strict_schema_name(model),
        schema=schema,
    )
    text, body, request = call_openrouter_strict(
        api_key=api_key,
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        seed=seed,
        request_class=request_class,
        response_format=response_format,
        require_parameters=True,
    )

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StructuredJsonCallError(
            "STRICT_JSON_SCHEMA_RESPONSE_INVALID_JSON",
            {
                "stage": "strict_json_schema_parse",
                "model": model,
                "request_class": request_class,
                "request": request,
                "raw_response": text,
                "body": body,
                "parse_failures": [{
                    "parse_attempt": 1,
                    "error": str(exc),
                    "raw_response": text,
                }],
                "retry_suppressed": True,
                "retry_suppressed_reason": "provider_strict_schema_call",
            },
        ) from exc

    if not isinstance(parsed, dict):
        raise StructuredJsonCallError(
            "STRICT_JSON_SCHEMA_RESPONSE_ROOT_NOT_OBJECT",
            {
                "stage": "strict_json_schema_parse",
                "model": model,
                "request_class": request_class,
                "request": request,
                "raw_response": text,
                "body": body,
                "parse_failures": [{
                    "parse_attempt": 1,
                    "error": "root_not_object",
                    "raw_response": text,
                }],
                "retry_suppressed": True,
                "retry_suppressed_reason": "provider_strict_schema_call",
            },
        )

    return parsed, body, request, []
