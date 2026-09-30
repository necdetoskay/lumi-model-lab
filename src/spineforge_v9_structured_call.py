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
SONNET_STRICT_SCHEMA_MAX_BYTES = 4096

TASK_SCHEMA_NAMES = {
    "compile_structural_frame": "spineforge_structural_frame_v1",
    "compile_structural_beats": "spineforge_structural_beats_v1",
    "compile_structural_resolution": "spineforge_structural_resolution_v1",
    "evaluate_spineforge_product": "spineforge_product_gate_v1",
}


PROVIDER_SCHEMA_DROP_KEYS = {
    "title",
    "description",
    "default",
    "pattern",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "minItems",
    "maxItems",
    "enum",
    "const",
}


def schema_size_bytes(schema: dict[str, Any]) -> int:
    return len(
        json.dumps(
            schema,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )


SCHEMA_NAME_MAP_KEYS = {"properties", "$defs", "definitions", "patternProperties", "dependentSchemas"}


def build_provider_transport_schema(value: Any, *, parent_key: str | None = None) -> Any:
    if isinstance(value, list):
        return [
            build_provider_transport_schema(item, parent_key=parent_key)
            for item in value
        ]
    if not isinstance(value, dict):
        return value

    preserve_mapping_keys = parent_key in SCHEMA_NAME_MAP_KEYS
    result: dict[str, Any] = {}
    for key, item in value.items():
        if not preserve_mapping_keys and key in PROVIDER_SCHEMA_DROP_KEYS:
            continue
        result[key] = build_provider_transport_schema(item, parent_key=key)
    return result


def validate_required_properties(schema: Any, *, path: str = "$") -> None:
    if isinstance(schema, list):
        for index, item in enumerate(schema):
            validate_required_properties(item, path=f"{path}[{index}]")
        return
    if not isinstance(schema, dict):
        return

    properties = schema.get("properties")
    required = schema.get("required")
    if isinstance(required, list):
        if not isinstance(properties, dict):
            raise RuntimeError(
                f"Strict schema invariant failed at {path}: required exists without properties."
            )
        missing = [name for name in required if name not in properties]
        if missing:
            raise RuntimeError(
                f"Strict schema invariant failed at {path}: required keys missing from properties: "
                + ", ".join(str(name) for name in missing)
            )

    for key, item in schema.items():
        validate_required_properties(item, path=f"{path}.{key}")


def validate_provider_schema_budget(*, model: str, task: str, schema: dict[str, Any]) -> int:
    size = schema_size_bytes(schema)
    if model == SONNET_MODEL and size > SONNET_STRICT_SCHEMA_MAX_BYTES:
        raise RuntimeError(
            "SpineForge v9 refuses oversized Sonnet strict transport schema before provider call: "
            f"task={task} bytes={size}>{SONNET_STRICT_SCHEMA_MAX_BYTES}"
        )
    return size


def call_structured_json_once(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int | None,
    seed: int | None,
    request_class: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
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
            max_parse_attempts=1,
        )

    try:
        request_payload = json.loads(user_prompt)
    except json.JSONDecodeError as exc:
        raise RuntimeError("SpineForge v9 strict user prompt must be one JSON object.") from exc
    if not isinstance(request_payload, dict):
        raise RuntimeError("SpineForge v9 strict user prompt root must be an object.")

    task = str(request_payload.get("task") or "")
    schema = request_payload.get("output_contract")
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise RuntimeError("SpineForge v9 strict call requires object output_contract.")
    if task not in TASK_SCHEMA_NAMES:
        raise RuntimeError(f"Unsupported SpineForge v9 strict task: {task}")

    transport_schema = build_provider_transport_schema(schema)
    validate_required_properties(transport_schema)
    validate_provider_schema_budget(model=model, task=task, schema=transport_schema)
    response_format = build_json_schema_response_format(
        name=TASK_SCHEMA_NAMES[task],
        schema=transport_schema,
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
                "parse_failures": [{"parse_attempt": 1, "error": str(exc)}],
                "retry_suppressed": True,
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
                "body": body,
                "retry_suppressed": True,
            },
        )
    return parsed, body, request, []
