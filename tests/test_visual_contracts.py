from __future__ import annotations

import unittest

from pydantic import ValidationError

from src.visual_contracts import (
    CharacterVisualProfile,
    VisualCategory,
    VisualIntent,
    VisualRequest,
)


def character() -> CharacterVisualProfile:
    return CharacterVisualProfile(
        character_id="elara",
        version="1.0.0",
        apparent_age=11,
        skin="light wheat",
        eyes="amber brown",
        hair={"color": "dark chestnut", "length": "shoulder", "texture": "slightly wavy"},
        signature_features=["left braid with turquoise bead"],
        signature_clothing=["moss green explorer jacket"],
        signature_accessories=["brass compass necklace"],
        must_keep=["amber brown eyes", "left braid with turquoise bead"],
    )


class VisualContractTests(unittest.TestCase):
    def test_character_request_requires_character_profile(self) -> None:
        with self.assertRaises(ValidationError):
            VisualRequest(
                request_id="r1",
                profile_id="p1",
                category=VisualCategory.CHARACTER_PORTRAIT,
                intent=VisualIntent(subject="Elara"),
                style_id="lumi-storybook-soft",
            )

    def test_unknown_field_fails_closed(self) -> None:
        payload = character().model_dump(mode="json")
        payload["provider_model"] = "forbidden-leak"
        with self.assertRaises(ValidationError):
            CharacterVisualProfile.model_validate(payload)

    def test_character_request_accepts_canonical_profile(self) -> None:
        request = VisualRequest(
            request_id="r1",
            profile_id="p1",
            category=VisualCategory.CHARACTER_PORTRAIT,
            intent=VisualIntent(subject="Elara", pose="relaxed three-quarter pose"),
            style_id="lumi-storybook-soft",
            character_profile=character(),
        )
        self.assertEqual(request.character_profile.character_id, "elara")


if __name__ == "__main__":
    unittest.main()
