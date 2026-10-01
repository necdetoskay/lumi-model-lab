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

from src.episode_spine_v3_contract import (
    AntiRepetitionSignatureV2,
    DecisionBranchV2,
    DecisionPointV2,
    EpisodeSpineV3,
    LogisticsPlanV2,
    PersistentOutcomeCandidateV2,
    ReversalEvidenceV2,
    ReversalV2,
    SagaProgressionIntentV2,
)
from src.generate import OpenRouterCallError, parse_cost
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v3_contract import SpineProductGateV1
from src.spineforge_v5_contract import SpineCreativeBlueprintV2, SpineStructuralAssemblyV1
from src.spineforge_v7_contract import SpineForgeProductV7, SpineForgeRevisionFeedbackV7
from src.spineforge_v10_contract import (
    StructuralBeatsV10 as StructuralBeatsV1,
    StructuralFrameV10 as StructuralFrameV1,
    StructuralResolutionV10 as StructuralResolutionV1,
)
from src.spineforge_v10_structured_call import call_structured_json_once


AION_MODEL = "aion-labs/aion-3.5-mini"
SONNET_MODEL = "anthropic/claude-sonnet-5.5"
LUNA_MODEL = "openai/gpt-5.6-luna"

DEFAULT_CREATIVE_PROMPT = Path("prompts/spineforge_creative_architect_v5_blueprint.md")
DEFAULT_STRUCTURAL_PROMPT = Path("prompts/spineforge_structural_compiler_v7_partitioned.md")
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
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _model_call(stage: str, model: str, body: dict[str, Any], latency: float) -> dict[str, Any]:
    return normalize_model_call(
        stage=stage,
        model=model,
        provider=runtime_profile_identity(model).get("provider"),
        raw_usage=body.get("usage") or {},
        cost=parse_cost(body).model_dump(mode="json"),
        latency_seconds=latency,
    )


def _checkpoint(
    *,
    out_path: Path,
    evidence: dict[str, Any],
    calls: list[dict[str, Any]],
    started: float,
) -> dict[str, Any]:
    rollup = rollup_model_calls(calls)
    evidence["pipeline_usage_rollup"] = rollup
    evidence["total_cost_usd"] = rollup["totals"]["cost_usd"]
    evidence["latency_seconds"] = round(time.perf_counter() - started, 3)
    evidence["checkpointed_at"] = _now()
    _write(out_path, evidence)
    return rollup


def _failure(
    *,
    out_path: Path,
    evidence: dict[str, Any],
    calls: list[dict[str, Any]],
    started: float,
    status: str,
    stage: str,
    exc: Exception,
) -> dict[str, Any]:
    trace = getattr(exc, "trace", None)
    evidence.update(
        {
            "status": status,
            "failure": {
                "stage": stage,
                "type": type(exc).__name__,
                "message": str(exc),
                "trace": trace if isinstance(trace, dict) else None,
            },
            "completed_at": _now(),
        }
    )
    _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)
    return evidence


def _normalize_blueprint_raw(raw: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    value = json.loads(json.dumps(raw))
    repairs: list[dict[str, Any]] = []
    if value.get("creative_model") != AION_MODEL:
        repairs.append(
            {
                "kind": "stamp_application_owned_model_identity",
                "field": "creative_model",
                "old": value.get("creative_model"),
                "new": AION_MODEL,
                "reason": "The application owns provider/model lineage.",
            }
        )
        value["creative_model"] = AION_MODEL
    return value, repairs


def _allowed_full_locations(pack: SpineContextPackV1) -> set[str]:
    return {
        str(row["key"])
        for row in pack.knowledge_boundaries["accessible_locations"]
        if row.get("premise_usage") == "FULL"
    }


def _validate_blueprint_authority(
    *,
    blueprint: SpineCreativeBlueprintV2,
    pack: SpineContextPackV1,
) -> None:
    if blueprint.creative_model != AION_MODEL:
        raise RuntimeError("Creative Blueprint model identity mismatch.")
    premise_locations = set(pack.approved_premise["location_refs"])
    full = _allowed_full_locations(pack)
    if not premise_locations.issubset(full):
        raise RuntimeError("Approved premise contains location without FULL access.")
    used = {beat.location_ref for beat in blueprint.creative_beats}
    if not used.issubset(premise_locations):
        raise RuntimeError("Creative Blueprint uses location outside approved premise.")


def _validate_section_locations(
    *,
    beats: StructuralBeatsV1,
    pack: SpineContextPackV1,
) -> None:
    allowed = set(pack.approved_premise["location_refs"])
    full = _allowed_full_locations(pack)
    if not allowed.issubset(full):
        raise RuntimeError("Approved premise contains location without FULL access.")
    used = {beat.location_ref for beat in beats.beats}
    if not used.issubset(allowed):
        raise RuntimeError("Structural Beats use location outside approved premise.")


def _location_sequence(beats: StructuralBeatsV1) -> list[str]:
    sequence: list[str] = []
    for beat in beats.beats:
        if not sequence or sequence[-1] != beat.location_ref:
            sequence.append(beat.location_ref)
    return sequence


def _assemble_structural(
    *,
    pack: SpineContextPackV1,
    frame: StructuralFrameV1,
    beats: StructuralBeatsV1,
    resolution: StructuralResolutionV1,
) -> SpineStructuralAssemblyV1:
    reversal = ReversalV2(
        prior_belief=resolution.reversal.prior_belief,
        evidence=[
            ReversalEvidenceV2.model_validate(row.model_dump(mode="json"))
            for row in resolution.reversal.evidence
        ],
        reinterpretation=resolution.reversal.reinterpretation,
        inference_ceiling=resolution.reversal.inference_ceiling,
        unresolved_after_reversal=resolution.reversal.unresolved_after_reversal,
    )
    decision = DecisionPointV2(
        pressure=resolution.decision_point.pressure,
        branches=[
            DecisionBranchV2.model_validate(row.model_dump(mode="json"))
            for row in resolution.decision_point.branches
        ],
        what_is_unknown=resolution.decision_point.what_is_unknown,
        outcome_uncommitted=True,
    )
    outcomes = [
        PersistentOutcomeCandidateV2.model_validate(row.model_dump(mode="json"))
        for row in resolution.persistent_outcome_candidates
    ]
    saga = SagaProgressionIntentV2(
        intended_milestone_keys=list(pack.saga["intended_milestone_keys"]),
        commit_only_if_earned=True,
        completion_evidence=resolution.saga_progression.completion_evidence,
    )
    anti = AntiRepetitionSignatureV2.model_validate(
        resolution.anti_repetition_signature.model_dump(mode="json")
    )
    session = pack.session_target
    spine = EpisodeSpineV3(
        schema="episode-spine.v2",
        premise_key=pack.approved_premise["key"],
        title=frame.title,
        exact_age=int(pack.reader_profile["exact_age"]),
        session=session["name"],
        target_words_min=int(session["target_words_min"]),
        target_words_max=int(session["target_words_max"]),
        episode_role=frame.episode_role,
        story_promise=frame.story_promise,
        protagonist_role=frame.protagonist_role,
        immediate_objective=frame.immediate_objective,
        central_question=frame.central_question,
        stakes=frame.stakes,
        constraints=frame.constraints,
        opening_hook=frame.opening_hook,
        logistics_plan=LogisticsPlanV2(
            time_window=frame.logistics.time_window,
            location_sequence=_location_sequence(beats),
            movement_constraints=frame.logistics.movement_constraints,
            feasibility_rationale=frame.logistics.feasibility_rationale,
        ),
        beats=beats.beats,
        escalation_ladder=frame.escalation_ladder,
        reversal=reversal,
        decision_point=decision,
        climax=frame.climax,
        local_payoff=frame.local_payoff,
        forward_hook=frame.forward_hook,
        persistent_outcome_candidates=outcomes,
        saga_progression=saga,
        anti_repetition_signature=anti,
        writer_rules=frame.writer_rules,
    )
    return SpineStructuralAssemblyV1(
        schema="spineforge-structural-assembly.v1",
        structural_model=SONNET_MODEL,
        preserved_creative_strengths=frame.preserved_creative_strengths,
        episode_spine=spine,
        compilation_notes=frame.compilation_notes,
        creative_deviations=frame.creative_deviations,
    )


def _validate_episode_authority(
    *,
    assembly: SpineStructuralAssemblyV1,
    pack: SpineContextPackV1,
) -> None:
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
    if {beat.location_ref for beat in spine.beats} - allowed:
        raise RuntimeError("Spine uses location outside approved premise.")
    intended = set(pack.saga["intended_milestone_keys"])
    if set(spine.saga_progression.intended_milestone_keys) != intended:
        raise RuntimeError("Spine intended milestones differ from ContextPack authority.")
    if intended and spine.episode_role not in {
        "MAIN_SAGA_ENTRY",
        "MAIN_SAGA_PROGRESS",
        "MIXED",
    }:
        raise RuntimeError("Main Saga milestone requires Main Saga episode role.")



FRAME_OWNED_FIELDS = {
    "title", "episode_role", "story_promise", "protagonist_role",
    "immediate_objective", "central_question", "stakes", "constraints",
    "opening_hook", "logistics_plan", "escalation_ladder", "climax",
    "local_payoff", "forward_hook", "writer_rules",
}
RESOLUTION_OWNED_FIELDS = {
    "reversal", "decision_point", "persistent_outcome_candidates",
    "saga_progression", "anti_repetition_signature",
}


def _assembly_failure_owner(exc: Exception) -> str | None:
    messages: list[str] = [str(exc).lower()]
    locations: list[str] = []
    if isinstance(exc, ValidationError):
        for row in exc.errors():
            locations.append(".".join(str(x) for x in row.get("loc", ())).lower())
            messages.append(str(row.get("msg") or "").lower())

    text = " | ".join(messages + locations)

    beat_signals = (
        "missing required phases",
        "structural beats",
        "beat key",
        "beats.",
        "dependencies must reference earlier beats",
        "uses location outside approved premise",
    )
    if any(signal in text for signal in beat_signals):
        return "STRUCTURAL_BEATS"

    resolution_signals = (
        "reversal",
        "decision_point",
        "decision point",
        "persistent_outcome",
        "persistent outcome",
        "saga_progression",
        "anti_repetition",
    )
    if any(signal in text for signal in resolution_signals):
        return "STRUCTURAL_RESOLUTION"

    if any(field in text for field in FRAME_OWNED_FIELDS):
        return "STRUCTURAL_FRAME"

    return None


def _revision(
    *,
    pack: SpineContextPackV1,
    attempt: int,
    source_status: str,
    retry_stage: str,
    must_change: list[str],
    blueprint: SpineCreativeBlueprintV2 | None,
    frame: StructuralFrameV1 | None = None,
    beats: StructuralBeatsV1 | None = None,
) -> SpineForgeRevisionFeedbackV7:
    preserve: list[str] = []
    if blueprint is not None:
        preserve.extend(
            [
                blueprint.creative_signature.dramatic_engine,
                blueprint.creative_signature.central_wonder_or_intrigue,
            ]
        )
    if not preserve:
        preserve = [str(pack.approved_premise.get("logline") or "approved premise")]
    return SpineForgeRevisionFeedbackV7(
        schema="spineforge-revision-feedback.v7",
        context_pack_id=pack.context_pack_id,
        context_fingerprint=pack.context_fingerprint,
        source_attempt=attempt,
        next_attempt=attempt + 1,
        source_status=source_status,
        retry_stage=retry_stage,
        must_preserve=preserve[:12],
        must_change=must_change[:12] or ["Resolve the recorded blocking defect."],
        preserved_blueprint=(
            blueprint.model_dump(mode="json", by_alias=True)
            if retry_stage != "CREATIVE_ARCHITECT" and blueprint is not None
            else None
        ),
        preserved_frame=(
            frame.model_dump(mode="json", by_alias=True)
            if retry_stage in {"STRUCTURAL_BEATS", "STRUCTURAL_RESOLUTION"}
            and frame is not None
            else None
        ),
        preserved_beats=(
            beats.model_dump(mode="json", by_alias=True)
            if retry_stage == "STRUCTURAL_RESOLUTION" and beats is not None
            else None
        ),
        validation_errors=must_change[:12],
        authority_freezes=list(pack.hard_freezes)[:20],
    )


def _load_revision(
    *,
    revision_path: Path | None,
    pack: SpineContextPackV1,
    max_attempts: int,
) -> tuple[SpineForgeRevisionFeedbackV7 | None, int]:
    if revision_path is None:
        return None, 1
    revision = SpineForgeRevisionFeedbackV7.model_validate(_read(revision_path))
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
    return "STRUCTURAL_FRAME"


def _call_and_checkpoint(
    *,
    out_path: Path,
    evidence: dict[str, Any],
    calls: list[dict[str, Any]],
    started: float,
    stage: str,
    model: str,
    task: str,
    system_prompt: str,
    payload: dict[str, Any],
    temperature: float,
    max_tokens: int,
    seed: int | None,
    request_class: str,
    api_key: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    call_started = time.perf_counter()
    try:
        raw, body, request, failures = call_structured_json_once(
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            user_prompt=json.dumps(payload, ensure_ascii=False),
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed,
            request_class=request_class,
        )
    except Exception as exc:
        _failure(
            out_path=out_path,
            evidence=evidence,
            calls=calls,
            started=started,
            status="provider_or_transport_rejected",
            stage=stage,
            exc=exc,
        )
        raise
    latency = round(time.perf_counter() - call_started, 3)
    calls.append(_model_call(stage, model, body, latency))
    evidence.setdefault("stage_evidence", {})[stage] = {
        "task": task,
        "raw_payload": raw,
        "parse_failures": failures,
        "request_transport": {
            "response_format": request.get("response_format"),
            "provider": request.get("provider"),
        },
    }
    _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)
    return raw, body


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
    revision, attempt_index = _load_revision(
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
        "schema_version": "spineforge-v10-evidence.v1",
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
        "structural_transport": "partitioned_provider_strict_json_schema",
        "human_review": {
            "required": True,
            "verdict": None,
            "writer_authorized": False,
        },
    }
    _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)

    blueprint: SpineCreativeBlueprintV2
    frame: StructuralFrameV1 | None = None
    beats: StructuralBeatsV1 | None = None

    if revision is not None and revision.retry_stage != "CREATIVE_ARCHITECT":
        blueprint = SpineCreativeBlueprintV2.model_validate(revision.preserved_blueprint)
        _validate_blueprint_authority(blueprint=blueprint, pack=pack)
        evidence["creative_blueprint_reused"] = True
        evidence["creative_blueprint"] = blueprint.model_dump(mode="json", by_alias=True)
    else:
        payload = {
            "task": "create_spineforge_creative_blueprint",
            "spine_context_pack": pack_payload,
            "revision_context": (
                revision.model_dump(mode="json", by_alias=True) if revision else None
            ),
            "output_contract": SpineCreativeBlueprintV2.model_json_schema(by_alias=True),
        }
        try:
            raw, _ = _call_and_checkpoint(
                out_path=out_path,
                evidence=evidence,
                calls=calls,
                started=started,
                stage="spineforge_creative_architect",
                model=AION_MODEL,
                task="create_spineforge_creative_blueprint",
                system_prompt=creative_prompt_path.read_text(encoding="utf-8").strip(),
                payload=payload,
                temperature=0.85,
                max_tokens=9500,
                seed=None,
                request_class="teacher_story_medium_reasoning",
                api_key=key,
            )
        except Exception:
            _write(out_path, evidence)
            return evidence
        normalized, repairs = _normalize_blueprint_raw(raw)
        evidence["creative_safe_normalization"] = {
            "applied": bool(repairs),
            "repairs": repairs,
            "semantic_fields_changed": False,
        }
        try:
            blueprint = SpineCreativeBlueprintV2.model_validate(normalized)
            _validate_blueprint_authority(blueprint=blueprint, pack=pack)
        except (ValidationError, RuntimeError) as exc:
            evidence["status"] = "creative_blueprint_contract_rejected"
            evidence["failure"] = {"type": type(exc).__name__, "message": str(exc)}
            if attempt_index < max_attempts:
                evidence["revision_feedback_candidate"] = _revision(
                    pack=pack,
                    attempt=attempt_index,
                    source_status=evidence["status"],
                    retry_stage="CREATIVE_ARCHITECT",
                    must_change=[str(exc)],
                    blueprint=None,
                ).model_dump(mode="json", by_alias=True)
            evidence["completed_at"] = _now()
            _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)
            return evidence
        evidence["creative_blueprint"] = blueprint.model_dump(mode="json", by_alias=True)
        _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)

    if revision is not None and revision.retry_stage in {
        "STRUCTURAL_BEATS",
        "STRUCTURAL_RESOLUTION",
    }:
        frame = StructuralFrameV1.model_validate(revision.preserved_frame)
        evidence["structural_frame_reused"] = True
        evidence["structural_frame"] = frame.model_dump(mode="json", by_alias=True)
    else:
        frame_payload = {
            "task": "compile_structural_frame",
            "spine_context_pack": pack_payload,
            "creative_blueprint": blueprint.model_dump(mode="json", by_alias=True),
            "revision_context": (
                revision.model_dump(mode="json", by_alias=True)
                if revision is not None and revision.retry_stage == "STRUCTURAL_FRAME"
                else None
            ),
            "output_contract": StructuralFrameV1.model_json_schema(by_alias=True),
        }
        try:
            raw, _ = _call_and_checkpoint(
                out_path=out_path,
                evidence=evidence,
                calls=calls,
                started=started,
                stage="spineforge_structural_frame",
                model=SONNET_MODEL,
                task="compile_structural_frame",
                system_prompt=structural_prompt_path.read_text(encoding="utf-8").strip(),
                payload=frame_payload,
                temperature=0.0,
                max_tokens=5000,
                seed=None,
                request_class="saga_architect",
                api_key=key,
            )
            frame = StructuralFrameV1.model_validate(raw)
        except Exception as exc:
            if evidence.get("status") != "provider_or_transport_rejected":
                evidence["status"] = "structural_frame_contract_rejected"
                evidence["failure"] = {"type": type(exc).__name__, "message": str(exc)}
            if attempt_index < max_attempts:
                evidence["revision_feedback_candidate"] = _revision(
                    pack=pack,
                    attempt=attempt_index,
                    source_status=evidence["status"],
                    retry_stage="STRUCTURAL_FRAME",
                    must_change=[str(exc)],
                    blueprint=blueprint,
                ).model_dump(mode="json", by_alias=True)
            evidence["completed_at"] = _now()
            _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)
            return evidence
        evidence["structural_frame"] = frame.model_dump(mode="json", by_alias=True)
        _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)

    if revision is not None and revision.retry_stage == "STRUCTURAL_RESOLUTION":
        beats = StructuralBeatsV1.model_validate(revision.preserved_beats)
        _validate_section_locations(beats=beats, pack=pack)
        evidence["structural_beats_reused"] = True
        evidence["structural_beats"] = beats.model_dump(mode="json", by_alias=True)
    else:
        beats_payload = {
            "task": "compile_structural_beats",
            "spine_context_pack": pack_payload,
            "creative_blueprint": blueprint.model_dump(mode="json", by_alias=True),
            "structural_frame": frame.model_dump(mode="json", by_alias=True),
            "revision_context": (
                revision.model_dump(mode="json", by_alias=True)
                if revision is not None and revision.retry_stage == "STRUCTURAL_BEATS"
                else None
            ),
            "output_contract": StructuralBeatsV1.model_json_schema(by_alias=True),
        }
        try:
            raw, _ = _call_and_checkpoint(
                out_path=out_path,
                evidence=evidence,
                calls=calls,
                started=started,
                stage="spineforge_structural_beats",
                model=SONNET_MODEL,
                task="compile_structural_beats",
                system_prompt=structural_prompt_path.read_text(encoding="utf-8").strip(),
                payload=beats_payload,
                temperature=0.0,
                max_tokens=6500,
                seed=None,
                request_class="saga_architect",
                api_key=key,
            )
            beats = StructuralBeatsV1.model_validate(raw)
            _validate_section_locations(beats=beats, pack=pack)
        except Exception as exc:
            if evidence.get("status") != "provider_or_transport_rejected":
                evidence["status"] = "structural_beats_contract_rejected"
                evidence["failure"] = {"type": type(exc).__name__, "message": str(exc)}
            if attempt_index < max_attempts:
                evidence["revision_feedback_candidate"] = _revision(
                    pack=pack,
                    attempt=attempt_index,
                    source_status=evidence["status"],
                    retry_stage="STRUCTURAL_BEATS",
                    must_change=[str(exc)],
                    blueprint=blueprint,
                    frame=frame,
                ).model_dump(mode="json", by_alias=True)
            evidence["completed_at"] = _now()
            _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)
            return evidence
        evidence["structural_beats"] = beats.model_dump(mode="json", by_alias=True)
        _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)

    resolution_payload = {
        "task": "compile_structural_resolution",
        "spine_context_pack": pack_payload,
        "creative_blueprint": blueprint.model_dump(mode="json", by_alias=True),
        "structural_frame": frame.model_dump(mode="json", by_alias=True),
        "structural_beats": beats.model_dump(mode="json", by_alias=True),
        "revision_context": (
            revision.model_dump(mode="json", by_alias=True)
            if revision is not None and revision.retry_stage == "STRUCTURAL_RESOLUTION"
            else None
        ),
        "output_contract": StructuralResolutionV1.model_json_schema(by_alias=True),
    }
    try:
        raw, _ = _call_and_checkpoint(
            out_path=out_path,
            evidence=evidence,
            calls=calls,
            started=started,
            stage="spineforge_structural_resolution",
            model=SONNET_MODEL,
            task="compile_structural_resolution",
            system_prompt=structural_prompt_path.read_text(encoding="utf-8").strip(),
            payload=resolution_payload,
            temperature=0.0,
            max_tokens=6500,
            seed=None,
            request_class="saga_architect",
            api_key=key,
        )
        resolution = StructuralResolutionV1.model_validate(raw)
    except Exception as exc:
        if evidence.get("status") != "provider_or_transport_rejected":
            evidence["status"] = "structural_resolution_contract_rejected"
            evidence["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        if attempt_index < max_attempts:
            evidence["revision_feedback_candidate"] = _revision(
                pack=pack,
                attempt=attempt_index,
                source_status=evidence["status"],
                retry_stage="STRUCTURAL_RESOLUTION",
                must_change=[str(exc)],
                blueprint=blueprint,
                frame=frame,
                beats=beats,
            ).model_dump(mode="json", by_alias=True)
        evidence["completed_at"] = _now()
        _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)
        return evidence
    evidence["structural_resolution"] = resolution.model_dump(mode="json", by_alias=True)

    try:
        assembly = _assemble_structural(
            pack=pack,
            frame=frame,
            beats=beats,
            resolution=resolution,
        )
        _validate_episode_authority(assembly=assembly, pack=pack)
    except (ValidationError, RuntimeError) as exc:
        owner = _assembly_failure_owner(exc)
        evidence["status"] = (
            "structural_assembly_contract_rejected"
            if owner is not None
            else "structural_assembly_owner_unclassified"
        )
        evidence["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "owning_partition": owner,
        }
        if attempt_index < max_attempts and owner is not None:
            evidence["revision_feedback_candidate"] = _revision(
                pack=pack,
                attempt=attempt_index,
                source_status=evidence["status"],
                retry_stage=owner,
                must_change=[str(exc)],
                blueprint=blueprint,
                frame=frame if owner in {"STRUCTURAL_BEATS", "STRUCTURAL_RESOLUTION"} else None,
                beats=beats if owner == "STRUCTURAL_RESOLUTION" else None,
            ).model_dump(mode="json", by_alias=True)
        evidence["completed_at"] = _now()
        _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)
        return evidence

    evidence["structural_assembly"] = assembly.model_dump(mode="json", by_alias=True)
    _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)

    gate_payload = {
        "task": "evaluate_spineforge_product",
        "spine_context_pack": pack_payload,
        "creative_blueprint": blueprint.model_dump(mode="json", by_alias=True),
        "structural_assembly": assembly.model_dump(mode="json", by_alias=True),
        "hardened_spine": assembly.episode_spine.model_dump(mode="json", by_alias=True),
        "output_contract": SpineProductGateV1.model_json_schema(by_alias=True),
    }
    try:
        raw, _ = _call_and_checkpoint(
            out_path=out_path,
            evidence=evidence,
            calls=calls,
            started=started,
            stage="spineforge_product_gate",
            model=LUNA_MODEL,
            task="evaluate_spineforge_product",
            system_prompt=gate_prompt_path.read_text(encoding="utf-8").strip(),
            payload=gate_payload,
            temperature=0.0,
            max_tokens=5500,
            seed=2026093010,
            request_class="editorial_audit",
            api_key=key,
        )
        gate = SpineProductGateV1.model_validate(raw)
    except Exception as exc:
        if evidence.get("status") != "provider_or_transport_rejected":
            evidence["status"] = "product_gate_contract_rejected"
            evidence["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        evidence["completed_at"] = _now()
        _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)
        return evidence

    evidence["product_gate"] = gate.model_dump(mode="json", by_alias=True)
    if gate.decision == "REPLAN":
        retry_stage = _gate_retry_stage(gate)
        evidence["status"] = "product_replan_required"
        if attempt_index < max_attempts:
            reasons = gate.blocking_reasons or [gate.decision_reason]
            evidence["revision_feedback_candidate"] = _revision(
                pack=pack,
                attempt=attempt_index,
                source_status=evidence["status"],
                retry_stage=retry_stage,
                must_change=reasons,
                blueprint=blueprint,
            ).model_dump(mode="json", by_alias=True)
        evidence["completed_at"] = _now()
        _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)
        return evidence

    rollup = rollup_model_calls(calls)
    product = SpineForgeProductV7(
        schema="spineforge-product.v7",
        status="AWAITING_HUMAN_REVIEW",
        context_pack_id=pack.context_pack_id,
        context_fingerprint=pack.context_fingerprint,
        creative_blueprint=blueprint,
        structural_frame=frame.model_dump(mode="json", by_alias=True),
        structural_beats=beats.model_dump(mode="json", by_alias=True),
        structural_resolution=resolution.model_dump(mode="json", by_alias=True),
        structural_assembly=assembly,
        product_gate=gate,
        deterministic_checks={
            "creative_blueprint_valid": True,
            "partitioned_structural_sections_valid": True,
            "assembled_episode_spine_valid": True,
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
    evidence.update(
        {
            "status": "awaiting_human_review",
            "spine_product": product.model_dump(mode="json", by_alias=True),
            "completed_at": _now(),
        }
    )
    _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context-pack", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--creative-prompt", type=Path, default=DEFAULT_CREATIVE_PROMPT)
    parser.add_argument("--structural-prompt", type=Path, default=DEFAULT_STRUCTURAL_PROMPT)
    parser.add_argument("--gate-prompt", type=Path, default=DEFAULT_GATE_PROMPT)
    parser.add_argument("--revision-feedback", type=Path)
    parser.add_argument("--max-attempts", type=int, default=3)
    args = parser.parse_args()
    result = run(
        context_pack_path=args.context_pack,
        out_path=args.out,
        creative_prompt_path=args.creative_prompt,
        structural_prompt_path=args.structural_prompt,
        gate_prompt_path=args.gate_prompt,
        revision_feedback_path=args.revision_feedback,
        max_attempts=args.max_attempts,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "attempt_index": result["attempt_index"],
                "context_pack_id": result["context_pack_id"],
                "context_fingerprint": result["context_fingerprint"],
                "usage": (result.get("pipeline_usage_rollup") or {}).get("totals"),
                "human_review": result["human_review"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
