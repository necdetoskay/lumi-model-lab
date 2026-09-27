from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.visual_contracts import CharacterVisualProfile, VisualCategory, VisualIntent, VisualRequest
from src.visual_generation import generate_visual
from src.visual_ledger import read_jsonl
from src.visual_provider import FixtureVisualProviderAdapter, VisualProviderAdapter
from src.visual_contracts import CompiledPromptPackage, VisualModelProfile


def request() -> VisualRequest:
    return VisualRequest(
        request_id="fixture-request-1",
        profile_id="profile-1",
        category=VisualCategory.CHARACTER_PORTRAIT,
        intent=VisualIntent(subject="Elara", pose="relaxed three-quarter pose"),
        style_id="lumi-storybook-soft",
        model_id="fixture/lumi-visual-v1",
        character_profile=CharacterVisualProfile(
            character_id="elara",
            version="1.0.0",
            apparent_age=11,
            eyes="amber brown",
            hair={"color": "dark chestnut", "length": "shoulder"},
            must_keep=["amber brown eyes", "dark chestnut hair"],
        ),
    )


class ExplodingAdapter(VisualProviderAdapter):
    def generate(self, *, model: VisualModelProfile, compiled: CompiledPromptPackage):
        raise RuntimeError("fixture explosion")


class VisualGenerationTests(unittest.TestCase):
    def test_fixture_generation_persists_invocation_before_artifact_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = generate_visual(
                request(),
                adapter=FixtureVisualProviderAdapter(image_bytes=b"visual-test"),
                evidence_dir=root,
                require_qualified=True,
            )
            self.assertEqual(result.invocation.status, "SUCCESS")
            self.assertEqual(result.invocation.cost_usd, 0.0)
            self.assertEqual(len(result.artifacts), 1)
            self.assertTrue(Path(result.artifacts[0].storage_ref).exists())
            invocations = read_jsonl(root / "visual_invocations.jsonl")
            artifacts = read_jsonl(root / "visual_artifacts.jsonl")
            self.assertEqual(len(invocations), 1)
            self.assertEqual(len(artifacts), 1)
            self.assertEqual(artifacts[0]["invocation_id"], invocations[0]["invocation_id"])

    def test_failed_provider_call_records_error_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(RuntimeError, "fixture explosion"):
                generate_visual(request(), adapter=ExplodingAdapter(), evidence_dir=root)
            invocations = read_jsonl(root / "visual_invocations.jsonl")
            self.assertEqual(len(invocations), 1)
            self.assertEqual(invocations[0]["status"], "ERROR")
            self.assertEqual(read_jsonl(root / "visual_artifacts.jsonl"), [])


if __name__ == "__main__":
    unittest.main()
