from __future__ import annotations

import unittest

from src.teacher_benchmark import summarize_entries


class TeacherBenchmarkSummaryTests(unittest.TestCase):
    def test_quality_and_reliability_metrics_are_aggregated_per_model(self) -> None:
        entries = [
            {
                "model": "model-a",
                "generation_status": "complete",
                "technical_pass": True,
                "teacher_cost_usd": 0.10,
                "judge_status": "complete",
                "judge_accepted": True,
                "judge_average": 4.5,
                "judge_scores": {
                    "instruction_following": 5,
                    "coherence": 5,
                    "character_consistency": 4,
                    "age_appropriateness": 5,
                    "creativity": 4,
                    "style_quality": 4,
                },
                "critical_failures": [],
                "judge_cost_usd": 0.20,
            },
            {
                "model": "model-a",
                "generation_status": "complete",
                "technical_pass": False,
                "teacher_cost_usd": 0.08,
            },
            {
                "model": "model-b",
                "generation_status": "complete",
                "technical_pass": True,
                "teacher_cost_usd": 0.03,
                "judge_status": "complete",
                "judge_accepted": False,
                "judge_average": 2.5,
                "judge_scores": {
                    "instruction_following": 3,
                    "coherence": 2,
                    "character_consistency": 3,
                    "age_appropriateness": 3,
                    "creativity": 2,
                    "style_quality": 2,
                },
                "critical_failures": ["repetition"],
                "judge_cost_usd": 0.18,
            },
        ]

        result = summarize_entries(entries, ["model-a", "model-b"])

        self.assertEqual(result["model-a"]["technical_pass_rate"], 0.5)
        self.assertEqual(result["model-a"]["judge_average"], 4.5)
        self.assertEqual(result["model-a"]["criterion_averages"]["coherence"], 5.0)
        self.assertEqual(result["model-a"]["teacher_cost_total_usd"], 0.18)
        self.assertEqual(result["model-b"]["critical_failure_count"], 1)
        self.assertEqual(result["model-b"]["accept_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
