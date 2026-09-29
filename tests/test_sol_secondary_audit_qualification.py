from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.episode_postprocess_v2 import _validate_source
from src.sol_secondary_audit_qualification import MODEL
from src.story_canon_authority_qualification import _gold_segment_map

SOURCE = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_postprocess_source_36552606045.json"
)
APPROVED = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_p27_approved.json"
)
GOLD = Path(
    "data/specifications/story_lab/sonnet55_writer_36552606045_confirmed_canon_gold.json"
)


class SolSecondaryAuditQualificationTests(unittest.TestCase):
    def test_source_and_approved_match(self):
        source = json.loads(SOURCE.read_text())
        approved = json.loads(APPROVED.read_text())
        _validate_source(source, approved)
        self.assertEqual(MODEL, "openai/gpt-5.6-sol")

    def test_gold_targets_are_blind_scoreable(self):
        source = json.loads(SOURCE.read_text())
        gold = json.loads(GOLD.read_text())
        mapping = _gold_segment_map(source["english_story"], gold["targets"])
        self.assertEqual(len(mapping), 5)
        self.assertTrue(all(mapping.values()))


if __name__ == "__main__":
    unittest.main()
