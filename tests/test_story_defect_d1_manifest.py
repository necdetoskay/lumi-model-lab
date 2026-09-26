import json
import unittest
from pathlib import Path

MANIFEST = Path(
    "experiments/fixtures/story_defect_d1_validation_manifest.tr-age4.v1.1.json"
)
REJECTED_V1 = Path(
    "experiments/fixtures/story_defect_d1_validation_manifest.tr-age4.v1.json"
)


class StoryDefectD1ValidationManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.rejected = json.loads(REJECTED_V1.read_text(encoding="utf-8"))

    def test_d1_v11_manifest_is_frozen_for_d2(self):
        self.assertEqual(self.payload["status"], "FROZEN_FOR_D2")
        self.assertEqual(
            self.payload["schema_version"],
            "story-defect-d1-validation-manifest.v1.1",
        )

    def test_rejected_v1_manifest_cannot_be_d2_authority(self):
        self.assertEqual(
            self.rejected["status"],
            "REJECTED_SUPERSEDED_NOT_D2_AUTHORITY",
        )
        self.assertFalse(self.rejected["policy"]["d2_authority"])

    def test_d1_has_at_least_200_validated_gold_cases(self):
        summary = self.payload["summary"]
        self.assertGreaterEqual(summary["total_validated"], 200)
        self.assertEqual(summary["total_validated"], len(self.payload["cases"]))

    def test_priority_qualification_families_each_have_at_least_twenty_cases(self):
        by_family = self.payload["summary"]["qualification_by_family"]
        for family in (
            "physical_feasibility",
            "causal_logic",
            "state_continuity",
        ):
            self.assertGreaterEqual(by_family[family], 20, family)

    def test_response_causality_is_preserved_raw_but_qualified_under_causal_logic(self):
        summary = self.payload["summary"]
        self.assertEqual(
            self.payload["policy"]["qualification_mapping"]["response_causality"],
            "causal_logic",
        )
        self.assertGreater(summary["raw_by_family"]["response_causality"], 0)
        self.assertEqual(
            summary["qualification_by_family"]["causal_logic"],
            summary["raw_by_family"]["causal_logic"]
            + summary["raw_by_family"]["response_causality"],
        )

    def test_calibration_and_held_out_both_survive_validation(self):
        summary = self.payload["summary"]
        self.assertGreater(summary["calibration_validated"], 0)
        self.assertGreater(summary["held_out_validated"], 0)
        self.assertEqual(
            summary["calibration_validated"] + summary["held_out_validated"],
            summary["total_validated"],
        )

    def test_only_base_corpus_is_d2_authority(self):
        policy = self.payload["policy"]
        self.assertTrue(policy["base_corpus_only"])
        self.assertTrue(policy["response_supplement_v1_excluded"])
        self.assertTrue(policy["response_supplement_v2_excluded"])
        self.assertTrue(policy["quarantined_cases_excluded"])

    def test_held_out_is_forbidden_for_threshold_selection(self):
        self.assertTrue(
            self.payload["policy"]["held_out_never_used_for_threshold_selection"]
        )


if __name__ == "__main__":
    unittest.main()
