from __future__ import annotations

import unittest

from src.visual_contracts import VisualCategory
from src.visual_qualification import (
    VisualQualificationObservation,
    VisualQualificationThresholds,
    aggregate_visual_qualification,
)
from src.visual_router import route_visual_model


def observations(model_id: str, *, cost: float, latency: int, identity: float, style: float):
    return [
        VisualQualificationObservation(
            model_id=model_id,
            style_id="lumi-storybook-soft",
            category=VisualCategory.CHARACTER_PORTRAIT,
            success=True,
            validation_pass=True,
            identity_consistency=identity,
            style_consistency=style,
            latency_ms=latency + index,
            cost_usd=cost,
            selected_by_user=(index % 2 == 0),
        )
        for index in range(3)
    ]


class VisualQualificationTests(unittest.TestCase):
    def test_matrix_qualifies_only_complete_evidence(self) -> None:
        rows = aggregate_visual_qualification(
            observations(
                "fixture/lumi-visual-v1",
                cost=0.0,
                latency=5,
                identity=1.0,
                style=1.0,
            ),
            thresholds=VisualQualificationThresholds(min_runs=3),
        )
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0].qualified)
        self.assertEqual(rows[0].runs, 3)

    def test_insufficient_runs_fail_closed(self) -> None:
        rows = aggregate_visual_qualification(
            observations(
                "fixture/lumi-visual-v1",
                cost=0.0,
                latency=5,
                identity=1.0,
                style=1.0,
            )[:1],
            thresholds=VisualQualificationThresholds(min_runs=3),
        )
        self.assertFalse(rows[0].qualified)
        self.assertIn("INSUFFICIENT_RUNS", rows[0].rejection_reasons)

    def test_router_uses_qualified_evidence_not_user_model_lock(self) -> None:
        rows = aggregate_visual_qualification(
            observations(
                "fixture/lumi-visual-v1",
                cost=0.0,
                latency=5,
                identity=1.0,
                style=1.0,
            )
        )
        decision = route_visual_model(
            category=VisualCategory.CHARACTER_PORTRAIT,
            style_id="lumi-storybook-soft",
            rows=rows,
        )
        self.assertEqual(decision.model_id, "fixture/lumi-visual-v1")
        self.assertEqual(decision.style_id, "lumi-storybook-soft")

    def test_router_fails_when_no_qualified_evidence_exists(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "VISUAL_ROUTE_NO_QUALIFIED_MODEL"):
            route_visual_model(
                category=VisualCategory.CHARACTER_PORTRAIT,
                style_id="lumi-storybook-soft",
                rows=[],
            )


if __name__ == "__main__":
    unittest.main()
