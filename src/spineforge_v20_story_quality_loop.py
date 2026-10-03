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
from src.spineforge_v20_story_audit_once import (
    AUDIT_RESPONSE_SCHEMA,
    AUDIT_SCHEMA_NAME,
    PRIMARY_MODEL,
    PRIMARY_PROMPT,
    PRIMARY_AUDIT_CANONICAL_FAMILY_ORDER,
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
from src.spineforge_v20_story_local_repair_once import (
    REPAIR_MODEL,
    REPAIR_REQUEST_CLASS,
    REPAIR_RESPONSE_SCHEMA,
    _apply_patches,
    _normalize_repair_payload,
)
from src.spineforge_v20_story_reaudit_once import _decision_from_findings


PROFILE_PATH = Path(
    "data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json"
)
WRITER_MANIFEST_PATH = Path(
    "evidence/spineforge-v20-writer-product/36965340665/writer-story-artifact.json"
)
WRITER_HANDOFF_PATH = Path(
    "evidence/spineforge-v20-writer-handoff/36910614976-writer-ready.json"
)
REPAIR_PROMPT = Path("prompts/spineforge_v20_story_local_repair_cycle2.md")
REPAIR_SCHEMA_NAME = "spineforge_v20_story_quality_local_repair_v1"

JsonCall = Callable[
    ..., tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]
]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _canonical_story(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text[:-1] if text.endswith("\n") else text


def _artifact_id(payload: dict[str, Any], prefix: str) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"{prefix}:{_sha256_bytes(encoded)}"


def _load_story_artifact(path: Path) -> dict[str, Any]:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    allowed_schemas = {
        "spineforge-v20-story-local-repair-artifact.v1",
        "spineforge-v20-story-local-repair-cycle2-artifact.v1",
        "spineforge-v20-story-quality-story-artifact.v1",
    }
    if artifact.get("schema") not in allowed_schemas:
        raise RuntimeError("Story Quality Loop source story artifact schema mismatch.")
    if artifact.get("status") != "FROZEN" or artifact.get("immutable") is not True:
        raise RuntimeError("Story Quality Loop requires frozen immutable story artifact.")
    if int(artifact.get("stable_span_count") or 0) != 199:
        raise RuntimeError("Story Quality Loop requires 199 stable spans.")
    segments = list(artifact.get("repaired_segments") or [])
    if len(segments) != 199:
        raise RuntimeError("Story Quality Loop repaired segment count mismatch.")
    ids = [str(row.get("span_id") or "") for row in segments]
    if ids != [f"S{i:03d}" for i in range(1, 200)]:
        raise RuntimeError("Story Quality Loop span identity/order mismatch.")
    story_path = Path(str(artifact["repaired_story_path"]))
    story = _canonical_story(story_path)
    if _sha256_file(story_path) != artifact.get("repaired_story_file_sha256"):
        raise RuntimeError("Story Quality Loop story file SHA mismatch.")
    if _sha256_text(story) != artifact.get("repaired_story_text_sha256"):
        raise RuntimeError("Story Quality Loop canonical story SHA mismatch.")
    return {"artifact": artifact, "story": story, "story_path": story_path}


def _story_segments(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": str(row["span_id"]),
            "paragraph_id": row["paragraph_id"],
            "paragraph_index": row["paragraph_index"],
            "text": row["repaired_text"],
        }
        for row in artifact["repaired_segments"]
    ]




def build_recovered_reaudit_envelope(
    *,
    result_path: Path,
    raw_envelope_path: Path,
) -> dict[str, Any]:
    """Recover only a post-inference envelope write-order interruption.

    This does not retry or infer. It requires a completed immutable re-audit
    result and exact usage equality with the raw paid envelope.
    """
    result = json.loads(result_path.read_text(encoding="utf-8"))
    raw = json.loads(raw_envelope_path.read_text(encoding="utf-8"))
    if result.get("status") != "reaudit_completed":
        raise RuntimeError("Re-audit recovery requires completed result.")
    if raw.get("result_status") != "started":
        raise RuntimeError("Re-audit recovery requires raw envelope status started.")
    if raw.get("action") != "REAUDIT":
        raise RuntimeError("Re-audit recovery is only valid for REAUDIT.")
    if raw.get("explicit_paid_authorization") is not True:
        raise RuntimeError("Re-audit recovery requires explicit paid authorization.")
    if raw.get("automatic_retry_executed") is not False:
        raise RuntimeError("Re-audit recovery forbids automatic retry.")
    if raw.get("automatic_paid_transition_executed") is not False:
        raise RuntimeError("Re-audit recovery forbids automatic paid transition.")
    if raw.get("usage_rollup") != result.get("reaudit_usage_rollup"):
        raise RuntimeError("Re-audit recovery usage lineage mismatch.")

    recovered = dict(raw)
    recovered["schema"] = "spineforge-v20-paid-story-quality-loop-recovered-envelope.v1"
    recovered["result_status"] = "reaudit_completed"
    recovered["postprocess_recovery"] = {
        "reason": "envelope_status_write_order_after_successful_inference",
        "source_raw_envelope_path": str(raw_envelope_path),
        "source_raw_envelope_sha256": _sha256_file(raw_envelope_path),
        "source_result_path": str(result_path),
        "source_result_sha256": _sha256_file(result_path),
        "paid_inference_reexecuted": False,
    }
    return recovered

def build_reaudit_product(
    *,
    result_path: Path,
    envelope_path: Path,
    source_story_artifact_path: Path,
    stage: int,
    cycle_index: int,
) -> dict[str, Any]:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    source = _load_story_artifact(source_story_artifact_path)["artifact"]

    if result.get("status") != "reaudit_completed":
        raise RuntimeError("Story Quality Loop re-audit result must be completed.")
    embedded = result.get("reaudit_artifact")
    if not isinstance(embedded, dict):
        raise RuntimeError("Story Quality Loop re-audit embedded artifact missing.")
    if result.get("source_repaired_story_sha256") != source["repaired_story_text_sha256"]:
        raise RuntimeError("Story Quality Loop re-audit source SHA mismatch.")
    source_id = (
        result.get("source_stage8_artifact_id")
        or result.get("source_story_artifact_id")
        or result.get("source_stage6_artifact_id")
    )
    if source_id != source["artifact_id"]:
        raise RuntimeError("Story Quality Loop re-audit source artifact mismatch.")
    if embedded.get("full_story_reaudited") is not True:
        raise RuntimeError("Story Quality Loop requires full-story re-audit.")
    if int(embedded.get("stable_span_count") or 0) != 199:
        raise RuntimeError("Story Quality Loop re-audit stable span count mismatch.")
    if result.get("source_story_mutated") is not False:
        raise RuntimeError("Story Quality Loop re-audit mutated source.")
    if result.get("automatic_retry_executed") is not False:
        raise RuntimeError("Story Quality Loop automatic retry must remain disabled.")
    if envelope.get("result_status") != "reaudit_completed":
        raise RuntimeError("Story Quality Loop re-audit envelope mismatch.")

    findings = list(embedded.get("findings") or [])
    body: dict[str, Any] = {
        "schema": "spineforge-v20-story-quality-reaudit-product.v1",
        "artifact_type": "IMMUTABLE_STORY_QUALITY_REAUDIT_RESULT",
        "stage": stage,
        "cycle_index": cycle_index,
        "status": "FROZEN",
        "immutable": True,
        "source_story_artifact_id": source["artifact_id"],
        "source_story_artifact_path": str(source_story_artifact_path),
        "source_story_artifact_sha256": _sha256_file(source_story_artifact_path),
        "source_story_text_sha256": source["repaired_story_text_sha256"],
        "embedded_reaudit_artifact_id": embedded["artifact_id"],
        "decision": embedded["decision"],
        "next_stage": embedded["next_stage"],
        "finding_count": len(findings),
        "findings": findings,
        "full_story_reaudited": True,
        "stable_span_count": 199,
        "result_path": str(result_path),
        "result_sha256": _sha256_file(result_path),
        "envelope_path": str(envelope_path),
        "envelope_sha256": _sha256_file(envelope_path),
        "usage_rollup": result["reaudit_usage_rollup"],
        "source_story_mutated": False,
        "automatic_retry_executed": False,
    }
    body["artifact_id"] = _artifact_id(body, "story-quality-reaudit")
    return body


def _span_offsets(
    *,
    story: str,
    repaired_segments: list[dict[str, Any]],
) -> dict[str, tuple[int, int]]:
    offsets: dict[str, tuple[int, int]] = {}
    cursor = 0
    for row in repaired_segments:
        span_id = str(row["span_id"])
        text = str(row["repaired_text"])
        start = story.find(text, cursor)
        if start < 0:
            raise RuntimeError(f"Story Quality Loop cannot bind source span: {span_id}")
        end = start + len(text)
        offsets[span_id] = (start, end)
        cursor = end
    if len(offsets) != 199:
        raise RuntimeError("Story Quality Loop requires 199 source offsets.")
    return offsets


def build_local_repair_handoff(
    *,
    reaudit_product_path: Path,
    source_story_artifact_path: Path,
    stage: int,
    repair_cycle_index: int,
    paid_attempt_index: int,
) -> dict[str, Any]:
    product = json.loads(reaudit_product_path.read_text(encoding="utf-8"))
    source_bundle = _load_story_artifact(source_story_artifact_path)
    source = source_bundle["artifact"]
    story = source_bundle["story"]

    if product.get("schema") != "spineforge-v20-story-quality-reaudit-product.v1":
        raise RuntimeError("Story Quality Loop re-audit product schema mismatch.")
    if product.get("status") != "FROZEN" or product.get("immutable") is not True:
        raise RuntimeError("Story Quality Loop re-audit product must be immutable.")
    if product.get("source_story_artifact_id") != source["artifact_id"]:
        raise RuntimeError("Story Quality Loop repair source lineage mismatch.")
    if product.get("source_story_text_sha256") != source["repaired_story_text_sha256"]:
        raise RuntimeError("Story Quality Loop repair story SHA lineage mismatch.")
    if product.get("decision") != "LOCAL_REPAIR_REQUIRED":
        raise RuntimeError("Story Quality Loop repair requires LOCAL_REPAIR_REQUIRED.")
    if product.get("next_stage") != "STORY_LOCAL_REPAIR":
        raise RuntimeError("Story Quality Loop repair next-stage mismatch.")

    findings = list(product.get("findings") or [])
    if not findings:
        raise RuntimeError("Story Quality Loop repair requires findings.")
    if any(str(row.get("repair_scope")) != "LOCAL_REPAIR" for row in findings):
        raise RuntimeError("Story Quality Loop generic repair forbids non-local findings.")

    segments = list(source["repaired_segments"])
    by_id = {str(row["span_id"]): row for row in segments}
    order = {str(row["span_id"]): i for i, row in enumerate(segments)}
    offsets = _span_offsets(story=story, repaired_segments=segments)

    target_to_findings: dict[str, list[int]] = {}
    normalized_findings: list[dict[str, Any]] = []
    for index, finding in enumerate(findings):
        span_ids = [str(x) for x in (finding.get("span_ids") or [])]
        if not span_ids or any(span_id not in by_id for span_id in span_ids):
            raise RuntimeError(f"Story Quality Loop finding {index} has invalid spans.")
        for span_id in span_ids:
            target_to_findings.setdefault(span_id, []).append(index)
        normalized_findings.append({
            "finding_index": index,
            "family": str(finding["family"]),
            "severity": str(finding["severity"]),
            "repair_scope": "LOCAL_REPAIR",
            "span_ids": span_ids,
            "exact_text": str(finding.get("exact_text") or ""),
            "reason": str(finding["reason"]),
        })

    allowed_ids = sorted(target_to_findings, key=lambda sid: order[sid])
    targets = []
    for span_id in allowed_ids:
        row = by_id[span_id]
        start, end = offsets[span_id]
        targets.append({
            "span_id": span_id,
            "paragraph_id": row["paragraph_id"],
            "paragraph_index": row["paragraph_index"],
            "char_start": start,
            "char_end": end,
            "source_text": row["repaired_text"],
            "finding_indexes": target_to_findings[span_id],
        })

    body: dict[str, Any] = {
        "schema": "spineforge-v20-story-quality-repair-handoff.v1",
        "artifact_type": "IMMUTABLE_STORY_QUALITY_LOCAL_REPAIR_INPUT",
        "stage": stage,
        "repair_cycle_index": repair_cycle_index,
        "paid_attempt_index": paid_attempt_index,
        "status": "READY_NOT_AUTHORIZED",
        "immutable": True,
        "source_reaudit_product_artifact_id": product["artifact_id"],
        "source_reaudit_product_path": str(reaudit_product_path),
        "source_reaudit_product_sha256": _sha256_file(reaudit_product_path),
        "source_reaudit_artifact_id": product["embedded_reaudit_artifact_id"],
        "source_story_artifact_id": source["artifact_id"],
        "source_story_artifact_path": str(source_story_artifact_path),
        "source_story_artifact_sha256": _sha256_file(source_story_artifact_path),
        "source_story_path": source["repaired_story_path"],
        "source_story_sha256": source["repaired_story_text_sha256"],
        "source_story_file_sha256": source["repaired_story_file_sha256"],
        "finding_count": len(normalized_findings),
        "findings": normalized_findings,
        "allowed_edit_span_count": len(allowed_ids),
        "allowed_edit_span_ids": allowed_ids,
        "target_segments": targets,
        "repair_policy": {
            "repair_scope": "LOCAL_REPAIR",
            "source_story_mutation_forbidden": True,
            "unreferenced_span_edit_forbidden": True,
            "structural_rewrite_forbidden": True,
            "premise_change_forbidden": True,
            "canon_change_forbidden": True,
            "new_plot_event_forbidden": True,
            "all_findings_must_be_addressed": True,
            "patches_only": True,
            "no_change_disposition_allowed": True,
            "no_change_requires_mandatory_reaudit": True,
        },
        "repair_model": REPAIR_MODEL,
        "automatic_retry_enabled": False,
        "automatic_repair_loop_enabled": False,
        "paid_execution_authorized": False,
        "next_stage_after_success": "STORY_REAUDIT",
    }
    body["artifact_id"] = _artifact_id(body, "story-quality-repair-handoff")
    return body


def execute_local_repair(
    *,
    api_key: str,
    handoff: dict[str, Any],
    call_fn: JsonCall | None = None,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    if handoff.get("schema") != "spineforge-v20-story-quality-repair-handoff.v1":
        raise RuntimeError("Story Quality Loop repair handoff schema mismatch.")
    if handoff.get("status") != "READY_NOT_AUTHORIZED":
        raise RuntimeError("Story Quality Loop repair handoff status mismatch.")
    if handoff.get("paid_execution_authorized") is not False:
        raise RuntimeError("Story Quality Loop immutable handoff must be non-authorizing.")

    source_story_path = Path(str(handoff["source_story_path"]))
    source_story = _canonical_story(source_story_path)
    if _sha256_text(source_story) != handoff["source_story_sha256"]:
        raise RuntimeError("Story Quality Loop repair source story SHA mismatch.")
    if _sha256_file(source_story_path) != handoff["source_story_file_sha256"]:
        raise RuntimeError("Story Quality Loop repair source file SHA mismatch.")

    payload = {
        "task": "repair_story_quality_findings_locally",
        "source_reaudit_product_artifact_id": handoff[
            "source_reaudit_product_artifact_id"
        ],
        "source_story_sha256": handoff["source_story_sha256"],
        "findings": handoff["findings"],
        "allowed_edit_span_ids": handoff["allowed_edit_span_ids"],
        "target_segments": handoff["target_segments"],
        "repair_policy": handoff["repair_policy"],
    }
    fn = call_fn or call_strict_json_once
    prompt = system_prompt or REPAIR_PROMPT.read_text(encoding="utf-8").strip()
    started = time.perf_counter()
    raw, body, request, failures = fn(
        api_key=api_key,
        model=REPAIR_MODEL,
        system_prompt=prompt,
        user_prompt=json.dumps(payload, ensure_ascii=False),
        temperature=0.0,
        max_tokens=8000,
        seed=None,
        request_class=REPAIR_REQUEST_CLASS,
        schema_name=REPAIR_SCHEMA_NAME,
        schema=REPAIR_RESPONSE_SCHEMA,
    )
    latency = round(time.perf_counter() - started, 3)
    model_call = normalize_model_call(
        stage="spineforge_v20_story_quality_local_repair",
        model=REPAIR_MODEL,
        provider=runtime_profile_identity(REPAIR_MODEL).get("provider"),
        raw_usage=body.get("usage") or {},
        cost=parse_cost(body).model_dump(mode="json"),
        latency_seconds=latency,
    )
    usage = rollup_model_calls([model_call])
    try:
        normalized = _normalize_repair_payload(raw=raw, handoff=handoff)
    except Exception as exc:
        setattr(exc, "trace", {
            "phase": "post_provider_story_quality_repair_validation",
            "raw_response": raw,
            "request": request,
            "transport_failures": failures,
            "repair_usage_rollup": usage,
        })
        raise

    repaired_story, changed_ids = _apply_patches(
        source_story=source_story,
        handoff=handoff,
        patches=normalized["patches"],
    )
    return {
        "schema": "spineforge-v20-story-quality-repair-execution.v1",
        "status": "repair_generated",
        "stage": int(handoff["stage"]),
        "repair_cycle_index": int(handoff["repair_cycle_index"]),
        "paid_attempt_index": int(handoff["paid_attempt_index"]),
        "source_reaudit_product_artifact_id": handoff[
            "source_reaudit_product_artifact_id"
        ],
        "source_reaudit_artifact_id": handoff["source_reaudit_artifact_id"],
        "source_story_artifact_id": handoff["source_story_artifact_id"],
        "source_story_sha256": handoff["source_story_sha256"],
        "repair_model": REPAIR_MODEL,
        "patches": normalized["patches"],
        "no_change_resolutions": normalized["no_change_resolutions"],
        "changed_span_ids": changed_ids,
        "patch_count": len(normalized["patches"]),
        "no_change_resolution_count": len(normalized["no_change_resolutions"]),
        "repaired_story": repaired_story,
        "repaired_story_sha256": _sha256_text(repaired_story),
        "source_story_mutated": False,
        "all_findings_addressed": True,
        "changed_spans_subset_of_allowed": set(changed_ids).issubset(
            set(handoff["allowed_edit_span_ids"])
        ),
        "repair_usage_rollup": usage,
        "incremental_cost_usd": usage["totals"]["cost_usd"],
        "incremental_latency_seconds": usage["totals"]["latency_seconds"],
        "automatic_retry_executed": False,
        "reaudit_executed": False,
        "translation_executed": False,
        "state_commit_executed": False,
        "next_stage": "STORY_REAUDIT",
        "transport_failures": failures,
        "request": {
            "temperature": request.get("temperature"),
            "max_tokens": request.get("max_tokens"),
            "response_format": request.get("response_format"),
        },
    }


def build_repair_product(
    *,
    result_path: Path,
    story_path: Path,
    envelope_path: Path,
    source_story_artifact_path: Path,
    source_reaudit_product_path: Path,
) -> dict[str, Any]:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    source_bundle = _load_story_artifact(source_story_artifact_path)
    source = source_bundle["artifact"]
    reaudit_product = json.loads(source_reaudit_product_path.read_text(encoding="utf-8"))
    if result.get("schema") != "spineforge-v20-story-quality-repair-execution.v1":
        raise RuntimeError("Story Quality Loop repair result schema mismatch.")
    if result.get("status") != "repair_generated":
        raise RuntimeError("Story Quality Loop repair result status mismatch.")
    if result.get("source_story_artifact_id") != source["artifact_id"]:
        raise RuntimeError("Story Quality Loop repair product source mismatch.")
    if result.get("source_reaudit_product_artifact_id") != reaudit_product["artifact_id"]:
        raise RuntimeError("Story Quality Loop repair/re-audit lineage mismatch.")

    story = _canonical_story(story_path)
    if story != result.get("repaired_story"):
        raise RuntimeError("Story Quality Loop repaired story file/content mismatch.")
    if _sha256_text(story) != result.get("repaired_story_sha256"):
        raise RuntimeError("Story Quality Loop repaired story SHA mismatch.")

    patches = list(result.get("patches") or [])
    no_change = list(result.get("no_change_resolutions") or [])
    patch_by_id = {str(row["span_id"]): row for row in patches}
    no_change_by_id = {str(row["span_id"]): row for row in no_change}
    prior_segments = list(source["repaired_segments"])
    repaired_segments = []
    for row in prior_segments:
        sid = str(row["span_id"])
        source_text = str(row["repaired_text"])
        if sid in patch_by_id:
            repaired_text = str(patch_by_id[sid]["replacement_text"])
            disposition = "PATCH"
            indexes = list(patch_by_id[sid].get("addresses_finding_indexes") or [])
        elif sid in no_change_by_id:
            repaired_text = source_text
            disposition = "NO_CHANGE"
            indexes = list(no_change_by_id[sid].get("addresses_finding_indexes") or [])
        else:
            repaired_text = source_text
            disposition = "UNCHANGED"
            indexes = []
        repaired_segments.append({
            "span_id": sid,
            "paragraph_id": row["paragraph_id"],
            "paragraph_index": row["paragraph_index"],
            "source_text": source_text,
            "repaired_text": repaired_text,
            "disposition": disposition,
            "addresses_finding_indexes": indexes,
        })

    body: dict[str, Any] = {
        "schema": "spineforge-v20-story-quality-story-artifact.v1",
        "artifact_type": "IMMUTABLE_STORY_QUALITY_REPAIRED_STORY",
        "stage": int(result["stage"]),
        "repair_cycle_index": int(result["repair_cycle_index"]),
        "status": "FROZEN",
        "immutable": True,
        "source_story_artifact_id": source["artifact_id"],
        "source_story_artifact_path": str(source_story_artifact_path),
        "source_reaudit_product_artifact_id": reaudit_product["artifact_id"],
        "repaired_story_path": str(story_path),
        "repaired_story_text_sha256": result["repaired_story_sha256"],
        "repaired_story_file_sha256": _sha256_file(story_path),
        "result_path": str(result_path),
        "result_sha256": _sha256_file(result_path),
        "envelope_path": str(envelope_path),
        "envelope_sha256": _sha256_file(envelope_path),
        "patch_count": len(patches),
        "no_change_resolution_count": len(no_change),
        "changed_span_ids": list(result["changed_span_ids"]),
        "no_change_span_ids": [
            str(row["span_id"]) for row in no_change
        ],
        "stable_span_count": 199,
        "repaired_segments": repaired_segments,
        "repair_model": result["repair_model"],
        "repair_usage_rollup": result["repair_usage_rollup"],
        "mandatory_full_reaudit": True,
        "source_story_mutated": False,
        "next_stage": "STORY_REAUDIT",
    }
    body["artifact_id"] = _artifact_id(body, "story-quality-story")
    return body


def build_reaudit_handoff(
    *,
    story_artifact_path: Path,
    stage: int,
    cycle_index: int,
    writer_handoff_path: Path = WRITER_HANDOFF_PATH,
) -> dict[str, Any]:
    source = _load_story_artifact(story_artifact_path)["artifact"]
    writer = json.loads(writer_handoff_path.read_text(encoding="utf-8"))
    body: dict[str, Any] = {
        "schema": "spineforge-v20-story-quality-reaudit-handoff.v1",
        "artifact_type": "IMMUTABLE_STORY_QUALITY_REAUDIT_INPUT",
        "stage": stage,
        "cycle_index": cycle_index,
        "status": "READY_NOT_AUTHORIZED",
        "immutable": True,
        "source_story_artifact_id": source["artifact_id"],
        "source_story_artifact_path": str(story_artifact_path),
        "source_story_artifact_sha256": _sha256_file(story_artifact_path),
        "repaired_story_path": source["repaired_story_path"],
        "repaired_story_text_sha256": source["repaired_story_text_sha256"],
        "repaired_story_file_sha256": source["repaired_story_file_sha256"],
        "stable_span_count": 199,
        "changed_span_ids": source["changed_span_ids"],
        "no_change_span_ids": source["no_change_span_ids"],
        "reader": {"exact_age": writer["exact_age"]},
        "context_pack_id": writer["context_pack_id"],
        "context_fingerprint": writer["context_fingerprint"],
        "spine_hash": writer["spine_hash"],
        "approval_id": writer["approval_id"],
        "reaudit_policy": {
            "full_story_required": True,
            "all_199_stable_spans_required": True,
            "changed_spans_only_forbidden": True,
            "automatic_retry_enabled": False,
            "automatic_repair_loop_enabled": False,
            "translation_forbidden": True,
            "state_commit_forbidden": True,
        },
        "paid_execution_authorized": False,
        "next_stage_on_accept": "ENGLISH_MASTER_SEAL",
        "next_stage_on_local_repair": "STORY_LOCAL_REPAIR",
        "next_stage_on_structural_or_replan": "STOP",
    }
    body["artifact_id"] = _artifact_id(body, "story-quality-reaudit-handoff")
    return body


def execute_reaudit(
    *,
    api_key: str,
    handoff: dict[str, Any],
    primary_call_fn: JsonCall | None = None,
    secondary_call_fn: JsonCall | None = None,
    primary_prompt: str | None = None,
    secondary_prompt: str | None = None,
) -> dict[str, Any]:
    if handoff.get("schema") != "spineforge-v20-story-quality-reaudit-handoff.v1":
        raise RuntimeError("Story Quality Loop re-audit handoff schema mismatch.")
    if handoff.get("status") != "READY_NOT_AUTHORIZED":
        raise RuntimeError("Story Quality Loop re-audit handoff status mismatch.")
    if handoff.get("paid_execution_authorized") is not False:
        raise RuntimeError("Story Quality Loop immutable re-audit handoff must be non-authorizing.")

    source_bundle = _load_story_artifact(Path(handoff["source_story_artifact_path"]))
    source = source_bundle["artifact"]
    if source["artifact_id"] != handoff["source_story_artifact_id"]:
        raise RuntimeError("Story Quality Loop re-audit source artifact mismatch.")

    writer_manifest = json.loads(WRITER_MANIFEST_PATH.read_text(encoding="utf-8"))
    authority = _load_authority(
        writer_manifest=writer_manifest,
        handoff_path=WRITER_HANDOFF_PATH,
    )
    for key in ("context_pack_id", "context_fingerprint", "spine_hash", "approval_id"):
        if authority[key] != handoff[key]:
            raise RuntimeError(f"Story Quality Loop authority mismatch: {key}")

    segments = _story_segments(source)
    projection = _build_audit_authority_projection(authority)
    source_identity = {
        "artifact_id": source["artifact_id"],
        "story_sha256": source["repaired_story_text_sha256"],
        "stage": source["stage"],
    }
    primary_payload = {
        "task": "reaudit_story_quality_loop_frozen_story",
        "required_evaluation_families": list(
            PRIMARY_AUDIT_CANONICAL_FAMILY_ORDER
        ),
        "required_evaluation_family_count": len(
            PRIMARY_AUDIT_CANONICAL_FAMILY_ORDER
        ),
        "source_artifact": source_identity,
        "audit_authority_projection": projection["projection"],
        "audit_authority_projection_sha256": projection["sha256"],
        "approved_narrative_spine": authority["approved_narrative_spine"],
        "story_segments": segments,
        "repair_lineage": {
            "changed_span_ids": source["changed_span_ids"],
            "no_change_span_ids": source["no_change_span_ids"],
        },
    }
    secondary_payload = {
        "task": "contrastive_edit_story_quality_loop_frozen_story",
        "source_artifact": source_identity,
        "reader": {"exact_age": authority["reader_profile"].get("exact_age")},
        "story_segments": segments,
    }
    expected_ids = [str(row["id"]) for row in segments]
    text_by_id = {str(row["id"]): str(row["text"]) for row in segments}
    primary, primary_meta = _call_auditor(
        fn=primary_call_fn or call_strict_json_once,
        api_key=api_key,
        model=PRIMARY_MODEL,
        prompt=primary_prompt or PRIMARY_PROMPT.read_text(encoding="utf-8").strip(),
        payload=primary_payload,
        stage="spineforge_v20_story_quality_reaudit_primary",
        schema_name=AUDIT_SCHEMA_NAME,
        schema=AUDIT_RESPONSE_SCHEMA,
    )
    secondary, secondary_meta = _call_auditor(
        fn=secondary_call_fn or call_strict_json_once,
        api_key=api_key,
        model=SECONDARY_MODEL,
        prompt=secondary_prompt or SECONDARY_PROMPT.read_text(encoding="utf-8").strip(),
        payload=secondary_payload,
        stage="spineforge_v20_story_quality_reaudit_language_specialist",
        schema_name=SECONDARY_AUDIT_SCHEMA_NAME,
        schema=SECONDARY_AUDIT_RESPONSE_SCHEMA,
        normalize_fn=lambda raw: _normalize_language_specialist_payload(
            raw=raw,
            expected_span_ids=expected_ids,
            story_text_by_id=text_by_id,
        ),
    )
    usage = rollup_model_calls([
        primary_meta["model_call"],
        secondary_meta["model_call"],
    ])
    merged = _merge_findings(primary["findings"], secondary["findings"])
    try:
        merged, corrections = _repair_finding_locators(
            findings=merged,
            story_segments=segments,
            allow_valid_span_quote_normalization=True,
        )
    except Exception as exc:
        setattr(exc, "partial_usage_rollup", usage)
        setattr(exc, "trace", {
            "stage": "spineforge_v20_story_quality_reaudit_post_provider_locator",
            "model_calls": [
                primary_meta["model_call"],
                secondary_meta["model_call"],
            ],
        })
        raise
    decision, next_stage = _decision_from_findings(merged)
    embedded: dict[str, Any] = {
        "schema": "spineforge-v20-story-quality-reaudit-artifact.v1",
        "artifact_type": "IMMUTABLE_STORY_QUALITY_REAUDIT",
        "stage": int(handoff["stage"]),
        "cycle_index": int(handoff["cycle_index"]),
        "source_story_artifact_id": source["artifact_id"],
        "source_repaired_story_sha256": source["repaired_story_text_sha256"],
        "context_pack_id": handoff["context_pack_id"],
        "context_fingerprint": handoff["context_fingerprint"],
        "spine_hash": handoff["spine_hash"],
        "approval_id": handoff["approval_id"],
        "input_verified": True,
        "source_story_mutated": False,
        "full_story_reaudited": True,
        "stable_span_count": 199,
        "decision": decision,
        "next_stage": next_stage,
        "findings": merged,
    }
    embedded["artifact_id"] = _artifact_id(embedded, "story-quality-reaudit-result")
    return {
        "schema": "spineforge-v20-story-quality-reaudit-execution.v1",
        "status": "reaudit_completed",
        "stage": int(handoff["stage"]),
        "cycle_index": int(handoff["cycle_index"]),
        "source_story_artifact_id": source["artifact_id"],
        "source_repaired_story_sha256": source["repaired_story_text_sha256"],
        "reaudit_artifact": embedded,
        "secondary_language_sentence_scan": secondary["language_sentence_scan"],
        "secondary_language_sentence_scan_count": len(
            secondary["language_sentence_scan"]
        ),
        "locator_corrections": corrections,
        "reaudit_usage_rollup": usage,
        "incremental_cost_usd": usage["totals"]["cost_usd"],
        "incremental_latency_seconds": usage["totals"]["latency_seconds"],
        "source_story_mutated": False,
        "automatic_retry_executed": False,
        "repair_executed": False,
        "translation_executed": False,
        "state_commit_executed": False,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
