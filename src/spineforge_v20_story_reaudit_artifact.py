from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_RESULT = Path(
    "evidence/spineforge-v20-paid-story-reaudit/37007924152/"
    "age12-island-v20-story-reaudit1-result.json"
)
DEFAULT_ENVELOPE = Path(
    "evidence/spineforge-v20-paid-story-reaudit/37007924152/"
    "age12-island-v20-story-reaudit1-envelope.json"
)
DEFAULT_STAGE6_ARTIFACT = Path(
    "evidence/spineforge-v20-story-local-repair-product/37006087948/"
    "story-local-repair-artifact.json"
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


def build_story_reaudit_product(
    *,
    result_path: Path = DEFAULT_RESULT,
    envelope_path: Path = DEFAULT_ENVELOPE,
    stage6_artifact_path: Path = DEFAULT_STAGE6_ARTIFACT,
) -> dict[str, Any]:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    stage6 = json.loads(stage6_artifact_path.read_text(encoding="utf-8"))

    if result.get("schema") != "spineforge-v20-story-reaudit-execution.v1":
        raise RuntimeError("Stage 7 result schema mismatch.")
    if result.get("status") != "reaudit_completed":
        raise RuntimeError("Stage 7 result must be completed.")
    artifact = result.get("reaudit_artifact")
    if not isinstance(artifact, dict):
        raise RuntimeError("Stage 7 result missing re-audit artifact.")
    if artifact.get("schema") != "spineforge-v20-story-reaudit-artifact.v1":
        raise RuntimeError("Stage 7 embedded artifact schema mismatch.")
    if artifact.get("source_stage6_artifact_id") != stage6.get("artifact_id"):
        raise RuntimeError("Stage 7/Stage 6 artifact lineage mismatch.")
    if artifact.get("source_repaired_story_sha256") != stage6.get(
        "repaired_story_text_sha256"
    ):
        raise RuntimeError("Stage 7 repaired story lineage mismatch.")
    if result.get("source_repaired_story_sha256") != stage6.get(
        "repaired_story_text_sha256"
    ):
        raise RuntimeError("Stage 7 result repaired story SHA mismatch.")
    if artifact.get("full_story_reaudited") is not True:
        raise RuntimeError("Stage 7 product requires full-story re-audit.")
    if int(artifact.get("stable_span_count") or 0) != 199:
        raise RuntimeError("Stage 7 product requires 199 stable spans.")
    if result.get("source_story_mutated") is not False:
        raise RuntimeError("Stage 7 source story must remain immutable.")
    if result.get("automatic_retry_executed") is not False:
        raise RuntimeError("Stage 7 automatic retry must remain disabled.")
    if envelope.get("result_status") != "reaudit_completed":
        raise RuntimeError("Stage 7 envelope/result status mismatch.")

    findings = artifact.get("findings")
    if not isinstance(findings, list):
        raise RuntimeError("Stage 7 findings must be a list.")

    body: dict[str, Any] = {
        "schema": "spineforge-v20-story-reaudit-product.v1",
        "artifact_type": "IMMUTABLE_STAGE7_REAUDIT_RESULT",
        "stage": 7,
        "status": "FROZEN",
        "immutable": True,
        "source_run_id": 37007924152,
        "source_stage6_artifact_id": stage6["artifact_id"],
        "source_stage6_artifact_path": str(stage6_artifact_path),
        "source_stage6_artifact_sha256": _sha256_file(stage6_artifact_path),
        "source_repaired_story_path": stage6["repaired_story_path"],
        "source_repaired_story_text_sha256": stage6["repaired_story_text_sha256"],
        "source_repaired_story_file_sha256": stage6["repaired_story_file_sha256"],
        "embedded_reaudit_artifact_id": artifact["artifact_id"],
        "decision": artifact["decision"],
        "next_stage": artifact["next_stage"],
        "finding_count": len(findings),
        "findings": findings,
        "full_story_reaudited": True,
        "stable_span_count": 199,
        "result_path": str(result_path),
        "result_sha256": _sha256_file(result_path),
        "envelope_path": str(envelope_path),
        "envelope_sha256": _sha256_file(envelope_path),
        "reaudit_usage_rollup": result["reaudit_usage_rollup"],
        "source_story_mutated": False,
        "automatic_retry_executed": False,
        "repair_executed": False,
        "translation_executed": False,
        "state_commit_executed": False,
    }
    body["artifact_id"] = _artifact_id(body, "story-reaudit-product")
    return body


def write_story_reaudit_product(output_path: Path, **kwargs: Any) -> dict[str, Any]:
    artifact = build_story_reaudit_product(**kwargs)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return artifact
