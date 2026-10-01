from __future__ import annotations

import json
import time
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
DEFAULT_ARCHITECT_PROMPT = Path("prompts/spineforge_v19_narrative_architect.md")
DEFAULT_GATE_PROMPT = Path("prompts/spineforge_v19_product_gate.md")

JsonCall = Callable[
    ..., tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]
]


def _default_architect_call(**kwargs: Any):
    return call_json_object_once(**kwargs)


def _default_gate_call(**kwargs: Any):
    return call_strict_json_once(
        schema_name="spineforge_v19_product_gate",
        schema=SpineProductGateV19.model_json_schema(by_alias=True),
        **kwargs,
    )


def _normalized_call(
    *,
    stage: str,
    model: str,
    body: dict[str, Any],
    latency_seconds: float,
) -> dict[str, Any]:
    return normalize_model_call(
        stage=stage,
        model=model,
        provider=runtime_profile_identity(model).get("provider"),
        raw_usage=body.get("usage") or {},
        cost=parse_cost(body).model_dump(mode="json"),
        latency_seconds=latency_seconds,
    )


def _call_once(
    *,
    call_fn: JsonCall,
    api_key: str,
    model: str,
    prompt: str,
    payload: dict[str, Any],
    max_tokens: int,
    request_class: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]], float]:
    started = time.perf_counter()
    raw, body, request, failures = call_fn(
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


def run(
    *,
    context_pack: SpineContextPackV1,
    obligations: ReaderStoryObligationsV1,
    api_key: str,
    architect_call_fn: JsonCall | None = None,
    gate_call_fn: JsonCall | None = None,
    architect_prompt: str | None = None,
    gate_prompt: str | None = None,
) -> dict[str, Any]:
    calls: list[dict[str, Any]] = []
    evidence: dict[str, Any] = {
        "schema": "spineforge-v19-evidence.v1",
        "status": "started",
        "context_pack_id": context_pack.context_pack_id,
        "context_fingerprint": context_pack.context_fingerprint,
        "generation_topology": [
            "SONNET_SINGLE_NARRATIVE_SPINE_ARCHITECT",
            "DETERMINISTIC_AUTHORITY_AND_OBLIGATION_VALIDATION",
            "LUNA_COMPACT_ADVERSARIAL_PRODUCT_GATE",
            "STOP_FOR_HUMAN_REVIEW",
        ],
        "automatic_retry_enabled": False,
        "automatic_repair_enabled": False,
        "writer_authorized": False,
        "human_review": {"required": True, "verdict": None},
        "application_authority": {
            "exact_age": int(context_pack.reader_profile["exact_age"]),
            "session": context_pack.session_target["name"],
            "target_words_min": int(context_pack.session_target["target_words_min"]),
            "target_words_max": int(context_pack.session_target["target_words_max"]),
            "authority_revisions": [
                row.model_dump(mode="json")
                for row in context_pack.authority_revisions
            ],
            "eligible_milestone_keys": [
                row["key"]
                for row in context_pack.saga.get("eligible_milestones", [])
                if isinstance(row, dict) and row.get("key")
            ],
            "commit_only_if_earned": True,
        },
    }

    architect = architect_call_fn or _default_architect_call
    architect_payload = {
        "task": "create_one_complete_narrative_spine_product",
        "spine_context_pack": context_pack.model_dump(mode="json", by_alias=True),
        "reader_story_obligations": obligations.model_dump(mode="json", by_alias=True),
        "application_owned_fields": sorted(evidence["application_authority"].keys()),
        "output_contract": NarrativeSpineV1.model_json_schema(by_alias=True),
    }

    raw, body, request, failures, latency = _call_once(
        call_fn=architect,
        api_key=api_key,
        model=SONNET_MODEL,
        prompt=architect_prompt
        or DEFAULT_ARCHITECT_PROMPT.read_text(encoding="utf-8").strip(),
        payload=architect_payload,
        max_tokens=9000,
        request_class="saga_architect",
    )
    calls.append(
        _normalized_call(
            stage="spineforge_v19_architect",
            model=SONNET_MODEL,
            body=body,
            latency_seconds=latency,
        )
    )
    evidence["architect_transport"] = {
        "response_format": request.get("response_format"),
        "provider": request.get("provider"),
        "parse_failures": failures,
    }
    evidence["architect_raw"] = raw

    try:
        spine = NarrativeSpineV1.model_validate(raw)
        report = validate_narrative_spine(
            spine=spine,
            pack=context_pack,
            obligations=obligations,
        )
    except Exception as exc:
        evidence["status"] = "architect_contract_or_authority_rejected"
        evidence["failure"] = {
            "stage": "architect_validation",
            "type": type(exc).__name__,
            "message": str(exc),
        }
        evidence["pipeline_usage_rollup"] = rollup_model_calls(calls)
        return evidence

    evidence["narrative_spine"] = spine.model_dump(mode="json", by_alias=True)
    evidence["deterministic_validation"] = report.model_dump(mode="json", by_alias=True)

    gate = gate_call_fn or _default_gate_call
    gate_payload = {
        "task": "adversarially_gate_narrative_spine",
        "spine_context_pack": context_pack.model_dump(mode="json", by_alias=True),
        "reader_story_obligations": obligations.model_dump(mode="json", by_alias=True),
        "narrative_spine": spine.model_dump(mode="json", by_alias=True),
        "output_contract": SpineProductGateV19.model_json_schema(by_alias=True),
    }
    try:
        raw_gate, body, request, failures, latency = _call_once(
            call_fn=gate,
            api_key=api_key,
            model=LUNA_MODEL,
            prompt=gate_prompt or DEFAULT_GATE_PROMPT.read_text(encoding="utf-8").strip(),
            payload=gate_payload,
            max_tokens=2500,
            request_class="editorial_audit",
        )
    except Exception as exc:
        evidence["status"] = "product_gate_transport_failed"
        evidence["failure"] = {
            "stage": "product_gate_transport",
            "type": type(exc).__name__,
            "message": str(exc),
            "trace": getattr(exc, "trace", None),
        }
        evidence["pipeline_usage_rollup"] = rollup_model_calls(calls)
        return evidence

    calls.append(
        _normalized_call(
            stage="spineforge_v19_product_gate",
            model=LUNA_MODEL,
            body=body,
            latency_seconds=latency,
        )
    )
    evidence["gate_transport"] = {
        "response_format": request.get("response_format"),
        "provider": request.get("provider"),
        "parse_failures": failures,
    }
    evidence["gate_raw"] = raw_gate

    try:
        gate_product = SpineProductGateV19.model_validate(raw_gate)
    except Exception as exc:
        evidence["status"] = "product_gate_contract_rejected"
        evidence["failure"] = {
            "stage": "product_gate_validation",
            "type": type(exc).__name__,
            "message": str(exc),
        }
        evidence["pipeline_usage_rollup"] = rollup_model_calls(calls)
        return evidence

    evidence["product_gate"] = gate_product.model_dump(mode="json", by_alias=True)
    if gate_product.decision == "ACCEPT":
        evidence["status"] = "awaiting_human_review"
    elif gate_product.decision == "REPAIR":
        evidence["status"] = "repair_required"
        evidence["repair_candidate"] = {
            "scope": "ONE_TARGETED_SONNET_PATCH",
            "automatic_execution": False,
            "findings": [
                row.model_dump(mode="json")
                for row in gate_product.blocking_findings
            ],
        }
    else:
        evidence["status"] = "replan_required"
        evidence["replan_candidate"] = {
            "scope": "NEW_EXPLICITLY_AUTHORIZED_ARCHITECT_ATTEMPT",
            "automatic_execution": False,
            "findings": [
                row.model_dump(mode="json")
                for row in gate_product.blocking_findings
            ],
        }

    evidence["pipeline_usage_rollup"] = rollup_model_calls(calls)
    return evidence
