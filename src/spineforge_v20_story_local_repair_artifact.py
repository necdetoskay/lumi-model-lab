from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from src.spineforge_v20_story_audit_artifact import build_story_audit_source


DEFAULT_RESULT = Path(
    "evidence/spineforge-v20-paid-story-local-repair/37006087948/"
    "age12-island-v20-story-local-repair2-result.json"
)
DEFAULT_STORY = Path(
    "evidence/spineforge-v20-paid-story-local-repair/37006087948/"
    "age12-island-v20-story-local-repair2-story.txt"
)
DEFAULT_ENVELOPE = Path(
    "evidence/spineforge-v20-paid-story-local-repair/37006087948/"
    "age12-island-v20-story-local-repair2-envelope.json"
)
DEFAULT_WRITER_MANIFEST = Path(
    "evidence/spineforge-v20-writer-product/36965340665/writer-story-artifact.json"
)
DEFAULT_REPAIR_HANDOFF = Path(
    "evidence/spineforge-v20-story-local-repair/36990160527-handoff.json"
)


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
    if text.endswith("\n"):
        return text[:-1]
    return text


def build_story_local_repair_artifact(
    *,
    result_path: Path = DEFAULT_RESULT,
    story_path: Path = DEFAULT_STORY,
    envelope_path: Path = DEFAULT_ENVELOPE,
    writer_manifest_path: Path = DEFAULT_WRITER_MANIFEST,
    repair_handoff_path: Path = DEFAULT_REPAIR_HANDOFF,
) -> dict[str, Any]:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    writer = json.loads(writer_manifest_path.read_text(encoding="utf-8"))
    handoff = json.loads(repair_handoff_path.read_text(encoding="utf-8"))

    if result.get("schema") != "spineforge-v20-story-local-repair-execution.v1":
        raise RuntimeError("Stage 6 result schema mismatch.")
    if result.get("status") != "repair_generated":
        raise RuntimeError("Stage 6 result must be repair_generated.")
    if result.get("source_story_mutated") is not False:
        raise RuntimeError("Stage 6 source story must remain immutable.")
    if result.get("automatic_retry_executed") is not False:
        raise RuntimeError("Stage 6 automatic retry must remain disabled.")
    if result.get("reaudit_executed") is not False:
        raise RuntimeError("Stage 7 must not already have executed.")
    if result.get("next_stage") != "STORY_REAUDIT":
        raise RuntimeError("Stage 6 must route to STORY_REAUDIT.")

    if envelope.get("result_status") != "repair_generated":
        raise RuntimeError("Stage 6 envelope/result status mismatch.")
    if int(envelope.get("attempt_index") or 0) != 2:
        raise RuntimeError("Stage 6 artifact requires repair attempt 2.")

    if result.get("source_writer_artifact_id") != writer.get("artifact_id"):
        raise RuntimeError("Stage 6 writer artifact lineage mismatch.")
    if result.get("source_story_sha256") != writer.get("story_sha256"):
        raise RuntimeError("Stage 6 writer story SHA lineage mismatch.")
    if result.get("source_audit_artifact_id") != handoff.get("source_audit_artifact_id"):
        raise RuntimeError("Stage 6 audit artifact lineage mismatch.")
    if handoff.get("source_writer_artifact_id") != writer.get("artifact_id"):
        raise RuntimeError("Stage 6 handoff writer lineage mismatch.")

    canonical_story = _canonical_story_from_file(story_path)
    if canonical_story != result.get("repaired_story"):
        raise RuntimeError("Stage 6 repaired story file/content mismatch.")
    if _sha256_text(canonical_story) != result.get("repaired_story_sha256"):
        raise RuntimeError("Stage 6 canonical repaired story SHA mismatch.")

    source = build_story_audit_source(manifest_path=writer_manifest_path)
    source_segments = source["story_segments"]
    source_ids = [str(row["id"]) for row in source_segments]
    if len(source_ids) != 199 or len(set(source_ids)) != 199:
        raise RuntimeError("Stage 6 expects 199 stable source span IDs.")

    patches = list(result.get("patches") or [])
    no_change = list(result.get("no_change_resolutions") or [])
    patch_by_id = {str(row["span_id"]): row for row in patches}
    no_change_by_id = {str(row["span_id"]): row for row in no_change}

    if set(patch_by_id) & set(no_change_by_id):
        raise RuntimeError("Stage 6 span cannot be both PATCH and NO_CHANGE.")
    if any(span_id not in source_ids for span_id in patch_by_id | no_change_by_id):
        raise RuntimeError("Stage 6 repair references unknown source span.")
    if list(result.get("changed_span_ids") or []) != [
        span_id for span_id in source_ids if span_id in patch_by_id
    ]:
        raise RuntimeError("Stage 6 changed span order/identity mismatch.")
    if int(result.get("patch_count") or -1) != len(patches):
        raise RuntimeError("Stage 6 patch count mismatch.")
    if int(result.get("no_change_resolution_count") or -1) != len(no_change):
        raise RuntimeError("Stage 6 no-change count mismatch.")

    repaired_segments: list[dict[str, Any]] = []
    for row in source_segments:
        span_id = str(row["id"])
        source_text = str(row["text"])
        if span_id in patch_by_id:
            repaired_text = str(patch_by_id[span_id]["replacement_text"])
            disposition = "PATCH"
            finding_indexes = list(
                patch_by_id[span_id].get("addresses_finding_indexes") or []
            )
        elif span_id in no_change_by_id:
            repaired_text = source_text
            disposition = "NO_CHANGE"
            finding_indexes = list(
                no_change_by_id[span_id].get("addresses_finding_indexes") or []
            )
        else:
            repaired_text = source_text
            disposition = "UNCHANGED"
            finding_indexes = []

        repaired_segments.append({
            "span_id": span_id,
            "paragraph_id": row["paragraph_id"],
            "paragraph_index": row["paragraph_index"],
            "source_text": source_text,
            "repaired_text": repaired_text,
            "disposition": disposition,
            "addresses_finding_indexes": finding_indexes,
        })

    word_count = len(re.findall(r"\b\w+(?:['’-]\w+)*\b", canonical_story))
    body: dict[str, Any] = {
        "schema": "spineforge-v20-story-local-repair-artifact.v1",
        "artifact_type": "IMMUTABLE_REPAIRED_ENGLISH_STORY",
        "stage": 6,
        "status": "FROZEN",
        "immutable": True,
        "source_run_id": int(envelope.get("source_run_id") or 37006087948),
        "attempt_index": 2,
        "source_writer_artifact_id": writer["artifact_id"],
        "source_story_sha256": writer["story_sha256"],
        "source_audit_artifact_id": result["source_audit_artifact_id"],
        "source_repair_handoff_artifact_id": handoff["artifact_id"],
        "source_repair_handoff_sha256": _sha256_file(repair_handoff_path),
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
            span_id for span_id in source_ids if span_id in no_change_by_id
        ],
        "stable_span_count": len(repaired_segments),
        "repaired_segments": repaired_segments,
        "word_count": word_count,
        "repair_model": result["repair_model"],
        "repair_usage_rollup": result["repair_usage_rollup"],
        "mandatory_full_reaudit": True,
        "reaudit_required_for_no_change_resolutions": bool(no_change),
        "source_story_mutated": False,
        "next_stage": "STORY_REAUDIT",
    }
    body["artifact_id"] = _artifact_id(body, "story-local-repair")
    return body


def write_story_local_repair_artifact(
    output_path: Path,
    **kwargs: Any,
) -> dict[str, Any]:
    artifact = build_story_local_repair_artifact(**kwargs)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return artifact
