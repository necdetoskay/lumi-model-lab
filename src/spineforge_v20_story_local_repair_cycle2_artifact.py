from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_RESULT = Path(
    "evidence/spineforge-v20-paid-story-local-repair-cycle2/37010331757/"
    "age12-island-v20-story-local-repair3-result.json"
)
DEFAULT_STORY = Path(
    "evidence/spineforge-v20-paid-story-local-repair-cycle2/37010331757/"
    "age12-island-v20-story-local-repair3-story.txt"
)
DEFAULT_ENVELOPE = Path(
    "evidence/spineforge-v20-paid-story-local-repair-cycle2/37010331757/"
    "age12-island-v20-story-local-repair3-envelope.json"
)
DEFAULT_STAGE6_ARTIFACT = Path(
    "evidence/spineforge-v20-story-local-repair-product/37006087948/"
    "story-local-repair-artifact.json"
)
DEFAULT_STAGE7_PRODUCT = Path(
    "evidence/spineforge-v20-story-reaudit-product/37007924152/"
    "story-reaudit-product.json"
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


def _canonical_story(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text[:-1] if text.endswith("\n") else text


def build_story_local_repair_cycle2_artifact(
    *,
    result_path: Path = DEFAULT_RESULT,
    story_path: Path = DEFAULT_STORY,
    envelope_path: Path = DEFAULT_ENVELOPE,
    stage6_artifact_path: Path = DEFAULT_STAGE6_ARTIFACT,
    stage7_product_path: Path = DEFAULT_STAGE7_PRODUCT,
) -> dict[str, Any]:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    prior = json.loads(stage6_artifact_path.read_text(encoding="utf-8"))
    stage7 = json.loads(stage7_product_path.read_text(encoding="utf-8"))

    if result.get("schema") != "spineforge-v20-story-local-repair-cycle2-execution.v1":
        raise RuntimeError("Stage 8 result schema mismatch.")
    if result.get("status") != "repair_generated":
        raise RuntimeError("Stage 8 result must be repair_generated.")
    if int(result.get("stage") or 0) != 8:
        raise RuntimeError("Stage 8 result stage mismatch.")
    if result.get("source_stage7_product_artifact_id") != stage7.get("artifact_id"):
        raise RuntimeError("Stage 8/Stage 7 product lineage mismatch.")
    if result.get("source_stage7_reaudit_artifact_id") != stage7.get(
        "embedded_reaudit_artifact_id"
    ):
        raise RuntimeError("Stage 8/Stage 7 re-audit lineage mismatch.")
    if result.get("source_stage6_artifact_id") != prior.get("artifact_id"):
        raise RuntimeError("Stage 8/Stage 6 artifact lineage mismatch.")
    if result.get("source_story_sha256") != prior.get("repaired_story_text_sha256"):
        raise RuntimeError("Stage 8 source story SHA lineage mismatch.")
    if result.get("source_story_mutated") is not False:
        raise RuntimeError("Stage 8 source story must remain immutable.")
    if result.get("automatic_retry_executed") is not False:
        raise RuntimeError("Stage 8 automatic retry must remain disabled.")
    if result.get("reaudit_executed") is not False:
        raise RuntimeError("Stage 9 must not already have executed.")
    if result.get("next_stage") != "STORY_REAUDIT":
        raise RuntimeError("Stage 8 must route to STORY_REAUDIT.")
    if envelope.get("result_status") != "repair_generated":
        raise RuntimeError("Stage 8 envelope/result mismatch.")
    if int(envelope.get("paid_attempt_index") or 0) != 3:
        raise RuntimeError("Stage 8 artifact requires paid attempt 3.")

    story = _canonical_story(story_path)
    if story != result.get("repaired_story"):
        raise RuntimeError("Stage 8 repaired story file/content mismatch.")
    if _sha256_text(story) != result.get("repaired_story_sha256"):
        raise RuntimeError("Stage 8 canonical repaired story SHA mismatch.")

    prior_segments = list(prior.get("repaired_segments") or [])
    if len(prior_segments) != 199:
        raise RuntimeError("Stage 8 expects 199 stable prior spans.")
    ids = [str(row["span_id"]) for row in prior_segments]
    if ids != [f"S{i:03d}" for i in range(1, 200)]:
        raise RuntimeError("Stage 8 prior span identity/order mismatch.")

    patches = list(result.get("patches") or [])
    no_change = list(result.get("no_change_resolutions") or [])
    patch_by_id = {str(row["span_id"]): row for row in patches}
    no_change_by_id = {str(row["span_id"]): row for row in no_change}
    if set(patch_by_id) & set(no_change_by_id):
        raise RuntimeError("Stage 8 span cannot be PATCH and NO_CHANGE.")
    if any(span_id not in ids for span_id in patch_by_id | no_change_by_id):
        raise RuntimeError("Stage 8 repair references unknown stable span.")

    repaired_segments: list[dict[str, Any]] = []
    for row in prior_segments:
        span_id = str(row["span_id"])
        source_text = str(row["repaired_text"])
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

    if list(result.get("changed_span_ids") or []) != [
        sid for sid in ids if sid in patch_by_id
    ]:
        raise RuntimeError("Stage 8 changed span order/identity mismatch.")
    if int(result.get("patch_count") or -1) != len(patches):
        raise RuntimeError("Stage 8 patch count mismatch.")
    if int(result.get("no_change_resolution_count") or -1) != len(no_change):
        raise RuntimeError("Stage 8 no-change count mismatch.")

    word_count = len(re.findall(r"\b\w+(?:['’-]\w+)*\b", story))
    body: dict[str, Any] = {
        "schema": "spineforge-v20-story-local-repair-cycle2-artifact.v1",
        "artifact_type": "IMMUTABLE_REPAIRED_ENGLISH_STORY_CYCLE2",
        "stage": 8,
        "status": "FROZEN",
        "immutable": True,
        "source_run_id": 37010331757,
        "source_stage7_product_artifact_id": stage7["artifact_id"],
        "source_stage7_reaudit_artifact_id": stage7["embedded_reaudit_artifact_id"],
        "source_stage6_artifact_id": prior["artifact_id"],
        "source_story_sha256": prior["repaired_story_text_sha256"],
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
            sid for sid in ids if sid in no_change_by_id
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
    body["artifact_id"] = _artifact_id(body, "story-local-repair-cycle2")
    return body


def write_story_local_repair_cycle2_artifact(
    output_path: Path,
    **kwargs: Any,
) -> dict[str, Any]:
    artifact = build_story_local_repair_cycle2_artifact(**kwargs)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return artifact
