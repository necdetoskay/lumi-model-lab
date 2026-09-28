from __future__ import annotations

import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from src.reader_profile_v2 import ReaderDevelopmentProfileV2


PROFILE = Path("data/specifications/reader_profiles/age12_adventure_v2.json")


class ReaderDevelopmentProfileV2Tests(unittest.TestCase):
    def test_age12_profile_is_complete_and_explicitly_separates_maturity_from_language(self):
        profile = ReaderDevelopmentProfileV2.model_validate_json(
            PROFILE.read_text(encoding="utf-8")
        )
        self.assertEqual(profile.exact_age, 12)
        self.assertEqual(profile.audience_band, "OLDER_CHILD")
        self.assertEqual(profile.standard_session.target_words_min, 1600)
        self.assertEqual(profile.standard_session.target_words_max, 2500)

        self.assertEqual(profile.capability_bridge.narrative_age_tier, "MIDDLE_CHILD")
        self.assertEqual(profile.capability_bridge.reading_mode, "INDEPENDENT_READER")
        self.assertEqual(
            profile.capability_bridge.qualification_standard_target_words,
            2800,
        )
        self.assertTrue(
            profile.capability_bridge.product_session_length_is_separate_authority
        )

        targets = {row.name: row.target_level for row in profile.dimensions}
        self.assertGreaterEqual(targets["PREMISE_MATURITY"], 4)
        self.assertGreaterEqual(targets["AGENCY_COMPLEXITY"], 4)
        self.assertGreaterEqual(targets["WONDER_DISCOVERY"], 4)
        self.assertLess(
            targets["LANGUAGE_READABILITY"],
            targets["PREMISE_MATURITY"] + 1,
        )

        reject_text = " ".join(profile.reject_signals).lower()
        self.assertIn("pretend-play", reject_text)
        self.assertIn("difficult vocabulary", reject_text)

    def test_rejects_missing_dimension(self):
        payload = json.loads(PROFILE.read_text(encoding="utf-8"))
        payload["dimensions"] = payload["dimensions"][:-1]
        with self.assertRaisesRegex(ValidationError, "dimensions must be complete"):
            ReaderDevelopmentProfileV2.model_validate(payload)

    def test_rejects_capability_bridge_drift(self):
        payload = json.loads(PROFILE.read_text(encoding="utf-8"))
        payload["capability_bridge"]["narrative_age_tier"] = "TEEN"
        with self.assertRaisesRegex(ValidationError, "maps to MIDDLE_CHILD"):
            ReaderDevelopmentProfileV2.model_validate(payload)

    def test_rejects_standard_band_in_optional_sessions(self):
        payload = json.loads(PROFILE.read_text(encoding="utf-8"))
        payload["optional_sessions"].append(payload["standard_session"])
        with self.assertRaisesRegex(ValidationError, "STANDARD belongs only"):
            ReaderDevelopmentProfileV2.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
