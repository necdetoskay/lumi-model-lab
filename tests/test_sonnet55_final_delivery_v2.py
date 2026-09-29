from __future__ import annotations

import json
import unittest
from pathlib import Path

SOURCE = Path("data/specifications/story_lab/age12_episode1_sonnet55_final_english_source_v4.json")
GATE = Path("data/specifications/story_lab/sonnet55_final_compact_authority_gate_run_36566995937.json")
SCRIPT = Path("src/sonnet55_final_delivery_v2.py")


class Sonnet55FinalDeliveryV2Tests(unittest.TestCase):
    def test_source_and_clean_gate_are_green(self):
        source = json.loads(SOURCE.read_text())
        gate = json.loads(GATE.read_text())
        self.assertEqual(source["deterministic_checks"]["word_count"], 1889)
        self.assertTrue(gate["pass"])
        self.assertEqual(gate["findings"], [])

    def test_script_checkpoints_usage_and_adjudicates_before_repair(self):
        text = SCRIPT.read_text()
        self.assertIn("def _checkpoint(", text)
        self.assertIn("ADJUDICATION_SYSTEM", text)
        self.assertIn("fidelity_adjudication_", text)
        self.assertIn("max_tokens=8000", text)
        self.assertIn("pipeline_usage_rollup", text)
        self.assertIn("delivery_usage_rollup", text)


if __name__ == "__main__":
    unittest.main()
