from __future__ import annotations

import copy
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import ValidationError

from src.english_story_pipeline import call_structured_json_with_retry
from src.generate import parse_cost
from src.spineforge_v5_strict_call import call_openrouter
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.openrouter_json_schema import build_json_schema_response_format
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v5_authority import validate_compiled_spine_authority
from src.spineforge_v5_contract import (
    SpineCreativeIntentV1,
    SpineForgeProductV5,
    SpineForgeRevisionFeedbackV5,
    SpineProductGateV5,
    SpineStructuralCompilationV1,
)

AION_MODEL = "aion-labs/aion-3.5-mini"
SONNET_MODEL = "anthropic/claude-sonnet-5.5"
LUNA_MODEL = "openai/gpt-5.6-luna"

DEFAULT_CREATIVE_PROMPT = Path("prompts/spineforge_creative_architect_v5_intent.md")
DEFAULT_COMPILER_PROMPT = Path("prompts/spineforge_structural_compiler_v5.md")
DEFAULT_GATE_PROMPT = Path("prompts/spineforge_product_gate_v5.md")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _model_call(stage: str, model: str, body: dict[str, Any], latency: float) -> dict[str, Any]:
    return normalize_model_call(
        stage=stage,
        model=model,
        provider=runtime_profile_identity(model).get("provider"),
        raw_usage=body.get("usage") or {},
        cost=parse_cost(body).model_dump(mode="json"),
        latency_seconds=latency,
    )


def _normalize_intent_raw(raw: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    value = copy.deepcopy(raw)
    repairs: list[dict[str, Any]] = []
    if value.get("schema") != "spineforge-creative-intent.v1":
        repairs.append({
            "kind": "stamp_application_owned_creative_schema",
            "field": "schema",
            "old": value.get("schema"),
            "new": "spineforge-creative-intent.v1",
        })
        value["schema"] = "spineforge-creative-intent.v1"
    if value.get("creative_model") != AION_MODEL:
        repairs.append({
            "kind": "stamp_application_owned_model_identity",
            "field": "creative_model",
            "old": value.get("creative_model"),
            "new": AION_MODEL,
        })
        value["creative_model"] = AION_MODEL
    return value, repairs


def _preserve(intent: SpineCreativeIntentV1) -> list[str]:
    sig = intent.creative_signature
    return [sig.dramatic_engine, sig.central_wonder_or_intrigue]


def _build_feedback(
    *,
    pack: SpineContextPackV1,
    attempt_index: int,
    target_stage: str,
    source_status: str,
    intent: SpineCreativeIntentV1 | None,
    compiled_spine: dict[str, Any] | None,
    must_change: list[str],
    creative_feedback: list[str] | None = None,
    structural_feedback: list[str] | None = None,
    validation_errors: list[str] | None = None,
) -> dict[str, Any]:
    preserved = (
        _preserve(intent)
        if intent is not None
        else ["Preserve the approved premise.", "Preserve unchanged ContextPack authority."]
    )
    value = SpineForgeRevisionFeedbackV5(
        schema="spineforge-revision-feedback.v5",
        context_pack_id=pack.context_pack_id,
        context_fingerprint=pack.context_fingerprint,
        source_attempt=attempt_index,
        next_attempt=attempt_index + 1,
        target_stage=target_stage,
        source_status=source_status,
        must_preserve=preserved,
        must_change=must_change,
        creative_feedback=list(creative_feedback or []),
        structural_feedback=list(structural_feedback or []),
        previous_creative_intent=(
            intent.model_dump(mode="json", by_alias=True) if intent is not None else None
        ),
        previous_compiled_spine=compiled_spine,
        validation_errors=list(validation_errors or []),
        authority_freezes=list(pack.hard_freezes),
    )
    return value.model_dump(mode="json", by_alias=True)


def _load_revision(
    *,
    path: Path | None,
    pack: SpineContextPackV1,
    max_attempts: int,
) -> tuple[SpineForgeRevisionFeedbackV5 | None, int]:
    if path is None:
        return None, 1
    revision = SpineForgeRevisionFeedbackV5.model_validate(_read(path))
    if revision.context_pack_id != pack.context_pack_id:
        raise RuntimeError("Revision feedback context_pack_id is stale.")
    if revision.context_fingerprint != pack.context_fingerprint:
        raise RuntimeError("Revision feedback context_fingerprint is stale.")
    if revision.next_attempt > max_attempts:
        raise RuntimeError(
            f"SpineForge v5 attempt limit exceeded: {revision.next_attempt}>{max_attempts}"
        )
    return revision, revision.next_attempt


def _parse_json_text(text: str) -> dict[str, Any]:
    value = json.loads(text)
    if not isinstance(value, dict):
        raise RuntimeError("Structured model response root must be an object.")
    return value


def run(
    *,
    context_pack_path: Path,
    out_path: Path,
    creative_prompt_path: Path = DEFAULT_CREATIVE_PROMPT,
    compiler_prompt_path: Path = DEFAULT_COMPILER_PROMPT,
    gate_prompt_path: Path = DEFAULT_GATE_PROMPT,
    revision_feedback_path: Path | None = None,
    max_attempts: int = 3,
    api_key: str | None = None,
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    pack = SpineContextPackV1.model_validate(_read(context_pack_path))
    revision, attempt_index = _load_revision(
        path=revision_feedback_path,
        pack=pack,
        max_attempts=max_attempts,
    )
    for model in (AION_MODEL, SONNET_MODEL, LUNA_MODEL):
        require_qualification_runtime_profile(model)

    pack_payload = pack.model_dump(mode="json", by_alias=True)
    calls: list[dict[str, Any]] = []
    started = time.perf_counter()
    evidence: dict[str, Any] = {
        "schema_version": "spineforge-v5-evidence.v1",
        "status": "started",
        "attempt_index": attempt_index,
        "context_pack_id": pack.context_pack_id,
        "context_fingerprint": pack.context_fingerprint,
        "context_pack": pack_payload,
        "revision_feedback": (
            revision.model_dump(mode="json", by_alias=True) if revision else None
        ),
        "started_at": _now(),
        "models": {
            "creative_architect": AION_MODEL,
            "structural_compiler": SONNET_MODEL,
            "product_gate": LUNA_MODEL,
        },
        "human_review": {"required": True, "verdict": None, "writer_authorized": False},
    }

    intent: SpineCreativeIntentV1
    if revision is not None and revision.target_stage == "SONNET_STRUCTURAL":
        intent = SpineCreativeIntentV1.model_validate(revision.previous_creative_intent)
        evidence["creative_intent_reused_from_revision"] = True
        evidence["creative_intent"] = intent.model_dump(mode="json", by_alias=True)
    else:
        creative_input = {
            "task": "create_spineforge_creative_intent",
            "spine_context_pack": pack_payload,
            "revision_context": (
                revision.model_dump(mode="json", by_alias=True) if revision else None
            ),
            "output_contract": SpineCreativeIntentV1.model_json_schema(by_alias=True),
        }
        call_started = time.perf_counter()
        raw, body, _, failures = call_structured_json_with_retry(
            api_key=key,
            model=AION_MODEL,
            system_prompt=creative_prompt_path.read_text(encoding="utf-8").strip(),
            user_prompt=json.dumps(creative_input, ensure_ascii=False),
            temperature=0.85,
            max_tokens=14000,
            seed=None,
            request_class="teacher_story_medium_reasoning",
            max_parse_attempts=1,
        )
        latency = round(time.perf_counter() - call_started, 3)
        calls.append(_model_call("spineforge_creative_intent", AION_MODEL, body, latency))
        evidence["creative_raw_payload"] = raw
        evidence["creative_parse_failures"] = failures
        normalized, repairs = _normalize_intent_raw(raw)
        evidence["creative_normalized_payload"] = normalized
        evidence["creative_safe_normalization"] = {
            "applied": bool(repairs),
            "repairs": repairs,
            "semantic_fields_changed": False,
        }
        try:
            intent = SpineCreativeIntentV1.model_validate(normalized)
        except ValidationError as exc:
            rollup = rollup_model_calls(calls)
            message = str(exc)
            evidence.update({
                "status": "creative_intent_rejected",
                "failure": {"type": type(exc).__name__, "message": message},
                "pipeline_usage_rollup": rollup,
                "total_cost_usd": rollup["totals"]["cost_usd"],
                "completed_at": _now(),
                "latency_seconds": round(time.perf_counter() - started, 3),
            })
            evidence["revision_feedback_candidate"] = _build_feedback(
                pack=pack,
                attempt_index=attempt_index,
                target_stage="AION_CREATIVE",
                source_status="creative_intent_rejected",
                intent=None,
                compiled_spine=None,
                must_change=[message],
                creative_feedback=[message],
                validation_errors=[message],
            )
            _write(out_path, evidence)
            return evidence
        evidence["creative_intent"] = intent.model_dump(mode="json", by_alias=True)

    compiler_input = {
        "task": "compile_and_harden_creative_intent",
        "spine_context_pack": pack_payload,
        "creative_intent": intent.model_dump(mode="json", by_alias=True),
        "revision_context": (
            revision.model_dump(mode="json", by_alias=True)
            if revision is not None and revision.target_stage == "SONNET_STRUCTURAL"
            else None
        ),
        "episode_spine_contract": SpineStructuralCompilationV1.model_json_schema(by_alias=True),
    }
    compiler_schema = SpineStructuralCompilationV1.model_json_schema(by_alias=True)
    call_started = time.perf_counter()
    compiler_text, compiler_body, compiler_request = call_openrouter(
        api_key=key,
        model=SONNET_MODEL,
        system_prompt=compiler_prompt_path.read_text(encoding="utf-8").strip(),
        user_prompt=json.dumps(compiler_input, ensure_ascii=False),
        temperature=0.0,
        max_tokens=18000,
        seed=None,
        request_class="saga_architect",
        response_format=build_json_schema_response_format(
            name="spineforge_structural_compilation_v1",
            schema=compiler_schema,
        ),
        require_parameters=True,
    )
    compiler_latency = round(time.perf_counter() - call_started, 3)
    calls.append(_model_call("spineforge_structural_compiler", SONNET_MODEL, compiler_body, compiler_latency))
    evidence["structural_compiler_request_contract"] = {
        "response_format": compiler_request.get("response_format"),
        "provider": compiler_request.get("provider"),
    }
    try:
        compiler_raw = _parse_json_text(compiler_text)
        compilation = SpineStructuralCompilationV1.model_validate(compiler_raw)
    except (json.JSONDecodeError, ValidationError, RuntimeError) as exc:
        rollup = rollup_model_calls(calls)
        message = str(exc)
        evidence.update({
            "status": "structural_compile_rejected",
            "failure": {"type": type(exc).__name__, "message": message},
            "structural_compiler_raw_text": compiler_text,
            "pipeline_usage_rollup": rollup,
            "total_cost_usd": rollup["totals"]["cost_usd"],
            "completed_at": _now(),
            "latency_seconds": round(time.perf_counter() - started, 3),
        })
        evidence["revision_feedback_candidate"] = _build_feedback(
            pack=pack,
            attempt_index=attempt_index,
            target_stage="SONNET_STRUCTURAL",
            source_status="structural_compile_rejected",
            intent=intent,
            compiled_spine=None,
            must_change=[message],
            structural_feedback=[message],
            validation_errors=[message],
        )
        _write(out_path, evidence)
        return evidence

    evidence["structural_compilation"] = compilation.model_dump(mode="json", by_alias=True)
    if compilation.decision == "REPLAN":
        rollup = rollup_model_calls(calls)
        reasons = list(compilation.replan_feedback)
        evidence.update({
            "status": "structural_replan_required",
            "pipeline_usage_rollup": rollup,
            "total_cost_usd": rollup["totals"]["cost_usd"],
            "completed_at": _now(),
            "latency_seconds": round(time.perf_counter() - started, 3),
        })
        evidence["revision_feedback_candidate"] = _build_feedback(
            pack=pack,
            attempt_index=attempt_index,
            target_stage="AION_CREATIVE",
            source_status="structural_replan_required",
            intent=intent,
            compiled_spine=None,
            must_change=reasons,
            creative_feedback=reasons,
            structural_feedback=reasons,
        )
        _write(out_path, evidence)
        return evidence

    assert compilation.compiled_spine is not None
    compiled = compilation.compiled_spine
    try:
        validate_compiled_spine_authority(spine=compiled, pack=pack)
    except (ValidationError, RuntimeError) as exc:
        rollup = rollup_model_calls(calls)
        message = str(exc)
        compiled_payload = compiled.model_dump(mode="json", by_alias=True)
        evidence.update({
            "status": "structural_compile_rejected",
            "failure": {"type": type(exc).__name__, "message": message},
            "compiled_spine": compiled_payload,
            "pipeline_usage_rollup": rollup,
            "total_cost_usd": rollup["totals"]["cost_usd"],
            "completed_at": _now(),
            "latency_seconds": round(time.perf_counter() - started, 3),
        })
        evidence["revision_feedback_candidate"] = _build_feedback(
            pack=pack,
            attempt_index=attempt_index,
            target_stage="SONNET_STRUCTURAL",
            source_status="structural_compile_rejected",
            intent=intent,
            compiled_spine=compiled_payload,
            must_change=[message],
            structural_feedback=[message],
            validation_errors=[message],
        )
        _write(out_path, evidence)
        return evidence

    compiled_payload = compiled.model_dump(mode="json", by_alias=True)
    evidence["compiled_spine"] = compiled_payload

    gate_input = {
        "task": "evaluate_spineforge_v5_product",
        "spine_context_pack": pack_payload,
        "creative_signature": intent.creative_signature.model_dump(mode="json"),
        "creative_intent": intent.episode_spine,
        "structural_compilation": compilation.model_dump(mode="json", by_alias=True),
        "compiled_spine": compiled_payload,
        "output_contract": SpineProductGateV5.model_json_schema(by_alias=True),
    }
    gate_schema = SpineProductGateV5.model_json_schema(by_alias=True)
    call_started = time.perf_counter()
    gate_text, gate_body, gate_request = call_openrouter(
        api_key=key,
        model=LUNA_MODEL,
        system_prompt=gate_prompt_path.read_text(encoding="utf-8").strip(),
        user_prompt=json.dumps(gate_input, ensure_ascii=False),
        temperature=0.0,
        max_tokens=6500,
        seed=2026093011,
        request_class="editorial_audit",
        response_format=build_json_schema_response_format(
            name="spineforge_product_gate_v5",
            schema=gate_schema,
        ),
        require_parameters=True,
    )
    gate_latency = round(time.perf_counter() - call_started, 3)
    calls.append(_model_call("spineforge_product_gate", LUNA_MODEL, gate_body, gate_latency))
    evidence["product_gate_request_contract"] = {
        "response_format": gate_request.get("response_format"),
        "provider": gate_request.get("provider"),
    }
    try:
        gate_raw = _parse_json_text(gate_text)
        gate = SpineProductGateV5.model_validate(gate_raw)
    except (json.JSONDecodeError, ValidationError, RuntimeError) as exc:
        rollup = rollup_model_calls(calls)
        evidence.update({
            "status": "product_gate_contract_rejected",
            "failure": {"type": type(exc).__name__, "message": str(exc)},
            "pipeline_usage_rollup": rollup,
            "total_cost_usd": rollup["totals"]["cost_usd"],
            "completed_at": _now(),
            "latency_seconds": round(time.perf_counter() - started, 3),
        })
        _write(out_path, evidence)
        return evidence

    evidence["product_gate"] = gate.model_dump(mode="json", by_alias=True)
    rollup = rollup_model_calls(calls)
    if gate.decision == "REPLAN":
        reasons = list(gate.blocking_reasons)
        target = gate.replan_target or "SONNET_STRUCTURAL"
        evidence.update({
            "status": "product_replan_required",
            "pipeline_usage_rollup": rollup,
            "total_cost_usd": rollup["totals"]["cost_usd"],
            "completed_at": _now(),
            "latency_seconds": round(time.perf_counter() - started, 3),
        })
        evidence["revision_feedback_candidate"] = _build_feedback(
            pack=pack,
            attempt_index=attempt_index,
            target_stage=target,
            source_status="product_replan_required",
            intent=intent,
            compiled_spine=compiled_payload,
            must_change=reasons,
            creative_feedback=(reasons if target == "AION_CREATIVE" else []),
            structural_feedback=reasons,
        )
        _write(out_path, evidence)
        return evidence

    evidence["status"] = "awaiting_human_review"
    product = SpineForgeProductV5(
        schema="spineforge-product.v5",
        status="AWAITING_HUMAN_REVIEW",
        context_pack_id=pack.context_pack_id,
        context_fingerprint=pack.context_fingerprint,
        creative_intent=intent,
        structural_compilation=compilation,
        compiled_spine=compiled,
        product_gate=gate,
        deterministic_checks={
            "creative_intent_outer_contract_valid": True,
            "strict_structural_compile_valid": True,
            "context_pack_authority_valid": True,
            "context_fingerprint_bound": True,
            "writer_blocked_before_human": True,
        },
        lineage={
            "models": evidence["models"],
            "usage_rollup": rollup,
            "attempt_index": attempt_index,
        },
        human_review=evidence["human_review"],
    )
    evidence["spine_product"] = product.model_dump(mode="json", by_alias=True)
    evidence.update({
        "pipeline_usage_rollup": rollup,
        "total_cost_usd": rollup["totals"]["cost_usd"],
        "completed_at": _now(),
        "latency_seconds": round(time.perf_counter() - started, 3),
    })
    _write(out_path, evidence)
    return evidence
