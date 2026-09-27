from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from src.visual_qualification_runner import (
    plan_visual_qualification,
    run_visual_qualification,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "visual_qualification_fixture.yaml"
LIVE_SCREEN_CONFIG = ROOT / "configs" / "visual_qualification_live_screen_v1.yaml"


class VisualQualificationRunnerTests(unittest.TestCase):
    def test_full_fixture_matrix_is_green(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_visual_qualification(CONFIG, evidence_dir=Path(tmp))
            self.assertEqual(report["total_rows"], 40)
            self.assertEqual(report["qualified_rows"], 40)
            self.assertEqual(len(report["routes"]), 40)
            self.assertEqual(len(report["observations"]), 120)
            self.assertEqual(report["plan"]["generation_calls"], 120)
            self.assertEqual(report["plan"]["evaluator_calls"], 120)
            self.assertTrue((Path(tmp) / "qualification_plan.json").exists())
            self.assertTrue((Path(tmp) / "qualification_report.json").exists())

    def test_live_screen_plan_is_bounded_before_provider_access(self) -> None:
        plan = plan_visual_qualification(LIVE_SCREEN_CONFIG)
        self.assertEqual(plan["candidate_cells"], 100)
        self.assertEqual(plan["executable_cells"], 100)
        self.assertEqual(plan["skipped_cells_count"], 0)
        self.assertEqual(plan["generation_calls"], 100)
        self.assertEqual(plan["evaluator_calls"], 100)
        self.assertEqual(plan["total_provider_calls"], 200)
        self.assertEqual(plan["known_generation_cost_usd"], 1.0)
        self.assertFalse(plan["evaluator_cost_known"])
        self.assertEqual(
            plan["unknown_pricing_models"],
            [
                "google/gemini-3.1-flash-image",
                "google/gemini-3.1-flash-lite-image",
                "openai/gpt-image-2.5-sunburst",
            ],
        )

    def test_live_screen_requires_explicit_paid_authorization(self) -> None:
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "fake-key"}):
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(
                    RuntimeError,
                    "LIVE_VISUAL_QUALIFICATION_NOT_AUTHORIZED",
                ):
                    run_visual_qualification(
                        LIVE_SCREEN_CONFIG,
                        evidence_dir=Path(tmp),
                    )

    def test_live_screen_fails_closed_without_provider_key_after_authorization(self) -> None:
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(
                    RuntimeError,
                    "OPENROUTER_API_KEY is required for live visual qualification",
                ):
                    run_visual_qualification(
                        LIVE_SCREEN_CONFIG,
                        evidence_dir=Path(tmp),
                        authorize_paid=True,
                    )

    def test_live_call_cap_blocks_before_provider_access(self) -> None:
        payload = yaml.safe_load(LIVE_SCREEN_CONFIG.read_text())
        payload["execution_guard"]["max_generation_calls"] = 99
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "guarded.yaml"
            config.write_text(yaml.safe_dump(payload, sort_keys=False))
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "fake-key"}):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "VISUAL_QUALIFICATION_GUARD_EXCEEDED",
                ):
                    run_visual_qualification(
                        config,
                        evidence_dir=Path(tmp) / "evidence",
                        authorize_paid=True,
                    )


    def test_explicit_cells_can_reuse_seed_observation_to_reach_three_runs(self) -> None:
        base = yaml.safe_load(CONFIG.read_text())
        base["name"] = "seeded-promotion"
        base.pop("models", None)
        base.pop("styles", None)
        base.pop("categories", None)
        base["cells"] = [
            {
                "model_id": "fixture/lumi-visual-v1",
                "style_id": "lumi-storybook-soft",
                "category": "CHARACTER_PORTRAIT",
            }
        ]
        base["runs_per_cell"] = 2
        base["execution_guard"] = {
            "max_generation_calls": 2,
            "max_evaluator_calls": 2,
            "max_total_provider_calls": 2,
            "max_known_generation_cost_usd": 0.0,
            "fail_on_unknown_pricing": True,
            "require_explicit_paid_authorization": False,
        }

        seed_report = {
            "schema": "visual-qualification-report.v1",
            "name": "screen",
            "provider_mode": "fixture",
            "evaluator_mode": "fixture",
            "observations": [
                {
                    "model_id": "fixture/lumi-visual-v1",
                    "style_id": "lumi-storybook-soft",
                    "category": "CHARACTER_PORTRAIT",
                    "success": True,
                    "validation_pass": True,
                    "identity_consistency": 1.0,
                    "style_consistency": 1.0,
                    "latency_ms": 1,
                    "cost_usd": 0.0,
                    "selected_by_user": None,
                    "retry_count": 0,
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed = root / "seed.json"
            seed.write_text(__import__("json").dumps(seed_report))
            base["seed_reports"] = [str(seed)]
            config = root / "promotion.yaml"
            config.write_text(yaml.safe_dump(base, sort_keys=False))
            report = run_visual_qualification(
                config,
                evidence_dir=root / "evidence",
            )
            self.assertEqual(report["seed_observations_count"], 1)
            self.assertEqual(len(report["new_observations"]), 2)
            self.assertEqual(len(report["observations"]), 3)
            self.assertEqual(report["total_rows"], 1)
            self.assertEqual(report["qualified_rows"], 1)
            self.assertEqual(report["rows"][0]["runs"], 3)
            self.assertTrue(report["rows"][0]["qualified"])
            self.assertEqual(report["plan"]["generation_calls"], 2)
            self.assertEqual(report["plan"]["cells_reaching_min_runs"], 1)


if __name__ == "__main__":
    unittest.main()
