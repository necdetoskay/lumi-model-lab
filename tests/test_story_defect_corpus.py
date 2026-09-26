import unittest

from src.story_defect_corpus import (
    HELD_OUT_GROUPS,
    assign_source_splits,
    build_audit_manifest,
    load_source_pool,
    source_pool_summary,
    validate_source_pool,
)


class StoryDefectCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool = load_source_pool()

    def test_real_source_pool_has_expected_minimum_diversity(self):
        summary = source_pool_summary(self.pool)
        self.assertEqual(summary["source_count"], 22)
        self.assertGreaterEqual(summary["scenario_group_count"], 16)
        self.assertEqual(len(summary["families"]), 5)

    def test_source_pool_is_valid_and_requires_clean_audit(self):
        self.assertEqual(validate_source_pool(self.pool), [])
        self.assertEqual(
            self.pool["status"], "FROZEN_SOURCE_POOL_REQUIRES_CLEAN_AUDIT"
        )

    def test_same_scenario_group_never_crosses_split(self):
        rows = assign_source_splits(self.pool)
        by_group = {}
        for row in rows:
            by_group.setdefault(row["scenario_group"], set()).add(
                row["dataset_split"]
            )
        self.assertTrue(all(len(splits) == 1 for splits in by_group.values()))

    def test_held_out_split_is_frozen_before_detector_threshold_selection(self):
        self.assertEqual(
            HELD_OUT_GROUPS,
            {
                "cohort_b_exploration_mystery",
                "cohort_b_friendship_social_problem",
                "paper_hat_no_reply",
                "basket_star_shadow",
                "cohort_b_nature_environment",
            },
        )

    def test_held_out_contains_all_five_story_families(self):
        rows = assign_source_splits(self.pool)
        families = {
            row["family"] for row in rows if row["dataset_split"] == "held_out"
        }
        self.assertEqual(
            families,
            {
                "exploration_mystery",
                "friendship_social_problem",
                "emotional_development",
                "everyday_fantastical_discovery",
                "nature_environment",
            },
        )

    def test_audit_manifest_does_not_claim_sources_are_clean(self):
        manifest = build_audit_manifest(self.pool)
        self.assertEqual(manifest["status"], "AWAITING_INDEPENDENT_AUDIT")
        self.assertTrue(
            manifest["policy"]["source_story_is_not_clean_gold_until_audit_passes"]
        )
        self.assertTrue(
            all(
                source["source_clean_status"]
                == "REQUIRES_INDEPENDENT_CLEAN_AUDIT"
                for source in manifest["sources"]
            )
        )


if __name__ == "__main__":
    unittest.main()
