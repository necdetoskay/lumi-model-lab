from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.openrouter_jev import call_openrouter_jev
from src.story_defect_corpus import load_source_pool
from src.story_defect_detection import (
    DEFECT_FAMILIES,
    build_jev_defect_questions,
    build_jev_state,
    jev_scores_from_response,
)
from src.story_defect_synthetic_corpus import load_synthetic_corpus

ADMISSION = Path("experiments/fixtures/story_defect_clean_source_admission.tr-age4.v1.json")
D1_MANIFEST = Path("experiments/fixtures/story_defect_d1_validated_manifest.v1.json")
OUT = Path("runs/story-defect-jev-calibration/result.json")
THRESHOLDS = [round(x / 100, 2) for x in range(1, 100)]


def load_admitted_clean_ids() -> set[str]:
    payload = json.loads(ADMISSION.read_text(encoding="utf-8"))
    return {
        row["source_id"]
        for row in payload["entries"]
        if row["admitted_as_clean_source"]
    }


def load_validated_manifest() -> dict[str, Any]:
    payload = json.loads(D1_MANIFEST.read_text(encoding="utf-8"))
    if payload.get("status") != "FROZEN_FOR_D2":
        raise RuntimeError("D1 validated manifest is not frozen for D2")
    if int(payload.get("summary", {}).get("case_count", 0)) != 203:
        raise RuntimeError("D1 validated manifest case count drift")
    return payload


def source_splits_from_manifest(manifest: dict[str, Any]) -> dict[str, str]:
    splits: dict[str, str] = {}
    for row in manifest["cases"]:
        source_id = row["source_id"]
        split = row["dataset_split"]
        previous = splits.get(source_id)
        if previous is not None and previous != split:
            raise RuntimeError(
                f"validated_source_split_conflict:{source_id}:{previous}:{split}"
            )
        splits[source_id] = split
    return splits


def calibration_cases() -> list[dict[str, Any]]:
    manifest = load_validated_manifest()
    synthetic = load_synthetic_corpus()
    synthetic_by_id = {row["case_id"]: row for row in synthetic["cases"]}

    rows: list[dict[str, Any]] = []
    for gold in manifest["cases"]:
        if gold["dataset_split"] != "calibration":
            continue
        case = synthetic_by_id.get(gold["case_id"])
        if case is None:
            raise RuntimeError(f"validated_case_missing:{gold['case_id']}")
        if case["gold"]["family"] != gold["family"]:
            raise RuntimeError(f"validated_family_drift:{gold['case_id']}")
        rows.append({
            "case_id": gold["case_id"],
            "kind": "defect",
            "dataset_split": "calibration",
            "story_family": case["family"],
            "text": case["text"],
            "gold_family": gold["family"],
            "gold_severity": gold["severity"],
        })

    source_splits = source_splits_from_manifest(manifest)
    admitted = load_admitted_clean_ids()
    pool = load_source_pool()
    for source in pool["sources"]:
        source_id = source["source_id"]
        if source_id not in admitted:
            continue
        split = source_splits.get(source_id)
        if split is None:
            raise RuntimeError(f"clean_source_missing_frozen_split:{source_id}")
        if split != "calibration":
            continue
        rows.append({
            "case_id": f"clean__{source_id}",
            "kind": "clean",
            "dataset_split": "calibration",
            "story_family": source["family"],
            "text": source["story"],
            "gold_family": None,
            "gold_severity": None,
        })

    rows = sorted(rows, key=lambda row: row["case_id"])
    defect_count = sum(row["kind"] == "defect" for row in rows)
    clean_count = sum(row["kind"] == "clean" for row in rows)
    if defect_count != 130 or clean_count != 10 or len(rows) != 140:
        raise RuntimeError(
            f"calibration_case_count_mismatch:total={len(rows)}:"
            f"defect={defect_count}:clean={clean_count}"
        )
    return rows


def threshold_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_family: dict[str, Any] = {}
    for family in DEFECT_FAMILIES:
        positives = [row for row in rows if row["gold_family"] == family]
        negatives = [row for row in rows if row["gold_family"] != family]
        curve = []
        for threshold in THRESHOLDS:
            tp = sum(row["scores"][family] >= threshold for row in positives)
            fn = len(positives) - tp
            fp = sum(row["scores"][family] >= threshold for row in negatives)
            tn = len(negatives) - fp
            recall = None if not positives else tp / len(positives)
            precision = None if tp + fp == 0 else tp / (tp + fp)
            fpr = None if not negatives else fp / len(negatives)
            curve.append({
                "threshold": threshold,
                "tp": tp,
                "fn": fn,
                "fp": fp,
                "tn": tn,
                "recall": recall,
                "precision": precision,
                "false_positive_rate": fpr,
            })

        target_recall = 0.99 if family in {
            "physical_feasibility",
            "causal_logic",
            "response_causality",
        } else 0.98
        eligible = [
            point
            for point in curve
            if point["recall"] is not None and point["recall"] >= target_recall
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
    defect_rows = [row for row in rows if row["kind"] == "defect"]
    clean_rows = [row for row in rows if row["kind"] == "clean"]

    detected = 0
    by_family: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "detected": 0}
    )
    for row in defect_rows:
        family = row["gold_family"]
        by_family[family]["total"] += 1
        if row["scores"][family] >= family_thresholds[family]:
            detected += 1
            by_family[family]["detected"] += 1

    clean_alarm = sum(
        any(row["scores"][family] >= family_thresholds[family] for family in DEFECT_FAMILIES)
        for row in clean_rows
    )

    return {
        "defect_cases": len(defect_rows),
        "clean_cases": len(clean_rows),
        "defect_recall": detected / len(defect_rows),
        "clean_story_alarm_rate": clean_alarm / len(clean_rows),
        "clean_story_no_alarm_rate": (len(clean_rows) - clean_alarm) / len(clean_rows),
        "by_family": {
            family: {
                **counts,
                "recall": counts["detected"] / counts["total"],
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
                    },
                ),
                questions=questions,
                timeout_seconds=60.0,
            )
            scores = jev_scores_from_response(body)
            cost = usage_cost(body)
            total_cost += cost
            rows.append({
                "case_id": case["case_id"],
                "kind": case["kind"],
                "story_family": case["story_family"],
                "gold_family": case["gold_family"],
                "gold_severity": case["gold_severity"],
                "scores": scores,
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
                    "schema_version": "story-defect-jev-calibration.v1",
                    "status": "IN_PROGRESS",
                    "completed_cases": len(rows),
                    "error_cases": len(errors),
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
        overall_metrics(rows, thresholds) if not unqualified else None
    )

    output = {
        "schema_version": "story-defect-jev-calibration.v1",
        "status": "CALIBRATION_COMPLETE",
        "model_id": "typesafe/jev-1.13",
        "dataset": {
            "split": "calibration",
            "total_cases": len(rows),
            "defect_cases": sum(row["kind"] == "defect" for row in rows),
            "clean_cases": sum(row["kind"] == "clean" for row in rows),
            "held_out_touched": False,
            "d1_manifest": str(D1_MANIFEST),
        },
        "threshold_selection_policy": {
            "per_family_thresholds": True,
            "physical_causal_response_target_recall": 0.99,
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
