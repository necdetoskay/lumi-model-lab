from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from src.generate import parse_cost
from src.model_registry import runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.spineforge_v19_transport import call_json_object_once
from src.spineforge_v20_story_audit_artifact import (
    AUDIT_FAMILIES,
    build_story_audit_source,
    load_verified_writer_story_artifact,
    run_story_audit_once,
)


PRIMARY_MODEL = "anthropic/claude-sonnet-5.5"
SECONDARY_MODEL = "openai/gpt-5.6-sol"
DEFAULT_PROMPT = Path("prompts/spineforge_v20_story_audit.md")
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
    coverage = raw.get("coverage")
    if not isinstance(coverage, list):
        raise RuntimeError("Story auditor coverage must be a list.")
    coverage_values = [str(item) for item in coverage]
    if len(coverage_values) != len(set(coverage_values)):
        raise RuntimeError("Story auditor coverage contains duplicates.")
    if set(coverage_values) != set(AUDIT_FAMILIES):
        missing = sorted(set(AUDIT_FAMILIES) - set(coverage_values))
        extra = sorted(set(coverage_values) - set(AUDIT_FAMILIES))
        raise RuntimeError(
            f"Story auditor coverage mismatch. missing={missing} extra={extra}"
        )

    findings = raw.get("findings") or []
    if not isinstance(findings, list):
        raise RuntimeError("Story auditor findings must be a list.")
    return {
        "coverage": coverage_values,
        "findings": findings,
        "summary": str(raw.get("summary") or "").strip(),
    }


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
        max_tokens=3500,
        seed=None,
        request_class="editorial_audit",
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
    prompt: str | None = None,
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

    payload = {
        "task": "audit_one_frozen_writer_story",
        "source_artifact": {
            "artifact_id": manifest["artifact_id"],
            "story_sha256": source_story_sha,
            "source_run_id": manifest["source_run_id"],
        },
        "reader_profile": authority["reader_profile"],
        "spine_context_pack": authority["spine_context_pack"],
        "approved_narrative_spine": authority["approved_narrative_spine"],
        "story_segments": audit_source["story_segments"],
    }
    system_prompt = prompt or DEFAULT_PROMPT.read_text(encoding="utf-8").strip()

    primary_fn = primary_call_fn or call_json_object_once
    secondary_fn = secondary_call_fn or call_json_object_once

    primary, primary_meta = _call_auditor(
        fn=primary_fn,
        api_key=api_key,
        model=PRIMARY_MODEL,
        prompt=system_prompt,
        payload=payload,
        stage="spineforge_v20_story_audit_primary",
    )
    secondary, secondary_meta = _call_auditor(
        fn=secondary_fn,
        api_key=api_key,
        model=SECONDARY_MODEL,
        prompt=system_prompt,
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

    merged = _merge_findings(primary["findings"], secondary["findings"])

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
    calls = [primary_meta["model_call"], secondary_meta["model_call"]]
    usage = rollup_model_calls(calls)

    return {
        "schema": "spineforge-v20-story-audit-execution.v1",
        "status": "audit_completed",
        "source_artifact_id": manifest["artifact_id"],
        "source_story_sha256": source_story_sha,
        "input_verified_before_inference": True,
        "input_verified_after_inference": True,
        "source_story_mutated": False,
        "models": {
            "primary": PRIMARY_MODEL,
            "secondary": SECONDARY_MODEL,
        },
        "primary_audit": primary,
        "secondary_audit": secondary,
        "primary_meta": primary_meta,
        "secondary_meta": secondary_meta,
        "audit_artifact": artifact,
        "audit_usage_rollup": usage,
        "incremental_cost_usd": usage["totals"]["cost_usd"],
        "incremental_latency_seconds": usage["totals"]["latency_seconds"],
        "automatic_retry_executed": False,
        "repair_executed": False,
        "translation_executed": False,
        "state_commit_executed": False,
    }
