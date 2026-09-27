from __future__ import annotations

import unittest

from src.visual_contracts import VisualCategory
from src.visual_model_registry import (
    require_visual_model_profile,
    visual_model_profile_identity,
)
from src.visual_style_registry import (
    resolve_visual_style_profile,
    visual_style_profile_identity,
)


class VisualRegistryTests(unittest.TestCase):
    def test_fixture_profile_is_qualified(self) -> None:
        profile = require_visual_model_profile(
            "fixture/lumi-visual-v1",
            category=VisualCategory.CHARACTER_PORTRAIT,
            style_id="lumi-storybook-soft",
            require_qualified=True,
        )
        self.assertTrue(profile.qualification.ready)

    def test_live_profiles_exist_but_start_unqualified(self) -> None:
        for model_id in (
            "google/gemini-3.1-flash-image",
            "google/gemini-3.1-flash-lite-image",
            "bytedance-seed/seedream-4.5",
            "openai/gpt-image-2.5-sunburst",
            "meta/muse-image",
        ):
            profile = require_visual_model_profile(model_id)
            self.assertFalse(profile.qualification.ready)
            with self.assertRaisesRegex(RuntimeError, "VISUAL_MODEL_NOT_QUALIFIED"):
                require_visual_model_profile(model_id, require_qualified=True)

    def test_unknown_model_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "VISUAL_MODEL_PROFILE_MISSING"):
            require_visual_model_profile("vendor/unknown-image")

    def test_profile_identity_is_stable_shape(self) -> None:
        identity = visual_model_profile_identity("fixture/lumi-visual-v1")
        self.assertEqual(set(identity), {
            "profile_sha256", "runtime_contract_sha256", "prompt_policy_sha256"
        })
        self.assertTrue(all(len(value) == 64 for value in identity.values()))

    def test_style_profiles_resolve_and_fingerprint(self) -> None:
        style = resolve_visual_style_profile("lumi-storybook-soft")
        identity = visual_style_profile_identity(style.id, style.version)
        self.assertEqual(style.display_name, "Soft Storybook")
        self.assertEqual(len(identity["profile_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
