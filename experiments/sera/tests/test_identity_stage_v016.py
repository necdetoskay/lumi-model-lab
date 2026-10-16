"""v0.16 single-stage generation + automatic repair tests, no provider."""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
from tempfile import TemporaryDirectory
from copy import deepcopy
import json
import unittest

from experiments.sera.identity_stage_v016 import execute
from experiments.sera.mara_s1_typed_live_v05 import entry_state
from experiments.sera.tests.test_identity_auto_repair_v016 import problem_response
from experiments.sera.tests.test_identity_resolution_v014 import (
    PROSE,synthetic_mention_census,
)

def envelope(payload):
    return {"error":None,"raw":{
        "id":"fixture-response","model":"anthropic/claude-haiku-4.5",
        "usage":{"cost":0.001},
        "choices":[{"finish_reason":"stop","message":{
            "content":json.dumps(payload,ensure_ascii=False)}}],
    }}

class IdentityStageTests(unittest.TestCase):
    def test_one_invocation_carries_main_and_repair_without_manual_actions(self):
        calls=[]
        def provider(*,model,prepared):
            calls.append(deepcopy(prepared))
            self.assertNotIn("max_tokens",str(prepared))
            self.assertNotIn("max_output_tokens",str(prepared))
            if len(calls)==1:
                return envelope(problem_response())
            # The second model sees only the one remaining bad ref.
            task=json.loads(prepared["request"]["messages"][1]["content"])
            self.assertEqual(task["entity_ref"],"new:strike_record")
            repaired=next(x for x in problem_response()["rows"]
                          if x["entity_ref"]=="new:strike_record")
            repaired["relation"]="POTENTIAL_PART_OF"
            return envelope({"rows":[repaired]})
        with TemporaryDirectory() as directory:
            path=Path(directory)/"stage"
            out=execute(
                prose=PROSE,world=entry_state(),
                census=synthetic_mention_census(),
                call_model=provider,output_dir=path,
            )
            self.assertEqual(len(calls),2)
            self.assertEqual(out["primary_calls"],1)
            self.assertEqual(out["targeted_calls"],1)
            self.assertEqual(out["status"],
                             "AUTO_REPAIR_FINISHED_NONCANONICAL_HOLD")
            self.assertEqual(out["result"]["accepted_source_bound_count"],16)
            self.assertEqual(out["result"]["automatic_abstain_count"],0)
            self.assertEqual(out["result"]["additional_model_calls"],1)
            self.assertTrue((path/"primary.json").is_file())
            safe="targeted_"+sha256(b"new:strike_record").hexdigest()[:24]+".json"
            self.assertTrue((path/safe).is_file())
            self.assertEqual(json.loads((path/"result.json").read_text())
                             ["status"],out["status"])
            events=json.loads((path/"ledger.json").read_text())
            self.assertEqual(sum(x["stage"]=="REQUEST_STARTED" for x in events),2)
            self.assertFalse(out["canonical_commit_authorized"])
            self.assertEqual(out["world_db_writes"],0)

    def test_no_targeted_model_available_carries_fifteen_forward_as_proposals(self):
        calls=[]
        with TemporaryDirectory() as directory:
            out=execute(
                prose=PROSE,world=entry_state(),
                census=synthetic_mention_census(),
                call_model=lambda **kwargs: (calls.append(kwargs) or
                                             envelope(problem_response())),
                output_dir=Path(directory)/"stage",repair_calls_allowed=0,
            )
        self.assertEqual(len(calls),1)
        self.assertEqual(out["targeted_calls"],0)
        self.assertEqual(out["result"]["accepted_source_bound_count"],15)
        self.assertEqual(out["result"]["automatic_abstain_count"],1)
        self.assertEqual(out["status"],"AUTO_REPAIR_FINISHED_NONCANONICAL_HOLD")

    def test_invalid_targeted_model_data_auto_abstains_only_bad_ref(self):
        calls=[]
        def provider(*,model,prepared):
            calls.append(prepared)
            return (envelope(problem_response()) if len(calls)==1
                    else envelope({"rows":17}))
        with TemporaryDirectory() as directory:
            out=execute(
                prose=PROSE,world=entry_state(),
                census=synthetic_mention_census(),
                call_model=provider,output_dir=Path(directory)/"stage",
            )
        self.assertEqual(out["targeted_calls"],1)
        self.assertEqual(out["result"]["accepted_source_bound_count"],15)
        self.assertEqual(out["result"]["automatic_abstain_count"],1)
        self.assertFalse(out["canonical_commit_authorized"])

    def test_invalid_attempt_policy_prevents_any_paid_call(self):
        calls=[]
        with TemporaryDirectory() as directory:
            from experiments.sera.coverage import CoverageError
            with self.assertRaisesRegex(
                CoverageError,"V016_STAGE_REPAIR_POLICY_INVALID"
            ):
                execute(
                    prose=PROSE,world=entry_state(),
                    census=synthetic_mention_census(),
                    call_model=calls.append,
                    output_dir=Path(directory)/"new",
                    repair_calls_allowed=99,
                )
        self.assertEqual(calls,[])

    def test_high_observed_primary_cost_stops_targeted_charge_safely(self):
        calls=[]
        def expensive(*,model,prepared):
            calls.append(prepared)
            result=envelope(problem_response())
            result["raw"]["usage"]["cost"]=0.06
            return result
        with TemporaryDirectory() as directory:
            out=execute(
                prose=PROSE,world=entry_state(),
                census=synthetic_mention_census(),call_model=expensive,
                output_dir=Path(directory)/"stage",
            )
        self.assertEqual(len(calls),1)
        self.assertEqual(out["status"],"AUTO_REPAIR_FINISHED_NONCANONICAL_HOLD")
        self.assertEqual(out["targeted_calls"],0)
        self.assertEqual(out["result"]["automatic_abstain_count"],1)
        self.assertEqual(out["provider_reported_total_spend_usd"],0.06)

    def test_model_error_at_first_call_stays_safe_without_manual_retry(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/"stage"
            out=execute(
                prose=PROSE,world=entry_state(),
                census=synthetic_mention_census(),
                call_model=lambda **kw:{"error":"HTTP_500"},
                output_dir=path,
            )
            self.assertEqual(out["status"],"AUTO_REPAIR_FAILED_SAFE_HOLD")
            self.assertEqual(out["primary_calls"],1)
            self.assertEqual(out["targeted_calls"],0)
            self.assertIn("HTTP_500",out["error"])
            self.assertTrue((path/"result.json").is_file())

if __name__=="__main__":
    unittest.main()
