"""Frozen 10 + same-input 10 + unseen 10; zero-provider guard tests."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from src.story_harness_frozen_cohort_v1 import (
    preflight, verify_attempt_seal, round_coverage, COMPONENTS,
)
from src.story_harness_v1 import HarnessStop

POLICY = Path("configs/story_harness_frozen_cohort_v1.json")


class FrozenCohortTests(unittest.TestCase):
    def test_envelope_does_not_authorize_payment_or_claim_success(self):
        result = preflight()
        self.assertEqual(result["global_user_ceiling_usd"], "20.00")
        self.assertEqual(result["baseline_and_regression_maximum_reserve_usd"], "8.800")
        self.assertEqual(result["holdout_maximum_reserve_usd"], "4.400")
        self.assertEqual(result["illustrative_total_conservative_reserve_usd"], "16.449558")
        self.assertEqual(result["illustrative_headroom_usd"], "3.550442")
        self.assertEqual(len(result["case_input_sha256"]), 10)
        self.assertEqual(result["paid_calls_authorized"], 0)
        self.assertFalse(result["cohort_frozen"])
        self.assertTrue(result["live_provider_ledger_reconciliation_required"])

    def mutate_policy(self, field, value):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "configs").mkdir()
            shutil.copy("configs/story_harness_p415_benchmark.json",
                        p / "configs/story_harness_p415_benchmark.json")
            value_dict = json.loads(POLICY.read_text(encoding="utf-8"))
            value_dict[field] = value
            (p / POLICY).write_text(json.dumps(value_dict), encoding="utf-8")
            with self.assertRaises(HarnessStop):
                preflight(p)

    def test_spent_b07_quality_grant_archived_no_second_provider_call(self):
        gate = Path(".github/workflows/story-harness-p458-b07-quality-gate.yml").read_text()
        self.assertIn("  workflow_dispatch:", gate)
        self.assertNotIn("  pull_request:", gate)
        self.assertIn("    if: ${{ false }}", gate)

    def test_cap_cannot_exceed_explicit_20(self):
        self.mutate_policy("global_aggregate_budget_usd", "20.01")

    def test_new_policy_cannot_grant_paid_calls(self):
        self.mutate_policy("paid_calls_authorized", 1)

    def test_cannot_shrink_cohort_or_change_harness_mid_trial(self):
        self.mutate_policy("baseline_cases", 9)
        self.mutate_policy("baseline_configuration_immutable", False)
        self.mutate_policy("no_mid_cohort_quality_fix", False)
        self.mutate_policy("all_ten_attempts_required_for_analysis", False)

    def test_cannot_change_reservation_in_metadata_only(self):
        self.mutate_policy("indicative_full_trial_reserve_usd", "0.30")

    def test_ten_failed_stories_are_recorded_before_analysis(self):
        rows = [{"case_id": f"B{i:02d}", "round": "BASELINE",
                 "status": "REJECT"} for i in range(1, 10)]
        result = round_coverage(rows, "BASELINE")
        self.assertFalse(result["root_cause_review_permitted"])
        self.assertEqual(result["missing_case_ids"], ["B10"])
        rows.append({"case_id": "B10", "round": "BASELINE", "status": "REJECT"})
        result = round_coverage(rows, "BASELINE")
        self.assertTrue(result["root_cause_review_permitted"])
        self.assertEqual(result["quality_rejections"], 10)
        self.assertFalse(result["independent_success_rate_certified"])

    def test_forged_ten_accepts_do_not_certify_rate(self):
        rows = [{"case_id": f"B{i:02d}", "round": "BASELINE",
                 "status": "ACCEPT_CLAIMED"} for i in range(1, 11)]
        result = round_coverage(rows, "BASELINE")
        self.assertEqual(result["unverified_accept_claims"], 10)
        self.assertFalse(result["independent_success_rate_certified"])

    def test_cohort_lock_blocks_changed_code_model_prompts_or_input(self):
        sha = "a" * 64
        components = {key: sha for key in COMPONENTS}
        inputs = {f"B{i:02d}": sha for i in range(1, 11)}
        lock = {"status": "SEALED", "harness_commit": "b" * 40,
                "component_sha256": components, "round": "BASELINE"}
        attempt = {"case_id": "B01", "harness_commit": "b" * 40,
                   "component_sha256": components,
                   "input_sha256": sha, "round": "BASELINE",
                   "manual_prose_edits": 0, "automatic_quality_retry": False}
        verify_attempt_seal(lock, attempt, inputs)
        for field, bad in [
            ("input_sha256", "f" * 64),
            ("harness_commit", "c" * 40),
            ("round", "PAIRED_REGRESSION"),
            ("manual_prose_edits", 1),
            ("automatic_quality_retry", True),
        ]:
            copy_attempt = copy.deepcopy(attempt)
            copy_attempt[field] = bad
            with self.subTest(field=field), self.assertRaises(HarnessStop):
                verify_attempt_seal(lock, copy_attempt, inputs)
        tampered = copy.deepcopy(attempt)
        tampered["component_sha256"]["prompt_bundle"] = "f" * 64
        with self.assertRaises(HarnessStop):
            verify_attempt_seal(lock, tampered, inputs)


if __name__ == "__main__":
    unittest.main()
