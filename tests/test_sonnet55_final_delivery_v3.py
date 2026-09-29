from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.sonnet55_final_delivery_v3_notation_recovery import _apply_notation_patch

SOURCE = Path(
    "data/specifications/story_lab/sonnet55_final_delivery_v2_run_36580391689.json"
)


class Sonnet55FinalDeliveryV3Tests(unittest.TestCase):
    def test_v2_source_is_publication_ready_but_has_g_notation(self):
        source = json.loads(SOURCE.read_text())
        self.assertTrue(source["publication_ready"])
        tr = source["turkish_delivery_story"]
        self.assertEqual(tr.count("*G — tek düzenek.*"), 1)
        self.assertEqual(tr.count("*P — tek düzenek.*"), 0)
        self.assertIn("*P — single setup.*", source["accepted_english_master"])

    def test_deterministic_patch_aligns_notation(self):
        source = json.loads(SOURCE.read_text())
        patched, row = _apply_notation_patch(source["turkish_delivery_story"])
        self.assertEqual(patched.count("*P — tek düzenek.*"), 1)
        self.assertEqual(patched.count("*G — tek düzenek.*"), 0)
        self.assertEqual(row["mode"], "deterministic_exact_replacement")


if __name__ == "__main__":
    unittest.main()
