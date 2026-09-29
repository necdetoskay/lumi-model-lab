from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.episode_postprocess_v2 import _validate_source
from src.sonnet55_final_repair_v1 import _manual_authority_cleanups

SOURCE = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_postprocess_source_36552606045.json"
)
APPROVED = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_p27_approved.json"
)
P3D1 = Path(
    "data/specifications/story_lab/sonnet55_p3d1_compact_authority_result.json"
)


class Sonnet55FinalRepairV1Tests(unittest.TestCase):
    def test_sources_match_and_p3d1_is_green(self):
        source = json.loads(SOURCE.read_text())
        approved = json.loads(APPROVED.read_text())
        p3d1 = json.loads(P3D1.read_text())
        _validate_source(source, approved)
        self.assertEqual(p3d1["status"], "completed")
        self.assertEqual(p3d1["score"]["recall"], 1)

    def test_manual_authority_cleanups_are_present(self):
        source = json.loads(SOURCE.read_text())
        rows = _manual_authority_cleanups(source["english_story"])
        reasons = " ".join(row["reason"] for row in rows)
        self.assertEqual(len(rows), 2)
        self.assertIn("Serel", reasons)
        self.assertIn("prior apprentice incident", reasons)


if __name__ == "__main__":
    unittest.main()
