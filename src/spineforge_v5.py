from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import ValidationError

from src.english_story_pipeline import call_structured_json_with_retry
from src.episode_spine_safe_normalize_v4 import normalize_episode_spine_syntax
from src.generate import parse_cost
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v3_contract import SpineProductGateV1
from src.spineforge_v5_contract import (
    SpineCreativeBlueprintV2,
    SpineForgeProductV5,
    SpineForgeRevisionFeedbackV5,
    SpineStructuralAssemblyV1,
)

AION_MODEL = "aion-labs/aion-3.5-mini"
SONNET_MODEL = "anthropic/claude-sonnet-5.5"
LUNA_MODEL = "openai/gpt-5.6-luna"

DEFAULT_CREATIVE_PROMPT = Path("prompts/spineforge_creative_architect_v5_blueprint.md")
DEFAULT_STRUCTURAL_PROMPT = Path("prompts/spineforge_structural_compiler_v5.md")
DEFAULT_GATE_PROMPT = Path("prompts/spineforge_product_gate_v2_context.md")

CREATIVE_GATE_DIMENSIONS = {
    "STORY_DESIRE",
    "ROLEPLAY_POTENTIAL",
    "SCENE_POTENTIAL",
    "CHARACTER_DRIVENNESS",
    "WORLD_SPECIFICITY",
    "WONDER_OR_INTRIGUE",
    "FRESHNESS",
}


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


def _normalize_blueprint_raw(raw: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    value = json.loads(json.dumps(raw))
    repairs: list[dict[str, Any]] = []
    if value.get("creative_model") != AION_MODEL:
        repairs.append({
            "kind": "stamp_application_owned_model_identity",
            "field": "creative_model",
            "old": value.get("creative_model"),
            "new": AION_MODEL,
            "reason": "The application owns provider/model lineage.",
        })
        value["creative_model"] = AION_MODEL
    return value, repairs


def _normalize_assembly_raw(raw: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    value = json.loads(json.dumps(raw))
    repairs: list[dict[str, Any]] = []
    if value.get("structural_model") != SONNET_MODEL:
        repairs.append({
            "kind": "stamp_application_owned_model_identity",
            "field": "structural_model",
            "old": value.get("structural_model"),
            "new": SONNET_MODEL,
            "reason": "The application owns provider/model lineage.",
        })
        value["structural_model"] = SONNET_MODEL

    spine = value.get("episode_spine")
    if not isinstance(spine, dict):
        return value, repairs

    normalized, syntax_repairs = normalize_episode_spine_syntax(spine)
    repairs.extend(syntax_repairs)

    beats = normalized.get("beats")
    logistics = normalized.get("logistics_plan")
    if isinstance(beats, list) and isinstance(logistics, dict):
        derived: list[str] = []
        for beat in beats:
            if not isinstance(beat, dict):
                continue
            location = beat.get("location_ref")
            if isinstance(location, str) and location and (
                not derived or derived[-1] != location
            ):
                derived.append(location)
        if derived and logistics.get("location_sequence") != derived:
            repairs.append({
                "kind": "derive_logistics_location_sequence",
                "field": "episode_spine.logistics_plan.location_sequence",
                "old": logistics.get("location_sequence"),
                "new": derived,
                "reason": "location_sequence is a deterministic projection of final beat order.",
            })
            logistics["location_sequence"] = derived

    value["episode_spine"] = normalized
    return value, repairs


def _allowed_full_locations(pack: SpineContextPackV1) -> set[str]:
    return {
        str(x["key"])
        for x in pack.knowledge_boundaries["accessible_locations"]
        if x.get("premise_usage") == "FULL"
    }


def _validate_blueprint_authority(*, blueprint: SpineCreativeBlueprintV2, pack: SpineContextPackV1) -> None:
    if blueprint.creative_model != AION_MODEL:
        raise RuntimeError("Creative Blueprint model identity mismatch.")
    premise_locations = set(pack.approved_premise["location_refs"])
    full = _allowed_full_locations(pack)
    if not premise_locations.issubset(full):
        raise RuntimeError("Approved premise contains location without FULL access.")
    used = {beat.location_ref for beat in blueprint.creative_beats}
    if not used.issubset(premise_locations):
        raise RuntimeError("Creative Blueprint uses location outside approved premise.")


def _validate_episode_authority(*, assembly: SpineStructuralAssemblyV1, pack: SpineContextPackV1) -> None:
    if assembly.structural_model != SONNET_MODEL:
        raise RuntimeError("Structural Assembly model identity mismatch.")

    spine = assembly.episode_spine
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
        raise RuntimeError("Spine uses location outside approved premise.")

    intended = set(pack.saga["intended_milestone_keys"])
    if set(spine.saga_progression.intended_milestone_keys) != intended:
        raise RuntimeError("Spine intended milestones differ from ContextPack authority.")
    if intended and spine.episode_role not in {
        "MAIN_SAGA_ENTRY", "MAIN_SAGA_PROGRESS", "MIXED"
    }:
        raise RuntimeError("Main Saga milestone requires Main Saga episode role.")


def _preserve_strengths(
    *,
    blueprint: SpineCreativeBlueprintV2 | None,
    raw: dict[str, Any] | None,
    pack: SpineContextPackV1,
) -> list[str]:
    values: list[str] = []
    if blueprint is not None:
        values.extend([
            blueprint.creative_signature.dramatic_engine,
            blueprint.creative_signature.central_wonder_or_intrigue,
        ])
    elif isinstance(raw, dict):
        sig = raw.get("creative_signature")
        if isinstance(sig, dict):
            for key in ("dramatic_engine", "central_wonder_or_intrigue"):
                value = sig.get(key)
                if isinstance(value, str) and value.strip():
                    values.append(value.strip())
    if not values:
        for key in ("logline", "central_problem"):
            value = pack.approved_premise.get(key)
            if isinstance(value, str) and value.strip():
                values.append(value.strip())
    return values[:12] or ["Preserve the approved premise and ContextPack authority."]


def _feedback(
    *,
    pack: SpineContextPackV1,
    source_attempt: int,
    source_status: str,
    retry_stage: str,
    must_change: list[str],
    blueprint: SpineCreativeBlueprintV2 | None,
    raw_blueprint: dict[str, Any] | None = None,
    creative_feedback: list[str] | None = None,
    structural_feedback: list[str] | None = None,
) -> SpineForgeRevisionFeedbackV5:
    return SpineForgeRevisionFeedbackV5(
        schema="spineforge-revision-feedback.v5",
        context_pack_id=pack.context_pack_id,
        context_fingerprint=pack.context_fingerprint,
        source_attempt=source_attempt,
        next_attempt=source_attempt + 1,
        source_status=source_status,
        retry_stage=retry_stage,
        must_preserve=_preserve_strengths(
            blueprint=blueprint,
            raw=raw_blueprint,
            pack=pack,
        ),
        must_change=must_change[:12] or ["Resolve the recorded blocking defect."],
        creative_feedback=(creative_feedback or [])[:12],
        structural_feedback=(structural_feedback or [])[:12],
        preserved_blueprint=(
            blueprint.model_dump(mode="json", by_alias=True)
            if retry_stage == "STRUCTURAL_COMPILER" and blueprint is not None
            else None
        ),
        validation_errors=must_change[:12],
        authority_freezes=list(pack.hard_freezes)[:20],
    )


def _validate_revision(
    *,
    revision_path: Path | None,
    pack: SpineContextPackV1,
    max_attempts: int,
) -> tuple[SpineForgeRevisionFeedbackV5 | None, int]:
    if revision_path is None:
        return None, 1
    revision = SpineForgeRevisionFeedbackV5.model_validate(_read(revision_path))
    if revision.context_pack_id != pack.context_pack_id:
        raise RuntimeError("Revision feedback context_pack_id is stale.")
    if revision.context_fingerprint != pack.context_fingerprint:
        raise RuntimeError("Revision feedback context_fingerprint is stale.")
    if revision.next_attempt > max_attempts:
        raise RuntimeError(
            f"SpineForge attempt limit exceeded: {revision.next_attempt}>{max_attempts}"
        )
    return revision, revision.next_attempt


def _gate_retry_stage(gate: SpineProductGateV1) -> str:
    for row in gate.dimensions:
        if row.name in CREATIVE_GATE_DIMENSIONS and (
            row.blocking_failure or row.score < 4
        ):
            return "CREATIVE_ARCHITECT"
    return "STRUCTURAL_COMPILER"


def run(
    *,
    context_pack_path: Path,
    out_path: Path,
    creative_prompt_path: Path = DEFAULT_CREATIVE_PROMPT,
    structural_prompt_path: Path = DEFAULT_STRUCTURAL_PROMPT,
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
    revision, attempt_index = _validate_revision(
        revision_path=revision_feedback_path,
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
        "human_review": {
            "required": True,
            "verdict": None,
            "writer_authorized": False,
        },
    }

    blueprint: SpineCreativeBlueprintV2
    if revision is not None and revision.retry_stage == "STRUCTURAL_COMPILER":
        blueprint = SpineCreativeBlueprintV2.model_validate(revision.preserved_blueprint)
        _validate_blueprint_authority(blueprint=blueprint, pack=pack)
        evidence["creative_blueprint_reused"] = True
        evidence["creative_blueprint"] = blueprint.model_dump(mode="json", by_alias=True)
    else:
        creative_input = {
            "task": "create_spineforge_creative_blueprint",
            "spine_context_pack": pack_payload,
            "revision_context": (
                revision.model_dump(mode="json", by_alias=True) if revision else None
            ),
            "output_contract": SpineCreativeBlueprintV2.model_json_schema(by_alias=True),
        }
        call_started = time.perf_counter()
        raw, body, _, failures = call_structured_json_with_retry(
            api_key=key,
            model=AION_MODEL,
            system_prompt=creative_prompt_path.read_text(encoding="utf-8").strip(),
            user_prompt=json.dumps(creative_input, ensure_ascii=False),
            temperature=0.85,
            max_tokens=9500,
            seed=None,
            request_class="teacher_story_medium_reasoning",
            max_parse_attempts=1,
        )
        latency = round(time.perf_counter() - call_started, 3)
        calls.append(_model_call("spineforge_creative_architect", AION_MODEL, body, latency))
        evidence["creative_raw_payload"] = raw
        evidence["creative_parse_failures"] = failures
        normalized, repairs = _normalize_blueprint_raw(raw)
        evidence["creative_normalized_payload"] = normalized
        evidence["creative_safe_normalization"] = {
            "applied": bool(repairs),
            "repairs": repairs,
            "semantic_fields_changed": False,
        }
        try:
            blueprint = SpineCreativeBlueprintV2.model_validate(normalized)
            _validate_blueprint_authority(blueprint=blueprint, pack=pack)
        except (ValidationError, RuntimeError) as exc:
            rollup = rollup_model_calls(calls)
            evidence.update({
                "status": "creative_blueprint_contract_rejected",
                "failure": {"type": type(exc).__name__, "message": str(exc)},
                "pipeline_usage_rollup": rollup,
                "total_cost_usd": rollup["totals"]["cost_usd"],
                "completed_at": _now(),
                "latency_seconds": round(time.perf_counter() - started, 3),
            })
            if attempt_index < max_attempts:
                fb = _feedback(
                    pack=pack,
                    source_attempt=attempt_index,
                    source_status="creative_blueprint_contract_rejected",
                    retry_stage="CREATIVE_ARCHITECT",
                    must_change=[str(exc)],
                    blueprint=None,
                    raw_blueprint=normalized,
                    creative_feedback=[
                        "Repair only the Creative Blueprint contract/authority defect while preserving valid creative strengths."
                    ],
                )
                evidence["revision_feedback_candidate"] = fb.model_dump(
                    mode="json", by_alias=True
                )
            else:
                evidence["attempt_limit_reached"] = True
            _write(out_path, evidence)
            return evidence
        evidence["creative_blueprint"] = blueprint.model_dump(mode="json", by_alias=True)

    structural_input = {
        "task": "compile_and_harden_spineforge_blueprint",
        "spine_context_pack": pack_payload,
        "creative_blueprint": blueprint.model_dump(mode="json", by_alias=True),
        "revision_context": (
            revision.model_dump(mode="json", by_alias=True)
            if revision is not None and revision.retry_stage == "STRUCTURAL_COMPILER"
            else None
        ),
        "output_contract": SpineStructuralAssemblyV1.model_json_schema(by_alias=True),
    }
    call_started = time.perf_counter()
    raw, body, _, failures = call_structured_json_with_retry(
        api_key=key,
        model=SONNET_MODEL,
        system_prompt=structural_prompt_path.read_text(encoding="utf-8").strip(),
        user_prompt=json.dumps(structural_input, ensure_ascii=False),
        temperature=0.0,
        max_tokens=14000,
        seed=None,
        request_class="saga_architect",
        max_parse_attempts=1,
    )
    latency = round(time.perf_counter() - call_started, 3)
    calls.append(_model_call("spineforge_structural_compiler", SONNET_MODEL, body, latency))
    evidence["structural_raw_payload"] = raw
    evidence["structural_parse_failures"] = failures
    normalized, repairs = _normalize_assembly_raw(raw)
    evidence["structural_normalized_payload"] = normalized
    evidence["structural_safe_normalization"] = {
        "applied": bool(repairs),
        "repairs": repairs,
        "semantic_fields_changed": False,
    }

    try:
        assembly = SpineStructuralAssemblyV1.model_validate(normalized)
        _validate_episode_authority(assembly=assembly, pack=pack)
    except (ValidationError, RuntimeError) as exc:
        rollup = rollup_model_calls(calls)
        evidence.update({
            "status": "structural_assembly_contract_rejected",
            "failure": {"type": type(exc).__name__, "message": str(exc)},
            "pipeline_usage_rollup": rollup,
            "total_cost_usd": rollup["totals"]["cost_usd"],
            "completed_at": _now(),
            "latency_seconds": round(time.perf_counter() - started, 3),
        })
        if attempt_index < max_attempts:
            fb = _feedback(
                pack=pack,
                source_attempt=attempt_index,
                source_status="structural_assembly_contract_rejected",
                retry_stage="STRUCTURAL_COMPILER",
                must_change=[str(exc)],
                blueprint=blueprint,
                structural_feedback=[
                    "Recompile the preserved Creative Blueprint into a complete strict EpisodeSpine without changing creative identity."
                ],
            )
            evidence["revision_feedback_candidate"] = fb.model_dump(
                mode="json", by_alias=True
            )
        else:
            evidence["attempt_limit_reached"] = True
        _write(out_path, evidence)
        return evidence

    evidence["structural_assembly"] = assembly.model_dump(mode="json", by_alias=True)
    gate_input = {
        "task": "evaluate_spineforge_product",
        "spine_context_pack": pack_payload,
        "creative_blueprint": blueprint.model_dump(mode="json", by_alias=True),
        "structural_assembly": assembly.model_dump(mode="json", by_alias=True),
        "hardened_spine": assembly.episode_spine.model_dump(mode="json", by_alias=True),
        "output_contract": SpineProductGateV1.model_json_schema(by_alias=True),
    }
    call_started = time.perf_counter()
    raw, body, _, failures = call_structured_json_with_retry(
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
    latency = round(time.perf_counter() - call_started, 3)
    calls.append(_model_call("spineforge_product_gate", LUNA_MODEL, body, latency))
    evidence["product_gate_raw_payload"] = raw
    evidence["product_gate_parse_failures"] = failures

    try:
        gate = SpineProductGateV1.model_validate(raw)
    except ValidationError as exc:
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
        retry_stage = _gate_retry_stage(gate)
        evidence.update({
            "status": "product_replan_required",
            "pipeline_usage_rollup": rollup,
            "total_cost_usd": rollup["totals"]["cost_usd"],
            "completed_at": _now(),
            "latency_seconds": round(time.perf_counter() - started, 3),
        })
        if attempt_index < max_attempts:
            reasons = gate.blocking_reasons or [gate.decision_reason]
            fb = _feedback(
                pack=pack,
                source_attempt=attempt_index,
                source_status="product_replan_required",
                retry_stage=retry_stage,
                must_change=reasons,
                blueprint=blueprint,
                creative_feedback=(
                    reasons if retry_stage == "CREATIVE_ARCHITECT" else []
                ),
                structural_feedback=(
                    reasons if retry_stage == "STRUCTURAL_COMPILER" else []
                ),
            )
            evidence["revision_feedback_candidate"] = fb.model_dump(
                mode="json", by_alias=True
            )
        else:
            evidence["attempt_limit_reached"] = True
        _write(out_path, evidence)
        return evidence

    product = SpineForgeProductV5(
        schema="spineforge-product.v5",
        status="AWAITING_HUMAN_REVIEW",
        context_pack_id=pack.context_pack_id,
        context_fingerprint=pack.context_fingerprint,
        creative_blueprint=blueprint,
        structural_assembly=assembly,
        product_gate=gate,
        deterministic_checks={
            "creative_blueprint_valid": True,
            "structural_assembly_valid": True,
            "context_pack_authority_valid": True,
            "context_fingerprint_bound": True,
            "writer_blocked": True,
        },
        lineage={
            "models": evidence["models"],
            "usage_rollup": rollup,
            "attempt_index": attempt_index,
        },
        human_review=evidence["human_review"],
    )
    evidence.update({
        "status": "awaiting_human_review",
        "spine_product": product.model_dump(mode="json", by_alias=True),
        "pipeline_usage_rollup": rollup,
        "total_cost_usd": rollup["totals"]["cost_usd"],
        "completed_at": _now(),
        "latency_seconds": round(time.perf_counter() - started, 3),
    })
    _write(out_path, evidence)
    return evidence


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--context-pack", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--creative-prompt", type=Path, default=DEFAULT_CREATIVE_PROMPT)
    p.add_argument("--structural-prompt", type=Path, default=DEFAULT_STRUCTURAL_PROMPT)
    p.add_argument("--gate-prompt", type=Path, default=DEFAULT_GATE_PROMPT)
    p.add_argument("--revision-feedback", type=Path)
    p.add_argument("--max-attempts", type=int, default=3)
    a = p.parse_args()
    result = run(
        context_pack_path=a.context_pack,
        out_path=a.out,
        creative_prompt_path=a.creative_prompt,
        structural_prompt_path=a.structural_prompt,
        gate_prompt_path=a.gate_prompt,
        revision_feedback_path=a.revision_feedback,
        max_attempts=a.max_attempts,
    )
    print(json.dumps({
        "status": result["status"],
        "attempt_index": result["attempt_index"],
        "context_pack_id": result["context_pack_id"],
        "context_fingerprint": result["context_fingerprint"],
        "usage": (result.get("pipeline_usage_rollup") or {}).get("totals"),
        "human_review": result["human_review"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
