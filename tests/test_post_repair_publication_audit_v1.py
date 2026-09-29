from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.episode_postprocess_v2 import _validate_source
from src.story_authority_packet import build_story_authority_packet

SOURCE = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_repaired_postprocess_source.json"
)
APPROVED = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_p27_approved.json"
)


class PostRepairPublicationAuditV1Tests(unittest.TestCase):
    def test_repaired_source_is_valid(self):
        source = json.loads(SOURCE.read_text())
        approved = json.loads(APPROVED.read_text())
        _validate_source(source, approved)
        self.assertEqual(source["deterministic_checks"]["word_count"], 1950)
        self.assertTrue(source["deterministic_checks"]["length_pass"])

    def test_repaired_story_has_no_known_authority_leaks(self):
        source = json.loads(SOURCE.read_text())
        story = source["english_story"]
        for phrase in [
            "Serel",
            "older than any chart in the harbor archive",
            "the old builders had known things about tides",
            "Last spring I had an apprentice bring me an odd reading",
            "Two other pilots, Deniz had overheard",
            "The pilots would be talking soon.",
            "the logbook left this ridge empty",
        ]:
            self.assertNotIn(phrase, story)

    def test_authority_packet_still_binds_beacon_ridge_narrowly(self):
        approved = json.loads(APPROVED.read_text())
        packet = build_story_authority_packet(approved)
        self.assertEqual(
            packet["entity_specific_world_facts"]["beacon_ridge"],
            ["Beacon Ridge is part of the known inner navigation network."],
        )


if __name__ == "__main__":
    unittest.main()
