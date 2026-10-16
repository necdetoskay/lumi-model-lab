"""v0.40 no-cost preflight and response-contract regression only."""
import json
from copy import deepcopy
from unittest import TestCase

from experiments.sera.coverage import CoverageError
from experiments.sera.real_blind_benchmark_v040 import (
    EXPECTED_SHA, MODELS, SCHEMA, SPEND_STOP_USD, prepare,
    _cost, _result_from_response, verified_grant,
)


class RealModelBlindPilotV040Tests(TestCase):
    def test_frozen_original_source_and_independently_blind_batch(self):
        src=prepare()
        self.assertEqual(src["plan"]["source_prose_sha256"],EXPECTED_SHA)
        self.assertTrue(src["target_sentence_id"].startswith("s"))
        self.assertIn(src["target_sentence_id"],src["batch"]["sentence_ids"])
        self.assertIn("bench",src["prose"].lower())
        self.assertFalse(src["plan"]["prior_writer_report_included"])
        self.assertFalse(src["plan"]["prior_analyst_events_included"])
        self.assertNotIn("fixture_grants",str(src["batch"]["messages"]))
        self.assertNotIn("validator_world",str(src["batch"]["messages"]))
        self.assertFalse(src["plan"]["canonical_commit_authorized"])

    def test_key_billing_receipt_is_not_guessed(self):
        self.assertIsNone(_cost(None))
        self.assertIsNone(_cost({}))
        self.assertIsNone(_cost({"cost":"NaN"}))
        self.assertIsNone(_cost({"cost":-0.1}))
        self.assertEqual(str(_cost({"cost":0.000421})),"0.000421")
        self.assertEqual(str(SPEND_STOP_USD),"0.05")

    def test_grant_never_accepts_an_alternate_model_or_token_ceiling(self):
        src=prepare()
        grant={
            "schema":"sera.real-blind-oneuse-grant.v0.40",
            "authorized":True,
            "scope":"FROZEN_MARA_S1_BENCH_BATCH_ONLY",
            "source_prose_sha256":EXPECTED_SHA,
            "model_ids":list(MODELS),
            "max_provider_attempts":2,
            "observed_spend_stop_usd":"0.05",
            "no_reruns":True,
            "no_output_token_limit":True,
            "no_canonical_commit":True,
            "approved_code_sha":"a"*40,
        }
        verified_grant(src,grant)
        for key,value in [
            ("model_ids",["model-not-approved"]),
            ("max_provider_attempts",3),
            ("no_output_token_limit",False),
            ("source_prose_sha256","b"*64),
            ("authorized",False),
        ]:
            wrong=deepcopy(grant)
            wrong[key]=value
            with self.assertRaisesRegex(CoverageError,
                                        "V040_EXACT_ONE_USE_GRANT_INVALID"):
                verified_grant(src,wrong)

    def test_missing_finish_or_cost_never_masquerades_as_success(self):
        src=prepare()
        err=_result_from_response(source=src,model=MODELS[0],
                                  returned={"error":"HTTP_429","raw":None})
        self.assertEqual(err["status"],"PROVIDER_ERROR_HOLD")
        self.assertIsNone(err["provider_cost_usd"])
        wrong=_result_from_response(source=src,model=MODELS[0],
                                    returned={"error":None,"raw":{
                "id":"test","model":MODELS[0],
                "choices":[{"finish_reason":"length","message":{"content":"{}"}}],
                "usage":{"cost":0.002},
            }})
        self.assertEqual(wrong["status"],"PROVIDER_INCOMPLETE_HOLD")
        self.assertFalse(wrong["source_bound"])

    def test_actual_v010_binder_matches_four_sentence_batch(self):
        src=prepare()
        # This is a protocol synthetic fixture, not a real model result.
        s={x["id"]:x for x in src["plan"]["source_sentences"]}
        rows=[]
        for sid in src["batch"]["sentence_ids"]:
            sentence=s[sid]
            mentions=[]
            if sid==src["target_sentence_id"]:
                mentions=[{
                    "entity_ref":"candidate:bench",
                    "role":"MENTIONED",
                    "evidence_quote":"bench",
                    "occurrence":0,
                }]
            rows.append({
                "sentence_id":sid,"disposition":"TEXTURE",
                "reason":"synthetic binder contract, not model truth",
                "mentions":mentions,"events":[],
            })
        raw={
            "id":"test-model-result",
            "model":MODELS[0],
            "choices":[{
                "finish_reason":"stop",
                "message":{"content":json.dumps({"rows":rows})},
            }],
            "usage":{"cost":0.001},
        }
        result=_result_from_response(source=src,model=MODELS[0],
                                     returned={"error":None,"raw":raw})
        self.assertEqual(result["status"],
                         "SOURCE_BOUND_CANDIDATES_SEMANTIC_HOLD")
        self.assertTrue(result["target_bench_mentioned"])
        self.assertTrue(result["source_bound"])
        self.assertGreater(result["candidate_mention_count"],0)
