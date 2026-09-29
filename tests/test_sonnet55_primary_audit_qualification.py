from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.episode_postprocess_v2 import _validate_source
from src.sonnet55_primary_audit_qualification import (
    PRIMARY_MODEL,
    _gold_segment_map,
    _score,
)

SOURCE = Path("data/specifications/story_lab/age12_episode1_sonnet55_postprocess_source_36552606045.json")
APPROVED = Path("data/specifications/story_lab/age12_episode1_sonnet55_p27_approved.json")
GOLD = Path("data/specifications/story_lab/sonnet55_writer_36552606045_human_preaudit.json")


class Sonnet55PrimaryAuditQualificationTests(unittest.TestCase):
    def test_source_and_approved_match(self):
        source = json.loads(SOURCE.read_text())
        approved = json.loads(APPROVED.read_text())
        _validate_source(source, approved)
        self.assertEqual(source["source_writer_run_id"], 36552606045)
        self.assertEqual(source["source_spine_run_id"], 36551283455)
        self.assertEqual(PRIMARY_MODEL, "anthropic/claude-sonnet-5.5")

    def test_all_human_preaudit_anchors_exist(self):
        source = json.loads(SOURCE.read_text())
        gold = json.loads(GOLD.read_text())
        mapping = _gold_segment_map(source["english_story"], gold["audit_targets"])
        self.assertEqual(len(mapping), len(gold["audit_targets"]))
        self.assertTrue(all(mapping.values()))

    def test_scoring_separates_blocking_and_review_targets(self):
        targets = [
            {"id": "a", "severity": "serious"},
            {"id": "b", "severity": "major"},
            {"id": "c", "severity": "review"},
        ]
        findings = [
            {"span_ids": ["S1"]},
            {"span_ids": ["S3"]},
            {"span_ids": ["S9"]},
        ]
        score = _score(
            findings,
            targets,
            {"a": ["S1"], "b": ["S2"], "c": ["S3"]},
        )
        self.assertEqual(score["blocking_recall"], 0.5)
        self.assertEqual(score["matched_blocking_targets"], ["a"])
        self.assertEqual(score["missed_blocking_targets"], ["b"])
        self.assertEqual(score["matched_review_count"], 1)
        self.assertEqual(score["unmapped_finding_count"], 1)


if __name__ == "__main__":
    unittest.main()
