from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable



AUDIT_FAMILIES = {
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
}
SEVERITIES = {"minor", "moderate", "serious", "critical"}
REPAIR_SCOPES = {"NO_REPAIR", "LOCAL_REPAIR", "STRUCTURAL_REPAIR", "REPLAN"}

AuditCall = Callable[..., dict[str, Any]]


def _segment_story(text: str) -> list[dict[str, Any]]:
    normalized = re.sub(r"\r\n?", "\n", text or "").strip()
    if not normalized:
        return []
    segments: list[dict[str, Any]] = []
    sentence_index = 1
    paragraph_index = 1
    for paragraph_match in re.finditer(r"[^\n]+", normalized):
        raw_paragraph = paragraph_match.group(0)
        if not raw_paragraph.strip():
            continue
        leading = len(raw_paragraph) - len(raw_paragraph.lstrip())
        trailing = len(raw_paragraph) - len(raw_paragraph.rstrip())
        paragraph = raw_paragraph.strip()
        paragraph_start = paragraph_match.start() + leading
        paragraph_end = paragraph_match.end() - trailing
        paragraph_id = f"P{paragraph_index:03d}"
        sentence_start = 0
        for boundary in re.finditer(r"(?<=[.!?…])\s+", paragraph):
            raw_sentence = paragraph[sentence_start:boundary.start()]
            if raw_sentence.strip():
                left = len(raw_sentence) - len(raw_sentence.lstrip())
                right = len(raw_sentence) - len(raw_sentence.rstrip())
                segments.append({
                    "id": f"S{sentence_index:03d}",
                    "paragraph_id": paragraph_id,
                    "paragraph_index": paragraph_index,
                    "text": raw_sentence.strip(),
                    "char_start": paragraph_start + sentence_start + left,
                    "char_end": paragraph_start + boundary.start() - right,
                })
                sentence_index += 1
            sentence_start = boundary.end()
        raw_sentence = paragraph[sentence_start:]
        if raw_sentence.strip():
            left = len(raw_sentence) - len(raw_sentence.lstrip())
            right = len(raw_sentence) - len(raw_sentence.rstrip())
            segments.append({
                "id": f"S{sentence_index:03d}",
                "paragraph_id": paragraph_id,
                "paragraph_index": paragraph_index,
                "text": raw_sentence.strip(),
                "char_start": paragraph_start + sentence_start + left,
                "char_end": paragraph_end - right,
            })
            sentence_index += 1
        paragraph_index += 1
    return segments


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_repo_path(repo_root: Path, rel: str) -> Path:
    root = repo_root.resolve()
    path = (root / rel).resolve()
    if root != path and root not in path.parents:
        raise RuntimeError(f"Artifact path escapes repository root: {rel}")
    return path


def _artifact_id(payload: dict[str, Any], prefix: str) -> str:
    digest = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return f"{prefix}:{digest}"


def load_verified_writer_story_artifact(
    *,
    manifest_path: Path,
    repo_root: Path = Path("."),
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "spineforge-v20-writer-story-artifact.v1":
        raise RuntimeError("Writer story artifact schema mismatch.")
    if manifest.get("artifact_type") != "IMMUTABLE_ENGLISH_WRITER_STORY":
        raise RuntimeError("Writer story artifact type mismatch.")
    if manifest.get("stage") != 4 or manifest.get("status") != "FROZEN":
        raise RuntimeError("Writer story artifact is not a frozen Stage 4 product.")
    if manifest.get("immutable") is not True:
        raise RuntimeError("Writer story artifact must be immutable.")
    if manifest.get("next_stage") != "STORY_AUDIT":
        raise RuntimeError("Writer story artifact next-stage binding mismatch.")

    story_path = _safe_repo_path(repo_root, str(manifest["story_path"]))
    result_path = _safe_repo_path(repo_root, str(manifest["result_path"]))
    envelope_path = _safe_repo_path(repo_root, str(manifest["envelope_path"]))

    expected = {
        story_path: str(manifest["story_sha256"]),
        result_path: str(manifest["result_sha256"]),
        envelope_path: str(manifest["envelope_sha256"]),
    }
    for path, wanted in expected.items():
        if not path.is_file():
            raise RuntimeError(f"Artifact dependency missing: {path}")
        actual = _sha256_file(path)
        if actual != wanted:
            raise RuntimeError(
                f"Artifact dependency hash mismatch: {path.name}: {actual} != {wanted}"
            )

    story = story_path.read_text(encoding="utf-8")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))

    if result.get("status") != "writer_generated":
        raise RuntimeError("Writer result is not a successful generated story.")
    if envelope.get("result_status") != "writer_generated":
        raise RuntimeError("Writer envelope does not record a successful story.")
    if story.rstrip("\n") != str(result.get("story") or "").rstrip("\n"):
        raise RuntimeError("Story file content differs from Writer result story.")

    lineage_keys = (
        "approval_id",
        "context_fingerprint",
        "spine_hash",
        "writer_model",
    )
    for key in lineage_keys:
        if manifest.get(key) != result.get(key):
            raise RuntimeError(f"Writer manifest/result lineage mismatch: {key}")
        if key in envelope and manifest.get(key) != envelope.get(key):
            raise RuntimeError(f"Writer manifest/envelope lineage mismatch: {key}")

    if manifest.get("context_pack_id") != result.get("context_pack_id"):
        raise RuntimeError("Writer manifest/result ContextPack id mismatch.")
    source_run_id = int(manifest.get("source_run_id"))
    if source_run_id <= 0:
        raise RuntimeError("Writer artifact source run id is invalid.")
    expected_run_dir = str(source_run_id)
    for rel_key in ("story_path", "result_path", "envelope_path"):
        rel_parts = Path(str(manifest[rel_key])).parts
        if expected_run_dir not in rel_parts:
            raise RuntimeError(f"Writer artifact path/run lineage mismatch: {rel_key}")
    if int(manifest.get("attempt_index")) != int(envelope.get("attempt_index")):
        raise RuntimeError("Writer artifact attempt index mismatch.")
    if int(manifest.get("word_count")) != int(
        (result.get("deterministic_checks") or {}).get("word_count")
    ):
        raise RuntimeError("Writer artifact word-count lineage mismatch.")

    identity_payload = {
        "source_run_id": int(manifest["source_run_id"]),
        "story_sha256": str(manifest["story_sha256"]),
        "context_fingerprint": str(manifest["context_fingerprint"]),
        "spine_hash": str(manifest["spine_hash"]),
        "approval_id": str(manifest["approval_id"]),
    }
    expected_id = _artifact_id(identity_payload, "writer-story")
    if manifest.get("artifact_id") != expected_id:
        raise RuntimeError("Writer story artifact id mismatch.")

    return {
        "manifest": manifest,
        "story": story.rstrip("\n"),
        "result": result,
        "envelope": envelope,
        "input_verified": True,
    }


def _validate_finding(
    *,
    finding: dict[str, Any],
    segments: list[dict[str, Any]],
) -> dict[str, Any]:
    family = str(finding.get("family") or "")
    severity = str(finding.get("severity") or "").lower()
    scope = str(finding.get("repair_scope") or "").upper()
    reason = str(finding.get("reason") or "").strip()
    span_ids = list(finding.get("span_ids") or [])
    exact_text = str(finding.get("exact_text") or "")

    if family not in AUDIT_FAMILIES:
        raise RuntimeError(f"Unsupported Story Audit family: {family}")
    if severity not in SEVERITIES:
        raise RuntimeError(f"Unsupported Story Audit severity: {severity}")
    if scope not in REPAIR_SCOPES:
        raise RuntimeError(f"Unsupported Story Audit repair scope: {scope}")
    if not reason:
        raise RuntimeError("Story Audit finding reason is required.")

    by_id = {row["id"]: row for row in segments}
    if scope == "LOCAL_REPAIR":
        if not span_ids:
            raise RuntimeError("LOCAL_REPAIR finding requires source span_ids.")
        if not exact_text:
            raise RuntimeError("LOCAL_REPAIR finding requires exact_text.")
        missing = [item for item in span_ids if item not in by_id]
        if missing:
            raise RuntimeError("Story Audit references unknown span ids: " + ", ".join(missing))
        source_window = " ".join(by_id[item]["text"] for item in span_ids)
        if exact_text not in source_window:
            raise RuntimeError("LOCAL_REPAIR exact_text is not present in referenced source span.")
    else:
        if span_ids:
            missing = [item for item in span_ids if item not in by_id]
            if missing:
                raise RuntimeError(
                    "Story Audit references unknown span ids: " + ", ".join(missing)
                )

    return {
        "family": family,
        "severity": severity,
        "repair_scope": scope,
        "span_ids": span_ids,
        "exact_text": exact_text,
        "reason": reason,
    }


def build_story_audit_source(
    *,
    manifest_path: Path,
    repo_root: Path = Path("."),
) -> dict[str, Any]:
    verified = load_verified_writer_story_artifact(
        manifest_path=manifest_path,
        repo_root=repo_root,
    )
    manifest = verified["manifest"]
    story = verified["story"]
    segments = _segment_story(story)
    payload = {
        "schema": "spineforge-v20-story-audit-source.v1",
        "stage": 5,
        "source_artifact_id": manifest["artifact_id"],
        "source_story_sha256": manifest["story_sha256"],
        "source_run_id": manifest["source_run_id"],
        "context_pack_id": manifest["context_pack_id"],
        "context_fingerprint": manifest["context_fingerprint"],
        "spine_hash": manifest["spine_hash"],
        "approval_id": manifest["approval_id"],
        "writer_model": manifest["writer_model"],
        "word_count": manifest["word_count"],
        "story_segments": segments,
    }
    payload["audit_source_id"] = _artifact_id(payload, "story-audit-source")
    return payload


def run_story_audit_once(
    *,
    manifest_path: Path,
    audit_call_fn: AuditCall,
    repo_root: Path = Path("."),
) -> dict[str, Any]:
    verified = load_verified_writer_story_artifact(
        manifest_path=manifest_path,
        repo_root=repo_root,
    )
    source = build_story_audit_source(
        manifest_path=manifest_path,
        repo_root=repo_root,
    )
    story = verified["story"]
    raw = audit_call_fn(
        story=story,
        audit_source=source,
        source_manifest=verified["manifest"],
    )
    if not isinstance(raw, dict):
        raise RuntimeError("Story Audit model output must be an object.")
    findings_raw = raw.get("findings") or []
    if not isinstance(findings_raw, list):
        raise RuntimeError("Story Audit findings must be a list.")

    segments = source["story_segments"]
    findings = [
        _validate_finding(finding=row, segments=segments)
        for row in findings_raw
    ]

    scopes = {row["repair_scope"] for row in findings}
    if "REPLAN" in scopes:
        decision = "REPLAN_REQUIRED"
        next_stage = "STOP"
    elif "STRUCTURAL_REPAIR" in scopes:
        decision = "STRUCTURAL_REPAIR_REQUIRED"
        next_stage = "STOP"
    elif "LOCAL_REPAIR" in scopes:
        decision = "LOCAL_REPAIR_REQUIRED"
        next_stage = "STORY_LOCAL_REPAIR"
    else:
        decision = "ACCEPT"
        next_stage = "ENGLISH_MASTER_SEAL"

    artifact_body = {
        "schema": "spineforge-v20-story-audit-artifact.v1",
        "artifact_type": "IMMUTABLE_STORY_AUDIT",
        "stage": 5,
        "source_artifact_id": verified["manifest"]["artifact_id"],
        "source_story_sha256": verified["manifest"]["story_sha256"],
        "audit_source_id": source["audit_source_id"],
        "context_pack_id": verified["manifest"]["context_pack_id"],
        "context_fingerprint": verified["manifest"]["context_fingerprint"],
        "spine_hash": verified["manifest"]["spine_hash"],
        "input_verified": True,
        "source_story_mutated": False,
        "decision": decision,
        "next_stage": next_stage,
        "findings": findings,
        "summary": str(raw.get("summary") or "").strip(),
    }
    artifact_body["artifact_id"] = _artifact_id(artifact_body, "story-audit")
    return artifact_body
