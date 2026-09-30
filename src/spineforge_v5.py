from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import ValidationError

from src.english_story_pipeline import call_structured_json_with_retry
from src.episode_spine_v3_contract import EpisodeBeatV2, EpisodeSpineV3
from src.generate import parse_cost
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v3_contract import SpineProductGateV1
from src.spineforge_v5_contract import (
    CreativeSpineSeedV5,
    SpineForgeProductV5,
    StructuralCompileV5,
)


AION_MODEL = "aion-labs/aion-3.5-mini"
SONNET_MODEL = "anthropic/claude-sonnet-5.5"
LUNA_MODEL = "openai/gpt-5.6-luna"

DEFAULT_CREATIVE_PROMPT = Path("prompts/spineforge_creative_seed_v5_context.md")
DEFAULT_COMPILER_PROMPT = Path("prompts/spineforge_structural_compiler_v5_context.md")
DEFAULT_GATE_PROMPT = Path("prompts/spineforge_product_gate_v5_context.md")

MANDATORY_PHASES = ["HOOK", "COMPLICATION", "REVERSAL", "DECISION", "CLIMAX", "PAYOFF"]


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


def build_structural_obligations(pack: SpineContextPackV1) -> dict[str, Any]:
    session = pack.session_target
    return {
        "schema": "spineforge-structural-obligations.v5",
        "mandatory_phases": list(MANDATORY_PHASES),
        "beat_count": {"min": 8, "max": 12},
        "required_beat_fields": list(EpisodeBeatV2.model_fields.keys()),
        "causal_dependencies": "every non-opening beat references earlier beats only",
        "reversal_evidence_boundary": "support may reference beats at or before REVERSAL, never future beats",
        "decision_min_branches": 2,
        "application_owned": {
            "premise_key": pack.approved_premise["key"],
            "exact_age": int(pack.reader_profile["exact_age"]),
            "session": session["name"],
            "target_words_min": int(session["target_words_min"]),
            "target_words_max": int(session["target_words_max"]),
            "intended_milestone_keys": list(pack.saga["intended_milestone_keys"]),
        },
    }


def _stamp_seed_model(raw: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    value = json.loads(json.dumps(raw))
    repairs: list[dict[str, Any]] = []
    if value.get("creative_model") != AION_MODEL:
        repairs.append({
            "kind": "stamp_application_owned_model_identity",
            "field": "creative_model",
            "old": value.get("creative_model"),
            "new": AION_MODEL,
            "reason": "The runtime owns provider/model identity.",
        })
        value["creative_model"] = AION_MODEL
    return value, repairs


def _allowed_full_locations(pack: SpineContextPackV1) -> set[str]:
    return {
        str(row["key"])
        for row in pack.knowledge_boundaries["accessible_locations"]
        if row.get("premise_usage") == "FULL"
    }


def validate_seed_authority(seed: CreativeSpineSeedV5, pack: SpineContextPackV1) -> None:
    allowed = set(pack.approved_premise["location_refs"])
    full = _allowed_full_locations(pack)
    if not allowed.issubset(full):
        raise RuntimeError("Approved premise contains location without FULL access.")
    used = {moment.location_ref for moment in seed.moments}
    if not used.issubset(allowed):
        raise RuntimeError("Creative seed uses location outside approved premise.")


def validate_compiled_authority(spine: EpisodeSpineV3, pack: SpineContextPackV1) -> None:
    premise = pack.approved_premise
    session = pack.session_target

    if spine.premise_key != premise["key"]:
        raise RuntimeError("Spine premise_key mismatch.")
    if spine.exact_age != int(pack.reader_profile["exact_age"]):
        raise RuntimeError("Spine exact_age mismatch.")
    if spine.session != session["name"]:
        raise RuntimeError("Spine session mismatch.")
    if (
        spine.target_words_min != int(session["target_words_min"])
        or spine.target_words_max != int(session["target_words_max"])
    ):
        raise RuntimeError("Spine word target mismatch.")

    allowed = set(premise["location_refs"])
    full = _allowed_full_locations(pack)
    if not allowed.issubset(full):
        raise RuntimeError("Approved premise contains location without FULL access.")
    used = {beat.location_ref for beat in spine.beats}
    if not used.issubset(allowed):
        raise RuntimeError("Compiled spine uses location outside approved premise.")

    intended = set(pack.saga["intended_milestone_keys"])
    if set(spine.saga_progression.intended_milestone_keys) != intended:
        raise RuntimeError("Compiled spine intended milestones differ from ContextPack authority.")
    if intended and spine.episode_role not in {
        "MAIN_SAGA_ENTRY",
        "MAIN_SAGA_PROGRESS",
        "MIXED",
    }:
        raise RuntimeError("Main Saga milestone requires Main Saga episode role.")


def _finish(
    evidence: dict[str, Any],
    calls: list[dict[str, Any]],
    started: float,
    out_path: Path,
    *,
    status: str,
    failure: Exception | None = None,
) -> dict[str, Any]:
    rollup = rollup_model_calls(calls)
    evidence.update({
        "status": status,
        "pipeline_usage_rollup": rollup,
        "total_cost_usd": rollup["totals"]["cost_usd"],
        "completed_at": _now(),
        "latency_seconds": round(time.perf_counter() - started, 3),
    })
    if failure is not None:
        evidence["failure"] = {"type": type(failure).__name__, "message": str(failure)}
    _write(out_path, evidence)
    return evidence


def run(
    *,
    context_pack_path: Path,
    out_path: Path,
    creative_prompt_path: Path = DEFAULT_CREATIVE_PROMPT,
    compiler_prompt_path: Path = DEFAULT_COMPILER_PROMPT,
    gate_prompt_path: Path = DEFAULT_GATE_PROMPT,
    api_key: str | None = None,
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    pack = SpineContextPackV1.model_validate(_read(context_pack_path))
    for model in (AION_MODEL, SONNET_MODEL, LUNA_MODEL):
        require_qualification_runtime_profile(model)

    pack_payload = pack.model_dump(mode="json", by_alias=True)
    obligations = build_structural_obligations(pack)
    calls: list[dict[str, Any]] = []
    started = time.perf_counter()

    evidence: dict[str, Any] = {
        "schema_version": "spineforge-v5-evidence.v1",
        "status": "started",
        "context_pack_id": pack.context_pack_id,
        "context_fingerprint": pack.context_fingerprint,
        "context_pack": pack_payload,
        "structural_obligations": obligations,
        "started_at": _now(),
        "models": {
            "creative_architect": AION_MODEL,
            "structural_compiler_hardener": SONNET_MODEL,
            "product_gate": LUNA_MODEL,
        },
        "human_review": {
            "required": True,
            "verdict": None,
            "writer_authorized": False,
        },
    }

    creative_input = {
        "task": "create_creative_spine_seed_without_authoring_final_episode_schema",
        "spine_context_pack": pack_payload,
        "structural_obligations_summary": {
            "mandatory_phases": obligations["mandatory_phases"],
            "beat_count": obligations["beat_count"],
        },
        "output_contract": CreativeSpineSeedV5.model_json_schema(by_alias=True),
    }

    call_started = time.perf_counter()
    seed_raw, seed_body, _, seed_failures = call_structured_json_with_retry(
        api_key=key,
        model=AION_MODEL,
        system_prompt=creative_prompt_path.read_text(encoding="utf-8").strip(),
        user_prompt=json.dumps(creative_input, ensure_ascii=False),
        temperature=0.85,
        max_tokens=9000,
        seed=None,
        request_class="teacher_story_medium_reasoning",
        max_parse_attempts=1,
    )
    calls.append(_model_call(
        "spineforge_creative_seed",
        AION_MODEL,
        seed_body,
        round(time.perf_counter() - call_started, 3),
    ))
    evidence["creative_seed_raw_payload"] = seed_raw
    evidence["creative_seed_parse_failures"] = seed_failures

    seed_normalized, seed_repairs = _stamp_seed_model(seed_raw)
    evidence["creative_seed_normalized_payload"] = seed_normalized
    evidence["creative_seed_safe_normalization"] = {
        "applied": bool(seed_repairs),
        "repairs": seed_repairs,
        "semantic_fields_changed": False,
    }

    try:
        seed = CreativeSpineSeedV5.model_validate(seed_normalized)
        validate_seed_authority(seed, pack)
    except (ValidationError, RuntimeError) as exc:
        return _finish(
            evidence,
            calls,
            started,
            out_path,
            status="creative_seed_rejected",
            failure=exc,
        )

    evidence["creative_seed"] = seed.model_dump(mode="json", by_alias=True)

    compiler_input = {
        "task": "compile_and_harden_creative_seed_into_strict_episode_spine",
        "spine_context_pack": pack_payload,
        "creative_seed": evidence["creative_seed"],
        "structural_obligations": obligations,
        "output_contract": StructuralCompileV5.model_json_schema(by_alias=True),
    }

    call_started = time.perf_counter()
    compile_raw, compile_body, _, compile_failures = call_structured_json_with_retry(
        api_key=key,
        model=SONNET_MODEL,
        system_prompt=compiler_prompt_path.read_text(encoding="utf-8").strip(),
        user_prompt=json.dumps(compiler_input, ensure_ascii=False),
        temperature=0.0,
        max_tokens=12000,
        seed=None,
        request_class="saga_architect",
        max_parse_attempts=1,
    )
    calls.append(_model_call(
        "spineforge_structural_compiler_hardener",
        SONNET_MODEL,
        compile_body,
        round(time.perf_counter() - call_started, 3),
    ))
    evidence["structural_compile_raw_payload"] = compile_raw
    evidence["structural_compile_parse_failures"] = compile_failures

    try:
        compiled = StructuralCompileV5.model_validate(compile_raw)
        if compiled.decision == "COMPILED":
            assert compiled.episode_spine is not None
            validate_compiled_authority(compiled.episode_spine, pack)
    except (ValidationError, RuntimeError, AssertionError) as exc:
        return _finish(
            evidence,
            calls,
            started,
            out_path,
            status="structural_compile_rejected",
            failure=exc,
        )

    evidence["structural_compile"] = compiled.model_dump(mode="json", by_alias=True)
    if compiled.decision == "REPLAN":
        return _finish(
            evidence,
            calls,
            started,
            out_path,
            status="creative_replan_required",
        )

    spine = compiled.episode_spine
    assert spine is not None

    gate_input = {
        "task": "evaluate_compiled_spineforge_product",
        "spine_context_pack": pack_payload,
        "creative_seed": evidence["creative_seed"],
        "structural_compile": evidence["structural_compile"],
        "compiled_spine": spine.model_dump(mode="json", by_alias=True),
        "output_contract": SpineProductGateV1.model_json_schema(by_alias=True),
    }

    call_started = time.perf_counter()
    gate_raw, gate_body, _, gate_failures = call_structured_json_with_retry(
        api_key=key,
        model=LUNA_MODEL,
        system_prompt=gate_prompt_path.read_text(encoding="utf-8").strip(),
        user_prompt=json.dumps(gate_input, ensure_ascii=False),
        temperature=0.0,
        max_tokens=5500,
        seed=2026093010,
        request_class="editorial_audit",
        max_parse_attempts=1,
    )
    calls.append(_model_call(
        "spineforge_product_gate",
        LUNA_MODEL,
        gate_body,
        round(time.perf_counter() - call_started, 3),
    ))
    evidence["product_gate_raw_payload"] = gate_raw
    evidence["product_gate_parse_failures"] = gate_failures

    try:
        gate = SpineProductGateV1.model_validate(gate_raw)
    except ValidationError as exc:
        return _finish(
            evidence,
            calls,
            started,
            out_path,
            status="product_gate_contract_rejected",
            failure=exc,
        )

    rollup = rollup_model_calls(calls)
    status = "awaiting_human_review" if gate.decision == "ACCEPT" else "product_replan_required"
    evidence.update({
        "status": status,
        "product_gate": gate.model_dump(mode="json", by_alias=True),
        "pipeline_usage_rollup": rollup,
        "total_cost_usd": rollup["totals"]["cost_usd"],
        "completed_at": _now(),
        "latency_seconds": round(time.perf_counter() - started, 3),
    })

    if gate.decision == "ACCEPT":
        product = SpineForgeProductV5(
            schema="spineforge-product.v5",
            context_pack_id=pack.context_pack_id,
            context_fingerprint=pack.context_fingerprint,
            creative_seed=seed,
            structural_compile=compiled,
            product_gate=gate,
            deterministic_checks={
                "creative_seed_contract_valid": True,
                "creative_seed_authority_valid": True,
                "compiled_episode_spine_contract_valid": True,
                "compiled_episode_spine_authority_valid": True,
                "same_context_pack_for_all_models": True,
                "writer_blocked_pending_human_review": True,
            },
            lineage={
                "models": evidence["models"],
                "usage_rollup": rollup,
            },
            human_review=evidence["human_review"],
        )
        evidence["spine_product"] = product.model_dump(mode="json", by_alias=True)

    _write(out_path, evidence)
    return evidence
