from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.visual_contracts import CharacterVisualProfile, VisualCategory, VisualIntent, VisualRequest
from src.visual_generation import generate_visual
from src.visual_provider import FixtureVisualProviderAdapter
from src.visual_semantic_evaluator import FixtureVisualSemanticEvaluator, evaluate_visual_artifact


class VisualSemanticEvaluatorTests(unittest.TestCase):
    def test_fixture_evaluator_records_cost_latency_and_result(self) -> None:
        request = VisualRequest(
            request_id="eval-1",
            profile_id="profile-1",
            category=VisualCategory.CHARACTER_PORTRAIT,
            intent=VisualIntent(subject="Elara"),
            style_id="lumi-storybook-soft",
            model_id="fixture/lumi-visual-v1",
            character_profile=CharacterVisualProfile(
                character_id="elara",
                version="1.0.0",
                apparent_age=11,
                eyes="amber brown",
                hair={"color": "dark chestnut"},
                must_keep=["amber brown eyes"],
            ),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            generated = generate_visual(
                request,
                adapter=FixtureVisualProviderAdapter(),
                evidence_dir=root,
                require_qualified=True,
            )
            record = evaluate_visual_artifact(
                request=request,
                artifact=generated.artifacts[0],
                evaluator=FixtureVisualSemanticEvaluator(),
                evidence_dir=root,
            )
            self.assertEqual(record.result.status.value, "PASS")
            self.assertEqual(record.cost_usd, 0.0)
            self.assertTrue((root / "visual_evaluations.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
