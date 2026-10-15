"""P4.37 ten original pilot cases, 30 genuinely independent holdout slots."""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import shutil
import unittest
from unittest.mock import patch

from src.story_harness_p437_pilot_matrix import (
    AGES, CAP, RESERVED, FULL_TRIAL_CAP, FROZEN,
    build_report, verify_historical,
)
from src.story_harness_v1 import HarnessStop

class P437Tests(unittest.TestCase):
    def test_frozen_real_initial_artifacts_not_overclaimed_as_release(self):
        p=build_report(".")
        self.assertEqual(p["schema"],"lumi.story-harness-p437-evidence-budget-pilot-matrix.v1")
        self.assertEqual(len(p["cases"]),10)
        self.assertEqual({(x["case_id"],x["reader_age"]) for x in p["cases"] if x["case_id"] in FROZEN},
                         {("B01",4),("B02",4),("B03",10)})
        self.assertEqual(p["historical_initial_pipeline_evidence_cases"],3)
        self.assertEqual(p["release_certified_cases"],0)
        self.assertEqual(p["holdout_real_independent_trials"],0)
        self.assertEqual(len(p["holdout"]),30)
        self.assertTrue(all(row["status"]=="NOT_RUN_NOT_ACCEPTED" for row in p["holdout"]))
        self.assertTrue(all(not row["frozen_v21_final_quality_certified"] for row in p["cases"]))
        self.assertFalse(p["paid_execution_authorized_by_this_report"])
        self.assertEqual(p["new_model_calls"],0)
        self.assertEqual(p["next_candidate_case"],"B04")

    def test_strict_budget_reservation_does_not_preapprove_30_runs(self):
        r=build_report(".")
        self.assertEqual(r["known_provider_reported_total_usd"],"0.378446")
        self.assertEqual(r["unknown_charge_reservation_usd"],"1.130000")
        self.assertEqual(r["unused_stage_reservation_usd"],"0.031112")
        self.assertEqual(r["total_conservative_reserved_usd"],"1.539558")
        self.assertEqual(r["remaining_conservative_budget_usd"],"8.460442")
        self.assertEqual(r["new_full_trial_worst_case_usd"],"0.440")
        self.assertEqual(r["max_new_full_trials_current_budget"],19)
        self.assertEqual(r["pilot_missing_generations"],7)
        self.assertEqual(r["pilot_new_run_worst_case_reserve_usd"],"3.080")
        self.assertEqual(r["conservative_budget_after_seven_case_pilot_usd"],"4.619558")
        self.assertEqual(r["new_full_trials_after_seven_case_pilot"],12)
        self.assertFalse(r["holdout_tranche_fully_preapproved"])
        self.assertGreater(RESERVED+30*FULL_TRIAL_CAP,CAP)

    def test_age_and_case_matrix_cannot_change(self):
        from src.story_harness_p415_benchmark import load_plan
        plan=load_plan(".")
        plan=deepcopy(plan)
        plan["cases"][3]["input"]["reader_age"]=4
        with patch("src.story_harness_p437_pilot_matrix.load_plan",return_value=plan):
            with self.assertRaises(HarnessStop):
                build_report(".")
        plan=load_plan(".")
        plan=deepcopy(plan)
        plan["cases"][3]["id"]="B44"
        with patch("src.story_harness_p437_pilot_matrix.load_plan",return_value=plan):
            with self.assertRaises(HarnessStop):
                build_report(".")

    def test_real_b03_quality_and_q25_cannot_be_replaced(self):
        original=FROZEN["B03"]
        with TemporaryDirectory() as td:
            for key in ("audit","master","q25","final"):
                file=Path(td)/original[key]
                file.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(original[key],file)
            self.assertEqual(verify_historical(td,"B03")["reader_score"],4)
            q=Path(td)/original["q25"]
            payload=json.loads(q.read_bytes())
            payload["story_sha256"]="f"*64
            q.write_text(json.dumps(payload))
            with self.assertRaises(HarnessStop):
                verify_historical(td,"B03")

    def test_unproved_quality_or_production_write_cannot_promote(self):
        original=FROZEN["B03"]
        with TemporaryDirectory() as td:
            for key in ("audit","master","q25","final"):
                file=Path(td)/original[key]
                file.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(original[key],file)
            path=Path(td)/original["audit"]
            data=json.loads(path.read_bytes())
            data["blocking_findings"]=[{"family":"canon","quote":"fake","reason":"fake"}]
            path.write_text(json.dumps(data))
            with self.assertRaises(HarnessStop):
                verify_historical(td,"B03")

if __name__=="__main__":
    unittest.main()
