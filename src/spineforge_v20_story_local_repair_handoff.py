from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.spineforge_v20_story_audit_artifact import (
    build_story_audit_source,
    load_verified_writer_story_artifact,
)


DEFAULT_WRITER_MANIFEST = Path(
    "evidence/spineforge-v20-writer-product/36965340665/writer-story-artifact.json"
)
DEFAULT_AUDIT_RESULT = Path(
    "evidence/spineforge-v20-paid-story-audit/36990160527/"
    "age12-island-v20-story-audit8-result.json"
)
DEFAULT_QUALIFICATION_REPORT = Path(
    "evidence/spineforge-v20-paid-story-audit/36990160527/qualification-report.json"
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_id(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "story-local-repair-handoff:" + hashlib.sha256(encoded).hexdigest()


def build_story_local_repair_handoff(
    *,
    writer_manifest_path: Path = DEFAULT_WRITER_MANIFEST,
    audit_result_path: Path = DEFAULT_AUDIT_RESULT,
    qualification_report_path: Path = DEFAULT_QUALIFICATION_REPORT,
    repo_root: Path = Path("."),
) -> dict[str, Any]:
    verified = load_verified_writer_story_artifact(
        manifest_path=writer_manifest_path,
        repo_root=repo_root,
    )
    manifest = verified["manifest"]

    audit_result = json.loads(audit_result_path.read_text(encoding="utf-8"))
    qualification = json.loads(
        qualification_report_path.read_text(encoding="utf-8")
    )

    if audit_result.get("status") != "audit_completed":
        raise RuntimeError("Stage 6 handoff requires a completed Stage 5 audit.")
    artifact = audit_result.get("audit_artifact")
    if not isinstance(artifact, dict):
        raise RuntimeError("Stage 6 handoff requires a Stage 5 audit artifact.")
    if artifact.get("schema") != "spineforge-v20-story-audit-artifact.v1":
        raise RuntimeError("Stage 5 audit artifact schema mismatch.")
    if artifact.get("decision") != "LOCAL_REPAIR_REQUIRED":
        raise RuntimeError("Stage 6 handoff requires LOCAL_REPAIR_REQUIRED.")
    if artifact.get("next_stage") != "STORY_LOCAL_REPAIR":
        raise RuntimeError("Stage 5 next-stage binding mismatch.")
    if qualification.get("qualification_pass") is not True:
        raise RuntimeError("Stage 6 handoff requires qualified Stage 5 evidence.")
    if qualification.get("status") != "PASS":
        raise RuntimeError("Stage 5 qualification status is not PASS.")

    if artifact.get("source_artifact_id") != manifest["artifact_id"]:
        raise RuntimeError("Stage 5/Writer artifact lineage mismatch.")
    if artifact.get("source_story_sha256") != manifest["story_sha256"]:
        raise RuntimeError("Stage 5/Writer story SHA mismatch.")
    if audit_result.get("source_story_sha256") != manifest["story_sha256"]:
        raise RuntimeError("Audit result/Writer story SHA mismatch.")

    findings = artifact.get("findings")
    if not isinstance(findings, list) or not findings:
        raise RuntimeError("Stage 6 handoff requires non-empty findings.")
    if any(row.get("repair_scope") != "LOCAL_REPAIR" for row in findings):
        raise RuntimeError("Stage 6 handoff forbids non-local repair findings.")

    story_source = build_story_audit_source(
        manifest_path=writer_manifest_path,
        repo_root=repo_root,
    )
    segments = story_source["story_segments"]
    segment_by_id = {str(row["id"]): row for row in segments}
    order = {str(row["id"]): i for i, row in enumerate(segments)}

    target_to_findings: dict[str, list[int]] = {}
    normalized_findings: list[dict[str, Any]] = []
    for index, finding in enumerate(findings):
        span_ids = [str(x) for x in finding.get("span_ids") or []]
        if not span_ids:
            raise RuntimeError(f"Stage 6 finding {index} has no source spans.")
        if any(span_id not in segment_by_id for span_id in span_ids):
            raise RuntimeError(f"Stage 6 finding {index} references unknown span.")
        for span_id in span_ids:
            target_to_findings.setdefault(span_id, []).append(index)
        normalized_findings.append({
            "finding_index": index,
            "family": str(finding["family"]),
            "severity": str(finding["severity"]),
            "repair_scope": "LOCAL_REPAIR",
            "span_ids": span_ids,
            "exact_text": str(finding["exact_text"]),
            "reason": str(finding["reason"]),
        })

    allowed_ids = sorted(target_to_findings, key=lambda sid: order[sid])
    targets = []
    for span_id in allowed_ids:
        row = segment_by_id[span_id]
        targets.append({
            "span_id": span_id,
            "paragraph_id": row["paragraph_id"],
            "paragraph_index": row["paragraph_index"],
            "char_start": row["char_start"],
            "char_end": row["char_end"],
            "source_text": row["text"],
            "finding_indexes": target_to_findings[span_id],
        })

    payload: dict[str, Any] = {
        "schema": "spineforge-v20-story-local-repair-handoff.v1",
        "artifact_type": "IMMUTABLE_STAGE6_LOCAL_REPAIR_INPUT",
        "stage": 6,
        "status": "READY_NOT_AUTHORIZED",
        "immutable": True,
        "source_writer_artifact_id": manifest["artifact_id"],
        "source_story_sha256": manifest["story_sha256"],
        "source_story_path": manifest["story_path"],
        "source_writer_manifest_path": str(writer_manifest_path),
        "source_audit_artifact_id": artifact["artifact_id"],
        "source_audit_result_path": str(audit_result_path),
        "source_audit_result_sha256": _sha256_file(audit_result_path),
        "source_qualification_report_path": str(qualification_report_path),
        "source_qualification_report_sha256": _sha256_file(
            qualification_report_path
        ),
        "source_audit_decision": artifact["decision"],
        "source_audit_next_stage": artifact["next_stage"],
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
        },
        "repair_model": "anthropic/claude-sonnet-5.5",
        "repair_attempt_index": 1,
        "automatic_retry_enabled": False,
        "paid_execution_authorized": False,
        "output_contract": {
            "schema": "spineforge-v20-story-local-repair-artifact.v1",
            "source_story_remains_immutable": True,
            "changed_spans_must_be_subset_of_allowed_edit_span_ids": True,
            "next_stage": "STORY_REAUDIT",
        },
        "next_stage_after_success": "STORY_REAUDIT",
    }
    payload["artifact_id"] = _artifact_id(payload)
    return payload


def write_story_local_repair_handoff(
    *,
    output_path: Path,
    writer_manifest_path: Path = DEFAULT_WRITER_MANIFEST,
    audit_result_path: Path = DEFAULT_AUDIT_RESULT,
    qualification_report_path: Path = DEFAULT_QUALIFICATION_REPORT,
    repo_root: Path = Path("."),
) -> dict[str, Any]:
    handoff = build_story_local_repair_handoff(
        writer_manifest_path=writer_manifest_path,
        audit_result_path=audit_result_path,
        qualification_report_path=qualification_report_path,
        repo_root=repo_root,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(handoff, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return handoff
