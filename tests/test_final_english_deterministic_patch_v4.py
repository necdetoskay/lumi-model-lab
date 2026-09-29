from __future__ import annotations

import json
import unittest

from src.final_english_deterministic_patch_v4 import OUT, apply


class FinalEnglishPatchV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        apply()
        cls.value=json.loads(OUT.read_text())
        cls.story=cls.value["english_story"]

    def test_length_pass(self):
        self.assertTrue(self.value["deterministic_checks"]["length_pass"])

    def test_temporal_phrase_fixed(self):
        self.assertIn("earlier that afternoon", self.story)
        self.assertNotIn("said it an hour ago", self.story)

    def test_closure_no_future_filing_commitment(self):
        self.assertIn('"Keep it provisional," the mentor said.', self.story)
        self.assertNotIn("When I file the week's calibrations at the harbor office", self.story)


if __name__ == "__main__":
    unittest.main()
