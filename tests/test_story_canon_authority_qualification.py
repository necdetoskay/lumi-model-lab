from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.episode_postprocess_v2 import _validate_source
from src.story_canon_authority_qualification import (
    MODEL,
    _gold_segment_map,
    _normalize_findings,
    _score,
)

SOURCE = Path("data/specifications/story_lab/age12_episode1_sonnet55_postprocess_source_36552606045.json")
APPROVED = Path("data/specifications/story_lab/age12_episode1_sonnet55_p27_approved.json")
GOLD = Path("data/specifications/story_lab/sonnet55_writer_36552606045_confirmed_canon_gold.json")


class StoryCanonAuthorityQualificationTests(unittest.TestCase):
    def test_source_and_approved_match(self):
        source = json.loads(SOURCE.read_text())
        approved = json.loads(APPROVED.read_text())
        _validate_source(source, approved)
        self.assertEqual(MODEL, "openai/gpt-5.6-luna")

    def test_all_confirmed_canon_anchors_exist(self):
        source = json.loads(SOURCE.read_text())
        gold = json.loads(GOLD.read_text())
        mapping = _gold_segment_map(source["english_story"], gold["targets"])
        self.assertEqual(len(mapping), 5)
        self.assertTrue(all(mapping.values()))

    def test_normalizer_rejects_unanchored_quote(self):
        story = "A fact appears here."
        with self.assertRaisesRegex(RuntimeError, "exact_quote not found"):
            _normalize_findings(
                {
                    "findings": [
                        {
                            "family": "canon_integrity",
                            "severity": "serious",
                            "repair_scope": "local",
                            "span_ids": ["S001"],
                            "exact_quote": "not present",
                            "reason": "x",
                        }
                    ]
                },
                story,
            )

    def test_score_tracks_unmapped(self):
        targets = [{"id": "a"}, {"id": "b"}]
        findings = [
            {"span_ids": ["S1"]},
            {"span_ids": ["S9"]},
        ]
        score = _score(findings, targets, {"a": ["S1"], "b": ["S2"]})
        self.assertEqual(score["recall"], 0.5)
        self.assertEqual(score["missed_targets"], ["b"])
        self.assertEqual(score["unmapped_finding_count"], 1)


if __name__ == "__main__":
    unittest.main()
