from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.episode_postprocess_v2 import _validate_source

SOURCE = Path("data/specifications/story_lab/age12_episode1_sonnet55_final_english_source_v4.json")
APPROVED = Path("data/specifications/story_lab/age12_episode1_sonnet55_p27_approved.json")
GATE = Path("data/specifications/story_lab/sonnet55_final_compact_authority_gate_run_36566995937.json")


class Sonnet55FinalDeliveryTests(unittest.TestCase):
    def test_final_english_source_and_gate_are_green(self):
        source = json.loads(SOURCE.read_text())
        approved = json.loads(APPROVED.read_text())
        gate = json.loads(GATE.read_text())
        _validate_source(source, approved)
        self.assertTrue(source["deterministic_checks"]["length_pass"])
        self.assertEqual(source["deterministic_checks"]["word_count"], 1889)
        self.assertTrue(gate["pass"])
        self.assertEqual(gate["findings"], [])
        self.assertEqual(gate["pipeline_usage_rollup"]["totals"]["cost_usd"], 0.15175385)

    def test_clean_gate_pipeline_includes_final_authority_call(self):
        gate = json.loads(GATE.read_text())
        stages = [x["stage"] for x in gate["pipeline_usage_rollup"]["calls"]]
        self.assertIn("final_compact_authority_gate", stages)
        self.assertIn("final_english_repair", stages)


if __name__ == "__main__":
    unittest.main()
