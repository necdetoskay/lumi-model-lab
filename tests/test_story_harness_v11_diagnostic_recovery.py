"""V1.1 postmortem: preserve safe codes and response metadata, no paid POST."""
from pathlib import Path
import json
import tempfile
import unittest

from src.story_harness_p417_live_pilot import ProviderTransportFault
from src.story_harness_cohort_batch_runner_v1 import Batch
from src.story_harness_v1 import HarnessStop
from test_story_harness_cohort_pipeline_v1 import MockProvider


def find_event(root, suffix):
    found=list((Path(root)/"baseline-v1"/"stage-events").glob(
        "B01-01-spineforge-"+suffix+".json"))
    if len(found)!=1:raise AssertionError("Expected one stage event")
    return json.loads(found[0].read_text())


class V11FailureEvidence(unittest.TestCase):
    def test_safe_original_provider_http_failure_not_erased(self):
        with tempfile.TemporaryDirectory() as td:
            batch=Batch(".",td,offline=True,historical_hold="3.249558")
            def fail(_):raise ProviderTransportFault("HTTP_422","SCHEMA_OTHER")
            with self.assertRaises(HarnessStop):
                batch.run(lambda case:fail, lambda case:None)
            fault=find_event(td,"provider-fault")
            self.assertEqual(fault["details"]["reason_code"],"HTTP_422")
            self.assertEqual(fault["details"]["provider_hint_code"],"SCHEMA_OTHER")
            self.assertFalse(fault["details"]["cost_reconciled"])
            self.assertFalse(fault["details"]["provider_response_available"])
            self.assertTrue(batch.global_stop)
            self.assertEqual(len(list((Path(td)/"baseline-v1"/"stage-events").glob(
                "*-intent.json"))),1)
            self.assertFalse(list((Path(td)/"baseline-v1"/"stage-events").glob(
                "*-settled.json")))
            self.assertNotIn("Authorization",json.dumps(fault))

    def test_generation_metadata_failure_persists_prior_response_cost_and_id(self):
        with tempfile.TemporaryDirectory() as td:
            batch=Batch(".",td,offline=True,historical_hold="3.249558")
            def no_proof(**kw):raise ConnectionError("sensitive provider error")
            with self.assertRaises(HarnessStop):
                batch.run(lambda case:MockProvider(case),
                          lambda case:no_proof)
            evidence=find_event(td,"provider-observed")["details"]
            self.assertEqual(evidence["provider_generation_id"],
                             "gen-MockOnlyNoProvider123")
            self.assertEqual(evidence["provider_reported_cost_usd"],"0.01")
            self.assertEqual(evidence["prompt_tokens"],100)
            self.assertEqual(evidence["completion_tokens"],100)
            self.assertFalse(evidence["independently_reconciled"])
            fault=find_event(td,"provider-fault")["details"]
            self.assertEqual(fault["reason_code"],
                             "GENERATION_RECEIPT_UNKNOWN_OR_MISMATCH")
            self.assertTrue(fault["provider_response_available"])
            self.assertNotIn("sensitive provider error",json.dumps(fault))
            self.assertTrue(batch.global_stop)

    def test_missing_cost_fails_closed_and_preserves_nonsecret_response(self):
        with tempfile.TemporaryDirectory() as td:
            batch=Batch(".",td,offline=True,historical_hold="3.249558")
            def missing_cost(body):
                result=MockProvider("B01")(body)
                del result["usage"]["cost"]
                return result
            with self.assertRaises(HarnessStop):
                batch.run(lambda case:missing_cost, lambda case:None)
            evidence=find_event(td,"provider-observed")["details"]
            self.assertIsNone(evidence["provider_reported_cost_usd"])
            self.assertEqual(evidence["provider_generation_id"],
                             "gen-MockOnlyNoProvider123")
            fault=find_event(td,"provider-fault")["details"]
            self.assertEqual(fault["reason_code"],
                             "PROVIDER_USAGE_COST_MISSING_OR_INVALID")
            self.assertFalse(fault["cost_reconciled"])
            self.assertTrue(batch.global_stop)
