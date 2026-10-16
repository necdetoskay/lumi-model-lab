"""v0.41 no-cost pencil-source and safe full JSON fence regression."""
import json
import unittest
from copy import deepcopy

from experiments.sera.coverage import CoverageError
from experiments.sera.real_blind_benchmark_v040 import MODELS, EXPECTED_SHA
from experiments.sera.real_pencil_benchmark_v041 import (
    SCHEMA, prepare, interpret, verify_grant,
)


class RealPencilBenchmarkV041Tests(unittest.TestCase):
    def test_distinct_four_sentence_pencil_source_is_blind(self):
        p=prepare()
        self.assertEqual(p["plan"]["source_prose_sha256"],EXPECTED_SHA)
        quote=next(s["quote"] for s in p["plan"]["source_sentences"]
                   if s["id"]==p["target_sentence_id"])
        self.assertIn("pencil",quote.lower())
        self.assertIn("watched",quote.lower())
        self.assertFalse(p["plan"]["prior_writer_report_included"])
        self.assertFalse(p["plan"]["prior_analyst_events_included"])
        self.assertLessEqual(len(p["batch"]["sentence_ids"]),4)

    def test_grant_fences_exact_model_list_and_frozen_sha(self):
        p=prepare()
        grant={
            "schema":"sera.real-pencil-oneuse-grant.v0.41",
            "authorized":True,
            "scope":"FROZEN_MARA_S1_PENCIL_BATCH_ONLY",
            "source_prose_sha256":EXPECTED_SHA,
            "model_ids":list(MODELS),
            "max_provider_attempts":2,
            "observed_spend_stop_usd":"0.05",
            "no_reruns":True,
            "no_output_token_limit":True,
            "no_canonical_commit":True,
            "approved_code_sha":"f"*40,
        }
        verify_grant(p,grant)
        for key,val in [
            ("scope","FROZEN_MARA_S1_BENCH_BATCH_ONLY"),
            ("model_ids",[MODELS[0]]),
            ("authorized",False),
            ("no_output_token_limit",False),
            ("max_provider_attempts",3),
        ]:
            bad=deepcopy(grant)
            bad[key]=val
            with self.assertRaisesRegex(CoverageError,
                                        "V041_PAID_GRANT_UNVERIFIED"):
                verify_grant(p,bad)

    def test_fenced_model_json_bound_source_but_no_physical_authority(self):
        p=prepare()
        rows=[]
        for sentence in p["plan"]["source_sentences"]:
            if sentence["id"] in p["batch"]["sentence_ids"]:
                mentions=([{
                    "entity_ref":"new:pencil",
                    "role":"MENTIONED",
                    "evidence_quote":"pencil",
                    "occurrence":0,
                }] if sentence["id"]==p["target_sentence_id"] else [])
                rows.append({
                    "sentence_id":sentence["id"],
                    "disposition":"TEXTURE",
                    "reason":"test double, not a semantic truth label",
                    "mentions":mentions,"events":[],
                })
        rawtext=json.dumps({"rows":rows},ensure_ascii=False)
        fence=chr(96)*3
        raw={"id":"synthetic-test","model":MODELS[1],
             "choices":[{
                 "finish_reason":"stop",
                 "message":{"content":fence+"json\n"+rawtext+"\n"+fence},
             }],
             "usage":{"cost":0.001},
        }
        result=interpret(source=p,model=MODELS[1],
                         returned={"error":None,"raw":raw})
        self.assertEqual(result["json_envelope"],"FULL_JSON_CODE_FENCE")
        self.assertTrue(result["source_bound"])
        self.assertTrue(result["target_pencil_mentioned"])
        self.assertFalse(result["physical_pencil_move_committable"])
        self.assertFalse(result["event_subject_and_cause_verified"])
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(result["production_db_writes"],0)
        self.assertEqual(result["raw_response"],raw)


if __name__=="__main__":
    unittest.main()
