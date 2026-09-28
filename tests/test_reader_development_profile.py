from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from src.reader_development_profile import (
    ReaderDevelopmentProfileV1,
    load_reader_development_profile,
    validate_capability_bridge,
)


PROFILE = Path("data/specifications/reader_profiles/age12_adventure_v1.json")


class ReaderDevelopmentProfileTests(unittest.TestCase):
    def test_age12_profile_loads_and_matches_capability_bridge(self):
        profile = load_reader_development_profile(PROFILE)

        self.assertEqual(profile.exact_age, 12)
        self.assertEqual(profile.narrative_age_tier, "MIDDLE_CHILD")
        self.assertEqual(profile.reading_mode, "INDEPENDENT_READER")
        self.assertGreaterEqual(profile.premise_maturity.target, 4)
        self.assertGreaterEqual(profile.interest_fit.target, 4)
        self.assertGreaterEqual(profile.wonder_discovery.target, 4)
        self.assertIn(
            "premise_too_young",
            {row.key for row in profile.hard_fail_signals},
        )

    def test_readability_cannot_mask_materially_lower_premise_target(self):
        payload = json.loads(PROFILE.read_text(encoding="utf-8"))
        payload["premise_maturity"]["target"] = 1
        payload["premise_maturity"]["floor"] = 1
        payload["language_readability"]["target"] = 5

        with self.assertRaisesRegex(
            ValidationError,
            "language_readability cannot mask",
        ):
            ReaderDevelopmentProfileV1.model_validate(payload)

    def test_capability_bridge_rejects_wrong_age_tier(self):
        payload = json.loads(PROFILE.read_text(encoding="utf-8"))
        payload["narrative_age_tier"] = "TEEN"
        profile = ReaderDevelopmentProfileV1.model_validate(payload)

        with self.assertRaisesRegex(ValueError, "maps to MIDDLE_CHILD"):
            validate_capability_bridge(profile)

    def test_capability_bridge_rejects_wrong_reading_mode(self):
        payload = json.loads(PROFILE.read_text(encoding="utf-8"))
        payload["reading_mode"] = "EARLY_READER"
        profile = ReaderDevelopmentProfileV1.model_validate(payload)

        with self.assertRaisesRegex(
            ValueError,
            "reading_mode must be INDEPENDENT_READER",
        ):
            validate_capability_bridge(profile)

    def test_hard_fail_keys_are_unique(self):
        payload = json.loads(PROFILE.read_text(encoding="utf-8"))
        payload["hard_fail_signals"].append(
            copy.deepcopy(payload["hard_fail_signals"][0])
        )

        with self.assertRaisesRegex(
            ValidationError,
            "duplicate hard_fail_signals",
        ):
            ReaderDevelopmentProfileV1.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
