from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.episode_postprocess_v2 import _validate_source
from src.story_authority_packet import build_story_authority_packet

SOURCE=Path("data/specifications/story_lab/age12_episode1_sonnet55_final_english_source_v4.json")
APPROVED=Path("data/specifications/story_lab/age12_episode1_sonnet55_p27_approved.json")


class CompactAuthorityCleanGateTests(unittest.TestCase):
    def test_v4_source_valid_and_authority_complete(self):
        source=json.loads(SOURCE.read_text())
        approved=json.loads(APPROVED.read_text())
        _validate_source(source, approved)
        packet=build_story_authority_packet(approved)
        premise=" ".join(packet["premise_authorized_facts"]).lower()
        self.assertIn("shipping logs", premise)
        self.assertIn("no confirming delays or complaints", premise)
        self.assertTrue(source["deterministic_checks"]["length_pass"])


if __name__=="__main__":
    unittest.main()
