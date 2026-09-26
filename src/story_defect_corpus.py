from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_SOURCE_POOL = Path(
    "experiments/fixtures/story_defect_source_pool.tr-age4.v1.json"
)

# Frozen before any D2 threshold selection. Same scenario_group always shares a split.
HELD_OUT_GROUPS = {
    "cohort_b_exploration_mystery",
    "cohort_b_friendship_social_problem",
    "paper_hat_no_reply",
    "glass_color_patch",
    "cohort_b_nature_environment",
}


def load_source_pool(path: str | Path = DEFAULT_SOURCE_POOL) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def story_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def assign_source_splits(pool: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in pool.get("sources") or []:
        group = str(source["scenario_group"])
        row = dict(source)
        row["story_sha256"] = story_sha256(str(source["story"]))
        row["dataset_split"] = "held_out" if group in HELD_OUT_GROUPS else "calibration"
        rows.append(row)
    return rows


def validate_source_pool(pool: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    sources = pool.get("sources")
    if not isinstance(sources, list) or not sources:
        return ["sources_missing"]

    ids: set[str] = set()
    hashes: dict[str, str] = {}
    split_by_group: dict[str, set[str]] = defaultdict(set)
    families_by_split: dict[str, set[str]] = defaultdict(set)

    for index, source in enumerate(assign_source_splits(pool)):
        source_id = str(source.get("source_id") or "")
        group = str(source.get("scenario_group") or "")
        family = str(source.get("family") or "")
        story = str(source.get("story") or "")
        split = str(source.get("dataset_split") or "")

        if not source_id:
            errors.append(f"source_{index}_id_missing")
        elif source_id in ids:
            errors.append(f"source_id_duplicate:{source_id}")
        ids.add(source_id)

        if not group:
            errors.append(f"source_{index}_scenario_group_missing")
        if not family:
            errors.append(f"source_{index}_family_missing")
        if len(story.split()) < 150:
            errors.append(f"source_{index}_story_too_short")

        digest = story_sha256(story)
        if digest in hashes:
            errors.append(
                f"duplicate_story_text:{source_id}:{hashes[digest]}"
            )
        else:
            hashes[digest] = source_id

        split_by_group[group].add(split)
        families_by_split[split].add(family)

        if source.get("source_clean_status") != "REQUIRES_INDEPENDENT_CLEAN_AUDIT":
            errors.append(f"source_{index}_clean_status_invalid")

    for group, splits in split_by_group.items():
        if len(splits) != 1:
            errors.append(f"scenario_group_split_leak:{group}")

    required_families = {
        "exploration_mystery",
        "friendship_social_problem",
        "emotional_development",
        "everyday_fantastical_discovery",
        "nature_environment",
    }
    held_out_missing = sorted(required_families - families_by_split["held_out"])
    if held_out_missing:
        errors.extend(
            f"held_out_family_missing:{family}" for family in held_out_missing
        )

    return errors


def source_pool_summary(pool: dict[str, Any]) -> dict[str, Any]:
    rows = assign_source_splits(pool)
    return {
        "source_count": len(rows),
        "scenario_group_count": len({row["scenario_group"] for row in rows}),
        "families": sorted({row["family"] for row in rows}),
        "split_counts": dict(Counter(row["dataset_split"] for row in rows)),
        "split_group_counts": {
            split: len({row["scenario_group"] for row in rows if row["dataset_split"] == split})
            for split in ("calibration", "held_out")
        },
        "held_out_groups": sorted(HELD_OUT_GROUPS),
    }


def build_audit_manifest(pool: dict[str, Any]) -> dict[str, Any]:
    errors = validate_source_pool(pool)
    if errors:
        raise RuntimeError("Invalid source pool: " + ", ".join(errors))
    rows = assign_source_splits(pool)
    return {
        "schema_version": "story-defect-clean-source-audit.v1",
        "status": "AWAITING_INDEPENDENT_AUDIT",
        "policy": {
            "source_story_is_not_clean_gold_until_audit_passes": True,
            "held_out_content_may_be_audited_but_must_not_influence_detector_thresholds": True,
            "same_scenario_group_cross_split_forbidden": True,
        },
        "sources": [
            {
                "source_id": row["source_id"],
                "scenario_group": row["scenario_group"],
                "family": row["family"],
                "dataset_split": row["dataset_split"],
                "story_sha256": row["story_sha256"],
                "source_clean_status": row["source_clean_status"],
                "provenance": row["provenance"],
            }
            for row in rows
        ],
    }
