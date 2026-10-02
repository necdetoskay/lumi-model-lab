from __future__ import annotations

import hashlib
from typing import Any, Callable

from src.generate import count_words
from src.narrative_spine_v1_contract import NarrativeSpineV1
from src.spine_context_pack_v1 import SpineContextPackV1, canonical_json
from src.spineforge_v19_human_review import spine_hash
from src.spineforge_v20_writer_once import WRITER_MODEL, execute_writer_once
from src.model_usage_rollup import rollup_model_calls


StageFn = Callable[..., dict[str, Any]]


def _result_calls(result: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("pipeline_usage_rollup", "writer_usage_rollup"):
        rollup = result.get(key)
        if isinstance(rollup, dict) and isinstance(rollup.get("calls"), list):
            return list(rollup["calls"])
    meta = result.get("meta")
    if isinstance(meta, dict) and isinstance(meta.get("model_call"), dict):
        return [meta["model_call"]]
    if isinstance(result.get("model_call"), dict):
        return [result["model_call"]]
    return []


def _with_usage(payload: dict[str, Any], calls: list[dict[str, Any]]) -> dict[str, Any]:
    out = dict(payload)
    rollup = rollup_model_calls(calls)
    out["pipeline_usage_rollup"] = rollup
    out["total_cost_usd"] = rollup["totals"]["cost_usd"]
    out["total_latency_seconds"] = rollup["totals"]["latency_seconds"]
    return out


def _approval_id(*, pack: SpineContextPackV1, spine: NarrativeSpineV1) -> str:
    payload = {
        "mode": "AUTOMATED_PRODUCT_GATE_ACCEPT",
        "context_pack_id": pack.context_pack_id,
        "context_fingerprint": pack.context_fingerprint,
        "spine_hash": spine_hash(spine),
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def build_automatic_writer_handoff(
    *,
    spine_result: dict[str, Any],
    current_context_pack: SpineContextPackV1,
) -> dict[str, Any]:
    if spine_result.get("status") != "awaiting_human_review":
        raise RuntimeError("Automatic Writer handoff requires an accepted Spine product.")
    gate = spine_result.get("product_gate") or {}
    if gate.get("decision") != "ACCEPT" or gate.get("blocking_findings"):
        raise RuntimeError("Automatic Writer handoff requires clean ACCEPT gate.")
    validation = spine_result.get("deterministic_validation") or {}
    for key in ("authority_valid", "reveal_safe", "obligations_valid"):
        if validation.get(key) is not True:
            raise RuntimeError(f"Automatic Writer handoff failed deterministic guard: {key}")

    spine = NarrativeSpineV1.model_validate(spine_result["narrative_spine"])
    source_fingerprint = spine_result.get("context_fingerprint")
    if source_fingerprint != current_context_pack.context_fingerprint:
        raise RuntimeError("Spine ContextPack fingerprint is stale.")

    reader = current_context_pack.reader_profile
    session = current_context_pack.session_target
    return {
        "schema": "spineforge-v20-writer-handoff.v1",
        "status": "WRITER_READY",
        "writer_model": WRITER_MODEL,
        "approval_id": _approval_id(pack=current_context_pack, spine=spine),
        "approval_mode": "AUTOMATED_PRODUCT_GATE_ACCEPT",
        "context_pack_id": current_context_pack.context_pack_id,
        "context_fingerprint": current_context_pack.context_fingerprint,
        "spine_hash": spine_hash(spine),
        "exact_age": int(reader["exact_age"]),
        "target_words_min": int(session["target_words_min"]),
        "target_words_max": int(session["target_words_max"]),
        "preferred_words_min": int(session.get("preferred_words_min") or session["target_words_min"]),
        "preferred_words_max": int(session.get("preferred_words_max") or session["target_words_max"]),
        "human_review": {
            "verdict": "APPROVE",
            "story_writer_authorized": True,
            "automated_compatibility_shim": True,
        },
        "paid_writer_execution_authorized": True,
        "writer_input": {
            "task": "write_one_finished_episode_from_accepted_narrative_spine",
            "reader_profile": reader,
            "session_target": session,
            "spine_context_pack": current_context_pack.model_dump(mode="json", by_alias=True),
            "approved_narrative_spine": spine.model_dump(mode="json", by_alias=True),
            "hard_rules": {
                "one_writer_call_only": True,
                "follow_selected_spine_path_only": True,
                "saga_unknowns_must_remain_unresolved": True,
                "database_state_commit_forbidden_until_final_gate": True,
            },
        },
    }


def _classify_findings(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return "CLEAN"
    scopes = {str(row.get("repair_scope") or "").upper() for row in findings}
    if "REPLAN" in scopes:
        return "REPLAN"
    if "STRUCTURAL_REPAIR" in scopes:
        return "STRUCTURAL_REPAIR"
    if scopes <= {"LOCAL_REPAIR"}:
        return "LOCAL_REPAIR"
    return "STOP"


def _apply_exact_replacements(
    story: str,
    repairs: list[dict[str, str]],
) -> tuple[str, list[dict[str, str]]]:
    repaired = story
    applied: list[dict[str, str]] = []
    for row in repairs:
        old = str(row.get("old") or "")
        new = str(row.get("new") or "")
        if not old or not new or old == new:
            raise RuntimeError("Local repair must provide non-empty changed old/new text.")
        if repaired.count(old) != 1:
            raise RuntimeError("Local repair old span must occur exactly once.")
        repaired = repaired.replace(old, new, 1)
        applied.append({"old": old, "new": new})
    return repaired, applied


def run_auto_pipeline(
    *,
    context_pack: SpineContextPackV1,
    obligations: Any,
    api_key: str,
    system_prompt: str | None = None,
    spine_fn: StageFn | None = None,
    audit_fn: StageFn | None = None,
    local_repair_fn: StageFn | None = None,
    translation_fn: StageFn | None = None,
    fidelity_fn: StageFn | None = None,
    writer_fn: StageFn = execute_writer_once,
    max_local_repair_rounds: int = 1,
) -> dict[str, Any]:
    trace: list[dict[str, Any]] = []
    usage_calls: list[dict[str, Any]] = []

    if spine_fn is None:
        from src.spineforge_v20 import run as spine_fn
    if audit_fn is None or local_repair_fn is None or translation_fn is None or fidelity_fn is None:
        from src.spineforge_v20_auto_stages import (
            fidelity_gate,
            local_story_repair,
            story_audit,
            translate_story,
        )
        audit_fn = audit_fn or story_audit
        local_repair_fn = local_repair_fn or local_story_repair
        translation_fn = translation_fn or translate_story
        fidelity_fn = fidelity_fn or fidelity_gate
    if system_prompt is None:
        from pathlib import Path
        system_prompt = Path("prompts/spineforge_v20_writer.md").read_text(encoding="utf-8").strip()

    spine_result = spine_fn(
        context_pack=context_pack,
        obligations=obligations,
        api_key=api_key,
    )
    usage_calls.extend(_result_calls(spine_result))
    trace.append({"stage": "SPINE", "status": spine_result.get("status")})
    if spine_result.get("status") != "awaiting_human_review":
        return {
            "schema": "spineforge-v20-auto-pipeline.v1",
            "status": "STOP_SPINE_NOT_ACCEPTED",
            "trace": trace,
            "spine_result": spine_result,
        }

    handoff = build_automatic_writer_handoff(
        spine_result=spine_result,
        current_context_pack=context_pack,
    )
    writer_result = writer_fn(
        handoff=handoff,
        api_key=api_key,
        system_prompt=system_prompt,
    )
    usage_calls.extend(_result_calls(writer_result))
    trace.append({"stage": "WRITER", "status": writer_result.get("status")})
    if writer_result.get("status") != "writer_generated":
        return {
            "schema": "spineforge-v20-auto-pipeline.v1",
            "status": "STOP_WRITER_FAILED",
            "trace": trace,
            "writer_result": writer_result,
        }

    english = str(writer_result["story"]).strip()
    audit = audit_fn(
        story=english,
        handoff=handoff,
        api_key=api_key,
    )
    usage_calls.extend(_result_calls(audit))
    findings = list(audit.get("findings") or [])
    classification = _classify_findings(findings)
    trace.append({"stage": "STORY_AUDIT", "status": classification, "findings": len(findings)})

    repair_rounds = 0
    repair_evidence: list[dict[str, Any]] = []
    if classification == "LOCAL_REPAIR":
        while repair_rounds < max_local_repair_rounds and classification == "LOCAL_REPAIR":
            repair = local_repair_fn(
                story=english,
                findings=findings,
                handoff=handoff,
                api_key=api_key,
            )
            usage_calls.extend(_result_calls(repair))
            repaired, applied = _apply_exact_replacements(
                english,
                list(repair.get("replacements") or []),
            )
            if not applied:
                return {
                    "schema": "spineforge-v20-auto-pipeline.v1",
                    "status": "STOP_LOCAL_REPAIR_EMPTY",
                    "trace": trace,
                }
            english = repaired
            repair_rounds += 1
            repair_evidence.append({"round": repair_rounds, "applied": applied})
            audit = audit_fn(
                story=english,
                handoff=handoff,
                api_key=api_key,
            )
            usage_calls.extend(_result_calls(audit))
            findings = list(audit.get("findings") or [])
            classification = _classify_findings(findings)
            trace.append({
                "stage": "POST_REPAIR_AUDIT",
                "status": classification,
                "findings": len(findings),
            })

    if classification != "CLEAN":
        return {
            "schema": "spineforge-v20-auto-pipeline.v1",
            "status": f"STOP_{classification}",
            "trace": trace,
            "english_master": english,
            "remaining_findings": findings,
            "repair_evidence": repair_evidence,
        }

    min_words = int(handoff["target_words_min"])
    max_words = int(handoff["target_words_max"])
    words = count_words(english)
    if not min_words <= words <= max_words:
        return {
            "schema": "spineforge-v20-auto-pipeline.v1",
            "status": "STOP_POST_REPAIR_LENGTH_FAILED",
            "trace": trace,
            "english_master": english,
            "word_count": words,
        }

    translation = translation_fn(
        english_master=english,
        exact_age=int(handoff["exact_age"]),
        api_key=api_key,
    )
    usage_calls.extend(_result_calls(translation))
    trace.append({"stage": "TRANSLATION", "status": translation.get("status")})
    if translation.get("status") != "translated":
        return {
            "schema": "spineforge-v20-auto-pipeline.v1",
            "status": "STOP_TRANSLATION_FAILED",
            "trace": trace,
            "translation": translation,
        }

    fidelity = fidelity_fn(
        english_master=english,
        turkish_delivery=str(translation["turkish_delivery"]),
        api_key=api_key,
    )
    usage_calls.extend(_result_calls(fidelity))
    trace.append({"stage": "FIDELITY", "status": fidelity.get("status")})
    if fidelity.get("status") != "clean":
        return {
            "schema": "spineforge-v20-auto-pipeline.v1",
            "status": "STOP_FIDELITY_FAILED",
            "trace": trace,
            "english_master": english,
            "turkish_delivery": translation["turkish_delivery"],
            "fidelity": fidelity,
        }

    return _with_usage({
        "schema": "spineforge-v20-auto-pipeline.v1",
        "status": "PUBLICATION_READY",
        "trace": trace,
        "context_pack_id": context_pack.context_pack_id,
        "context_fingerprint": context_pack.context_fingerprint,
        "spine_hash": handoff["spine_hash"],
        "approval_id": handoff["approval_id"],
        "approval_mode": handoff["approval_mode"],
        "writer_model": handoff["writer_model"],
        "writer_result": writer_result,
        "repair_rounds": repair_rounds,
        "repair_evidence": repair_evidence,
        "english_master": english,
        "english_word_count": words,
        "turkish_delivery": translation["turkish_delivery"],
        "fidelity": fidelity,
        "state_commit_authorized": True,
    }, usage_calls)
