from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


BLOCKING_FAMILIES = {
    "physical_feasibility",
    "causal_logic",
    "state_continuity",
    "epistemic_order",
    "spatial_consistency",
    "temporal_consistency",
    "response_causality",
    "closure_integrity",
    "canon_integrity",
    "spine_fidelity",
    "narrative_coherence",
    "age_suitability",
}

EDITORIAL_FAMILIES = {
    "language_naturalness",
}

BLOCKING_SEVERITIES = {"moderate", "serious", "critical"}
VALID_FINAL_DECISIONS = {"ACCEPT", "REJECT_NON_CONVERGENT"}


@dataclass(frozen=True)
class QualityFinding:
    index: int
    family: str
    severity: str
    repair_scope: str
    span_ids: tuple[str, ...]
    exact_text: str
    reason: str

    @property
    def blocking(self) -> bool:
        if self.family in EDITORIAL_FAMILIES and self.severity == "minor":
            return False
        if self.family not in BLOCKING_FAMILIES:
            return False
        return self.severity in BLOCKING_SEVERITIES

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "family": self.family,
            "severity": self.severity,
            "repair_scope": self.repair_scope,
            "span_ids": list(self.span_ids),
            "exact_text": self.exact_text,
            "reason": self.reason,
            "blocking": self.blocking,
        }


def normalize_findings(rows: Iterable[dict[str, Any]]) -> list[QualityFinding]:
    normalized: list[QualityFinding] = []
    for index, row in enumerate(rows):
        span_ids = tuple(str(x) for x in row.get("span_ids") or [])
        normalized.append(
            QualityFinding(
                index=index,
                family=str(row.get("family") or ""),
                severity=str(row.get("severity") or ""),
                repair_scope=str(row.get("repair_scope") or ""),
                span_ids=span_ids,
                exact_text=str(row.get("exact_text") or ""),
                reason=str(row.get("reason") or ""),
            )
        )
    return normalized


def split_findings(
    rows: Iterable[dict[str, Any]],
) -> tuple[list[QualityFinding], list[QualityFinding]]:
    findings = normalize_findings(rows)
    blocking = [row for row in findings if row.blocking]
    advisory = [row for row in findings if not row.blocking]
    return blocking, advisory


def _span_number(span_id: str) -> int:
    if not span_id.startswith("S") or not span_id[1:].isdigit():
        raise RuntimeError(f"Invalid stable span id: {span_id}")
    return int(span_id[1:])


def _segment_map(story_segments: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    rows = {str(row["span_id"]): row for row in story_segments}
    if not rows:
        raise RuntimeError("Story segments are required.")
    return rows


def _paragraph_bounds(
    *,
    segment_map: dict[str, dict[str, Any]],
    paragraph_index: int,
) -> tuple[int, int]:
    nums = sorted(
        _span_number(span_id)
        for span_id, row in segment_map.items()
        if int(row["paragraph_index"]) == paragraph_index
    )
    if not nums:
        raise RuntimeError(f"Missing paragraph index: {paragraph_index}")
    return nums[0], nums[-1]


def build_scene_repair_cluster(
    *,
    findings: Iterable[dict[str, Any]],
    story_segments: Iterable[dict[str, Any]],
    context_paragraphs: int = 0,
    max_scene_span_count: int = 40,
) -> dict[str, Any]:
    blocking, advisory = split_findings(findings)
    if not blocking:
        return {
            "repair_required": False,
            "blocking_findings": [],
            "advisory_findings": [row.to_dict() for row in advisory],
            "cluster": None,
        }

    segment_map = _segment_map(story_segments)
    referenced_ids = sorted(
        {
            span_id
            for finding in blocking
            for span_id in finding.span_ids
            if span_id in segment_map
        },
        key=_span_number,
    )
    if not referenced_ids:
        raise RuntimeError("Blocking findings contain no valid stable story spans.")

    paragraph_indexes = sorted(
        {int(segment_map[span_id]["paragraph_index"]) for span_id in referenced_ids}
    )
    first_para = paragraph_indexes[0]
    last_para = paragraph_indexes[-1]

    # Scene repair operates on the minimal contiguous semantic block that
    # contains every blocking finding. Neighboring spans remain immutable
    # entry/exit context instead of becoming editable repair scope.
    all_paragraphs = sorted(
        {int(row["paragraph_index"]) for row in segment_map.values()}
    )
    min_para = min(all_paragraphs)
    max_para = max(all_paragraphs)
    cluster_first_para = max(min_para, first_para - context_paragraphs)
    cluster_last_para = min(max_para, last_para + context_paragraphs)

    start_num, _ = _paragraph_bounds(
        segment_map=segment_map, paragraph_index=cluster_first_para
    )
    _, end_num = _paragraph_bounds(
        segment_map=segment_map, paragraph_index=cluster_last_para
    )
    span_count = end_num - start_num + 1
    if span_count > max_scene_span_count:
        raise RuntimeError(
            f"Blocking repair cluster too large: {span_count} > {max_scene_span_count}"
        )

    cluster_ids = [f"S{i:03d}" for i in range(start_num, end_num + 1)]
    if any(span_id not in segment_map for span_id in cluster_ids):
        raise RuntimeError("Scene repair cluster contains missing stable span ids.")

    entry_span_id = f"S{start_num - 1:03d}" if start_num > 1 else None
    exit_num = end_num + 1
    exit_span_id = f"S{exit_num:03d}" if f"S{exit_num:03d}" in segment_map else None

    return {
        "repair_required": True,
        "blocking_findings": [row.to_dict() for row in blocking],
        "advisory_findings": [row.to_dict() for row in advisory],
        "cluster": {
            "cluster_id": f"SCENE-{cluster_first_para:03d}-{cluster_last_para:03d}",
            "start_span_id": cluster_ids[0],
            "end_span_id": cluster_ids[-1],
            "span_ids": cluster_ids,
            "span_count": len(cluster_ids),
            "paragraph_start": cluster_first_para,
            "paragraph_end": cluster_last_para,
            "entry_boundary_span_id": entry_span_id,
            "exit_boundary_span_id": exit_span_id,
            "blocking_finding_indexes": [row.index for row in blocking],
            "repair_mode": "SCENE_REWRITE",
            "source_mutation_forbidden": True,
        },
    }


def next_quality_action(
    *,
    audit_phase: str,
    blocking_finding_count: int,
    repair_count: int,
) -> str:
    if audit_phase == "INITIAL":
        if blocking_finding_count == 0:
            return "ACCEPT"
        if repair_count == 0:
            return "SCENE_REPAIR"
        raise RuntimeError("Initial audit cannot start after a repair.")

    if audit_phase == "FINAL":
        if repair_count != 1:
            raise RuntimeError("Final audit requires exactly one completed scene repair.")
        return "ACCEPT" if blocking_finding_count == 0 else "REJECT_NON_CONVERGENT"

    raise RuntimeError(f"Unknown audit phase: {audit_phase}")


def build_bounded_quality_contract() -> dict[str, Any]:
    return {
        "schema": "spineforge-v21-bounded-quality-contract.v1",
        "quality_topology": [
            "INITIAL_AUDIT",
            "OPTIONAL_SCENE_REPAIR",
            "FINAL_AUDIT",
            "ACCEPT_OR_REJECT",
        ],
        "max_scene_repairs": 1,
        "max_audits": 2,
        "automatic_looping": False,
        "blocking_families": sorted(BLOCKING_FAMILIES),
        "editorial_families": sorted(EDITORIAL_FAMILIES),
        "minor_editorial_is_blocking": False,
        "final_audit_may_request_another_repair": False,
        "final_decisions": sorted(VALID_FINAL_DECISIONS),
        "source_story_mutation_forbidden": True,
        "immutable_artifact_handoff_required": True,
        "translation_before_accept_forbidden": True,
        "state_commit_before_accept_forbidden": True,
    }


def apply_scene_rewrite(
    *,
    source_story: str,
    story_segments: Iterable[dict[str, Any]],
    cluster: dict[str, Any],
    replacement_scene: str,
) -> dict[str, Any]:
    import hashlib

    from src.spineforge_v20_story_audit_artifact import _segment_story

    replacement = replacement_scene.strip()
    if not replacement:
        raise RuntimeError("Replacement scene must not be empty.")

    artifact_segment_map = _segment_map(story_segments)

    # v20 preserved stable sentence IDs across repairs even when punctuation
    # changed enough that a fresh sentence splitter would produce a different
    # count. Reconstruct exact offsets by matching the frozen span texts in
    # order against the immutable source story. This keeps v20 lineage valid
    # without carrying its fixed-199-span constraint into v21.
    located: dict[str, dict[str, Any]] = {}
    cursor = 0
    ordered_rows = sorted(
        artifact_segment_map.items(), key=lambda item: _span_number(item[0])
    )
    for span_id, artifact_row in ordered_rows:
        text_value = str(artifact_row["repaired_text"])
        pos = source_story.find(text_value, cursor)
        if pos < 0:
            raise RuntimeError(
                f"Frozen artifact span cannot be located in source story: {span_id}"
            )
        gap = source_story[cursor:pos]
        if gap.strip():
            raise RuntimeError(
                f"Unexpected non-whitespace text before frozen span: {span_id}"
            )
        located[span_id] = {
            "text": text_value,
            "char_start": pos,
            "char_end": pos + len(text_value),
        }
        cursor = pos + len(text_value)
    if source_story[cursor:].strip():
        raise RuntimeError("Frozen spans do not cover the complete source story.")

    start_id = str(cluster["start_span_id"])
    end_id = str(cluster["end_span_id"])
    if start_id not in located or end_id not in located:
        raise RuntimeError("Scene rewrite cluster boundary span is missing.")

    start = int(located[start_id]["char_start"])
    end = int(located[end_id]["char_end"])
    if start >= end:
        raise RuntimeError("Scene rewrite cluster offsets are invalid.")

    source_cluster = source_story[start:end]
    expected_start_text = str(located[start_id]["text"])
    expected_end_text = str(located[end_id]["text"])
    if not source_cluster.startswith(expected_start_text):
        raise RuntimeError("Scene rewrite start boundary does not match source story.")
    if not source_cluster.endswith(expected_end_text):
        raise RuntimeError("Scene rewrite end boundary does not match source story.")

    prefix = source_story[:start]
    suffix = source_story[end:]
    repaired_story = prefix + replacement + suffix

    new_segments = _segment_story(repaired_story)
    if not new_segments:
        raise RuntimeError("Scene rewrite produced an empty story.")

    digest = lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest()
    return {
        "schema": "spineforge-v21-scene-rewrite-result.v1",
        "source_story_sha256": digest(source_story),
        "repaired_story_sha256": digest(repaired_story),
        "source_cluster_sha256": digest(source_cluster),
        "replacement_scene_sha256": digest(replacement),
        "prefix_sha256": digest(prefix),
        "suffix_sha256": digest(suffix),
        "source_cluster_start_span_id": start_id,
        "source_cluster_end_span_id": end_id,
        "source_span_count": len(artifact_segment_map),
        "repaired_span_count": len(new_segments),
        "source_mutated": False,
        "outside_cluster_unchanged": (
            repaired_story.startswith(prefix) and repaired_story.endswith(suffix)
        ),
        "repaired_story": repaired_story,
        "repaired_segments": [
            {
                "span_id": row["id"],
                "paragraph_id": row["paragraph_id"],
                "paragraph_index": row["paragraph_index"],
                "text": row["text"],
                "char_start": row["char_start"],
                "char_end": row["char_end"],
            }
            for row in new_segments
        ],
        "lineage": {
            "repair_unit": "CONTIGUOUS_SCENE_CLUSTER",
            "source_cluster_id": cluster["cluster_id"],
            "source_span_ids": list(cluster["span_ids"]),
            "stable_span_identity_across_rewrite_required": False,
            "fresh_segmentation_after_rewrite": True,
        },
    }


def build_scene_repair_handoff(
    *,
    source_story_artifact_id: str,
    source_story_sha256: str,
    findings: Iterable[dict[str, Any]],
    story_segments: Iterable[dict[str, Any]],
    approved_spine_hash: str,
    canon_invariants: Iterable[str],
) -> dict[str, Any]:
    rows = list(story_segments)
    plan = build_scene_repair_cluster(
        findings=findings,
        story_segments=rows,
    )
    if not plan["repair_required"]:
        raise RuntimeError("Scene repair handoff requires blocking findings.")

    segment_map = _segment_map(rows)
    cluster = plan["cluster"]
    entry_id = cluster["entry_boundary_span_id"]
    exit_id = cluster["exit_boundary_span_id"]

    return {
        "schema": "spineforge-v21-scene-repair-handoff.v1",
        "status": "READY_NOT_AUTHORIZED",
        "immutable": True,
        "paid_execution_authorized": False,
        "source_story_artifact_id": source_story_artifact_id,
        "source_story_sha256": source_story_sha256,
        "approved_spine_hash": approved_spine_hash,
        "blocking_findings": plan["blocking_findings"],
        "editorial_advisories": plan["advisory_findings"],
        "scene_cluster": cluster,
        "entry_boundary": (
            {
                "span_id": entry_id,
                "text": segment_map[entry_id]["repaired_text"],
            }
            if entry_id
            else None
        ),
        "exit_boundary": (
            {
                "span_id": exit_id,
                "text": segment_map[exit_id]["repaired_text"],
            }
            if exit_id
            else None
        ),
        "canon_invariants": list(canon_invariants),
        "repair_policy": {
            "max_scene_repairs": 1,
            "rewrite_entire_scene": True,
            "sentence_patch_mode_forbidden": True,
            "same_sentence_count_required": False,
            "fresh_segmentation_after_rewrite": True,
            "outside_cluster_must_remain_identical": True,
            "final_audit_required": True,
            "final_audit_may_request_another_repair": False,
        },
    }
