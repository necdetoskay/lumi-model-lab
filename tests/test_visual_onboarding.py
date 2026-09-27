from __future__ import annotations

import unittest

from src.visual_contracts import CharacterVisualProfile, VisualCategory, VisualIntent, VisualRequest
from src.visual_onboarding import (
    VisualOnboardingCandidate,
    build_onboarding_requests,
    select_visual_preference,
)


def base_request() -> VisualRequest:
    return VisualRequest(
        request_id="onboard",
        profile_id="profile-1",
        category=VisualCategory.CHARACTER_PORTRAIT,
        intent=VisualIntent(subject="Elara"),
        style_id="lumi-storybook-soft",
        character_profile=CharacterVisualProfile(
            character_id="elara",
            version="1.0.0",
            apparent_age=11,
            eyes="amber brown",
            hair={"color": "dark chestnut"},
            must_keep=["amber brown eyes"],
        ),
    )


class VisualOnboardingTests(unittest.TestCase):
    def test_same_subject_expands_across_styles(self) -> None:
        requests = build_onboarding_requests(
            base_request(),
            style_ids=["lumi-storybook-soft", "lumi-soft-3d", "lumi-watercolor"],
        )
        self.assertEqual(len(requests), 3)
        self.assertEqual(len({item.intent.subject for item in requests}), 1)
        self.assertEqual(len({item.style_id for item in requests}), 3)

    def test_selection_persists_style_not_model_lock(self) -> None:
        preference = select_visual_preference(
            profile_id="profile-1",
            candidate=VisualOnboardingCandidate(
                candidate_id="candidate-b",
                style_id="lumi-soft-3d",
                style_version="1.0.0",
                model_id="google/gemini-3.1-flash-image",
                artifact_id="artifact-b",
            ),
        )
        self.assertEqual(preference.preferred_style_id, "lumi-soft-3d")
        self.assertNotIn("model", preference.model_dump())


if __name__ == "__main__":
    unittest.main()
