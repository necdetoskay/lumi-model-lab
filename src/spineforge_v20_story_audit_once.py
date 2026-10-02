from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

from src.generate import parse_cost
from src.model_registry import runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.spineforge_v19_transport import call_strict_json_once
from src.spineforge_v20_story_audit_artifact import (
    AUDIT_FAMILIES,
    build_story_audit_source,
    load_verified_writer_story_artifact,
    run_story_audit_once,
)


PRIMARY_MODEL = "anthropic/claude-sonnet-5.5"
SECONDARY_MODEL = "openai/gpt-5.6-sol"
PRIMARY_PROMPT = Path("prompts/spineforge_v20_story_audit.md")
SECONDARY_PROMPT = Path("prompts/spineforge_v20_story_audit_secondary.md")

AUDIT_REQUEST_CLASS = "spineforge_v20_story_audit"
AUDIT_SCHEMA_NAME = "spineforge_v20_story_audit_v3"
AUDIT_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["evaluations", "summary"],
    "properties": {
        "evaluations": {
            "type": "array",
            "minItems": 13,
            "maxItems": 13,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["family", "present", "findings", "reason"],
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
                    "present": {"type": "boolean"},
                    "findings": {
                        "type": "array",
                        "maxItems": 6,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "severity",
                                "repair_scope",
                                "span_ids",
                                "exact_text",
                                "reason",
                            ],
                            "properties": {
                                "severity": {
                                    "type": "string",
                                    "enum": ["minor", "moderate", "serious", "critical"],
                                },
                                "repair_scope": {
                                    "type": "string",
                                    "enum": [
                                        "LOCAL_REPAIR",
                                        "STRUCTURAL_REPAIR",
                                        "REPLAN",
                                        "NO_REPAIR",
                                    ],
                                },
                                "span_ids": {
                                    "type": "array",
                                    "minItems": 1,
                                    "maxItems": 6,
                                    "items": {"type": "string", "maxLength": 16},
                                },
                                "exact_text": {
                                    "type": "string",
                                    "minLength": 1,
                                    "maxLength": 700,
                                },
                                "reason": {
                                    "type": "string",
                                    "minLength": 1,
                                    "maxLength": 420,
                                },
                            },
                        },
                    },
                    "reason": {"type": "string", "maxLength": 240},
                },
            },
        },
        "summary": {"type": "string", "maxLength": 600},
    },
}
DEFAULT_WRITER_MANIFEST = Path(
    "evidence/spineforge-v20-writer-product/36965340665/writer-story-artifact.json"
)
DEFAULT_WRITER_HANDOFF = Path(
    "evidence/spineforge-v20-writer-handoff/36910614976-writer-ready.json"
)

JsonCall = Callable[
    ..., tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]
]


def _load_authority(
    *,
    writer_manifest: dict[str, Any],
    handoff_path: Path,
) -> dict[str, Any]:
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    if handoff.get("schema") != "spineforge-v20-writer-handoff.v1":
        raise RuntimeError("Stage 5 Writer handoff schema mismatch.")
    if handoff.get("status") != "WRITER_READY":
        raise RuntimeError("Stage 5 Writer handoff is not ready.")

    for key in ("approval_id", "context_pack_id", "context_fingerprint", "spine_hash"):
        if handoff.get(key) != writer_manifest.get(key):
            raise RuntimeError(f"Stage 5 Writer artifact/handoff lineage mismatch: {key}")

    writer_input = handoff.get("writer_input") or {}
    if not isinstance(writer_input.get("approved_narrative_spine"), dict):
        raise RuntimeError("Stage 5 handoff missing approved NarrativeSpine.")
    if not isinstance(writer_input.get("spine_context_pack"), dict):
        raise RuntimeError("Stage 5 handoff missing SpineContextPack.")
    if not isinstance(writer_input.get("reader_profile"), dict):
        raise RuntimeError("Stage 5 handoff missing reader profile.")

    return {
        "approval_id": handoff["approval_id"],
        "context_pack_id": handoff["context_pack_id"],
        "context_fingerprint": handoff["context_fingerprint"],
        "spine_hash": handoff["spine_hash"],
        "reader_profile": writer_input["reader_profile"],
        "spine_context_pack": writer_input["spine_context_pack"],
        "approved_narrative_spine": writer_input["approved_narrative_spine"],
    }


def _normalize_auditor_payload(
    *,
    raw: dict[str, Any],
) -> dict[str, Any]:
    order = [
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
    ]
    rows = raw.get("evaluations")
    if not isinstance(rows, list):
        raise RuntimeError("Story auditor evaluations must be a list.")
    families = [str(row.get("family") or "") for row in rows if isinstance(row, dict)]
    if families != order or len(rows) != len(order):
        raise RuntimeError(
            f"Story auditor must evaluate every family exactly once in canonical order: {families}"
        )

    valid_severity = {"minor", "moderate", "serious", "critical"}
    valid_scope = {"LOCAL_REPAIR", "STRUCTURAL_REPAIR", "REPLAN", "NO_REPAIR"}
    flattened: list[dict[str, Any]] = []
    normalized_rows: list[dict[str, Any]] = []

    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError("Story auditor evaluation must be an object.")
        family = str(row["family"])
        present = row.get("present")
        if not isinstance(present, bool):
            raise RuntimeError(f"Story auditor present flag must be boolean: {family}")

        # v3 canonical form: each family may carry multiple concrete findings.
        if "findings" in row:
            family_findings = row.get("findings")
            if not isinstance(family_findings, list):
                raise RuntimeError(f"Story auditor family findings must be a list: {family}")
            clean_reason = str(row.get("reason") or "").strip()
            if present and not family_findings:
                raise RuntimeError(f"Present Story Audit family requires findings: {family}")
            if not present and family_findings:
                raise RuntimeError(f"Clean Story Audit family findings must be empty: {family}")
            if not present and not clean_reason:
                raise RuntimeError(f"Clean Story Audit family reason is required: {family}")

            normalized_findings: list[dict[str, Any]] = []
            for finding in family_findings:
                if not isinstance(finding, dict):
                    raise RuntimeError(f"Story auditor family finding must be an object: {family}")
                severity = str(finding.get("severity") or "").lower()
                scope = str(finding.get("repair_scope") or "").upper()
                span_ids = [str(x) for x in (finding.get("span_ids") or [])]
                exact_text = str(finding.get("exact_text") or "")
                reason = str(finding.get("reason") or "").strip()
                if severity not in valid_severity:
                    raise RuntimeError(f"Invalid Story Audit severity: {family}:{severity}")
                if scope not in valid_scope:
                    raise RuntimeError(f"Invalid Story Audit repair scope: {family}:{scope}")
                if not span_ids:
                    raise RuntimeError(f"Present Story Audit finding requires span_ids: {family}")
                if not exact_text:
                    raise RuntimeError(f"Present Story Audit finding requires exact_text: {family}")
                if not reason:
                    raise RuntimeError(f"Present Story Audit finding requires reason: {family}")
                normalized = {
                    "family": family,
                    "severity": severity,
                    "repair_scope": scope,
                    "span_ids": span_ids,
                    "exact_text": exact_text,
                    "reason": reason,
                }
                normalized_findings.append(normalized)
                flattened.append(normalized)

            normalized_rows.append({
                "family": family,
                "present": present,
                "findings": normalized_findings,
                "reason": clean_reason if not present else str(row.get("reason") or "").strip(),
            })
            continue

        # Backward-compatible v2 parsing for frozen synthetic tests/evidence.
        reason = str(row.get("reason") or "").strip()
        if not reason:
            raise RuntimeError(f"Story auditor reason is required: {family}")
        if not present:
            if row.get("severity") is not None:
                raise RuntimeError(f"Clean audit severity must be null: {family}")
            if row.get("repair_scope") is not None:
                raise RuntimeError(f"Clean audit repair_scope must be null: {family}")
            if list(row.get("span_ids") or []):
                raise RuntimeError(f"Clean audit span_ids must be empty: {family}")
            if row.get("exact_text") not in (None, ""):
                raise RuntimeError(f"Clean audit exact_text must be null: {family}")
            normalized_rows.append({
                "family": family,
                "present": False,
                "findings": [],
                "reason": reason,
            })
            continue

        severity = str(row.get("severity") or "").lower()
        scope = str(row.get("repair_scope") or "").upper()
        span_ids = [str(x) for x in (row.get("span_ids") or [])]
        exact_text = str(row.get("exact_text") or "")
        if severity not in valid_severity:
            raise RuntimeError(f"Invalid Story Audit severity: {family}:{severity}")
        if scope not in valid_scope:
            raise RuntimeError(f"Invalid Story Audit repair scope: {family}:{scope}")
        if not span_ids:
            raise RuntimeError(f"Present Story Audit finding requires span_ids: {family}")
        if not exact_text:
            raise RuntimeError(f"Present Story Audit finding requires exact_text: {family}")
        normalized = {
            "family": family,
            "severity": severity,
            "repair_scope": scope,
            "span_ids": span_ids,
            "exact_text": exact_text,
            "reason": reason,
        }
        flattened.append(normalized)
        normalized_rows.append({
            "family": family,
            "present": True,
            "findings": [normalized],
            "reason": "",
        })

    return {
        "evaluations": normalized_rows,
        "findings": flattened,
        "summary": str(raw.get("summary") or "").strip(),
    }

def _build_audit_authority_projection(authority: dict[str, Any]) -> dict[str, Any]:
    pack = authority["spine_context_pack"]
    reader = authority["reader_profile"]
    projection = {
        "context_pack_id": authority["context_pack_id"],
        "context_fingerprint": authority["context_fingerprint"],
        "approval_id": authority["approval_id"],
        "spine_hash": authority["spine_hash"],
        "reader": {
            "exact_age": reader.get("exact_age"),
            "audience_band": reader.get("audience_band"),
            "developmental_stage": reader.get("developmental_stage"),
            "dimensions": reader.get("dimensions"),
        },
        "character": pack.get("character"),
        "origin": pack.get("origin"),
        "current_situation": pack.get("current_situation"),
        "relationships": pack.get("relationships"),
        "inventory": pack.get("inventory"),
        "memories": pack.get("memories"),
        "world": pack.get("world"),
        "knowledge_boundaries": pack.get("knowledge_boundaries"),
        "saga": pack.get("saga"),
        "opportunities": pack.get("opportunities"),
        "approved_premise": pack.get("approved_premise"),
        "creative_permission_envelope": pack.get("creative_permission_envelope"),
        "authority_rules": pack.get("authority_rules"),
        "hard_freezes": pack.get("hard_freezes"),
    }
    encoded = json.dumps(
        projection,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "projection": projection,
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "bytes": len(encoded),
    }



def _repair_finding_locators(
    *,
    findings: list[dict[str, Any]],
    story_segments: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    repaired: list[dict[str, Any]] = []
    corrections: list[dict[str, Any]] = []
    all_text = " ".join(seg["text"] for seg in story_segments)

    # Build offsets in the normalized joined representation used for deterministic lookup.
    offsets: list[tuple[int, int, str]] = []
    cursor = 0
    for index, seg in enumerate(story_segments):
        text = seg["text"]
        start_pos = cursor
        end_pos = start_pos + len(text)
        offsets.append((start_pos, end_pos, seg["id"]))
        cursor = end_pos + (1 if index < len(story_segments) - 1 else 0)

    for row in findings:
        item = dict(row)
        exact_text = str(item.get("exact_text") or "")
        if not exact_text:
            repaired.append(item)
            continue

        cited_ids = [str(x) for x in (item.get("span_ids") or [])]
        cited_set = set(cited_ids)
        cited = [seg for seg in story_segments if seg["id"] in cited_set]
        cited_window = " ".join(seg["text"] for seg in cited)
        if exact_text in cited_window:
            repaired.append(item)
            continue

        occurrences: list[int] = []
        start_at = 0
        while True:
            idx = all_text.find(exact_text, start_at)
            if idx < 0:
                break
            occurrences.append(idx)
            start_at = idx + 1

        if len(occurrences) != 1:
            raise RuntimeError(
                "Story Audit locator repair requires exact_text to resolve uniquely "
                f"in frozen story: {item.get('family')}:{len(occurrences)}"
            )

        occ_start = occurrences[0]
        occ_end = occ_start + len(exact_text)
        new_ids = [
            seg_id
            for seg_start, seg_end, seg_id in offsets
            if seg_end > occ_start and seg_start < occ_end
        ]
        if not new_ids:
            raise RuntimeError(
                f"Story Audit locator repair resolved no source spans: {item.get('family')}"
            )

        old_ids = cited_ids
        item["span_ids"] = new_ids
        repaired.append(item)
        corrections.append({
            "family": item.get("family"),
            "exact_text": exact_text,
            "old_span_ids": old_ids,
            "new_span_ids": new_ids,
            "reason": "deterministic_unique_exact_text_rebind",
        })
    return repaired, corrections

def _merge_findings(
    primary: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    out: list[dict[str, Any]] = []
    for group in (primary, secondary):
        for row in group:
            key = (
                str(row.get("family") or ""),
                str(row.get("severity") or "").lower(),
                str(row.get("repair_scope") or "").upper(),
                tuple(str(x) for x in (row.get("span_ids") or [])),
                str(row.get("exact_text") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(dict(row))
    return out


def _call_auditor(
    *,
    fn: JsonCall,
    api_key: str,
    model: str,
    prompt: str,
    payload: dict[str, Any],
    stage: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    raw, body, request, failures = fn(
        api_key=api_key,
        model=model,
        system_prompt=prompt,
        user_prompt=json.dumps(payload, ensure_ascii=False),
        temperature=0.0,
        max_tokens=6000,
        seed=None,
        request_class=AUDIT_REQUEST_CLASS,
        schema_name=AUDIT_SCHEMA_NAME,
        schema=AUDIT_RESPONSE_SCHEMA,
    )
    latency = round(time.perf_counter() - started, 3)
    normalized = _normalize_auditor_payload(raw=raw)
    call = normalize_model_call(
        stage=stage,
        model=model,
        provider=runtime_profile_identity(model).get("provider"),
        raw_usage=body.get("usage") or {},
        cost=parse_cost(body).model_dump(mode="json"),
        latency_seconds=latency,
    )
    return normalized, {
        "model": model,
        "request": {
            "temperature": request.get("temperature"),
            "max_tokens": request.get("max_tokens"),
            "reasoning": request.get("reasoning"),
            "response_format": request.get("response_format"),
        },
        "parse_failures": failures,
        "model_call": call,
    }


def execute_story_audit_once(
    *,
    api_key: str,
    writer_manifest_path: Path = DEFAULT_WRITER_MANIFEST,
    writer_handoff_path: Path = DEFAULT_WRITER_HANDOFF,
    primary_call_fn: JsonCall | None = None,
    secondary_call_fn: JsonCall | None = None,
    primary_prompt: str | None = None,
    secondary_prompt: str | None = None,
    repo_root: Path = Path("."),
) -> dict[str, Any]:
    verified = load_verified_writer_story_artifact(
        manifest_path=writer_manifest_path,
        repo_root=repo_root,
    )
    manifest = verified["manifest"]
    authority = _load_authority(
        writer_manifest=manifest,
        handoff_path=writer_handoff_path,
    )
    audit_source = build_story_audit_source(
        manifest_path=writer_manifest_path,
        repo_root=repo_root,
    )
    source_story_sha = manifest["story_sha256"]

    authority_projection = _build_audit_authority_projection(authority)
    payload = {
        "task": "audit_one_frozen_writer_story",
        "source_artifact": {
            "artifact_id": manifest["artifact_id"],
            "story_sha256": source_story_sha,
            "source_run_id": manifest["source_run_id"],
        },
        "audit_authority_projection": authority_projection["projection"],
        "audit_authority_projection_sha256": authority_projection["sha256"],
        "approved_narrative_spine": authority["approved_narrative_spine"],
        "story_segments": audit_source["story_segments"],
    }
    primary_system_prompt = (
        primary_prompt or PRIMARY_PROMPT.read_text(encoding="utf-8").strip()
    )
    secondary_system_prompt = (
        secondary_prompt or SECONDARY_PROMPT.read_text(encoding="utf-8").strip()
    )

    primary_fn = primary_call_fn or call_strict_json_once
    secondary_fn = secondary_call_fn or call_strict_json_once

    primary, primary_meta = _call_auditor(
        fn=primary_fn,
        api_key=api_key,
        model=PRIMARY_MODEL,
        prompt=primary_system_prompt,
        payload=payload,
        stage="spineforge_v20_story_audit_primary",
    )
    secondary, secondary_meta = _call_auditor(
        fn=secondary_fn,
        api_key=api_key,
        model=SECONDARY_MODEL,
        prompt=secondary_system_prompt,
        payload=payload,
        stage="spineforge_v20_story_audit_secondary",
    )

    # Re-verify immutable source after both model calls.
    after = load_verified_writer_story_artifact(
        manifest_path=writer_manifest_path,
        repo_root=repo_root,
    )
    if after["manifest"]["story_sha256"] != source_story_sha:
        raise RuntimeError("Writer artifact changed during Story Audit.")

    calls = [primary_meta["model_call"], secondary_meta["model_call"]]
    usage = rollup_model_calls(calls)

    merged = _merge_findings(primary["findings"], secondary["findings"])
    try:
        merged, locator_corrections = _repair_finding_locators(
            findings=merged,
            story_segments=audit_source["story_segments"],
        )

        def combined_audit(**kwargs: Any) -> dict[str, Any]:
            return {
                "findings": merged,
                "summary": (
                    f"Primary findings={len(primary['findings'])}; "
                    f"secondary findings={len(secondary['findings'])}; "
                    f"merged findings={len(merged)}."
                ),
            }

        artifact = run_story_audit_once(
            manifest_path=writer_manifest_path,
            audit_call_fn=combined_audit,
            repo_root=repo_root,
        )
    except Exception as exc:
        return {
            "schema": "spineforge-v20-story-audit-execution.v1",
            "status": "audit_contract_failure",
            "source_artifact_id": manifest["artifact_id"],
            "source_story_sha256": source_story_sha,
            "input_verified_before_inference": True,
            "input_verified_after_inference": True,
            "source_story_mutated": False,
            "audit_contract_revision": "family-by-family-multi-finding-v3",
            "audit_authority_projection_sha256": authority_projection["sha256"],
            "audit_authority_projection_bytes": authority_projection["bytes"],
            "models": {
                "primary": PRIMARY_MODEL,
                "secondary": SECONDARY_MODEL,
            },
            "primary_audit": primary,
            "secondary_audit": secondary,
            "primary_meta": primary_meta,
            "secondary_meta": secondary_meta,
            "merged_findings_before_artifact": merged,
            "artifact_error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
            "audit_usage_rollup": usage,
            "incremental_cost_usd": usage["totals"]["cost_usd"],
            "incremental_latency_seconds": usage["totals"]["latency_seconds"],
            "automatic_retry_executed": False,
            "repair_executed": False,
            "translation_executed": False,
            "state_commit_executed": False,
        }

    return {
        "schema": "spineforge-v20-story-audit-execution.v1",
        "status": "audit_completed",
        "source_artifact_id": manifest["artifact_id"],
        "source_story_sha256": source_story_sha,
        "input_verified_before_inference": True,
        "input_verified_after_inference": True,
        "source_story_mutated": False,
        "audit_contract_revision": "family-by-family-multi-finding-v3",
        "audit_authority_projection_sha256": authority_projection["sha256"],
        "audit_authority_projection_bytes": authority_projection["bytes"],
        "models": {
            "primary": PRIMARY_MODEL,
            "secondary": SECONDARY_MODEL,
        },
        "primary_audit": primary,
        "secondary_audit": secondary,
        "primary_meta": primary_meta,
        "secondary_meta": secondary_meta,
        "locator_corrections": locator_corrections,
        "audit_artifact": artifact,
        "audit_usage_rollup": usage,
        "incremental_cost_usd": usage["totals"]["cost_usd"],
        "incremental_latency_seconds": usage["totals"]["latency_seconds"],
        "automatic_retry_executed": False,
        "repair_executed": False,
        "translation_executed": False,
        "state_commit_executed": False,
    }


def reprocess_story_audit_evidence(
    *,
    prior_result: dict[str, Any],
    writer_manifest_path: Path = DEFAULT_WRITER_MANIFEST,
    repo_root: Path = Path("."),
) -> dict[str, Any]:
    if prior_result.get("schema") != "spineforge-v20-story-audit-execution.v1":
        raise RuntimeError("Story Audit reprocess schema mismatch.")
    if prior_result.get("status") != "audit_contract_failure":
        raise RuntimeError("Story Audit reprocess requires audit_contract_failure evidence.")
    if prior_result.get("source_story_mutated") is not False:
        raise RuntimeError("Story Audit reprocess requires immutable source evidence.")
    if not isinstance(prior_result.get("merged_findings_before_artifact"), list):
        raise RuntimeError("Story Audit reprocess requires persisted merged findings.")
    if not isinstance(prior_result.get("audit_usage_rollup"), dict):
        raise RuntimeError("Story Audit reprocess requires persisted usage evidence.")

    verified = load_verified_writer_story_artifact(
        manifest_path=writer_manifest_path,
        repo_root=repo_root,
    )
    manifest = verified["manifest"]
    if prior_result.get("source_artifact_id") != manifest["artifact_id"]:
        raise RuntimeError("Story Audit reprocess source artifact mismatch.")
    if prior_result.get("source_story_sha256") != manifest["story_sha256"]:
        raise RuntimeError("Story Audit reprocess source story SHA mismatch.")

    audit_source = build_story_audit_source(
        manifest_path=writer_manifest_path,
        repo_root=repo_root,
    )
    findings, locator_corrections = _repair_finding_locators(
        findings=list(prior_result["merged_findings_before_artifact"]),
        story_segments=audit_source["story_segments"],
    )

    def combined_audit(**kwargs: Any) -> dict[str, Any]:
        return {
            "findings": findings,
            "summary": (
                "Zero-cost artifact reprocess of already-paid Stage 5 findings; "
                f"findings={len(findings)}."
            ),
        }

    artifact = run_story_audit_once(
        manifest_path=writer_manifest_path,
        audit_call_fn=combined_audit,
        repo_root=repo_root,
    )

    return {
        **prior_result,
        "status": "audit_reprocessed_zero_cost",
        "artifact_error": None,
        "locator_corrections": locator_corrections,
        "audit_artifact": artifact,
        "reprocess": {
            "model_calls_executed": 0,
            "source_paid_usage_reused": True,
            "source_story_mutated": False,
        },
    }
