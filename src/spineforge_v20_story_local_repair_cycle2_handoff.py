from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_STAGE7_PRODUCT = Path(
    "evidence/spineforge-v20-story-reaudit-product/37007924152/"
    "story-reaudit-product.json"
)
DEFAULT_STAGE6_ARTIFACT = Path(
    "evidence/spineforge-v20-story-local-repair-product/37006087948/"
    "story-local-repair-artifact.json"
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
    return "story-local-repair-cycle2-handoff:" + hashlib.sha256(encoded).hexdigest()


def _canonical_story(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text[:-1] if text.endswith("\n") else text


def _repaired_span_offsets(
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
            raise RuntimeError(
                f"Stage 8 cannot bind repaired span in source story: {span_id}"
            )
        end = start + len(text)
        offsets[span_id] = (start, end)
        cursor = end
    if len(offsets) != 199:
        raise RuntimeError("Stage 8 requires 199 stable repaired spans.")
    return offsets


def build_story_local_repair_cycle2_handoff(
    *,
    stage7_product_path: Path = DEFAULT_STAGE7_PRODUCT,
    stage6_artifact_path: Path = DEFAULT_STAGE6_ARTIFACT,
) -> dict[str, Any]:
    stage7 = json.loads(stage7_product_path.read_text(encoding="utf-8"))
    stage6 = json.loads(stage6_artifact_path.read_text(encoding="utf-8"))

    if stage7.get("schema") != "spineforge-v20-story-reaudit-product.v1":
        raise RuntimeError("Stage 8 source Stage 7 product schema mismatch.")
    if stage7.get("status") != "FROZEN" or stage7.get("immutable") is not True:
        raise RuntimeError("Stage 8 requires immutable frozen Stage 7 product.")
    if stage7.get("decision") != "LOCAL_REPAIR_REQUIRED":
        raise RuntimeError("Stage 8 requires LOCAL_REPAIR_REQUIRED Stage 7 decision.")
    if stage7.get("next_stage") != "STORY_LOCAL_REPAIR":
        raise RuntimeError("Stage 8 Stage 7 next-stage binding mismatch.")
    if stage7.get("source_stage6_artifact_id") != stage6.get("artifact_id"):
        raise RuntimeError("Stage 8 Stage 7/Stage 6 lineage mismatch.")
    if stage7.get("source_repaired_story_text_sha256") != stage6.get(
        "repaired_story_text_sha256"
    ):
        raise RuntimeError("Stage 8 repaired story lineage mismatch.")
    if stage7.get("full_story_reaudited") is not True:
        raise RuntimeError("Stage 8 requires full Story Re-audit evidence.")

    findings = stage7.get("findings")
    if not isinstance(findings, list) or not findings:
        raise RuntimeError("Stage 8 requires non-empty Stage 7 findings.")
    if any(row.get("repair_scope") != "LOCAL_REPAIR" for row in findings):
        raise RuntimeError("Stage 8 forbids non-local repair findings.")

    story_path = Path(stage6["repaired_story_path"])
    story = _canonical_story(story_path)
    if hashlib.sha256(story.encode("utf-8")).hexdigest() != stage6.get(
        "repaired_story_text_sha256"
    ):
        raise RuntimeError("Stage 8 repaired story text SHA mismatch.")

    repaired_segments = list(stage6.get("repaired_segments") or [])
    if len(repaired_segments) != 199:
        raise RuntimeError("Stage 8 requires 199 repaired source segments.")
    segment_by_id = {str(row["span_id"]): row for row in repaired_segments}
    order = {str(row["span_id"]): i for i, row in enumerate(repaired_segments)}
    offsets = _repaired_span_offsets(story=story, repaired_segments=repaired_segments)

    target_to_findings: dict[str, list[int]] = {}
    normalized_findings: list[dict[str, Any]] = []
    for index, finding in enumerate(findings):
        span_ids = [str(x) for x in finding.get("span_ids") or []]
        if not span_ids:
            raise RuntimeError(f"Stage 8 finding {index} has no source spans.")
        if any(span_id not in segment_by_id for span_id in span_ids):
            raise RuntimeError(f"Stage 8 finding {index} references unknown span.")
        exact = str(finding.get("exact_text") or "")
        if exact and not any(
            exact in str(segment_by_id[span_id]["repaired_text"])
            for span_id in span_ids
        ):
            # Multi-span locator text may span/merge cited segments. The Stage 7
            # artifact already validated it against its frozen source; preserve
            # the finding instead of silently rewriting evidence here.
            pass
        for span_id in span_ids:
            target_to_findings.setdefault(span_id, []).append(index)
        normalized_findings.append({
            "finding_index": index,
            "family": str(finding["family"]),
            "severity": str(finding["severity"]),
            "repair_scope": "LOCAL_REPAIR",
            "span_ids": span_ids,
            "exact_text": exact,
            "reason": str(finding["reason"]),
        })

    allowed_ids = sorted(target_to_findings, key=lambda sid: order[sid])
    targets = []
    for span_id in allowed_ids:
        row = segment_by_id[span_id]
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

    payload: dict[str, Any] = {
        "schema": "spineforge-v20-story-local-repair-cycle2-handoff.v1",
        "artifact_type": "IMMUTABLE_STAGE8_LOCAL_REPAIR_INPUT",
        "stage": 8,
        "status": "READY_NOT_AUTHORIZED",
        "immutable": True,
        "source_stage7_product_artifact_id": stage7["artifact_id"],
        "source_stage7_product_path": str(stage7_product_path),
        "source_stage7_product_sha256": _sha256_file(stage7_product_path),
        "source_stage7_reaudit_artifact_id": stage7["embedded_reaudit_artifact_id"],
        "source_stage6_artifact_id": stage6["artifact_id"],
        "source_story_sha256": stage6["repaired_story_text_sha256"],
        "source_story_file_sha256": stage6["repaired_story_file_sha256"],
        "source_story_path": stage6["repaired_story_path"],
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
        "repair_model": "anthropic/claude-sonnet-5.5",
        "repair_cycle_index": 2,
        "paid_attempt_index": 3,
        "automatic_retry_enabled": False,
        "automatic_repair_loop_enabled": False,
        "paid_execution_authorized": False,
        "output_contract": {
            "schema": "spineforge-v20-story-local-repair-cycle2-artifact.v1",
            "source_story_remains_immutable": True,
            "changed_spans_must_be_subset_of_allowed_edit_span_ids": True,
            "no_change_resolutions_preserved": True,
            "next_stage": "STORY_REAUDIT",
        },
        "next_stage_after_success": "STORY_REAUDIT",
    }
    payload["artifact_id"] = _artifact_id(payload)
    return payload


def write_story_local_repair_cycle2_handoff(
    output_path: Path,
    **kwargs: Any,
) -> dict[str, Any]:
    handoff = build_story_local_repair_cycle2_handoff(**kwargs)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(handoff, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return handoff
