import json
import unittest
from pathlib import Path

from src.story_defect_corpus import load_source_pool
from src.story_defect_detection import DEFECT_FAMILIES, segment_story


POOL = Path("experiments/fixtures/story_defect_natural_positive_pool.tr-age4.v0.1.json")


class StoryDefectNaturalPositivePoolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(POOL.read_text(encoding="utf-8"))
        source_pool = load_source_pool()
        cls.sources = {row["source_id"]: row for row in source_pool["sources"]}

    def test_natural_pool_is_not_claimed_as_qualification_evidence(self):
        self.assertFalse(self.payload["qualification_evidence"])
        self.assertEqual(
            self.payload["status"],
            "MANUAL_GOLD_CANDIDATE_PENDING_FINAL_ADJUDICATION",
        )

    def test_pool_contains_five_natural_positive_stories(self):
        self.assertEqual(len(self.payload["cases"]), 5)
        self.assertEqual(self.payload["summary"]["natural_positive_stories"], 5)
        self.assertEqual(self.payload["summary"]["serious_findings"], 6)

    def test_all_findings_are_serious_semantic_defects_with_addressable_spans(self):
        count = 0
        for case in self.payload["cases"]:
            source = self.sources[case["source_id"]]
            valid_ids = {row["id"] for row in segment_story(source["story"])}
            for finding in case["findings"]:
                count += 1
                self.assertIn(finding["defect_family"], DEFECT_FAMILIES)
                self.assertIn(finding["severity"], {"serious", "critical"})
                self.assertTrue(set(finding["span_ids"]).issubset(valid_ids))
                self.assertIn(
                    finding["repair_scope"],
                    {"LOCAL_REPAIR", "STRUCTURAL_REPAIR", "REPLAN"},
                )
        self.assertEqual(count, 6)

    def test_ambiguous_historical_findings_are_explicitly_excluded(self):
        excluded = {
            row["source_id"] for row in self.payload["excluded_after_manual_review"]
        }
        self.assertIn("src_emotional_guard_03", excluded)
        self.assertIn("src_cohort_a_01", excluded)
        self.assertIn("src_cohort_a_05", excluded)

    def test_natural_pool_covers_priority_real_failure_shapes(self):
        families = {
            finding["defect_family"]
            for case in self.payload["cases"]
            for finding in case["findings"]
        }
        self.assertTrue(
            {"response_causality", "state_continuity", "causal_logic", "closure_integrity"}
            .issubset(families)
        )


if __name__ == "__main__":
    unittest.main()
