"""P4.15 acceptance gate: 90% means real stories, never mock CI passes."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import unittest

from src.story_harness_p415_benchmark import (
    load_plan, validate_plan, case_fingerprint, required_passes,
    validate_failure_fix_history, evaluate, status,
)
from src.story_harness_v1 import HarnessStop

ROOT = Path(__file__).resolve().parents[1]


def example_receipt(case, *, cost="0.12"):
    return {
        "case_id": case["id"], "input_sha256": case_fingerprint(case),
        "writer_origin": "live_model_generation", "quality_verdict": "ACCEPT",
        "master_sha256": "a" * 64, "q25_sha256": "b" * 64,
        "story_state_sha256": "c" * 64, "reader_score": 5,
        "manual_prose_edits": 0, "actual_model_cost_usd": cost,
        "evidence_kind": "externally_verified_live",
    }


def fix(n, *, outcome="STILL_FAILING"):
    return {
        "attempt": n, "failure_family": "spatial",
        "hypothesis": f"correct exit position of the character #{n}",
        "code_revision": str(n) * 64,
        "offline_regression_green": True,
        "same_approach": True,
        "outcome": outcome,
    }


class P415BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = load_plan(ROOT)

    def test_public_plan_is_complete_and_covers_five_ages(self):
        self.assertEqual(len(self.plan["cases"]), 10)
        ages = [x["input"]["reader_age"] for x in self.plan["cases"]]
        self.assertEqual({n: ages.count(n) for n in set(ages)},
                         {4: 2, 10: 2, 12: 2, 25: 2, 40: 2})
        self.assertEqual(len({case_fingerprint(x) for x in self.plan["cases"]}), 10)

    def test_requirement_is_nine_of_ten_and_twenty_seven_of_thirty(self):
        self.assertEqual(required_passes(10), Decimal(9))
        self.assertEqual(required_passes(30), Decimal(27))
        self.assertEqual(required_passes(11), Decimal(10))

    def test_weakened_target_budget_or_retry_policy_is_rejected(self):
        for key, value in [
            ("target_success_rate", "0.80"),
            ("global_model_budget_usd", "11.00"),
            ("per_failure_max_same_method_fixes", 4),
            ("no_automatic_provider_retries", False),
            ("minimum_pilot_cases", 9),
            ("release_holdout_cases", 20),
        ]:
            plan = deepcopy(self.plan)
            plan[key] = value
            with self.subTest(key=key), self.assertRaises(HarnessStop):
                validate_plan(plan)

    def test_repeating_same_topic_or_state_is_rejected(self):
        p = deepcopy(self.plan)
        p["cases"][1]["input"] = deepcopy(p["cases"][0]["input"])
        with self.assertRaises(HarnessStop):
            validate_plan(p)

    def test_missing_accepted_age_case_blocks(self):
        p = deepcopy(self.plan)
        p["cases"][0]["input"]["reader_age"] = 12
        with self.assertRaises(HarnessStop):
            validate_plan(p)

    def test_missing_spine_q25_state_or_reader_gate_blocks(self):
        for check in ("spine_state_grounded", "same_story_q25",
                      "state_evidence_support", "reader_score_at_least_4_of_5"):
            p = deepcopy(self.plan)
            p["cases"][0]["acceptance_checks"].remove(check)
            with self.subTest(check=check), self.assertRaises(HarnessStop):
                validate_plan(p)

    def test_no_evidence_is_not_measured_not_a_pass(self):
        r = evaluate(self.plan)
        self.assertEqual(r["submitted_case_count"], 0)
        self.assertFalse(r["ninety_percent_achieved"])
        self.assertIsNone(r["verified_observed_success_rate"])
        self.assertEqual(r["status"], "NOT_YET_INDEPENDENTLY_ATTESTED")

    def test_even_forged_ten_of_ten_passes_cannot_self_attest(self):
        rows = [example_receipt(x) for x in self.plan["cases"]]
        r = evaluate(self.plan, rows, externally_attested=True)
        self.assertEqual(r["candidate_qualified_claims"], 10)
        self.assertFalse(r["ninety_percent_achieved"])
        self.assertIsNone(r["externally_verified_genuine_success_count"])
        self.assertFalse(r["actual_model_cost_verified"])
        self.assertEqual(r["claimed_model_cost_usd"], "1.20")

    def test_editorial_or_synthetic_writer_does_not_count(self):
        for variant in ("editorially_rewritten", "mock_provider", "unknown"):
            rows = [example_receipt(self.plan["cases"][0])]
            rows[0]["writer_origin"] = variant
            self.assertEqual(evaluate(self.plan, rows)["candidate_qualified_claims"], 0)

    def test_edited_manuscript_reject_and_missing_link_block(self):
        for change in [
            {"manual_prose_edits": 1}, {"quality_verdict": "REJECT"},
            {"q25_sha256": None}, {"story_state_sha256": "wrong"},
            {"reader_score": 3}, {"evidence_kind": "mock"},
        ]:
            row = example_receipt(self.plan["cases"][0])
            row.update(change)
            self.assertEqual(
                evaluate(self.plan, [row])["candidate_qualified_claims"], 0)

    def test_duplicate_case_or_wrong_state_topic_sha_refused(self):
        a = example_receipt(self.plan["cases"][0])
        with self.assertRaises(HarnessStop):
            evaluate(self.plan, [a, a])
        a["input_sha256"] = "f" * 64
        with self.assertRaises(HarnessStop):
            evaluate(self.plan, [a])

    def test_all_ten_claimed_costs_may_not_exceed_global_budget(self):
        rows = [example_receipt(x, cost="1.01") for x in self.plan["cases"]]
        with self.assertRaises(HarnessStop):
            evaluate(self.plan, rows)

    def test_nan_negative_and_oversized_one_call_budget_rejected(self):
        for cost in ("NaN", "-0.5", "Infinity", "11", 0.1):
            row = example_receipt(self.plan["cases"][0], cost=cost)
            with self.subTest(cost=cost), self.assertRaises(HarnessStop):
                evaluate(self.plan, [row])

    def test_three_fix_attempts_then_manual_strategy_review(self):
        self.assertEqual(
            validate_failure_fix_history([])["next_action"],
            "DIAGNOSE_AND_TRY_FIX_1")
        self.assertEqual(
            validate_failure_fix_history([fix(1)])["next_action"],
            "DIAGNOSE_AND_TRY_FIX_2")
        self.assertEqual(
            validate_failure_fix_history([fix(1), fix(2)])["next_action"],
            "DIAGNOSE_AND_TRY_FIX_3")
        r = validate_failure_fix_history([fix(1), fix(2), fix(3)])
        self.assertEqual(r["next_action"], "STOP_AND_REVIEW_ALTERNATIVE_METHOD")
        self.assertFalse(r["automatic_model_retries_allowed"])

    def test_duplicate_or_untested_repair_is_forbidden(self):
        for updates in [
            {"hypothesis": fix(1)["hypothesis"]},
            {"offline_regression_green": False},
            {"same_approach": False}, {"code_revision": "dirty"},
        ]:
            item = fix(2)
            item.update(updates)
            with self.subTest(updates=updates), self.assertRaises(HarnessStop):
                validate_failure_fix_history([fix(1), item])
        with self.assertRaises(HarnessStop):
            validate_failure_fix_history([fix(1), fix(2), fix(3), fix(4)])

    def test_stop_retry_after_fix_success(self):
        with self.assertRaises(HarnessStop):
            validate_failure_fix_history([fix(1, outcome="FIXED"), fix(2)])
        self.assertEqual(
            validate_failure_fix_history([fix(1, outcome="FIXED")])["next_action"],
            "VERIFY_NO_RETRY_WITH_SEPARATE_GRANT")

    def test_status_is_deterministic_zero_cost_truth(self):
        a = status(ROOT)
        b = status(ROOT)
        self.assertEqual(a,b)
        self.assertEqual(len(a["case_ids"]), 10)
        self.assertEqual(a["frozen_budget_ceiling_usd"], "10.00")
        self.assertEqual(a["max_corrective_fixes_per_failure"], 3)
        self.assertFalse(a["ninety_percent_achieved"])
        self.assertFalse(a["production_admission_authorized"])
        self.assertFalse(a["actual_model_cost_verified"])
        self.assertEqual(a["claimed_model_cost_usd"], "0")


if __name__ == "__main__":
    unittest.main()
