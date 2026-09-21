from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import yaml

BENCHMARK_VERSION = "decision-engine-benchmark-v1"
SCORE_MIN = 0
SCORE_MAX = 4


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _round_score(value: float) -> int:
    return max(SCORE_MIN, min(SCORE_MAX, int(math.floor(value + 0.5))))


def quadratic_weighted_kappa(reference: list[int], predicted: list[int]) -> float | None:
    if len(reference) != len(predicted):
        raise ValueError("reference/predicted length mismatch")
    if not reference:
        return None

    size = SCORE_MAX - SCORE_MIN + 1
    observed = [[0.0 for _ in range(size)] for _ in range(size)]
    ref_hist = [0.0 for _ in range(size)]
    pred_hist = [0.0 for _ in range(size)]

    for ref, pred in zip(reference, predicted, strict=True):
        observed[ref][pred] += 1.0
        ref_hist[ref] += 1.0
        pred_hist[pred] += 1.0

    n = float(len(reference))
    denominator = 0.0
    numerator = 0.0
    scale = float((size - 1) ** 2)

    for i in range(size):
        for j in range(size):
            weight = ((i - j) ** 2) / scale
            expected = (ref_hist[i] * pred_hist[j]) / n
            numerator += weight * observed[i][j]
            denominator += weight * expected

    if denominator == 0.0:
        return 1.0 if reference == predicted else 0.0
    return 1.0 - (numerator / denominator)


def ordinal_metrics(reference: list[int], predicted_native: list[float]) -> dict[str, Any]:
    if len(reference) != len(predicted_native):
        raise ValueError("reference/predicted length mismatch")
    if not reference:
        return {
            "case_count": 0,
            "exact_agreement": None,
            "adjacent_agreement": None,
            "mean_absolute_error": None,
            "quadratic_weighted_kappa": None,
        }

    predicted = [_round_score(value) for value in predicted_native]
    n = len(reference)
    exact = sum(1 for ref, pred in zip(reference, predicted, strict=True) if ref == pred)
    adjacent = sum(
        1 for ref, pred in zip(reference, predicted, strict=True) if abs(ref - pred) <= 1
    )
    mae = sum(
        abs(float(ref) - float(pred))
        for ref, pred in zip(reference, predicted_native, strict=True)
    ) / n

    return {
        "case_count": n,
        "exact_agreement": exact / n,
        "adjacent_agreement": adjacent / n,
        "mean_absolute_error": mae,
        "quadratic_weighted_kappa": quadratic_weighted_kappa(reference, predicted),
    }


def _score_distribution(probabilities: Any) -> list[float] | None:
    if not isinstance(probabilities, dict):
        return None
    values: list[float] = []
    for level in range(SCORE_MIN, SCORE_MAX + 1):
        raw = probabilities.get(str(level), probabilities.get(level))
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            return None
        value = float(raw)
        if not math.isfinite(value) or value < 0.0 or value > 1.0:
            return None
        values.append(value)
    if abs(sum(values) - 1.0) > 0.05:
        return None
    return values


def probability_metrics(
    reference: list[int],
    distributions: list[list[float]],
    *,
    bins: int = 10,
) -> dict[str, Any]:
    if len(reference) != len(distributions):
        raise ValueError("reference/distribution length mismatch")
    if not reference:
        return {
            "case_count": 0,
            "multiclass_brier": None,
            "log_loss": None,
            "ece": None,
            "ece_bins": bins,
            "aurc": None,
            "risk_coverage": [],
        }

    brier_total = 0.0
    logloss_total = 0.0
    confidence_rows: list[tuple[float, int]] = []

    for ref, probs in zip(reference, distributions, strict=True):
        for level, probability in enumerate(probs):
            target = 1.0 if level == ref else 0.0
            brier_total += (probability - target) ** 2
        reference_probability = max(probs[ref], 1e-15)
        logloss_total += -math.log(reference_probability)
        predicted = max(range(len(probs)), key=probs.__getitem__)
        confidence_rows.append((max(probs), 1 if predicted == ref else 0))

    n = len(reference)
    ece = 0.0
    for bin_index in range(bins):
        low = bin_index / bins
        high = (bin_index + 1) / bins
        members = [
            row
            for row in confidence_rows
            if (low <= row[0] < high) or (bin_index == bins - 1 and row[0] == 1.0)
        ]
        if not members:
            continue
        mean_conf = sum(row[0] for row in members) / len(members)
        mean_acc = sum(row[1] for row in members) / len(members)
        ece += (len(members) / n) * abs(mean_acc - mean_conf)

    ordered = sorted(confidence_rows, key=lambda row: row[0], reverse=True)
    risk_coverage: list[dict[str, float]] = []
    correct = 0
    for index, (confidence, is_correct) in enumerate(ordered, start=1):
        correct += is_correct
        coverage = index / n
        risk = 1.0 - (correct / index)
        risk_coverage.append(
            {
                "coverage": coverage,
                "risk": risk,
                "minimum_confidence": confidence,
            }
        )

    aurc = sum(point["risk"] for point in risk_coverage) / len(risk_coverage)

    return {
        "case_count": n,
        "multiclass_brier": brier_total / n,
        "log_loss": logloss_total / n,
        "ece": ece,
        "ece_bins": bins,
        "aurc": aurc,
        "risk_coverage": risk_coverage,
    }


def verdict_metrics(
    reference: list[str],
    predicted: list[str],
    *,
    critical: list[bool] | None = None,
) -> dict[str, Any]:
    if len(reference) != len(predicted):
        raise ValueError("reference/predicted length mismatch")
    if critical is not None and len(critical) != len(reference):
        raise ValueError("critical/reference length mismatch")
    allowed = {"PASS", "BLOCK"}
    if any(item not in allowed for item in reference + predicted):
        raise ValueError("verdicts must be PASS/BLOCK")

    counts = {
        "pass_as_pass": 0,
        "pass_as_block": 0,
        "block_as_pass": 0,
        "block_as_block": 0,
    }
    critical_false_pass = 0
    for index, (ref, pred) in enumerate(zip(reference, predicted, strict=True)):
        if ref == "PASS" and pred == "PASS":
            counts["pass_as_pass"] += 1
        elif ref == "PASS" and pred == "BLOCK":
            counts["pass_as_block"] += 1
        elif ref == "BLOCK" and pred == "PASS":
            counts["block_as_pass"] += 1
            if critical and critical[index]:
                critical_false_pass += 1
        else:
            counts["block_as_block"] += 1

    n = len(reference)
    return {
        "case_count": n,
        "confusion": counts,
        "agreement": (
            counts["pass_as_pass"] + counts["block_as_block"]
        ) / n if n else None,
        "false_pass_rate": counts["block_as_pass"] / n if n else None,
        "false_block_rate": counts["pass_as_block"] / n if n else None,
        "critical_false_pass_count": critical_false_pass,
    }


def _atomic_dimensions(rubric: dict[str, Any]) -> list[str]:
    return [
        item["id"]
        for item in rubric.get("dimensions", [])
        if item.get("owner_candidate") in {"decision_engine", "hybrid"}
    ]


def _final_atomic_references(
    gold: dict[str, Any],
    *,
    partition: str,
    dimensions: list[str],
) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for case in gold.get("cases", []):
        if case.get("partition") != partition:
            continue
        ref = case.get("human_reference") or {}
        if ref.get("status") != "final":
            continue
        atomic = ref.get("atomic_scores")
        if not isinstance(atomic, dict):
            continue
        if any(
            isinstance(atomic.get(dimension), bool)
            or not isinstance(atomic.get(dimension), int)
            or not SCORE_MIN <= atomic[dimension] <= SCORE_MAX
            for dimension in dimensions
        ):
            continue
        result[case["case_id"]] = {
            dimension: int(atomic[dimension]) for dimension in dimensions
        }
    return result


def _answer_map(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    answers = row.get("answers") or []
    return {
        answer["question_id"]: answer
        for answer in answers
        if isinstance(answer, dict) and isinstance(answer.get("question_id"), str)
    }


def operational_summary(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "engine_identity": run.get("engine_identity"),
        "case_count": run.get("case_count"),
        "completed_count": run.get("completed_count"),
        "malformed_output_count": run.get("malformed_output_count"),
        "runtime_error_count": run.get("runtime_error_count"),
        "latency_ms": run.get("latency_ms"),
        "dataset_sha256": run.get("dataset_sha256"),
        "experiment_fingerprint": run.get("experiment_fingerprint"),
    }


def benchmark_engine_atomic(
    *,
    references: dict[str, dict[str, int]],
    dimensions: list[str],
    run: dict[str, Any],
) -> dict[str, Any]:
    rows = {
        row["case_id"]: row
        for row in run.get("cases", [])
        if isinstance(row, dict) and isinstance(row.get("case_id"), str)
    }

    per_dimension: dict[str, Any] = {}
    high_confidence_errors: list[dict[str, Any]] = []
    missing_reference_cases = sorted(set(references) - set(rows))

    for dimension in dimensions:
        refs: list[int] = []
        preds: list[float] = []
        prob_refs: list[int] = []
        distributions: list[list[float]] = []

        for case_id, atomic in references.items():
            row = rows.get(case_id)
            if not row or row.get("status") != "complete":
                continue
            answer = _answer_map(row).get(dimension)
            if not answer or answer.get("type") != "score":
                continue
            value = answer.get("value")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue

            ref = atomic[dimension]
            native = float(value)
            refs.append(ref)
            preds.append(native)

            distribution = _score_distribution(answer.get("probabilities"))
            if distribution is not None:
                prob_refs.append(ref)
                distributions.append(distribution)
                confidence = max(distribution)
                if confidence >= 0.90 and _round_score(native) != ref:
                    high_confidence_errors.append(
                        {
                            "case_id": case_id,
                            "dimension": dimension,
                            "reference": ref,
                            "predicted_score": native,
                            "confidence": confidence,
                            "confidence_source": "max_score_probability",
                        }
                    )

        metrics = ordinal_metrics(refs, preds)
        metrics["probability_metrics"] = probability_metrics(
            prob_refs,
            distributions,
        )
        per_dimension[dimension] = metrics

    return {
        "reference_case_count": len(references),
        "missing_reference_case_count": len(missing_reference_cases),
        "missing_reference_cases": missing_reference_cases,
        "per_dimension": per_dimension,
        "high_confidence_errors": high_confidence_errors,
    }


def benchmark(
    *,
    gold_path: Path,
    rubric_path: Path,
    run_paths: list[Path],
    partition: str,
    final_evaluation: bool,
) -> dict[str, Any]:
    if partition == "final_holdout" and not final_evaluation:
        raise ValueError(
            "final_holdout requires --final-evaluation; accidental tuning access is forbidden"
        )

    gold = _json(gold_path)
    rubric = _yaml(rubric_path)
    runs = [_json(path) for path in run_paths]
    dimensions = _atomic_dimensions(rubric)
    references = _final_atomic_references(
        gold,
        partition=partition,
        dimensions=dimensions,
    )

    input_fingerprint = {
        "benchmark_version": BENCHMARK_VERSION,
        "gold_sha256": _sha256(gold_path),
        "rubric_sha256": _sha256(rubric_path),
        "partition": partition,
        "final_evaluation": final_evaluation,
        "run_sha256": [_sha256(path) for path in run_paths],
    }
    benchmark_fingerprint = hashlib.sha256(
        json.dumps(input_fingerprint, sort_keys=True).encode("utf-8")
    ).hexdigest()

    engines: list[dict[str, Any]] = []
    for path, run in zip(run_paths, runs, strict=True):
        item = {
            "run_path": str(path),
            "operational": operational_summary(run),
        }
        if references:
            item["atomic_quality"] = benchmark_engine_atomic(
                references=references,
                dimensions=dimensions,
                run=run,
            )
        else:
            item["atomic_quality"] = None
        engines.append(item)

    status = "READY" if references else "REFERENCE_INCOMPLETE"
    return {
        "schema_version": 1,
        "benchmark_version": BENCHMARK_VERSION,
        "benchmark_fingerprint": benchmark_fingerprint,
        "status": status,
        "partition": partition,
        "final_evaluation": final_evaluation,
        "atomic_dimensions": dimensions,
        "complete_atomic_reference_cases": len(references),
        "gold_case_count": len(gold.get("cases", [])),
        "engines": engines,
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Decision Engine Benchmark Report",
        "",
        f"- Status: **{result['status']}**",
        f"- Partition: `{result['partition']}`",
        f"- Complete atomic reference cases: **{result['complete_atomic_reference_cases']}**",
        f"- Benchmark fingerprint: `{result['benchmark_fingerprint']}`",
        "",
    ]
    if result["status"] != "READY":
        lines.extend(
            [
                "Quality comparison is suppressed because complete final human atomic references are unavailable.",
                "Operational evidence may still be inspected; no quality conclusion is authorized.",
                "",
            ]
        )

    for engine in result["engines"]:
        identity = engine["operational"].get("engine_identity") or {}
        lines.extend(
            [
                f"## {identity.get('engine_family', 'unknown')} / {identity.get('model_id', 'unknown')}",
                "",
                f"- Cases: {engine['operational'].get('case_count')}",
                f"- Completed: {engine['operational'].get('completed_count')}",
                f"- Malformed: {engine['operational'].get('malformed_output_count')}",
                f"- Runtime errors: {engine['operational'].get('runtime_error_count')}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark decision-engine runs against human gold.")
    parser.add_argument(
        "--gold",
        default="data/specifications/judge_gold_corpus_v2.json",
    )
    parser.add_argument(
        "--rubric",
        default="data/specifications/judge_atomic_rubric_v1.yaml",
    )
    parser.add_argument("--engine-run", action="append", default=[])
    parser.add_argument(
        "--partition",
        choices=["calibration", "development_holdout", "final_holdout"],
        default="calibration",
    )
    parser.add_argument("--final-evaluation", action="store_true")
    parser.add_argument("--output-dir", default="runs/decision_benchmark")
    parser.add_argument("--require-reference-ready", action="store_true")
    args = parser.parse_args()

    result = benchmark(
        gold_path=Path(args.gold),
        rubric_path=Path(args.rubric),
        run_paths=[Path(path) for path in args.engine_run],
        partition=args.partition,
        final_evaluation=args.final_evaluation,
    )

    output_dir = Path(args.output_dir) / result["benchmark_fingerprint"]
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "report.md").write_text(
        render_markdown(result),
        encoding="utf-8",
    )

    print(json.dumps({**result, "output_dir": str(output_dir)}, ensure_ascii=False, indent=2))

    if args.require_reference_ready and result["status"] != "READY":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
