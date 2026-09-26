from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.openrouter_jev import call_openrouter_jev
from src.story_defect_corpus import assign_source_splits, load_source_pool
from src.story_defect_detection import (
    build_jev_defect_questions,
    build_jev_state,
    jev_scores_from_response,
)
from src.story_defect_synthetic_corpus import load_synthetic_corpus

ADMISSION = Path("experiments/fixtures/story_defect_clean_source_admission.tr-age4.v1.json")
D1_MANIFEST = Path("experiments/fixtures/story_defect_d1_validation_manifest.tr-age4.v1.1.json")
OUT = Path("runs/story-defect-jev-calibration/result.json")

THRESHOLDS = [round(value / 100, 2) for value in range(1, 100)]

QUALIFICATION_GROUPS: dict[str, tuple[str, ...]] = {
    "physical_feasibility": ("physical_feasibility",),
    "causal_logic": ("causal_logic", "response_causality"),
    "state_continuity": ("state_continuity",),
    "epistemic_order": ("epistemic_order",),
    "spatial_consistency": ("spatial_consistency",),
    "temporal_consistency": ("temporal_consistency",),
    "closure_integrity": ("closure_integrity",),
    "canon_integrity": ("canon_integrity",),
}


def qualification_family(raw_family: str | None) -> str | None:
    return "causal_logic" if raw_family == "response_causality" else raw_family


def qualification_scores(raw_scores: dict[str, float]) -> dict[str, float]:
    return {
        group: max(raw_scores[member] for member in members)
        for group, members in QUALIFICATION_GROUPS.items()
    }


def load_manifest() -> dict[str, Any]:
    payload = json.loads(D1_MANIFEST.read_text(encoding="utf-8"))
    if payload.get("status") != "FROZEN_FOR_D2":
        raise RuntimeError("D1 v1.1 manifest must be FROZEN_FOR_D2")
    if payload.get("schema_version") != "story-defect-d1-validation-manifest.v1.1":
        raise RuntimeError("Unexpected D1 v1.1 manifest schema")
    return payload


def admitted_clean_ids() -> set[str]:
    payload = json.loads(ADMISSION.read_text(encoding="utf-8"))
    return {
        row["source_id"]
        for row in payload["entries"]
        if row["admitted_as_clean_source"]
    }


def calibration_cases() -> list[dict[str, Any]]:
    manifest = load_manifest()
    synthetic = load_synthetic_corpus()
    synthetic_by_id = {case["case_id"]: case for case in synthetic["cases"]}

    rows: list[dict[str, Any]] = []
    source_split: dict[str, str] = {}

    for gold in manifest["cases"]:
        source_id = gold["source_id"]
        split = gold["dataset_split"]
        previous = source_split.get(source_id)
        if previous is not None and previous != split:
            raise RuntimeError(f"source_split_conflict:{source_id}:{previous}:{split}")
        source_split[source_id] = split

        if split != "calibration":
            continue
        case = synthetic_by_id.get(gold["case_id"])
        if case is None:
            raise RuntimeError(f"validated_case_missing_from_corpus:{gold['case_id']}")
        if case["gold"]["family"] != gold["family"]:
            raise RuntimeError(f"validated_family_drift:{gold['case_id']}")

        rows.append({
            "case_id": gold["case_id"],
            "kind": "defect",
            "dataset_split": "calibration",
            "story_family": case["family"],
            "text": case["text"],
            "gold_family": gold["family"],
            "gold_qualification_family": gold["qualification_family"],
            "gold_severity": gold["severity"],
        })

    clean_ids = admitted_clean_ids()
    for source in assign_source_splits(load_source_pool()):
        if source["source_id"] not in clean_ids:
            continue
        if source["dataset_split"] != "calibration":
            continue
        rows.append({
            "case_id": f"clean__{source['source_id']}",
            "kind": "clean",
            "dataset_split": "calibration",
            "story_family": source["family"],
            "text": source["story"],
            "gold_family": None,
            "gold_qualification_family": None,
            "gold_severity": None,
        })

    return sorted(rows, key=lambda row: row["case_id"])


def validate_calibration_partition(rows: list[dict[str, Any]]) -> dict[str, int]:
    if len(rows) != 140:
        raise RuntimeError(f"calibration_case_count_mismatch:{len(rows)}:140")

    defect_rows = [row for row in rows if row["kind"] == "defect"]
    clean_rows = [row for row in rows if row["kind"] == "clean"]
    if len(defect_rows) != 130:
        raise RuntimeError(f"calibration_defect_count_mismatch:{len(defect_rows)}:130")
    if len(clean_rows) != 10:
        raise RuntimeError(f"calibration_clean_count_mismatch:{len(clean_rows)}:10")

    counts: dict[str, int] = defaultdict(int)
    for row in defect_rows:
        counts[str(row["gold_qualification_family"])] += 1

    required_priority = {
        "physical_feasibility": 20,
        "causal_logic": 20,
        "state_continuity": 20,
    }
    for family, minimum in required_priority.items():
        if counts[family] < minimum:
            raise RuntimeError(
                f"priority_family_underpowered:{family}:{counts[family]}:{minimum}"
            )

    return dict(sorted(counts.items()))


def threshold_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_family: dict[str, Any] = {}

    for family in QUALIFICATION_GROUPS:
        positives = [
            row for row in rows
            if row["gold_qualification_family"] == family
        ]
        negatives = [
            row for row in rows
            if row["gold_qualification_family"] != family
        ]

        curve = []
        for threshold in THRESHOLDS:
            tp = sum(
                row["qualification_scores"][family] >= threshold
                for row in positives
            )
            fn = len(positives) - tp
            fp = sum(
                row["qualification_scores"][family] >= threshold
                for row in negatives
            )
            tn = len(negatives) - fp
            curve.append({
                "threshold": threshold,
                "tp": tp,
                "fn": fn,
                "fp": fp,
                "tn": tn,
                "recall": None if not positives else tp / len(positives),
                "precision": None if tp + fp == 0 else tp / (tp + fp),
                "false_positive_rate": None if not negatives else fp / len(negatives),
            })

        target_recall = (
            0.99
            if family in {"physical_feasibility", "causal_logic"}
            else 0.98
        )
        eligible = [
            point
            for point in curve
            if point["recall"] is not None
            and point["recall"] >= target_recall
        ]
        recommended = (
            min(
                eligible,
                key=lambda point: (
                    point["false_positive_rate"],
                    -point["threshold"],
                ),
            )
            if eligible
            else None
        )

        by_family[family] = {
            "positive_cases": len(positives),
            "negative_cases": len(negatives),
            "target_recall": target_recall,
            "recommended_calibration_point": recommended,
            "curve": curve,
        }

    return by_family


def overall_metrics(
    rows: list[dict[str, Any]],
    family_thresholds: dict[str, float],
) -> dict[str, Any]:
    defects = [row for row in rows if row["kind"] == "defect"]
    clean = [row for row in rows if row["kind"] == "clean"]

    detected = 0
    by_family: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "detected": 0}
    )

    for row in defects:
        family = row["gold_qualification_family"]
        by_family[family]["total"] += 1
        if row["qualification_scores"][family] >= family_thresholds[family]:
            detected += 1
            by_family[family]["detected"] += 1

    clean_alarm = sum(
        any(
            row["qualification_scores"][family] >= family_thresholds[family]
            for family in QUALIFICATION_GROUPS
        )
        for row in clean
    )

    return {
        "defect_cases": len(defects),
        "clean_cases": len(clean),
        "defect_recall": None if not defects else detected / len(defects),
        "clean_story_alarm_rate": None if not clean else clean_alarm / len(clean),
        "clean_story_no_alarm_rate": (
            None if not clean else (len(clean) - clean_alarm) / len(clean)
        ),
        "by_family": {
            family: {
                **counts,
                "recall": (
                    None
                    if not counts["total"]
                    else counts["detected"] / counts["total"]
                ),
            }
            for family, counts in sorted(by_family.items())
        },
    }


def usage_cost(body: dict[str, Any]) -> float:
    usage = body.get("usage") or {}
    for key in ("cost", "costUsd", "cost_usd"):
        value = usage.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return 0.0


def main() -> None:
    load_dotenv()
    api_key = os.environ["OPENROUTER_API_KEY"]
    cases = calibration_cases()
    family_counts = validate_calibration_partition(cases)
    questions = build_jev_defect_questions()

    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    total_cost = 0.0
    started = time.perf_counter()

    for index, case in enumerate(cases):
        try:
            body = call_openrouter_jev(
                api_key=api_key,
                state=build_jev_state(
                    story_id=case["case_id"],
                    story_text=case["text"],
                    authoritative_constraints={
                        "exact_age": 4,
                        "reading_mode": "READ_ALOUD",
                        "taxonomy_version": "story-defect-detection.v1.1",
                    },
                ),
                questions=questions,
                timeout_seconds=60.0,
            )
            raw_scores = jev_scores_from_response(body)
            grouped_scores = qualification_scores(raw_scores)
            cost = usage_cost(body)
            total_cost += cost

            rows.append({
                "case_id": case["case_id"],
                "kind": case["kind"],
                "story_family": case["story_family"],
                "gold_family": case["gold_family"],
                "gold_qualification_family": case["gold_qualification_family"],
                "gold_severity": case["gold_severity"],
                "scores": raw_scores,
                "qualification_scores": grouped_scores,
                "usage": body.get("usage"),
                "provider_model": body.get("model"),
                "provider": body.get("provider"),
                "cost_usd": cost,
            })
        except Exception as exc:
            errors.append({
                "case_id": case["case_id"],
                "error": f"{type(exc).__name__}: {exc}",
            })

        if (index + 1) % 10 == 0 or index + 1 == len(cases):
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(
                json.dumps({
                    "schema_version": "story-defect-jev-calibration.v1.1",
                    "status": "IN_PROGRESS",
                    "completed_cases": len(rows),
                    "error_cases": len(errors),
                    "family_counts": family_counts,
                    "rows": rows,
                    "errors": errors,
                    "total_cost_usd": round(total_cost, 9),
                }, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    if errors:
        raise RuntimeError(f"jev_calibration_errors:{len(errors)}")

    family_metrics = threshold_metrics(rows)
    thresholds: dict[str, float] = {}
    unqualified: list[str] = []

    for family, metrics in family_metrics.items():
        point = metrics["recommended_calibration_point"]
        if point is None:
            unqualified.append(family)
        else:
            thresholds[family] = float(point["threshold"])

    calibration_summary = (
        overall_metrics(rows, thresholds)
        if not unqualified
        else None
    )

    output = {
        "schema_version": "story-defect-jev-calibration.v1.1",
        "status": "CALIBRATION_COMPLETE",
        "model_id": "typesafe/jev-1.13",
        "dataset": {
            "manifest": str(D1_MANIFEST),
            "split": "calibration",
            "total_cases": len(rows),
            "defect_cases": sum(row["kind"] == "defect" for row in rows),
            "clean_cases": sum(row["kind"] == "clean" for row in rows),
            "qualification_family_counts": family_counts,
            "held_out_touched": False,
            "response_supplements_included": False,
        },
        "taxonomy": {
            "version": "story-defect-detection.v1.1",
            "qualification_groups": {
                group: list(members)
                for group, members in QUALIFICATION_GROUPS.items()
            },
            "raw_response_causality_preserved": True,
            "qualification_rule": (
                "response_causality is a diagnostic subtype of causal_logic; "
                "causal qualification score is max(causal_logic, response_causality)"
            ),
        },
        "threshold_selection_policy": {
            "per_family_thresholds": True,
            "physical_and_causal_logic_target_recall": 0.99,
            "other_family_target_recall": 0.98,
            "selection": (
                "among thresholds meeting recall target, choose minimum "
                "false-positive-rate then highest threshold"
            ),
            "threshold_grid": THRESHOLDS,
        },
        "family_metrics": family_metrics,
        "recommended_thresholds": thresholds,
        "unqualified_families": unqualified,
        "calibration_summary": calibration_summary,
        "total_cost_usd": round(total_cost, 9),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "rows": rows,
    }
    OUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": output["status"],
        "recommended_thresholds": thresholds,
        "unqualified_families": unqualified,
        "calibration_summary": calibration_summary,
        "total_cost_usd": output["total_cost_usd"],
        "elapsed_seconds": output["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
