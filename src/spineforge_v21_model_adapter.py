from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from src.spineforge_v19_transport import call_strict_json_once
from src.spineforge_v21_wire import project_payload
from src.spineforge_v21_constraints import digest_json


BASELINE_MODEL = "anthropic/claude-sonnet-5.5"
INITIAL_AUDIT_REQUEST_CLASS = "spineforge_v21_initial_blocking_audit"
SCENE_REPAIR_REQUEST_CLASS = "spineforge_v21_scene_repair"
FINAL_AUDIT_REQUEST_CLASS = "spineforge_v21_targeted_final_audit"

INITIAL_AUDIT_PROMPT = Path("prompts/spineforge_v21_blocking_audit.md")
SCENE_REPAIR_PROMPT = Path("prompts/spineforge_v21_scene_repair.md")
FINAL_AUDIT_PROMPT = Path("prompts/spineforge_v21_targeted_final_audit.md")

INITIAL_MAX_TOKENS = 3000
REPAIR_MAX_TOKENS = 3500
FINAL_MAX_TOKENS = 1800

FINDING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "family",
        "severity",
        "repair_scope",
        "span_ids",
        "exact_text",
        "reason",
    ],
    "properties": {
        "family": {
            "type": "string",
            "enum": [
                "physical_feasibility",
                "causal_logic",
                "state_continuity",
                "epistemic_order",
                "spatial_consistency",
                "temporal_consistency",
                "response_causality",
                "closure_integrity",
                "canon_integrity",
                "language_naturalness",
                "age_suitability",
                "spine_fidelity",
                "narrative_coherence",
            ],
        },
        "severity": {
            "type": "string",
            "enum": ["minor", "moderate", "serious", "critical"],
        },
        "repair_scope": {
            "type": "string",
            "enum": [
                "SCENE_REPAIR",
                "STRUCTURAL_REPAIR",
                "REPLAN",
                "NO_REPAIR",
            ],
        },
        "span_ids": {
            "type": "array",
            "minItems": 1,
            "maxItems": 24,
            "items": {"type": "string", "maxLength": 16},
        },
        "exact_text": {"type": "string", "maxLength": 1200},
        "reason": {"type": "string", "maxLength": 500},
    },
}

AUDIT_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["findings", "summary"],
    "properties": {
        "findings": {
            "type": "array",
            "maxItems": 32,
            "items": FINDING_SCHEMA,
        },
        "summary": {"type": "string", "maxLength": 800},
    },
}

REPAIR_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "replacement_scene",
        "resolved_blocking_finding_indexes",
        "preserved_invariants",
        "summary",
    ],
    "properties": {
        "replacement_scene": {
            "type": "string",
            "minLength": 1,
            "maxLength": 12000,
        },
        "resolved_blocking_finding_indexes": {
            "type": "array",
            "minItems": 1,
            "maxItems": 32,
            "uniqueItems": True,
            "items": {"type": "integer", "minimum": 0, "maximum": 255},
        },
        "preserved_invariants": {
            "type": "array",
            "maxItems": 32,
            "items": {"type": "string", "maxLength": 500},
        },
        "summary": {"type": "string", "maxLength": 800},
    },
}

JsonCall = Callable[
    ..., tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]
]


class AdapterResponseError(RuntimeError):
    def __init__(self, message, usage, provider_evidence=None):
        super().__init__(message)
        self.usage = usage
        self.provider_evidence = provider_evidence
        self.diagnostic_message = message


def validate_schema(value, schema, path="$"):
    kind = schema.get("type")
    ok = {"object": isinstance(value, dict), "array": isinstance(value, list),
          "string": isinstance(value, str), "integer": type(value) is int}.get(kind, False)
    if not ok:
        raise RuntimeError(f"{path}: Invalid response type: expected {kind}")
    if "enum" in schema and value not in schema["enum"]:
        raise RuntimeError(f"{path}: Invalid response enum")
    if kind == "object":
        missing = [k for k in schema.get("required", []) if k not in value]
        if missing:
            raise RuntimeError(f"{path}: Missing required response field: {', '.join(missing)}")
        if schema.get("additionalProperties") is False and set(value) - set(schema["properties"]):
            raise RuntimeError(f"{path}: Unexpected response field")
        for k, v in value.items():
            validate_schema(v, schema["properties"][k], f"{path}.{k}")
    if kind in {"array", "string"}:
        suffix = "Items" if kind == "array" else "Length"
        if not schema.get("min" + suffix, 0) <= len(value) <= schema.get("max" + suffix, float("inf")):
            raise RuntimeError(f"{path}: Response length outside contract")
    if kind == "array":
        if schema.get("uniqueItems") and len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
            raise RuntimeError(f"{path}: Duplicate response items")
        for i, v in enumerate(value):
            validate_schema(v, schema["items"], f"{path}[{i}]")
    if kind == "integer" and not schema.get("minimum", -float("inf")) <= value <= schema.get("maximum", float("inf")):
        raise RuntimeError(f"{path}: Response integer outside contract")


def response_evidence(body, wire_payload, *, raw=None, phase):
    # Never copy transport headers, API keys, or arbitrary exception traces.
    response = {k: body[k] for k in ("id", "model", "choices", "usage") if k in body}
    return {"phase": phase, "parsed_response": raw,
            "parsed_response_sha256": digest_json(raw),
            "provider_response": response, "provider_response_sha256": digest_json(response),
            "wire_payload": wire_payload, "wire_payload_sha256": digest_json(wire_payload)}


def provider_usage(body, stage, latency):
    raw = body.get("usage") or {}
    details = raw.get("completion_tokens_details") or {}
    usage = {"api_calls": 1, "input_tokens": raw.get("prompt_tokens"),
             "output_tokens": raw.get("completion_tokens"), "total_tokens": raw.get("total_tokens"),
             "reasoning_tokens": details.get("reasoning_tokens", raw.get("reasoning_tokens", 0)),
             "cost_usd": raw.get("cost"), "latency_seconds": latency}
    from src.spineforge_v21_quality_runtime import _usage
    try:
        _usage({"usage": usage}, stage)
    except RuntimeError as exc:
        raise AdapterResponseError(str(exc), usage, {"provider_usage": raw}) from exc
    return usage


def _call(
    *,
    api_key: str,
    payload: dict[str, Any],
    prompt_path: Path,
    request_class: str,
    schema_name: str,
    schema: dict[str, Any],
    max_tokens: int,
    stage: str,
    call_fn: JsonCall | None = None,
    model: str = BASELINE_MODEL,
) -> dict[str, Any]:
    fn = call_fn or call_strict_json_once
    wire_payload = project_payload(payload)
    started = time.perf_counter()
    try:
        raw, body, request, failures = fn(
            api_key=api_key,
            model=model,
            system_prompt=prompt_path.read_text(encoding="utf-8").strip(),
            user_prompt=json.dumps(wire_payload, ensure_ascii=False, separators=(",", ":")),
            temperature=0.0,
            max_tokens=max_tokens,
            seed=None,
            request_class=request_class,
            schema_name=schema_name,
            schema=schema,
        )
    except Exception as exc:
        trace = getattr(exc, "trace", {})
        body = trace.get("body") or {}
        latency = round(time.perf_counter() - started, 3)
        try:
            usage = provider_usage(body, stage, latency)
        except AdapterResponseError as usage_error:
            usage = usage_error.usage
        raise AdapterResponseError(type(exc).__name__, usage,
                                   response_evidence(body, wire_payload, phase=trace.get("stage", "transport"))) from exc
    latency = round(time.perf_counter() - started, 3)
    try:
        usage = provider_usage(body, stage, latency)
    except AdapterResponseError as exc:
        exc.provider_evidence = response_evidence(body, wire_payload, raw=raw, phase="usage_validation")
        raise
    try:
        validate_schema(raw, schema)
        if failures:
            raise RuntimeError("Unexpected retry/fallback evidence")
    except RuntimeError as exc:
        raise AdapterResponseError(str(exc), usage,
                                   response_evidence(body, wire_payload, raw=raw, phase="response_validation")) from exc
    return {
        **raw,
        "usage": usage,
        "model": model,
        "request_class": request_class,
        "transport_failures": failures,
        "automatic_retry_executed": False,
        "request": {
            "wire_payload": wire_payload,
            "wire_payload_sha256": digest_json(wire_payload),
            "temperature": request.get("temperature"),
            "max_tokens": request.get("max_tokens"),
            "response_format": request.get("response_format"),
        },
    }


def execute_initial_audit_call(
    *,
    api_key: str,
    payload: dict[str, Any],
    call_fn: JsonCall | None = None,
    model: str = BASELINE_MODEL,
) -> dict[str, Any]:
    return _call(
        api_key=api_key,
        payload=payload,
        prompt_path=INITIAL_AUDIT_PROMPT,
        request_class=INITIAL_AUDIT_REQUEST_CLASS,
        schema_name="spineforge_v21_initial_blocking_audit_v1",
        schema=AUDIT_RESPONSE_SCHEMA,
        max_tokens=INITIAL_MAX_TOKENS,
        stage="spineforge_v21_initial_blocking_audit",
        call_fn=call_fn,
        model=model,
    )


def execute_scene_repair_call(
    *,
    api_key: str,
    payload: dict[str, Any],
    call_fn: JsonCall | None = None,
    model: str = BASELINE_MODEL,
) -> dict[str, Any]:
    return _call(
        api_key=api_key,
        payload=payload,
        prompt_path=SCENE_REPAIR_PROMPT,
        request_class=SCENE_REPAIR_REQUEST_CLASS,
        schema_name="spineforge_v21_scene_repair_v1",
        schema=REPAIR_RESPONSE_SCHEMA,
        max_tokens=REPAIR_MAX_TOKENS,
        stage="spineforge_v21_scene_repair",
        call_fn=call_fn,
        model=model,
    )


def execute_final_audit_call(
    *,
    api_key: str,
    payload: dict[str, Any],
    call_fn: JsonCall | None = None,
    model: str = BASELINE_MODEL,
) -> dict[str, Any]:
    return _call(
        api_key=api_key,
        payload=payload,
        prompt_path=FINAL_AUDIT_PROMPT,
        request_class=FINAL_AUDIT_REQUEST_CLASS,
        schema_name="spineforge_v21_targeted_final_audit_v1",
        schema=AUDIT_RESPONSE_SCHEMA,
        max_tokens=FINAL_MAX_TOKENS,
        stage="spineforge_v21_targeted_final_audit",
        call_fn=call_fn,
        model=model,
    )
