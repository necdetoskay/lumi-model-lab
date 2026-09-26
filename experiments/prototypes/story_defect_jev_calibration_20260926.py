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

ADMISSION = Path(
    "experiments/fixtures/story_defect_clean_source_admission.tr-age4.v1.json"
)
D1_MANIFEST = Path(
    "experiments/fixtures/story_defect_d1_validation_manifest.tr-age4.v1.json"
)
RESPONSE_SUPPLEMENT = Path(
    "experiments/fixtures/story_defect_response_supplement.tr-age4.v1.json"
)
OUT = Path("runs/story-defect-jev-calibration/result.json")

THRESHOLDS = [round(x / 100, 2) for x in range(1, 100)]

# Response-causality remains visible in raw JEV scores, but qualification treats it
# as a diagnostic subtype of causal logic because independent validators repeatedly
# recognized the semantic defect while disagreeing on the narrower family name.
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

CRITICAL_FOCUS_GROUPS = {
    "physical_feasibility",
    "causal_logic",
    "state_continuity",
}


def qualification_family(raw_family: str | None) -> str | None:
    if raw_family == "response_causality":
        return "causal_logic"
    return raw_family


def qualification_scores(raw_scores: dict[str, float]) -> dict[str, float]:
    return {
        group: max(raw_scores[member] for member in members)
        for group, members in QUALIFICATION_GROUPS.items()
    }


def load_admitted_clean_ids() -> set[str]:
    payload = json.loads(ADMISSION.read_text(encoding="utf-8"))
    return {
        row["source_id"]
        for row in payload["entries"]
        if row["admitted_as_clean_source"]
    }


def load_d1_manifest() -> dict[str, Any]:
    payload = json.loads(D1_MANIFEST.read_text(encoding="utf-8"))
    if payload.get("status") != "D1_COMPLETE_FROZEN":
        raise RuntimeError(
            f"d1_manifest_not_frozen:{payload.get('status')}"
        )
    if not payload.get("summary", {}).get("d1_gate_pass"):
        raise RuntimeError("d1_manifest_gate_not_passed")
    return payload


def calibration_cases() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest = load_d1_manifest()
    base = load_synthetic_corpus()
    supplement = json.loads(RESPONSE_SUPPLEMENT.read_text(encoding="utf-8"))

    base_by_id = {row["case_id"]: row for row in base["cases"]}
    supplement_by_id = {row["case_id"]: row for row in supplement["cases"]}

    rows: list[dict[str, Any]] = []
    for gold in manifest["validated_cases"]:
        if gold["dataset_split"] != "calibration":
            continue

        corpus = gold["corpus"]
        if corpus == "story_defect_corpus.tr-age4.synthetic.v1":
            case = base_by_id.get(gold["case_id"])
        elif corpus == "story_defect_response_supplement.tr-age4.v1":
            case = supplement_by_id.get(gold["case_id"])
        else:
            raise RuntimeError(
                f"unknown_d1_corpus:{corpus}:{gold['case_id']}"
            )
        if case is None:
            raise RuntimeError(
                f"validated_case_missing_from_fixture:{gold['case_id']}"
            )

        raw_family = str(gold["family"])
        grouped_family = qualification_family(raw_family)
        if grouped_family not in QUALIFICATION_GROUPS:
            raise RuntimeError(
                f"qualification_family_unknown:{gold['case_id']}:{grouped_family}"
            )

        rows.append({
            "case_id": gold["case_id"],
            "kind": "defect",
            "dataset_split": "calibration",
            "story_family": case["family"],
            "text": case["text"],
            "gold_family": raw_family,
            "gold_qualification_family": grouped_family,
            "gold_severity": gold["severity"],
            "validation_basis": gold["validation_basis"],
            "source_corpus": corpus,
        })

    admitted = load_admitted_clean_ids()
    for source in assign_source_splits(load_source_pool()):
        if source["source_id"] not in admitted:
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
            "validation_basis": "independently_admitted_clean_source",
            "source_corpus": "story_defect_source_pool.tr-age4.v1",
        })

    defect_count = sum(row["kind"] == "defect" for row in rows)
    clean_count = sum(row["kind"] == "clean" for row in rows)
    expected_defects = int(manifest["summary"]["calibration_validated"])
    if defect_count != expected_defects:
        raise RuntimeError(
            f"calibration_defect_count_mismatch:{defect_count}:{expected_defects}"
        )
    if clean_count <= 0:
        raise RuntimeError("calibration_clean_controls_missing")

    ids = [row["case_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError("calibration_case_id_duplicate")

    return sorted(rows, key=lambda row: row["case_id"]), manifest


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
        } else 0.98
        eligible = [
            point for point in curve
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
    defect_rows = [row for row in rows if row["kind"] == "defect"]
    clean_rows = [row for row in rows if row["kind"] == "clean"]
    detected = 0
    by_family: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "detected": 0}
    )

    for row in defect_rows:
        family = row["gold_qualification_family"]
        by_family[family]["total"] += 1
        if row["qualification_scores"][family] >= family_thresholds[family]:
            detected += 1
            by_family[family]["detected"] += 1

    clean_alarm = 0
    for row in clean_rows:
        if any(
            row["qualification_scores"][family] >= family_thresholds[family]
            for family in QUALIFICATION_GROUPS
        ):
            clean_alarm += 1

    return {
        "defect_cases": len(defect_rows),
        "clean_cases": len(clean_rows),
        "defect_recall": (
            None if not defect_rows else detected / len(defect_rows)
        ),
        "clean_story_alarm_rate": (
            None if not clean_rows else clean_alarm / len(clean_rows)
        ),
        "clean_story_no_alarm_rate": (
            None
            if not clean_rows
            else (len(clean_rows) - clean_alarm) / len(clean_rows)
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
    cases, manifest = calibration_cases()

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
            raw_scores = jev_scores_from_response(body)
            grouped_scores = qualification_scores(raw_scores)
            cost = usage_cost(body)
            total_cost += cost
            rows.append({
                "case_id": case["case_id"],
                "kind": case["kind"],
                "story_family": case["story_family"],
                "gold_family": case["gold_family"],
                "gold_qualification_family": case[
                    "gold_qualification_family"
                ],
                "gold_severity": case["gold_severity"],
                "validation_basis": case["validation_basis"],
                "source_corpus": case["source_corpus"],
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
        overall_metrics(rows, thresholds)
        if not unqualified
        else None
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
            "d1_validated_total": manifest["summary"]["validated_gold"],
            "d1_calibration_defects": manifest["summary"][
                "calibration_validated"
            ],
        },
        "taxonomy": {
            "version": "story-defect-detection.v1.1",
            "qualification_groups": QUALIFICATION_GROUPS,
            "raw_response_causality_preserved": True,
            "qualification_rule": (
                "response_causality is a diagnostic subtype of causal_logic; "
                "causal score is max(causal_logic, response_causality)"
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
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": output["status"],
        "dataset": output["dataset"],
        "recommended_thresholds": thresholds,
        "unqualified_families": unqualified,
        "calibration_summary": calibration_summary,
        "total_cost_usd": output["total_cost_usd"],
        "elapsed_seconds": output["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
