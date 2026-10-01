from __future__ import annotations

import json
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

from src.generate import parse_cost
from src.model_registry import runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.narrative_spine_v1_contract import NarrativeSpineV1, SpineProductGateV19
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v19_obligations import ReaderStoryObligationsV1
from src.spineforge_v19_transport import call_json_object_once, call_strict_json_once
from src.spineforge_v19_validator import validate_narrative_spine


SONNET_MODEL = "anthropic/claude-sonnet-5.5"
LUNA_MODEL = "openai/gpt-5.6-luna"
DEFAULT_REPAIR_PROMPT = Path("prompts/spineforge_v20_local_repair.md")
DEFAULT_GATE_PROMPT = Path("prompts/spineforge_v19_product_gate.md")


JsonCall = Callable[
    ..., tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]
]


def _normalize(stage: str, model: str, body: dict[str, Any], latency: float) -> dict[str, Any]:
    return normalize_model_call(
        stage=stage,
        model=model,
        provider=runtime_profile_identity(model).get("provider"),
        raw_usage=body.get("usage") or {},
        cost=parse_cost(body).model_dump(mode="json"),
        latency_seconds=latency,
    )


def _call_once(
    *,
    fn: JsonCall,
    api_key: str,
    model: str,
    prompt: str,
    payload: dict[str, Any],
    max_tokens: int,
    request_class: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]], float]:
    started = time.perf_counter()
    raw, body, request, failures = fn(
        api_key=api_key,
        model=model,
        system_prompt=prompt,
        user_prompt=json.dumps(payload, ensure_ascii=False),
        temperature=0.0,
        max_tokens=max_tokens,
        seed=None,
        request_class=request_class,
    )
    return raw, body, request, failures, round(time.perf_counter() - started, 3)


def _path_tokens(path: str) -> list[str | int]:
    if not path.startswith("narrative_spine."):
        raise ValueError(f"Unsupported allowed path: {path}")
    text = path[len("narrative_spine."):]
    out: list[str | int] = []
    for part in text.split("."):
        while "[" in part:
            key, rest = part.split("[", 1)
            if key:
                out.append(key)
            idx, tail = rest.split("]", 1)
            out.append(int(idx))
            part = tail
        if part:
            out.append(part)
    return out


def _get(value: Any, tokens: list[str | int]) -> Any:
    cur = value
    for token in tokens:
        cur = cur[token]
    return cur


def _diff_paths(before: Any, after: Any, prefix: str = "narrative_spine") -> list[str]:
    if type(before) is not type(after):
        return [prefix]
    if isinstance(before, dict):
        paths: list[str] = []
        for key in sorted(set(before) | set(after)):
            p = f"{prefix}.{key}"
            if key not in before or key not in after:
                paths.append(p)
            else:
                paths.extend(_diff_paths(before[key], after[key], p))
        return paths
    if isinstance(before, list):
        if len(before) != len(after):
            return [prefix]
        paths: list[str] = []
        for i, (left, right) in enumerate(zip(before, after)):
            paths.extend(_diff_paths(left, right, f"{prefix}[{i}]"))
        return paths
    return [] if before == after else [prefix]


def validate_repair_diff(
    *,
    source: NarrativeSpineV1,
    repaired: NarrativeSpineV1,
    allowed_change_paths: list[str],
) -> list[str]:
    before = source.model_dump(mode="json", by_alias=True)
    after = repaired.model_dump(mode="json", by_alias=True)
    changed = _diff_paths(before, after)
    allowed = set(allowed_change_paths)
    forbidden = [path for path in changed if path not in allowed]
    if forbidden:
        raise ValueError(
            "Repair changed forbidden paths: " + ", ".join(forbidden)
        )
    if not changed:
        raise ValueError("Repair made no changes.")
    return changed


def run_local_repair(
    *,
    source_spine: NarrativeSpineV1,
    context_pack: SpineContextPackV1,
    obligations: ReaderStoryObligationsV1,
    repair_spec: dict[str, Any],
    api_key: str,
    repair_call_fn: JsonCall | None = None,
    gate_call_fn: JsonCall | None = None,
    repair_prompt: str | None = None,
    gate_prompt: str | None = None,
) -> dict[str, Any]:
    calls: list[dict[str, Any]] = []
    evidence: dict[str, Any] = {
        "schema": "spineforge-v20-local-repair-evidence.v1",
        "status": "started",
        "source_spine_hash": repair_spec["source_spine_hash"],
        "context_fingerprint": context_pack.context_fingerprint,
        "automatic_retry_enabled": False,
        "automatic_repair_enabled": False,
        "writer_authorized": False,
        "allowed_change_paths": list(repair_spec["allowed_change_paths"]),
    }

    repair_fn = repair_call_fn or call_json_object_once
    payload = {
        "task": "repair_one_local_spine_defect_only",
        "source_narrative_spine": source_spine.model_dump(mode="json", by_alias=True),
        "spine_context_pack": context_pack.model_dump(mode="json", by_alias=True),
        "reader_story_obligations": obligations.model_dump(mode="json", by_alias=True),
        "repair_spec": repair_spec,
        "output_contract": NarrativeSpineV1.model_json_schema(by_alias=True),
    }

    raw, body, request, failures, latency = _call_once(
        fn=repair_fn,
        api_key=api_key,
        model=SONNET_MODEL,
        prompt=repair_prompt or DEFAULT_REPAIR_PROMPT.read_text(encoding="utf-8").strip(),
        payload=payload,
        max_tokens=9000,
        request_class="saga_architect",
    )
    calls.append(_normalize("spineforge_v20_local_repair", SONNET_MODEL, body, latency))
    evidence["repair_transport"] = {
        "response_format": request.get("response_format"),
        "provider": request.get("provider"),
        "parse_failures": failures,
    }

    try:
        repaired = NarrativeSpineV1.model_validate(raw)
        changed_paths = validate_repair_diff(
            source=source_spine,
            repaired=repaired,
            allowed_change_paths=repair_spec["allowed_change_paths"],
        )
        validation = validate_narrative_spine(
            spine=repaired,
            pack=context_pack,
            obligations=obligations,
        )
    except Exception as exc:
        evidence["status"] = "repair_contract_diff_or_authority_rejected"
        evidence["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        evidence["repair_raw"] = raw
        evidence["pipeline_usage_rollup"] = rollup_model_calls(calls)
        return evidence

    evidence["repaired_spine"] = repaired.model_dump(mode="json", by_alias=True)
    evidence["changed_paths"] = changed_paths
    evidence["deterministic_validation"] = validation.model_dump(mode="json", by_alias=True)

    gate_fn = gate_call_fn
    if gate_fn is None:
        def gate_fn(**kwargs: Any):
            return call_strict_json_once(
                schema_name="spineforge_v19_product_gate",
                schema=SpineProductGateV19.model_json_schema(by_alias=True),
                **kwargs,
            )

    gate_payload = {
        "task": "adversarially_gate_narrative_spine",
        "spine_context_pack": context_pack.model_dump(mode="json", by_alias=True),
        "reader_story_obligations": obligations.model_dump(mode="json", by_alias=True),
        "narrative_spine": repaired.model_dump(mode="json", by_alias=True),
        "output_contract": SpineProductGateV19.model_json_schema(by_alias=True),
    }
    try:
        raw_gate, body, request, failures, latency = _call_once(
            fn=gate_fn,
            api_key=api_key,
            model=LUNA_MODEL,
            prompt=gate_prompt or DEFAULT_GATE_PROMPT.read_text(encoding="utf-8").strip(),
            payload=gate_payload,
            max_tokens=2500,
            request_class="editorial_audit",
        )
    except Exception as exc:
        evidence["status"] = "repair_regate_transport_failed"
        evidence["failure"] = {
            "stage": "repair_regate_transport",
            "type": type(exc).__name__,
            "message": str(exc),
            "trace": getattr(exc, "trace", None),
        }
        evidence["pipeline_usage_rollup"] = rollup_model_calls(calls)
        return evidence

    calls.append(_normalize("spineforge_v20_local_repair_regate", LUNA_MODEL, body, latency))
    evidence["gate_transport"] = {
        "response_format": request.get("response_format"),
        "provider": request.get("provider"),
        "parse_failures": failures,
    }
    try:
        gate = SpineProductGateV19.model_validate(raw_gate)
    except Exception as exc:
        evidence["status"] = "repair_regate_contract_rejected"
        evidence["failure"] = {
            "stage": "repair_regate_validation",
            "type": type(exc).__name__,
            "message": str(exc),
        }
        evidence["gate_raw"] = raw_gate
        evidence["pipeline_usage_rollup"] = rollup_model_calls(calls)
        return evidence
    evidence["product_gate"] = gate.model_dump(mode="json", by_alias=True)
    evidence["status"] = (
        "awaiting_human_review"
        if gate.decision == "ACCEPT"
        else "repair_required"
        if gate.decision == "REPAIR"
        else "replan_required"
    )
    evidence["pipeline_usage_rollup"] = rollup_model_calls(calls)
    return evidence
