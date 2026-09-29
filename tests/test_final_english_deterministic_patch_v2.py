from __future__ import annotations

import json
import unittest

from src.final_english_deterministic_patch_v2 import OUT, apply


class FinalEnglishPatchV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        apply()
        cls.value = json.loads(OUT.read_text())
        cls.story = cls.value["english_story"]

    def test_length_stays_in_range(self):
        self.assertTrue(self.value["deterministic_checks"]["length_pass"])

    def test_measurement_series_is_monotonic_to_table_edge(self):
        for phrase in [
            "two and three-quarters degrees",
            "two and a half degrees",
            "two and a quarter degrees",
            "two and a tenth degrees",
            "two degrees, exactly the table's edge",
        ]:
            self.assertIn(phrase, self.story)

    def test_unauthorized_history_and_future_spread_are_gone(self):
        for phrase in [
            "founder's line",
            "last annual check",
            "ledger sketch",
            "old magnetic-stone beacon",
            "old markers",
            "raise it with the pilots",
            "pilots would be talking soon",
            "high ebb",
        ]:
            self.assertNotIn(phrase, self.story)

    def test_tide_turn_occurs_after_packing(self):
        self.assertIn("the water nearly slack at the bronze staff", self.story)
        self.assertTrue(self.story.rstrip().endswith("Behind them, the tide turned."))


if __name__ == "__main__":
    unittest.main()
