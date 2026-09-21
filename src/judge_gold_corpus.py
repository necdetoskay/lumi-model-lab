from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

REQUIRED_CRITERIA = (
    "instruction_following",
    "coherence",
    "character_consistency",
    "age_appropriateness",
    "creativity",
    "style_quality",
)
PARTITIONS = {"calibration", "development_holdout", "final_holdout"}
LABEL_STATUSES = {"pending_blind_review", "provisional_quick_decision", "final"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_final_label(case: dict[str, Any], errors: list[str]) -> None:
    ref = case.get("human_reference") or {}
    if ref.get("status") != "final":
        return
    if ref.get("decision") not in {"PASS", "BLOCK"}:
        errors.append(f"{case['case_id']}: final label requires PASS/BLOCK decision")
    scores = ref.get("scores")
    if not isinstance(scores, dict):
        errors.append(f"{case['case_id']}: final label requires scores object")
        return
    for criterion in REQUIRED_CRITERIA:
        score = scores.get(criterion)
        if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 5:
            errors.append(
                f"{case['case_id']}: final label requires integer 1-5 for {criterion}"
            )


def validate_manifest(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    cases = data.get("cases")
    if not isinstance(cases, list):
        return {"valid": False, "promotion_ready": False, "errors": ["cases must be a list"]}

    if len(cases) < 100:
        errors.append("gold corpus must define at least 100 cases")

    ids: set[str] = set()
    family_partition: dict[str, str] = {}
    partition_counts: dict[str, int] = {}
    critical_count = 0
    language_comparison_count = 0
    materialized_count = 0
    final_label_count = 0

    for case in cases:
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            errors.append("case missing case_id")
            continue
        if case_id in ids:
            errors.append(f"duplicate case_id: {case_id}")
        ids.add(case_id)

        partition = case.get("partition")
        if partition not in PARTITIONS:
            errors.append(f"{case_id}: invalid partition {partition!r}")
        else:
            partition_counts[partition] = partition_counts.get(partition, 0) + 1

        family = case.get("source_family_id")
        if not isinstance(family, str) or not family:
            errors.append(f"{case_id}: missing source_family_id")
        elif partition in PARTITIONS:
            previous = family_partition.setdefault(family, partition)
            if previous != partition:
                errors.append(
                    f"{case_id}: source family {family} leaks across {previous}/{partition}"
                )

        source_sha = case.get("source_blob_sha")
        if not isinstance(source_sha, str) or HEX40.fullmatch(source_sha) is None:
            errors.append(f"{case_id}: invalid source_blob_sha")

        materialization = case.get("materialization") or {}
        if materialization.get("status") in {"source_artifact", "materialized"}:
            materialized_count += 1

        if case.get("critical_protected") is True:
            critical_count += 1

        variants = case.get("language_variants") or []
        if "tr_native" in variants and "controlled_en_projection" in variants:
            language_comparison_count += 1

        ref = case.get("human_reference") or {}
        label_status = ref.get("status")
        if label_status not in LABEL_STATUSES:
            errors.append(f"{case_id}: invalid human_reference status {label_status!r}")
        if label_status == "final":
            final_label_count += 1
        _validate_final_label(case, errors)

    if not partition_counts.get("final_holdout"):
        errors.append("final_holdout must not be empty")
    if critical_count == 0:
        errors.append("critical-protected subset must not be empty")
    if language_comparison_count == 0:
        errors.append("language comparison subset must not be empty")

    promotion_ready = (
        not errors
        and len(cases) >= 100
        and materialized_count == len(cases)
        and final_label_count == len(cases)
    )

    return {
        "valid": not errors,
        "promotion_ready": promotion_ready,
        "case_count": len(cases),
        "partition_counts": partition_counts,
        "critical_protected_count": critical_count,
        "language_comparison_count": language_comparison_count,
        "materialized_count": materialized_count,
        "final_label_count": final_label_count,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the frozen Judge Gold Corpus manifest.")
    parser.add_argument(
        "--manifest",
        default="data/specifications/judge_gold_corpus_v2.json",
    )
    parser.add_argument(
        "--require-promotion-ready",
        action="store_true",
        help="Exit non-zero unless every case is materialized and fully human-labeled.",
    )
    args = parser.parse_args()

    summary = validate_manifest(load_manifest(Path(args.manifest)))
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if not summary["valid"]:
        raise SystemExit(1)
    if args.require_promotion_ready and not summary["promotion_ready"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
