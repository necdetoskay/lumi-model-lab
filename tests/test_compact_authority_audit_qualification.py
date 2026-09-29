from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.compact_authority_audit_qualification import MODEL
from src.episode_postprocess_v2 import _validate_source
from src.story_authority_packet import build_story_authority_packet
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
PROMPT = Path("prompts/story_compact_authority_gate_v2.md")


class CompactAuthorityAuditQualificationTests(unittest.TestCase):
    def test_source_and_authority_packet_are_valid(self):
        source = json.loads(SOURCE.read_text())
        approved = json.loads(APPROVED.read_text())
        _validate_source(source, approved)
        packet = build_story_authority_packet(approved)
        self.assertEqual(MODEL, "openai/gpt-5.6-luna")
        self.assertEqual(
            packet["entity_specific_world_facts"]["beacon_ridge"],
            ["Beacon Ridge is part of the known inner navigation network."],
        )

    def test_gold_is_scoreable_but_not_part_of_authority_packet(self):
        source = json.loads(SOURCE.read_text())
        approved = json.loads(APPROVED.read_text())
        gold = json.loads(GOLD.read_text())
        mapping = _gold_segment_map(source["english_story"], gold["targets"])
        packet_text = json.dumps(
            build_story_authority_packet(approved), ensure_ascii=False
        )
        self.assertEqual(len(mapping), 5)
        self.assertNotIn("older than any chart in the harbor archive", packet_text)
        self.assertNotIn("The pilots would be talking soon.", packet_text)

    def test_workflow_source_persists_raw_payload_before_normalization_reraise(self):
        text = Path("src/compact_authority_audit_qualification.py").read_text()
        self.assertIn('"raw_model_payload": payload', text)
        self.assertIn('"status": "post_inference_normalization_failure"', text)
        self.assertIn('"incremental_cost_usd": audit_rollup["totals"]["cost_usd"]', text)

    def test_prompt_enforces_entity_binding_and_record_semantics(self):
        text = PROMPT.read_text()
        self.assertIn("world-level or class-level fact does NOT authorize", text)
        self.assertIn("Raw readings, sketches, notes, and measurements", text)
        self.assertIn("NEW DURABLE PROPER NAMES", text)
        self.assertIn("A character's stated intention", text)
        self.assertIn("premise_authorized_facts are explicit story authority", text)
        self.assertIn("the pilots would be talking soon", text)


if __name__ == "__main__":
    unittest.main()
