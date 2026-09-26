import json
import unittest
from pathlib import Path

MANIFEST = Path(
    "experiments/fixtures/story_defect_d1_validation_manifest.tr-age4.v1.json"
)


class StoryDefectD1ValidationManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_d1_manifest_is_frozen_and_gate_passes(self):
        self.assertEqual(self.payload["status"], "D1_COMPLETE_FROZEN")
        self.assertTrue(self.payload["summary"]["d1_gate_pass"])

    def test_d1_has_at_least_200_validated_gold_cases(self):
        self.assertGreaterEqual(self.payload["summary"]["validated_gold"], 200)
        self.assertEqual(
            self.payload["summary"]["validated_gold"],
            len(self.payload["validated_cases"]),
        )

    def test_priority_families_each_have_at_least_twenty_cases(self):
        by_family = self.payload["summary"]["by_family"]
        for family in (
            "physical_feasibility",
            "causal_logic",
            "state_continuity",
            "response_causality",
        ):
            self.assertGreaterEqual(by_family[family], 20, family)

    def test_calibration_and_held_out_both_survive_validation(self):
        summary = self.payload["summary"]
        self.assertGreater(summary["calibration_validated"], 0)
        self.assertGreater(summary["held_out_validated"], 0)
        self.assertEqual(
            summary["calibration_validated"] + summary["held_out_validated"],
            summary["validated_gold"],
        )

    def test_quarantine_is_explicit_and_excluded(self):
        validated_ids = {row["case_id"] for row in self.payload["validated_cases"]}
        quarantined_ids = {row["case_id"] for row in self.payload["quarantined_cases"]}
        self.assertFalse(validated_ids.intersection(quarantined_ids))
        self.assertEqual(
            len(quarantined_ids), self.payload["summary"]["quarantined"]
        )

    def test_taxonomy_authority_is_not_evaluator_majority_vote(self):
        policy = self.payload["policy"]
        self.assertEqual(
            policy["canonical_taxonomy_authority"],
            "LUMI defect ontology, not evaluator majority vote",
        )
        self.assertTrue(policy["held_out_cases_must_not_influence_d2_threshold_selection"])


if __name__ == "__main__":
    unittest.main()
