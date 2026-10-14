"""Mock aggregate exposure journal: ten records, no rerun or refund."""
from datetime import datetime, timezone
from pathlib import Path
import json
import tempfile
import unittest
from src.story_harness_cohort_accounting_v1 import OfflineCohortBudgetJournal
from src.story_harness_cohort_launch_gate_v1 import RECONCILIATION_SCHEMA
from src.story_harness_v1 import HarnessStop

NOW=datetime(2026,10,14,21,0,tzinfo=timezone.utc)
def fake_snapshot(**kw):
    data = {
        "schema":RECONCILIATION_SCHEMA,
        "as_of_utc":"2026-10-14T21:00:00Z",
        "settled_total_usd":"1.00","previously_reserved_usd":"2.249558",
        "unknown_charge_hold_usd":"0",
        "historical_budget_evidence_sha256":"f"*64,
        "all_existing_model_lab_key_spend_included":True,
        "other_spending_sources_excluded":True,
        "live_provider_reconciled":True,
        "externally_authenticated_by_finance_owner":True,
    }
    data.update(kw)
    return data

class JournalTests(unittest.TestCase):
    def make(self,td,**kw):
        return OfflineCohortBudgetJournal(".",
            td,run_id="lumi-ten-journal99",snapshot=fake_snapshot(**kw),clock=NOW)
    def test_ten_failures_still_finish_same_single_reserved_batch(self):
        with tempfile.TemporaryDirectory() as d:
            j=self.make(d)
            reservation=json.loads(
                (Path(d)/"lumi-ten-journal99"/"00-full-ten-reservation.json").read_text())
            self.assertEqual(reservation["new_full_ten_reserved_usd"],"4.400")
            self.assertFalse(reservation["financial_truth_externally_attested"])
            for n in range(1,11):
                case=f"B{n:02d}"
                j.begin(case)
                j.finish(case,provider_reported_usd="0.015",
                         outcome="REJECT")
            receipt=j.report()
            self.assertTrue(receipt["cohort_complete"])
            self.assertEqual(receipt["attempts_settled"],10)
            self.assertEqual(receipt["reported_spend_usd"],"0.150")
            self.assertEqual(receipt["baseline_reservation_usd"],"4.400")
            with self.assertRaises(HarnessStop):
                j.begin("B01")
            with self.assertRaises(FileExistsError):
                self.make(d)
    def test_no_mid_story_refund_or_double_attempt(self):
        with tempfile.TemporaryDirectory() as d:
            j=self.make(d)
            j.begin("B01")
            with self.assertRaises(HarnessStop):j.begin("B01")
            with self.assertRaises(HarnessStop):j.begin("B02")
            j.finish("B01",provider_reported_usd="0.01",
                     outcome="OPERATIONAL_STOP")
            with self.assertRaises(HarnessStop):j.finish(
                "B01",provider_reported_usd="0",outcome="REJECT")
            j.begin("B02")
            j.finish("B02",provider_reported_usd="0.02",outcome="REJECT")
            self.assertEqual(j.report()["baseline_reservation_usd"],"4.400")
    def test_unknown_charge_stops_remaining_cases_and_keeps_full_reserve(self):
        with tempfile.TemporaryDirectory() as d:
            j=self.make(d)
            j.begin("B01")
            j.unknown_stop("B01")
            self.assertFalse(j.report()["cohort_complete"])
            self.assertFalse(j.report()["future_story_fix_allowed"])
            self.assertEqual(j.report()["baseline_reservation_usd"],"4.400")
            with self.assertRaises(HarnessStop):j.begin("B02")
    def test_nonreconciled_or_overbudget_prior_spend_blocks_before_claim(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(HarnessStop):
                self.make(d,unknown_charge_hold_usd="0.1")
            self.assertFalse((Path(d)/"lumi-ten-journal99").exists())
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(HarnessStop):
                self.make(d,settled_total_usd="19.00")
            self.assertFalse((Path(d)/"lumi-ten-journal99").exists())
    def test_cannot_hide_spend_above_story_cap(self):
        with tempfile.TemporaryDirectory() as d:
            j=self.make(d)
            j.begin("B01")
            with self.assertRaises(HarnessStop):
                j.finish("B01",provider_reported_usd="0.441",outcome="REJECT")
            self.assertIsNotNone(j.report()["active_case"])
