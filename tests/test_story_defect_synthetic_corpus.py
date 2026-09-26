import unittest

from src.story_defect_synthetic_corpus import (
    corpus_summary,
    load_synthetic_corpus,
    validate_synthetic_corpus,
)


class StoryDefectSyntheticCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = load_synthetic_corpus()

    def test_corpus_has_exactly_210_controlled_corrupt_stories(self):
        summary = corpus_summary(self.corpus)
        self.assertEqual(summary["case_count"], 210)
        self.assertEqual(summary["source_count"], 14)
        self.assertEqual(summary["pending_validation"], 210)

    def test_corpus_is_not_claimed_as_qualification_evidence(self):
        self.assertFalse(self.corpus["qualification_evidence"])
        self.assertEqual(
            self.corpus["status"],
            "SYNTHETIC_PENDING_INDEPENDENT_VALIDATION",
        )

    def test_all_cases_preserve_frozen_split_and_gold_contracts(self):
        self.assertEqual(validate_synthetic_corpus(self.corpus), [])

    def test_priority_families_are_materially_represented(self):
        summary = corpus_summary(self.corpus)
        self.assertGreaterEqual(
            summary["by_defect_family"]["physical_feasibility"], 42
        )
        self.assertGreaterEqual(
            summary["by_defect_family"]["causal_logic"], 42
        )
        self.assertGreaterEqual(
            summary["by_defect_family"]["state_continuity"], 42
        )

    def test_both_calibration_and_held_out_sets_exist(self):
        summary = corpus_summary(self.corpus)
        self.assertGreater(summary["by_split"].get("calibration", 0), 0)
        self.assertGreater(summary["by_split"].get("held_out", 0), 0)


if __name__ == "__main__":
    unittest.main()
