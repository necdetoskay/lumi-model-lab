from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from src.deterministic_translation_semantic_guards import run_translation_semantic_guards
from src.generate import call_openrouter, parse_cost
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call
from src.spineforge_v19_transport import call_json_object_once


AUDIT_MODEL = "openai/gpt-5.6-luna"
REPAIR_MODEL = "openai/gpt-5.6-luna"
TRANSLATION_MODEL = "google/gemini-3.8-flash"
FIDELITY_MODEL = "openai/gpt-5.6-luna"

AUDIT_PROMPT = Path("prompts/spineforge_v20_story_audit.md")
REPAIR_PROMPT = Path("prompts/spineforge_v20_story_local_repair.md")
TRANSLATION_PROMPT = Path("prompts/translation_en_tr_v2_generic.md")
FIDELITY_PROMPT = Path("prompts/translation_fidelity_gate_v2_generic.md")

_ALLOWED_SCOPES = {"LOCAL_REPAIR", "STRUCTURAL_REPAIR", "REPLAN"}


def _call_json(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    payload: dict[str, Any],
    request_class: str,
    max_tokens: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    require_qualification_runtime_profile(model)
    started = time.perf_counter()
    raw, body, request, failures = call_json_object_once(
        api_key=api_key,
        model=model,
        system_prompt=system_prompt,
        user_prompt=json.dumps(payload, ensure_ascii=False),
        temperature=0.0,
        max_tokens=max_tokens,
        seed=None,
        request_class=request_class,
    )
    latency = round(time.perf_counter() - started, 3)
    call = normalize_model_call(
        stage=request_class,
        model=model,
        provider=runtime_profile_identity(model).get("provider"),
        raw_usage=body.get("usage") or {},
        cost=parse_cost(body).model_dump(mode="json"),
        latency_seconds=latency,
    )
    return raw, {
        "request": request,
        "parse_failures": failures,
        "model_call": call,
    }


def story_audit(
    *,
    story: str,
    handoff: dict[str, Any],
    api_key: str,
) -> dict[str, Any]:
    raw, meta = _call_json(
        api_key=api_key,
        model=AUDIT_MODEL,
        system_prompt=AUDIT_PROMPT.read_text(encoding="utf-8").strip(),
        payload={
            "task": "audit_finished_story_for_material_defects",
            "story": story,
            "reader_profile": handoff["writer_input"]["reader_profile"],
            "approved_narrative_spine": handoff["writer_input"]["approved_narrative_spine"],
            "hard_policy": {
                "do_not_grade_personal_taste": True,
                "minor_language_awkwardness_is_local_repair": True,
                "structural_repair_only_when_local_span_edits_cannot_fix": True,
                "replan_only_when_approved_spine_path_itself_is_invalid": True,
            },
        },
        request_class="editorial_audit",
        max_tokens=2200,
    )
    findings = raw.get("findings") or []
    if not isinstance(findings, list):
        raise RuntimeError("Story audit findings must be a list.")
    normalized: list[dict[str, Any]] = []
    for row in findings:
        if not isinstance(row, dict):
            raise RuntimeError("Story audit finding must be an object.")
        scope = str(row.get("repair_scope") or "").upper()
        if scope not in _ALLOWED_SCOPES:
            raise RuntimeError(f"Invalid story audit repair_scope: {scope}")
        reason = str(row.get("reason") or "").strip()
        if not reason:
            raise RuntimeError("Story audit finding reason is required.")
        normalized.append({
            "family": str(row.get("family") or "unspecified"),
            "severity": str(row.get("severity") or "moderate").lower(),
            "repair_scope": scope,
            "exact_text": str(row.get("exact_text") or ""),
            "reason": reason,
        })
    return {
        "status": "clean" if not normalized else "findings",
        "findings": normalized,
        "meta": meta,
    }


def local_story_repair(
    *,
    story: str,
    findings: list[dict[str, Any]],
    handoff: dict[str, Any],
    api_key: str,
) -> dict[str, Any]:
    if not findings or any(row.get("repair_scope") != "LOCAL_REPAIR" for row in findings):
        raise RuntimeError("Local story repair accepts LOCAL_REPAIR findings only.")
    raw, meta = _call_json(
        api_key=api_key,
        model=REPAIR_MODEL,
        system_prompt=REPAIR_PROMPT.read_text(encoding="utf-8").strip(),
        payload={
            "task": "return_minimal_exact_span_replacements_only",
            "story": story,
            "findings": findings,
            "approved_narrative_spine": handoff["writer_input"]["approved_narrative_spine"],
            "repair_policy": {
                "do_not_rewrite_unaffected_prose": True,
                "one_exact_replacement_per_confirmed_defect": True,
                "preserve_story_events_and_branch_choice": True,
            },
        },
        request_class="editorial_audit",
        max_tokens=1800,
    )
    replacements = raw.get("replacements") or []
    if not isinstance(replacements, list):
        raise RuntimeError("Local repair replacements must be a list.")
    clean: list[dict[str, str]] = []
    for row in replacements:
        if not isinstance(row, dict):
            raise RuntimeError("Local repair replacement must be an object.")
        old = str(row.get("old") or "")
        new = str(row.get("new") or "")
        if not old or not new or old == new:
            raise RuntimeError("Local repair requires changed old/new strings.")
        clean.append({"old": old, "new": new})
    if len(clean) > max(6, len(findings) * 2):
        raise RuntimeError("Local repair exceeded bounded replacement count.")
    return {"status": "replacements_ready", "replacements": clean, "meta": meta}


def translate_story(
    *,
    english_master: str,
    exact_age: int,
    api_key: str,
) -> dict[str, Any]:
    require_qualification_runtime_profile(TRANSLATION_MODEL)
    started = time.perf_counter()
    translation, body, request = call_openrouter(
        api_key=api_key,
        model=TRANSLATION_MODEL,
        system_prompt=TRANSLATION_PROMPT.read_text(encoding="utf-8").strip(),
        user_prompt=json.dumps({
            "exact_age": exact_age,
            "accepted_english_master": english_master,
        }, ensure_ascii=False),
        temperature=0.2,
        max_tokens=8000,
        seed=None,
        request_class="translation",
        structured_output=False,
    )
    latency = round(time.perf_counter() - started, 3)
    hard = run_translation_semantic_guards(english_master, translation)
    call = normalize_model_call(
        stage="translation",
        model=TRANSLATION_MODEL,
        provider=runtime_profile_identity(TRANSLATION_MODEL).get("provider"),
        raw_usage=body.get("usage") or {},
        cost=parse_cost(body).model_dump(mode="json"),
        latency_seconds=latency,
    )
    return {
        "status": "translated" if not hard else "semantic_guard_findings",
        "turkish_delivery": translation,
        "deterministic_findings": hard,
        "model_call": call,
        "request": request,
    }


def fidelity_gate(
    *,
    english_master: str,
    turkish_delivery: str,
    api_key: str,
) -> dict[str, Any]:
    hard = run_translation_semantic_guards(english_master, turkish_delivery)
    if hard:
        return {
            "status": "deterministic_semantic_findings",
            "findings": hard,
            "model_called": False,
        }
    raw, meta = _call_json(
        api_key=api_key,
        model=FIDELITY_MODEL,
        system_prompt=FIDELITY_PROMPT.read_text(encoding="utf-8").strip(),
        payload={
            "source_language": "en",
            "target_language": "tr",
            "source_story": english_master,
            "translation": turkish_delivery,
        },
        request_class="defect_locator",
        max_tokens=2200,
    )
    findings = [
        row for row in (raw.get("findings") or [])
        if str(row.get("severity") or "").lower() in {"serious", "critical"}
    ]
    clean = bool(raw.get("fidelity_clean")) and not findings
    return {
        "status": "clean" if clean else "findings",
        "findings": findings,
        "model_called": True,
        "meta": meta,
    }
