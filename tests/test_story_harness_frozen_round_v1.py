"""Ten-case execution cannot hotfix, retry, or skip a tiny error."""
import copy
import tempfile
import unittest
from src.story_harness_frozen_round_v1 import (
    GlobalSafetyStop, simulate_seal, check_lock, run_frozen_ten_offline
)
from src.story_harness_v1 import HarnessStop

def rejected(case, intent):
    return {"case_id": case, "status": "REJECT",
            "safe_reason": "SIMULATED_REJECT", "model_calls": 0,
            "manual_prose_edits": 0}

class FrozenTenExecutionTests(unittest.TestCase):
    def test_even_all_ten_rejections_continue_without_a_single_fix(self):
        called = []
        def callback(case, intent):
            called.append((case, intent["harness_commit"]))
            return rejected(case, intent)
        with tempfile.TemporaryDirectory() as td:
            result = run_frozen_ten_offline(".", td, callback)
            self.assertTrue(result["complete"])
            self.assertEqual(result["attempt_count"], 10)
            self.assertEqual(result["fix_count"], 0)
            self.assertEqual(result["retry_count"], 0)
            self.assertEqual(len({sha for _, sha in called}), 1)
            self.assertEqual([c for c, _ in called],
                             [f"B{i:02d}" for i in range(1, 11)])
            run_frozen_ten_offline(".", td, callback)
            self.assertEqual(len(called), 10, "No re-run even on resume")

    def test_tiny_first_error_still_attempts_other_nine_unmodified(self):
        called = []
        def callback(case, intent):
            called.append(case)
            if case == "B01":
                raise ValueError("tiny JSON field error; no fix")
            return rejected(case, intent)
        with tempfile.TemporaryDirectory() as td:
            r = run_frozen_ten_offline(".", td, callback)
            self.assertTrue(r["complete"])
            self.assertEqual(called, [f"B{i:02d}" for i in range(1, 11)])
            self.assertEqual(r["attempts"][0]["safe_reason"], "NO_RETRY_EXCEPTION")
            self.assertEqual(r["fix_count"], 0)

    def test_unknown_global_charge_stops_without_forging_seven_attempts(self):
        called = []
        def callback(case, intent):
            called.append(case)
            if case == "B03":
                raise GlobalSafetyStop()
            return rejected(case, intent)
        with tempfile.TemporaryDirectory() as td:
            r = run_frozen_ten_offline(".", td, callback)
            self.assertFalse(r["complete"])
            self.assertEqual(r["attempt_count"], 3)
            self.assertEqual(called, ["B01", "B02", "B03"])
            self.assertFalse(r["analysis_allowed"])
            again = run_frozen_ten_offline(".", td, callback)
            self.assertFalse(again["complete"])
            self.assertEqual(called, ["B01", "B02", "B03"])

    def test_code_or_prompt_hash_change_is_forbidden(self):
        seal = simulate_seal(".")
        broken = copy.deepcopy(seal)
        broken["files_sha256"]["src/story_harness_p416_input_bridge.py"] = "f" * 64
        with self.assertRaises(HarnessStop):
            check_lock(".", broken)
        broken = copy.deepcopy(seal)
        broken["harness_commit"] = "0" * 40
        with self.assertRaises(HarnessStop):
            check_lock(".", broken)

    def test_offline_callback_cannot_claim_billable_inference(self):
        def fraud(case, intent):
            row = rejected(case, intent)
            row["model_calls"] = 1
            return row
        with tempfile.TemporaryDirectory() as td:
            r = run_frozen_ten_offline(".", td, fraud)
            self.assertTrue(r["complete"])
            self.assertTrue(all(x["status"] == "OPERATIONAL_STOP" for x in r["attempts"]))
            self.assertFalse(r["independent_accepts_certified"])
            self.assertEqual(r["provider_calls"], 0)
