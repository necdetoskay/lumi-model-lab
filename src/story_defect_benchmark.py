from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.story_defect_detection import DEFECT_FAMILIES


BLOCKING_SEVERITIES = {"serious", "critical"}


def _safe_rate(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def score_defect_predictions(
    cases: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
) -> dict[str, Any]:
    prediction_by_case = {row["case_id"]: row for row in predictions}
    case_ids = {row["case_id"] for row in cases}
    extra_predictions = sorted(set(prediction_by_case) - case_ids)
    if extra_predictions:
        raise ValueError("Predictions contain unknown cases: " + ", ".join(extra_predictions))

    tp = fp = fn = 0
    blocking_tp = blocking_fn = 0
    critical_tp = critical_fn = 0
    locator_hits = locator_total = 0
    family_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fn": 0})

    missed: list[dict[str, Any]] = []
    false_positives: list[dict[str, Any]] = []

    for case in cases:
        case_id = case["case_id"]
        gold = case["gold"]
        findings = (prediction_by_case.get(case_id) or {}).get("findings") or []

        if not gold.get("defect_present"):
            if findings:
                fp += len(findings)
                false_positives.append({"case_id": case_id, "findings": findings})
            continue

        family = gold["family"]
        severity = gold["severity"]
        gold_spans = set(gold.get("span_ids") or [])
        matching = [finding for finding in findings if finding.get("family") == family]

        if matching:
            tp += 1
            family_counts[family]["tp"] += 1
            if severity in BLOCKING_SEVERITIES:
                blocking_tp += 1
            if severity == "critical":
                critical_tp += 1
            locator_total += 1
            if any(gold_spans.intersection(finding.get("span_ids") or []) for finding in matching):
                locator_hits += 1

            wrong_family_findings = [finding for finding in findings if finding.get("family") != family]
            fp += len(wrong_family_findings)
            if wrong_family_findings:
                false_positives.append(
                    {"case_id": case_id, "findings": wrong_family_findings}
                )
        else:
            fn += 1
            family_counts[family]["fn"] += 1
            if severity in BLOCKING_SEVERITIES:
                blocking_fn += 1
            if severity == "critical":
                critical_fn += 1
            missed.append(
                {
                    "case_id": case_id,
                    "family": family,
                    "severity": severity,
                    "span_ids": sorted(gold_spans),
                }
            )
            fp += len(findings)
            if findings:
                false_positives.append({"case_id": case_id, "findings": findings})

    precision = _safe_rate(tp, tp + fp)
    recall = _safe_rate(tp, tp + fn)
    blocking_recall = _safe_rate(blocking_tp, blocking_tp + blocking_fn)
    critical_recall = _safe_rate(critical_tp, critical_tp + critical_fn)

    per_family: dict[str, Any] = {}
    for family in DEFECT_FAMILIES:
        counts = family_counts[family]
        per_family[family] = {
            **counts,
            "recall": _safe_rate(counts["tp"], counts["tp"] + counts["fn"]),
        }

    return {
        "cases": len(cases),
        "true_positive_cases": tp,
        "false_positive_findings": fp,
        "false_negative_cases": fn,
        "precision": precision,
        "recall": recall,
        "serious_critical_recall": blocking_recall,
        "critical_recall": critical_recall,
        "span_locator_recall": _safe_rate(locator_hits, locator_total),
        "per_family": per_family,
        "missed": missed,
        "false_positives": false_positives,
    }
