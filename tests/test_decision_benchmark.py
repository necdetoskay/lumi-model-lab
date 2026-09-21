import json
import math
import tempfile
import unittest
from pathlib import Path

import yaml

from src.decision_benchmark import (
    benchmark,
    ordinal_metrics,
    probability_metrics,
    quadratic_weighted_kappa,
    verdict_metrics,
)


class DecisionBenchmarkMetricTests(unittest.TestCase):
    def test_ordinal_metrics_perfect(self) -> None:
        result = ordinal_metrics([0, 1, 2, 3, 4], [0.0, 1.0, 2.0, 3.0, 4.0])
        self.assertEqual(result["exact_agreement"], 1.0)
        self.assertEqual(result["adjacent_agreement"], 1.0)
        self.assertEqual(result["mean_absolute_error"], 0.0)
        self.assertAlmostEqual(result["quadratic_weighted_kappa"], 1.0)

    def test_weighted_kappa_penalizes_far_errors(self) -> None:
        near = quadratic_weighted_kappa([0, 1, 2, 3, 4], [1, 1, 2, 3, 3])
        far = quadratic_weighted_kappa([0, 1, 2, 3, 4], [4, 3, 2, 1, 0])
        self.assertIsNotNone(near)
        self.assertIsNotNone(far)
        self.assertGreater(near, far)

    def test_probability_metrics_perfect_distribution(self) -> None:
        refs = [0, 4]
        distributions = [
            [1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0],
        ]
        result = probability_metrics(refs, distributions)
        self.assertEqual(result["multiclass_brier"], 0.0)
        self.assertAlmostEqual(result["log_loss"], 0.0)
        self.assertAlmostEqual(result["ece"], 0.0)
        self.assertAlmostEqual(result["aurc"], 0.0)

    def test_verdict_metrics_tracks_critical_false_pass(self) -> None:
        result = verdict_metrics(
            ["PASS", "BLOCK", "BLOCK"],
            ["PASS", "PASS", "BLOCK"],
            critical=[False, True, True],
        )
        self.assertEqual(result["confusion"]["block_as_pass"], 1)
        self.assertEqual(result["critical_false_pass_count"], 1)


class DecisionBenchmarkReadinessTests(unittest.TestCase):
    def _write_inputs(self, root: Path, *, final_reference: bool) -> tuple[Path, Path, Path]:
        dimensions = [
            {
                "id": "contract_alignment",
                "owner_candidate": "decision_engine",
            }
        ]
        rubric = {
            "dimensions": dimensions,
        }
        human_reference = {"status": "pending_blind_review"}
        if final_reference:
            human_reference = {
                "status": "final",
                "atomic_scores": {"contract_alignment": 4},
            }
        gold = {
            "cases": [
                {
                    "case_id": "c1",
                    "partition": "calibration",
                    "human_reference": human_reference,
                }
            ]
        }
        run = {
            "engine_identity": {
                "engine_family": "fixture",
                "model_id": "fixture-a",
            },
            "case_count": 1,
            "completed_count": 1,
            "malformed_output_count": 0,
            "runtime_error_count": 0,
            "latency_ms": {"overall_p50": 1.0, "overall_p95": 1.0},
            "dataset_sha256": "x",
            "experiment_fingerprint": "y",
            "cases": [
                {
                    "case_id": "c1",
                    "status": "complete",
                    "answers": [
                        {
                            "question_id": "contract_alignment",
                            "type": "score",
                            "value": 4.0,
                            "probabilities": {
                                "0": 0.0,
                                "1": 0.0,
                                "2": 0.0,
                                "3": 0.0,
                                "4": 1.0,
                            },
                        }
                    ],
                }
            ],
        }

        gold_path = root / "gold.json"
        rubric_path = root / "rubric.yaml"
        run_path = root / "run.json"
        gold_path.write_text(json.dumps(gold), encoding="utf-8")
        rubric_path.write_text(yaml.safe_dump(rubric), encoding="utf-8")
        run_path.write_text(json.dumps(run), encoding="utf-8")
        return gold_path, rubric_path, run_path

    def test_incomplete_reference_suppresses_quality_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gold, rubric, run = self._write_inputs(Path(tmp), final_reference=False)
            result = benchmark(
                gold_path=gold,
                rubric_path=rubric,
                run_paths=[run],
                partition="calibration",
                final_evaluation=False,
            )
            self.assertEqual(result["status"], "REFERENCE_INCOMPLETE")
            self.assertIsNone(result["engines"][0]["atomic_quality"])

    def test_complete_reference_enables_atomic_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gold, rubric, run = self._write_inputs(Path(tmp), final_reference=True)
            result = benchmark(
                gold_path=gold,
                rubric_path=rubric,
                run_paths=[run],
                partition="calibration",
                final_evaluation=False,
            )
            self.assertEqual(result["status"], "READY")
            metrics = result["engines"][0]["atomic_quality"]["per_dimension"]["contract_alignment"]
            self.assertEqual(metrics["exact_agreement"], 1.0)
            self.assertEqual(metrics["probability_metrics"]["multiclass_brier"], 0.0)

    def test_final_holdout_requires_explicit_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gold, rubric, run = self._write_inputs(Path(tmp), final_reference=True)
            with self.assertRaises(ValueError):
                benchmark(
                    gold_path=gold,
                    rubric_path=rubric,
                    run_paths=[run],
                    partition="final_holdout",
                    final_evaluation=False,
                )


if __name__ == "__main__":
    unittest.main()
