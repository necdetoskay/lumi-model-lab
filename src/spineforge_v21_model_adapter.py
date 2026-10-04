from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from src.generate import parse_cost
from src.model_registry import runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.spineforge_v19_transport import call_strict_json_once


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
) -> dict[str, Any]:
    fn = call_fn or call_strict_json_once
    started = time.perf_counter()
    raw, body, request, failures = fn(
        api_key=api_key,
        model=BASELINE_MODEL,
        system_prompt=prompt_path.read_text(encoding="utf-8").strip(),
        user_prompt=json.dumps(payload, ensure_ascii=False),
        temperature=0.0,
        max_tokens=max_tokens,
        seed=None,
        request_class=request_class,
        schema_name=schema_name,
        schema=schema,
    )
    latency = round(time.perf_counter() - started, 3)
    model_call = normalize_model_call(
        stage=stage,
        model=BASELINE_MODEL,
        provider=runtime_profile_identity(BASELINE_MODEL).get("provider"),
        raw_usage=body.get("usage") or {},
        cost=parse_cost(body).model_dump(mode="json"),
        latency_seconds=latency,
    )
    rollup = rollup_model_calls([model_call])
    return {
        **raw,
        "usage": rollup["totals"],
        "model": BASELINE_MODEL,
        "request_class": request_class,
        "transport_failures": failures,
        "automatic_retry_executed": False,
        "request": {
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
    )


def execute_scene_repair_call(
    *,
    api_key: str,
    payload: dict[str, Any],
    call_fn: JsonCall | None = None,
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
    )


def execute_final_audit_call(
    *,
    api_key: str,
    payload: dict[str, Any],
    call_fn: JsonCall | None = None,
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
    )
