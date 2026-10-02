from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_STAGE6_ARTIFACT = Path(
    "evidence/spineforge-v20-story-local-repair-product/37006087948/"
    "story-local-repair-artifact.json"
)
DEFAULT_WRITER_HANDOFF = Path(
    "evidence/spineforge-v20-writer-handoff/36910614976-writer-ready.json"
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_id(payload: dict[str, Any], prefix: str) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


def build_story_reaudit_handoff(
    *,
    stage6_artifact_path: Path = DEFAULT_STAGE6_ARTIFACT,
    writer_handoff_path: Path = DEFAULT_WRITER_HANDOFF,
) -> dict[str, Any]:
    source = json.loads(stage6_artifact_path.read_text(encoding="utf-8"))
    writer = json.loads(writer_handoff_path.read_text(encoding="utf-8"))

    if source.get("schema") != "spineforge-v20-story-local-repair-artifact.v1":
        raise RuntimeError("Stage 7 source artifact schema mismatch.")
    if source.get("status") != "FROZEN" or source.get("immutable") is not True:
        raise RuntimeError("Stage 7 requires frozen immutable Stage 6 artifact.")
    if source.get("next_stage") != "STORY_REAUDIT":
        raise RuntimeError("Stage 6 artifact does not route to Story Re-audit.")
    if source.get("mandatory_full_reaudit") is not True:
        raise RuntimeError("Stage 7 requires mandatory full re-audit.")
    if int(source.get("stable_span_count") or 0) != 199:
        raise RuntimeError("Stage 7 requires 199 stable repaired spans.")

    story_path = Path(source["repaired_story_path"])
    if _sha256_file(story_path) != source["repaired_story_file_sha256"]:
        raise RuntimeError("Stage 7 repaired story file SHA mismatch.")
    if _sha256_file(Path(source["result_path"])) != source["result_sha256"]:
        raise RuntimeError("Stage 7 repair result SHA mismatch.")
    if _sha256_file(Path(source["envelope_path"])) != source["envelope_sha256"]:
        raise RuntimeError("Stage 7 repair envelope SHA mismatch.")

    if writer.get("context_pack_id") is None:
        raise RuntimeError("Stage 7 writer authority missing context pack.")
    if source.get("source_writer_artifact_id") is None:
        raise RuntimeError("Stage 7 source writer artifact identity missing.")

    body: dict[str, Any] = {
        "schema": "spineforge-v20-story-reaudit-handoff.v1",
        "artifact_type": "IMMUTABLE_STAGE7_REAUDIT_INPUT",
        "stage": 7,
        "status": "READY_NOT_AUTHORIZED",
        "immutable": True,
        "source_stage6_artifact_id": source["artifact_id"],
        "source_stage6_artifact_path": str(stage6_artifact_path),
        "source_stage6_artifact_sha256": _sha256_file(stage6_artifact_path),
        "source_writer_artifact_id": source["source_writer_artifact_id"],
        "source_stage5_audit_artifact_id": source["source_audit_artifact_id"],
        "repaired_story_path": source["repaired_story_path"],
        "repaired_story_text_sha256": source["repaired_story_text_sha256"],
        "repaired_story_file_sha256": source["repaired_story_file_sha256"],
        "stable_span_count": source["stable_span_count"],
        "changed_span_ids": source["changed_span_ids"],
        "no_change_span_ids": source["no_change_span_ids"],
        "patch_count": source["patch_count"],
        "no_change_resolution_count": source["no_change_resolution_count"],
        "reader": {"exact_age": writer["exact_age"]},
        "context_pack_id": writer["context_pack_id"],
        "context_fingerprint": writer["context_fingerprint"],
        "spine_hash": writer["spine_hash"],
        "approval_id": writer["approval_id"],
        "reaudit_policy": {
            "full_story_required": True,
            "all_199_stable_spans_required": True,
            "changed_spans_only_forbidden": True,
            "primary_model": "anthropic/claude-sonnet-5.5",
            "secondary_model": "openai/gpt-5.6-sol",
            "primary_contract": "story-audit-v3",
            "secondary_contract": "language-specialist-v2",
            "secondary_decision_contract": "KEEP_or_REWRITE",
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
    body["artifact_id"] = _artifact_id(body, "story-reaudit-handoff")
    return body


def write_story_reaudit_handoff(output_path: Path, **kwargs: Any) -> dict[str, Any]:
    handoff = build_story_reaudit_handoff(**kwargs)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(handoff, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return handoff
