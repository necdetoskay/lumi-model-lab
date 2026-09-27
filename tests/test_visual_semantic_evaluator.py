from __future__ import annotations

import tempfile
import json
import unittest
from unittest.mock import Mock, patch
from pathlib import Path

from src.visual_contracts import CharacterVisualProfile, VisualCategory, VisualIntent, VisualRequest
from src.visual_generation import generate_visual
from src.visual_provider import FixtureVisualProviderAdapter
from src.visual_semantic_evaluator import (
    FixtureVisualSemanticEvaluator,
    OpenRouterVisualSemanticEvaluator,
    evaluate_visual_artifact,
)


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

    @patch("src.visual_semantic_evaluator.requests.post")
    def test_openrouter_evaluator_accepts_content_array_json(self, post: Mock) -> None:
        request = VisualRequest(
            request_id="eval-array",
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
            payload = {
                "status": "PASS",
                "identity_consistency": 1.0,
                "style_consistency": 0.9,
                "scene_correctness": 1.0,
                "required_object_correctness": 1.0,
                "issues": [],
                "summary": "consistent",
            }
            response = Mock()
            response.ok = True
            response.json.return_value = {
                "id": "eval-response",
                "choices": [
                    {"message": {"content": [{"type": "text", "text": json.dumps(payload)}]}}
                ],
                "usage": {"cost": 0.001},
            }
            post.return_value = response
            evaluator = OpenRouterVisualSemanticEvaluator(api_key="test-key")
            evaluation, meta = evaluator.evaluate(
                request=request,
                artifact=generated.artifacts[0],
            )
            self.assertEqual(evaluation.status.value, "PASS")
            self.assertEqual(evaluation.style_consistency, 0.9)
            self.assertEqual(meta["response_id"], "eval-response")


if __name__ == "__main__":
    unittest.main()
