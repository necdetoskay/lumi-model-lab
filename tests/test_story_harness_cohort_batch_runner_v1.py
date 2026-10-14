"""One source-locked B01-B10 driver rehearsal, absolutely no paid API calls."""
from decimal import Decimal
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.story_harness_cohort_batch_runner_v1 import (
    Batch, run_ten, authorize_paid, RUN_ID, SCHEMA)
from src.story_harness_cohort_generation_receipt_v1 import validate_generation
from src.story_harness_p417_live_pilot import MODEL,PROVIDER
from src.story_harness_v1 import HarnessStop
from test_story_harness_cohort_pipeline_v1 import MockProvider

def fake_receipt(**q):
    return validate_generation({
        "data":{"id":q["generation_id"],"model":MODEL,
        "provider_name":PROVIDER,"cancelled":False,"finish_reason":"stop",
        "is_byok":False,"tokens_prompt":q["prompt_tokens"],
        "tokens_completion":q["completion_tokens"],
        "total_cost":q["reported_cost_usd"]}
    },**q)

class TenBatchTests(unittest.TestCase):
    def test_one_same_harness_ten_cases_with_rejection_and_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            r=run_ten(".",td,paid=False)
            self.assertEqual(r["status"],"TEN_ATTEMPTS_RECORDED")
            self.assertEqual(len(r["case_ids"]),10)
            self.assertEqual(r["case_ids"],[f"B{i:02d}" for i in range(1,11)])
            self.assertEqual(r["case_results"][3]["status"],"REJECT")
            self.assertEqual(r["provider_reported_cost_usd"],"0.39")
            self.assertTrue(r["simulated_offline_only"])
            self.assertFalse(r["model_quality_certified"])
            self.assertEqual(r["retry_count"],0)
            home=Path(td)/RUN_ID
            self.assertEqual(len(list((home/"stage-events").glob("*-intent.json"))),39)
            self.assertEqual(len(list((home/"stage-events").glob("*-settled.json"))),39)
            self.assertEqual(len(list(home.glob("B??-00-attempt.json"))),10)
            self.assertEqual(len(list(home.glob("B??-01-result.json"))),10)
            self.assertTrue((home/"99-cohort-result.json").is_file())
            a=json.loads((home/"00-full-round-reserve.json").read_text())
            self.assertEqual(a["new_ten_reserved_usd"],"4.400")
            self.assertFalse(a["provider_account_wide_spend_guaranteed"])
            with self.assertRaises(FileExistsError):
                run_ten(".",td,paid=False)

    def test_safe_story_stage_failure_does_not_stop_next_nine(self):
        with tempfile.TemporaryDirectory() as td:
            b=Batch(".",td,offline=True,historical_hold="3.249558")
            seen=[]
            def transport(case):
                p=MockProvider(case)
                def do(body):
                    result=p(body)
                    if case=="B01" and len(p.calls)==2:
                        result["choices"][0]["message"]["content"]="{}"
                    return result
                seen.append(case)
                return do
            r=b.run(transport, lambda case:fake_receipt)
            self.assertEqual(r["status"],"TEN_ATTEMPTS_RECORDED")
            self.assertEqual(r["case_results"][0]["status"],"OPERATIONAL_STOP")
            self.assertEqual(len(seen),10)
            self.assertEqual(b.reported,Decimal("0.38"))
            self.assertEqual(r["retry_count"],0)

    def test_unknown_charge_global_stops_without_fabricated_missing_cases(self):
        with tempfile.TemporaryDirectory() as td:
            batch=Batch(".",td,offline=True,historical_hold="3.249558")
            seen=[]
            def transport(case):
                seen.append(case)
                def bad(body):raise TimeoutError("unknown fee")
                return bad
            with self.assertRaisesRegex(HarnessStop,"UNKNOWN_OR_INTEGRITY"):
                batch.run(transport,lambda _:fake_receipt)
            self.assertEqual(seen,["B01"])
            self.assertTrue(batch.global_stop)
            self.assertFalse((Path(td)/RUN_ID/"99-cohort-result.json").exists())
            self.assertTrue((Path(td)/RUN_ID/"B01-99-global-stop.json").exists())
            self.assertFalse((Path(td)/RUN_ID/"B02-00-attempt.json").exists())
            self.assertEqual(len(list((Path(td)/RUN_ID/"stage-events").glob("*-intent.json"))),1)
            self.assertEqual(len(list((Path(td)/RUN_ID/"stage-events").glob("*-settled.json"))),0)

    def test_bad_generation_receipt_also_global_stops(self):
        with tempfile.TemporaryDirectory() as td:
            batch=Batch(".",td,offline=True,historical_hold="3.249558")
            with self.assertRaisesRegex(HarnessStop,"UNKNOWN_OR_INTEGRITY"):
                batch.run(lambda case:MockProvider(case),
                          lambda case:lambda **arg:{"invalid":True})
            self.assertEqual(len(list((Path(td)/RUN_ID/"stage-events").glob("*-intent.json"))),1)
            self.assertEqual(len(list((Path(td)/RUN_ID/"stage-events").glob("*-settled.json"))),0)

    def test_approved_cumulative_budget_stops_before_claim(self):
        with tempfile.TemporaryDirectory() as td:
            for amount in ("0","3.00","16.0","-1","NaN","infinite"):
                with self.subTest(amount=amount),self.assertRaises(HarnessStop):
                    Batch(".",td,offline=True,historical_hold=amount)
            self.assertFalse((Path(td)/RUN_ID).exists())

    def test_paid_mode_without_explicit_trusted_dispatch_never_gets_key(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ,{},clear=True):
                with patch("src.story_harness_cohort_batch_runner_v1.read_current_key") as get:
                    with self.assertRaisesRegex(HarnessStop,"NO_TRUSTED"):
                        run_ten(".",td,paid=True)
                    get.assert_not_called()
            self.assertFalse((Path(td)/RUN_ID).exists())
