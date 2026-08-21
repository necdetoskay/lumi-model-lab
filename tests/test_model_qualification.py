import tempfile
import unittest
from pathlib import Path

from src.leaderboard import leaderboard_rows
from src.model_qualify import generation_error_reasons, screen_gate, technical_screen_gate
from src.model_registry import build_fingerprint, find_by_fingerprint, model_slug


class ModelQualificationTests(unittest.TestCase):
    def test_slug_is_filesystem_safe(self) -> None:
        self.assertEqual(model_slug("aion-labs/aion-3.0"), "aion-labs__aion-3.0")

    def test_fingerprint_changes_with_runtime_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prompt.md"
            path.write_text("hello", encoding="utf-8")
            config = {"name": "v1", "fingerprint_files": [str(path)]}
            first, _ = build_fingerprint("provider/model", config, extra_identity={"judge_model": "judge-a"})
            second, _ = build_fingerprint("provider/model", config, extra_identity={"judge_model": "judge-b"})
            self.assertNotEqual(first, second)

    def test_registry_lookup_uses_fingerprint(self) -> None:
        registry = {"entries": [{"fingerprint": "abc", "model": "m"}]}
        self.assertEqual(find_by_fingerprint(registry, "abc")["model"], "m")
        self.assertIsNone(find_by_fingerprint(registry, "missing"))

    def test_technical_gate_stops_weak_model_before_judge(self) -> None:
        ok, reasons = technical_screen_gate(
            {"technical_pass_rate": 0.6},
            {"min_technical_pass_rate": 0.8},
        )
        self.assertFalse(ok)
        self.assertIn("technical_pass_rate_below_threshold", reasons)

    def test_generation_errors_are_reported_separately(self) -> None:
        manifest = {
            "entries": [
                {
                    "model": "google/gemini-3.7-flash",
                    "spec_path": "data/specifications/benchmark/01.yaml",
                    "generation_status": "error",
                    "generation_error": "Reasoning is mandatory for this endpoint",
                },
                {
                    "model": "other/model",
                    "spec_path": "data/specifications/benchmark/02.yaml",
                    "generation_status": "error",
                    "generation_error": "unrelated",
                },
            ]
        }
        reasons = generation_error_reasons(manifest, "google/gemini-3.7-flash")
        self.assertEqual(reasons[0], "generation_errors_present:1")
        self.assertIn("Reasoning is mandatory", reasons[1])

    def test_full_screen_gate_accepts_good_summary(self) -> None:
        ok, reasons = screen_gate(
            {
                "technical_pass_rate": 1.0,
                "accept_rate": 0.8,
                "judge_average": 4.2,
                "critical_failure_count": 0,
            },
            {
                "min_technical_pass_rate": 0.8,
                "min_judge_accept_rate": 0.8,
                "min_average_judge_score": 4.0,
                "max_critical_failures": 0,
            },
        )
        self.assertTrue(ok)
        self.assertEqual(reasons, [])

    def test_leaderboard_quality_first_cost_tiebreaker(self) -> None:
        registry = {
            "entries": [
                {"model": "b", "status": "qualified", "screen": {"judge_average": 4.2, "technical_pass_rate": 1.0}, "cost": {"cost_usd": 1.0}},
                {"model": "a", "status": "qualified", "screen": {"judge_average": 4.5, "technical_pass_rate": 0.8}, "cost": {"cost_usd": 2.0}},
                {"model": "c", "status": "qualified", "screen": {"judge_average": 4.2, "technical_pass_rate": 1.0}, "cost": {"cost_usd": 0.5}},
            ]
        }
        rows = leaderboard_rows(registry)
        self.assertEqual([row["model"] for row in rows], ["a", "c", "b"])


if __name__ == "__main__":
    unittest.main()
