from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from src.spineforge_v20_story_audit_once import (
    AUDIT_REQUEST_CLASS,
    AUDIT_RESPONSE_SCHEMA,
    AUDIT_SCHEMA_NAME,
    PRIMARY_MODEL,
    PRIMARY_PROMPT,
    SECONDARY_AUDIT_RESPONSE_SCHEMA,
    SECONDARY_AUDIT_SCHEMA_NAME,
    SECONDARY_MODEL,
    SECONDARY_PROMPT,
    _build_audit_authority_projection,
    _call_auditor,
    _load_authority,
    _merge_findings,
    _normalize_language_specialist_payload,
    _repair_finding_locators,
)
from src.spineforge_v20_story_reaudit_handoff import (
    DEFAULT_STAGE6_ARTIFACT,
    DEFAULT_WRITER_HANDOFF,
)


DEFAULT_REAUDIT_HANDOFF = Path(
    "evidence/spineforge-v20-story-reaudit/37006087948-handoff.json"
)
DEFAULT_WRITER_MANIFEST = Path(
    "evidence/spineforge-v20-writer-product/36965340665/writer-story-artifact.json"
)


JsonCall = Callable[..., tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _artifact_id(payload: dict[str, Any], prefix: str) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"{prefix}:{_sha256_bytes(encoded)}"


def _canonical_story_from_file(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text[:-1] if text.endswith("\n") else text


def _decision_from_findings(findings: list[dict[str, Any]]) -> tuple[str, str]:
    scopes = {str(row.get("repair_scope") or "").upper() for row in findings}
    if "REPLAN" in scopes:
        return "REPLAN_REQUIRED", "STOP"
    if "STRUCTURAL_REPAIR" in scopes:
        return "STRUCTURAL_REPAIR_REQUIRED", "STOP"
    if "LOCAL_REPAIR" in scopes:
        return "LOCAL_REPAIR_REQUIRED", "STORY_LOCAL_REPAIR"
    return "ACCEPT", "ENGLISH_MASTER_SEAL"


def _load_verified_reaudit_source(
    *,
    handoff_path: Path = DEFAULT_REAUDIT_HANDOFF,
    stage6_artifact_path: Path = DEFAULT_STAGE6_ARTIFACT,
) -> dict[str, Any]:
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    source = json.loads(stage6_artifact_path.read_text(encoding="utf-8"))

    if handoff.get("schema") != "spineforge-v20-story-reaudit-handoff.v1":
        raise RuntimeError("Story Re-audit handoff schema mismatch.")
    if handoff.get("status") != "READY_NOT_AUTHORIZED":
        raise RuntimeError("Story Re-audit handoff must remain READY_NOT_AUTHORIZED.")
    if handoff.get("paid_execution_authorized") is not False:
        raise RuntimeError("Story Re-audit handoff must never authorize paid inference.")
    if source.get("schema") != "spineforge-v20-story-local-repair-artifact.v1":
        raise RuntimeError("Story Re-audit source artifact schema mismatch.")
    if source.get("artifact_id") != handoff.get("source_stage6_artifact_id"):
        raise RuntimeError("Story Re-audit Stage 6 artifact lineage mismatch.")
    if _sha256_file(stage6_artifact_path) != handoff.get("source_stage6_artifact_sha256"):
        raise RuntimeError("Story Re-audit Stage 6 artifact SHA mismatch.")
    if source.get("immutable") is not True or source.get("status") != "FROZEN":
        raise RuntimeError("Story Re-audit source artifact must be frozen and immutable.")
    if source.get("mandatory_full_reaudit") is not True:
        raise RuntimeError("Story Re-audit source must require full re-audit.")

    story_path = Path(source["repaired_story_path"])
    story = _canonical_story_from_file(story_path)
    if _sha256_file(story_path) != source["repaired_story_file_sha256"]:
        raise RuntimeError("Story Re-audit repaired story file SHA mismatch.")
    if _sha256_text(story) != source["repaired_story_text_sha256"]:
        raise RuntimeError("Story Re-audit repaired story text SHA mismatch.")

    repaired_segments = list(source.get("repaired_segments") or [])
    if len(repaired_segments) != 199:
        raise RuntimeError("Story Re-audit requires all 199 stable spans.")
    ids = [str(row.get("span_id") or "") for row in repaired_segments]
    if len(set(ids)) != 199 or ids != [f"S{i:03d}" for i in range(1, 200)]:
        raise RuntimeError("Story Re-audit repaired span identity/order mismatch.")

    story_segments = [
        {
            "id": str(row["span_id"]),
            "paragraph_id": row["paragraph_id"],
            "paragraph_index": row["paragraph_index"],
            "text": row["repaired_text"],
        }
        for row in repaired_segments
    ]
    return {
        "handoff": handoff,
        "source_artifact": source,
        "story_path": story_path,
        "story": story,
        "story_segments": story_segments,
    }


def execute_story_reaudit_once(
    *,
    api_key: str,
    handoff_path: Path = DEFAULT_REAUDIT_HANDOFF,
    stage6_artifact_path: Path = DEFAULT_STAGE6_ARTIFACT,
    writer_manifest_path: Path = DEFAULT_WRITER_MANIFEST,
    writer_handoff_path: Path = DEFAULT_WRITER_HANDOFF,
    primary_call_fn: JsonCall | None = None,
    secondary_call_fn: JsonCall | None = None,
    primary_prompt: str | None = None,
    secondary_prompt: str | None = None,
) -> dict[str, Any]:
    verified = _load_verified_reaudit_source(
        handoff_path=handoff_path,
        stage6_artifact_path=stage6_artifact_path,
    )
    handoff = verified["handoff"]
    source = verified["source_artifact"]
    story_segments = verified["story_segments"]
    source_story_sha = source["repaired_story_text_sha256"]

    writer_manifest = json.loads(writer_manifest_path.read_text(encoding="utf-8"))
    authority = _load_authority(
        writer_manifest=writer_manifest,
        handoff_path=writer_handoff_path,
    )
    for key in ("context_pack_id", "context_fingerprint", "spine_hash", "approval_id"):
        if authority[key] != handoff[key]:
            raise RuntimeError(f"Story Re-audit authority lineage mismatch: {key}")

    authority_projection = _build_audit_authority_projection(authority)
    source_identity = {
        "artifact_id": source["artifact_id"],
        "story_sha256": source_story_sha,
        "source_run_id": source["source_run_id"],
    }
    primary_payload = {
        "task": "reaudit_one_frozen_repaired_story",
        "source_artifact": source_identity,
        "audit_authority_projection": authority_projection["projection"],
        "audit_authority_projection_sha256": authority_projection["sha256"],
        "approved_narrative_spine": authority["approved_narrative_spine"],
        "story_segments": story_segments,
        "stage6_lineage": {
            "patch_count": source["patch_count"],
            "no_change_resolution_count": source["no_change_resolution_count"],
            "changed_span_ids": source["changed_span_ids"],
            "no_change_span_ids": source["no_change_span_ids"],
        },
    }
    secondary_payload = {
        "task": "contrastive_edit_frozen_repaired_story_english_naturalness",
        "source_artifact": source_identity,
        "reader": {"exact_age": authority["reader_profile"].get("exact_age")},
        "story_segments": story_segments,
    }

    primary_fn = primary_call_fn
    secondary_fn = secondary_call_fn
    primary_system_prompt = primary_prompt or PRIMARY_PROMPT.read_text(encoding="utf-8").strip()
    secondary_system_prompt = secondary_prompt or SECONDARY_PROMPT.read_text(encoding="utf-8").strip()
    expected_span_ids = [str(row["id"]) for row in story_segments]
    story_text_by_id = {str(row["id"]): str(row["text"]) for row in story_segments}

    primary_kwargs = dict(
        api_key=api_key,
        model=PRIMARY_MODEL,
        prompt=primary_system_prompt,
        payload=primary_payload,
        stage="spineforge_v20_story_reaudit_primary",
        schema_name=AUDIT_SCHEMA_NAME,
        schema=AUDIT_RESPONSE_SCHEMA,
    )
    if primary_fn is not None:
        primary_kwargs["fn"] = primary_fn
    else:
        from src.spineforge_v19_transport import call_strict_json_once
        primary_kwargs["fn"] = call_strict_json_once
    primary, primary_meta = _call_auditor(**primary_kwargs)

    secondary_kwargs = dict(
        api_key=api_key,
        model=SECONDARY_MODEL,
        prompt=secondary_system_prompt,
        payload=secondary_payload,
        stage="spineforge_v20_story_reaudit_language_specialist",
        schema_name=SECONDARY_AUDIT_SCHEMA_NAME,
        schema=SECONDARY_AUDIT_RESPONSE_SCHEMA,
        normalize_fn=lambda raw: _normalize_language_specialist_payload(
            raw=raw,
            expected_span_ids=expected_span_ids,
            story_text_by_id=story_text_by_id,
        ),
    )
    if secondary_fn is not None:
        secondary_kwargs["fn"] = secondary_fn
    else:
        from src.spineforge_v19_transport import call_strict_json_once
        secondary_kwargs["fn"] = call_strict_json_once
    secondary, secondary_meta = _call_auditor(**secondary_kwargs)

    # Source must still be byte-identical after both calls.
    after = _load_verified_reaudit_source(
        handoff_path=handoff_path,
        stage6_artifact_path=stage6_artifact_path,
    )
    if after["source_artifact"]["artifact_id"] != source["artifact_id"]:
        raise RuntimeError("Story Re-audit Stage 6 artifact changed during inference.")
    if after["source_artifact"]["repaired_story_text_sha256"] != source_story_sha:
        raise RuntimeError("Story Re-audit repaired story changed during inference.")

    merged = _merge_findings(primary["findings"], secondary["findings"])
    merged, locator_corrections = _repair_finding_locators(
        findings=merged,
        story_segments=story_segments,
    )
    decision, next_stage = _decision_from_findings(merged)

    calls = [primary_meta["model_call"], secondary_meta["model_call"]]
    from src.model_usage_rollup import rollup_model_calls
    usage = rollup_model_calls(calls)

    artifact_body: dict[str, Any] = {
        "schema": "spineforge-v20-story-reaudit-artifact.v1",
        "artifact_type": "IMMUTABLE_STORY_REAUDIT",
        "stage": 7,
        "source_stage6_artifact_id": source["artifact_id"],
        "source_repaired_story_sha256": source_story_sha,
        "source_stage5_audit_artifact_id": source["source_audit_artifact_id"],
        "context_pack_id": handoff["context_pack_id"],
        "context_fingerprint": handoff["context_fingerprint"],
        "spine_hash": handoff["spine_hash"],
        "approval_id": handoff["approval_id"],
        "input_verified": True,
        "source_story_mutated": False,
        "full_story_reaudited": True,
        "stable_span_count": len(story_segments),
        "decision": decision,
        "next_stage": next_stage,
        "findings": merged,
        "summary": (
            f"Primary findings={len(primary['findings'])}; "
            f"secondary findings={len(secondary['findings'])}; "
            f"merged findings={len(merged)}."
        ),
    }
    artifact_body["artifact_id"] = _artifact_id(artifact_body, "story-reaudit")

    return {
        "schema": "spineforge-v20-story-reaudit-execution.v1",
        "status": "reaudit_completed",
        "source_stage6_artifact_id": source["artifact_id"],
        "source_repaired_story_sha256": source_story_sha,
        "reaudit_contract_revision": "primary-v3-plus-language-specialist-v2",
        "secondary_contract_revision": "language-specialist-v2",
        "models": {"primary": PRIMARY_MODEL, "secondary": SECONDARY_MODEL},
        "primary_audit": primary,
        "secondary_audit": secondary,
        "secondary_language_sentence_scan": secondary["language_sentence_scan"],
        "secondary_language_sentence_scan_count": len(secondary["language_sentence_scan"]),
        "locator_corrections": locator_corrections,
        "reaudit_artifact": artifact_body,
        "reaudit_usage_rollup": usage,
        "incremental_cost_usd": usage["totals"]["cost_usd"],
        "incremental_latency_seconds": usage["totals"]["latency_seconds"],
        "source_story_mutated": False,
        "automatic_retry_executed": False,
        "repair_executed": False,
        "translation_executed": False,
        "state_commit_executed": False,
    }
