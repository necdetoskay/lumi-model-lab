from __future__ import annotations

import unittest

from src.visual_contracts import CompiledPromptPackage
from src.visual_model_registry import require_visual_model_profile
from src.visual_provider import OpenRouterImageAdapter


def compiled(*, refs=None, n=1) -> CompiledPromptPackage:
    return CompiledPromptPackage(
        positive_prompt="Draw the canonical subject.",
        provider_options={"aspect_ratio": "3:4", "n": n},
        input_references=refs or [],
        continuity_constraints=[],
        style_profile_sha256="a" * 64,
        model_profile_sha256="b" * 64,
        template_id="character-portrait.v1",
        template_version="1.0.0",
    )


class VisualProviderTests(unittest.TestCase):
    def test_openrouter_payload_uses_unified_image_api_shape(self) -> None:
        adapter = OpenRouterImageAdapter(api_key="test-key")
        model = require_visual_model_profile("google/gemini-3.1-flash-image")
        payload = adapter._payload(model=model, compiled=compiled())
        self.assertEqual(payload["model"], "google/gemini-3.1-flash-image")
        self.assertEqual(payload["prompt"], "Draw the canonical subject.")
        self.assertEqual(payload["aspect_ratio"], "3:4")
        self.assertNotIn("n", payload)

    def test_reference_images_use_openrouter_input_references_shape(self) -> None:
        adapter = OpenRouterImageAdapter(api_key="test-key")
        model = require_visual_model_profile("openai/gpt-image-2.5-sunburst")
        payload = adapter._payload(
            model=model,
            compiled=compiled(refs=["data:image/png;base64,AAAA"]),
        )
        self.assertEqual(
            payload["input_references"][0],
            {
                "type": "image_url",
                "image_url": {"url": "data:image/png;base64,AAAA"},
            },
        )

    def test_model_reference_limit_is_fail_closed(self) -> None:
        adapter = OpenRouterImageAdapter(api_key="test-key")
        model = require_visual_model_profile("meta/muse-image")
        with self.assertRaisesRegex(ValueError, "at most 1 references"):
            adapter._payload(
                model=model,
                compiled=compiled(refs=[
                    "data:image/png;base64,AAAA",
                    "data:image/png;base64,BBBB",
                ]),
            )


if __name__ == "__main__":
    unittest.main()
