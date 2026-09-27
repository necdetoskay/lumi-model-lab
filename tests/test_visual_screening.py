from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from src.visual_screening import (
    VisualScreeningPolicy,
    build_promotion_config,
    select_visual_promotion_cells,
)


def row(
    model_id: str,
    *,
    identity: float,
    style: float,
    latency: float,
    cost: float,
    validation: float = 1.0,
    success: float = 1.0,
) -> dict:
    return {
        "model_id": model_id,
        "style_id": "lumi-storybook-soft",
        "category": "CHARACTER_PORTRAIT",
        "runs": 1,
        "success_rate": success,
        "validation_pass_rate": validation,
        "identity_consistency": identity,
        "style_consistency": style,
        "user_selection_rate": None,
        "retry_rate": 0.0,
        "average_latency_ms": latency,
        "p95_latency_ms": latency,
        "average_cost_usd": cost,
        "cost_per_accepted_image_usd": cost,
        "qualified": False,
        "rejection_reasons": ["INSUFFICIENT_RUNS"],
    }


class VisualScreeningTests(unittest.TestCase):
    def test_screening_selects_only_eligible_top_two_without_qualifying_them(self) -> None:
        report = {
            "schema": "visual-qualification-report.v1",
            "name": "screen",
            "rows": [
                row("fixture/lumi-visual-v1", identity=0.95, style=0.95, latency=10, cost=0.03),
                row("meta/muse-image", identity=0.90, style=0.92, latency=20, cost=0.01),
                row(
                    "bytedance-seed/seedream-4.5",
                    identity=0.99,
                    style=0.99,
                    latency=8,
                    cost=0.04,
                    validation=0.0,
                ),
            ],
        }
        shortlist = select_visual_promotion_cells(
            report,
            policy=VisualScreeningPolicy(top_k_per_cell=2),
        )
        self.assertEqual(shortlist["selected_cells_count"], 2)
        self.assertEqual(
            {item["model_id"] for item in shortlist["selected_cells"]},
            {"fixture/lumi-visual-v1", "meta/muse-image"},
        )
        self.assertEqual(shortlist["groups_without_candidates"], 0)

    def test_promotion_config_reuses_screen_as_seed_and_adds_only_two_runs(self) -> None:
        base = yaml.safe_load(
            Path("configs/visual_qualification_live_screen_v1.yaml").read_text()
        )
        shortlist = {
            "schema": "visual-screening-shortlist.v1",
            "source_report": "screen",
            "top_k_per_cell": 2,
            "selected_cells": [
                {
                    "model_id": "meta/muse-image",
                    "style_id": "lumi-storybook-soft",
                    "category": "CHARACTER_PORTRAIT",
                },
                {
                    "model_id": "bytedance-seed/seedream-4.5",
                    "style_id": "lumi-storybook-soft",
                    "category": "CHARACTER_PORTRAIT",
                },
            ],
            "selected_cells_count": 2,
            "groups": [],
            "groups_without_candidates": 0,
        }
        policy = VisualScreeningPolicy.model_validate(base["screening"])
        config = build_promotion_config(
            base_config=base,
            shortlist=shortlist,
            seed_report_path="runs/screen/qualification_report.json",
            policy=policy,
        )
        self.assertEqual(config["runs_per_cell"], 2)
        self.assertEqual(len(config["cells"]), 2)
        self.assertEqual(
            config["seed_reports"],
            ["runs/screen/qualification_report.json"],
        )
        self.assertEqual(config["execution_guard"]["max_generation_calls"], 4)
        self.assertEqual(config["execution_guard"]["max_total_provider_calls"], 8)
        self.assertNotIn("models", config)
        self.assertNotIn("styles", config)
        self.assertNotIn("categories", config)


if __name__ == "__main__":
    unittest.main()
