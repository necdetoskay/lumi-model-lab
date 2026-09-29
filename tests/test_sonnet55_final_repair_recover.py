from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.sonnet55_final_repair_recover import apply_recovered_repairs

SOURCE = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_postprocess_source_36552606045.json"
)
REPAIR = Path(
    "data/specifications/story_lab/sonnet55_final_repair_run_36564554796.json"
)


class FinalRepairRecoverTests(unittest.TestCase):
    def test_recovery_applies_ambiguous_identical_replacement_safely(self):
        source = json.loads(SOURCE.read_text())
        repair = json.loads(REPAIR.read_text())
        story, applied = apply_recovered_repairs(
            source["english_story"],
            repair["repair_payload"]["repairs"],
        )
        self.assertNotIn("Serel", story)
        self.assertNotIn("older than any chart in the harbor archive", story)
        self.assertNotIn("the old builders had known things about tides", story)
        self.assertNotIn("The pilots would be talking soon.", story)
        self.assertNotIn("Last spring I had an apprentice bring me an odd reading", story)
        self.assertNotIn("She nodded at the tide", story)
        self.assertNotIn('"Write it," she said.', story)
        self.assertNotIn("Then her initials.", story)
        self.assertEqual(len([row for row in applied if row["old"] == "Serel was quiet for a long moment."]), 1)


if __name__ == "__main__":
    unittest.main()
