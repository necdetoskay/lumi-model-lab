from __future__ import annotations

import json
import unittest

from src.final_english_deterministic_patch_v3 import OUT, apply


class FinalEnglishPatchV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        apply()
        cls.value = json.loads(OUT.read_text())
        cls.story = cls.value["english_story"]

    def test_length_stays_in_range(self):
        self.assertTrue(self.value["deterministic_checks"]["length_pass"])

    def test_fresh_setup_language_is_bounded(self):
        self.assertIn("the original setup would look less likely as the sole explanation", self.story)
        self.assertIn("could strengthen or weaken my confidence in the series", self.story)
        self.assertNotIn("the setup would be partly cleared", self.story)
        self.assertNotIn("either proves or doubts my series", self.story)

    def test_unmeasured_confounds_are_modal(self):
        self.assertIn("may have cooled", self.story)
        self.assertIn("may have been settling", self.story)
        self.assertNotIn("has been settling into the stone for two hours", self.story)

    def test_wider_tide_lore_speculation_removed(self):
        self.assertNotIn("drowned causeway", self.story)
        self.assertNotIn("tide-lore", self.story)


if __name__ == "__main__":
    unittest.main()
