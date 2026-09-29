from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.episode_writer_v2_generate import build_writer_input
from src.story_authority_packet import build_story_authority_packet

APPROVED = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_p27_approved.json"
)
PROMPT = Path("prompts/episode_writer_v2.md")


class StoryAuthorityPacketTests(unittest.TestCase):
    def approved(self):
        return json.loads(APPROVED.read_text())

    def test_beacon_ridge_only_receives_entity_specific_fact(self):
        packet = build_story_authority_packet(self.approved())
        facts = packet["entity_specific_world_facts"]["beacon_ridge"]
        self.assertEqual(
            facts,
            ["Beacon Ridge is part of the known inner navigation network."],
        )
        joined = " ".join(facts).lower()
        self.assertNotIn("predate every living culture", joined)
        self.assertTrue(packet["ambient_summary_is_not_entity_binding"])

    def test_unknown_mentor_name_is_not_authorized(self):
        packet = build_story_authority_packet(self.approved())
        names = set(packet["known_durable_proper_names"])
        self.assertNotIn("Serel", names)
        self.assertNotIn("Kural", names)
        self.assertFalse(packet["new_durable_proper_names_allowed"])

    def test_record_state_contract_preserves_branch_difference(self):
        packet = build_story_authority_packet(self.approved())
        contracts = packet["record_state_rules"]["branch_contracts"]
        self.assertIn("report_now", contracts)
        self.assertIn("fresh_setup_retest", contracts)
        self.assertIn("provisional dated entry", contracts["report_now"]["local_payoff_if_earned"])
        self.assertIn("no reviewed formal entry", contracts["fresh_setup_retest"]["local_payoff_if_earned"])

    def test_writer_input_carries_typed_authority_packet(self):
        payload = build_writer_input(self.approved())
        self.assertEqual(
            payload["authority_packet"]["schema_version"],
            "story-authority-packet.v1",
        )
        self.assertTrue(
            payload["authority_packet"]["record_state_rules"][
                "raw_observations_are_distinct_from_formal_reviewed_entry"
            ]
        )

    def test_writer_prompt_contains_negative_space_guards(self):
        text = PROMPT.read_text()
        self.assertIn("world-level or class-level fact does NOT authorize", text)
        self.assertIn("Do NOT invent durable historical facts for named entities", text)
        self.assertIn("Do NOT invent a proper name for a recurring/durable NPC", text)
        self.assertIn("raw observations/field notes from a reviewed formal entry", text)


if __name__ == "__main__":
    unittest.main()
