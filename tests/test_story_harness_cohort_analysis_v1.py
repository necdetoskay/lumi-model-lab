"""Batch clustering cannot hide missing outcomes or certify fake quality."""
import copy
import unittest

from src.story_harness_cohort_analysis_v1 import cluster_after_full_round
from src.story_harness_v1 import HarnessStop


def rows():
    sample = [{"case_id": f"B{i:02d}", "round": "BASELINE",
               "status": "ACCEPT_CLAIMED", "findings": []}
              for i in range(1, 11)]
    for n in range(1, 4):
        sample[n-1]["status"] = "REJECT"
        sample[n-1]["findings"] = [{
            "family": "causal", "stage": "SPINEFORGE",
            "severity": "BLOCKER", "role": "PRIMARY",
            "support_sha256": f"{n}" * 64,
        }]
    sample[2]["findings"].append({
        "family": "response", "stage": "WRITER",
        "severity": "ADVISORY", "role": "CONTRIBUTING",
        "support_sha256": "d" * 64,
    })
    sample[3]["status"] = "OPERATIONAL_STOP"
    return sample


class CohortAnalysisTests(unittest.TestCase):
    def test_repeated_cause_grouped_by_stage_not_story_specific_patch(self):
        result = cluster_after_full_round(rows(), round_name="BASELINE")
        self.assertEqual(result["candidate_repeated_root_causes"], [{
            "stage": "SPINEFORGE", "family": "causal",
            "affected_cases": 3, "case_ids": ["B01", "B02", "B03"],
            "primary_root_cause_cases": 3, "blocking_cases": 3,
        }])
        self.assertEqual(result["quality_rejected_cases"], 3)
        self.assertEqual(result["provider_or_operational_stops_not_story_quality"], 1)
        self.assertEqual(result["claimed_accepts_not_certified"], 6)
        self.assertIsNone(result["independent_passes"])
        self.assertFalse(result["quality_success_rate_certified"])
        self.assertFalse(result["harness_patch_authorized_by_report"])

    def test_cannot_analyze_nine_stories_even_if_all_reject(self):
        with self.assertRaises(HarnessStop):
            cluster_after_full_round(rows()[:-1], round_name="BASELINE")

    def test_same_case_twice_is_never_ten_records(self):
        s = rows()
        s[-1]["case_id"] = "B01"
        with self.assertRaises(HarnessStop):
            cluster_after_full_round(s, round_name="BASELINE")

    def test_no_operational_stop_attributed_to_writer_quality(self):
        s = rows()
        s[3]["findings"] = [{
            "family": "spine", "stage": "WRITER", "severity": "BLOCKER",
            "role": "PRIMARY", "support_sha256": "a" * 64,
        }]
        with self.assertRaises(HarnessStop):
            cluster_after_full_round(s, round_name="BASELINE")

    def test_reject_requires_one_traceable_primary_root_cause(self):
        s = rows()
        s[0]["findings"] = []
        with self.assertRaises(HarnessStop):
            cluster_after_full_round(s, round_name="BASELINE")
        s = rows()
        s[0]["findings"].append(copy.deepcopy(s[0]["findings"][0]))
        with self.assertRaises(HarnessStop):
            cluster_after_full_round(s, round_name="BASELINE")

    def test_zero_rejects_never_proves_ten_out_of_ten_accepted(self):
        s = [{"case_id": f"B{i:02d}", "round": "PAIRED_REGRESSION",
              "status": "ACCEPT_CLAIMED", "findings": []}
             for i in range(1, 11)]
        result = cluster_after_full_round(s, round_name="PAIRED_REGRESSION")
        self.assertEqual(result["candidate_repeated_root_causes"], [])
        self.assertEqual(result["claimed_accepts_not_certified"], 10)
        self.assertFalse(result["real_provider_or_quality_evidence_reverified"])


if __name__ == "__main__":
    unittest.main()
