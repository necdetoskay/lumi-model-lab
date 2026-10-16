"""v0.45 proof-bound zero-human offline challenge/re-extraction tests."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.real_blind_benchmark_v040 import prepare
from experiments.sera.scene_trace_autorepair_v045 import (
    execute, prepare_challenges, SCHEMA,
)
from experiments.sera.scene_trace_evidence_challenge_v044 import build_challenges
from experiments.sera.tests.test_scene_trace_evidence_challenge_v044 import (
    simulated_v043_envelope,
)


def risk_proof():
    prose,baseline=simulated_v043_envelope()
    return prose,build_challenges(archived_comparison=baseline,
                                   frozen_prose=prose)


def test_double(*,request,task_id,attempt,failure_codes):
    task=json.loads(request["messages"][1]["content"])
    source=task["target_sentence"]
    assert "CHANGE_STATE" not in str(request)
    assert "PENCIL_MOTION_OBSERVED_BUT_CAUSAL_ACTOR_UNKNOWN" not in str(request)
    if "watch open in his palm" in source:
        interpretation="STATIC_STATE_DESCRIPTION"
    elif "watched the pencil move" in source:
        interpretation="OBSERVED_MOTION_CAUSE_UNKNOWN"
    else:
        raise AssertionError("unexpected target")
    if attempt==1 and interpretation=="OBSERVED_MOTION_CAUSE_UNKNOWN":
        return {"source_quote":"a forged pencil teleport",
                "interpretation":"PHYSICAL_ACTION_WITH_EXPLICIT_ACTOR",
                "actor_id":"vane","transition_proven":True,
                "reason":"synthetic bad quote injected for retry"}
    return {"source_quote":source,"interpretation":interpretation,
            "actor_id":None,"transition_proven":False,
            "reason":"synthetic input only, not independent real judgment"}


class SceneTraceAutorepairV045Tests(unittest.TestCase):
    def test_exact_source_blind_requests_do_not_leak_model_proposals(self):
        prose,proof=risk_proof()
        tasks=prepare_challenges(proof=proof,prose=prose)
        self.assertEqual(len(tasks),2)
        self.assertNotEqual(tasks[0]["request_sha256"],tasks[1]["request_sha256"])
        for task in tasks:
            self.assertEqual(task["request"]["response_format"],
                             {"type":"json_object"})
            self.assertNotIn("max_tokens",str(task["request"]))
            self.assertNotIn("claude-haiku",str(task["request"]))
            self.assertNotIn("google/gemini",str(task["request"]))
            self.assertNotIn("challenge_id",str(task["request"]))
            self.assertNotIn("prior_model",str(task["request"]))
            self.assertNotIn("vane_is_the_actor",str(task["request"]))

    def test_failed_first_quote_auto_retry_then_no_world_write(self):
        prose,proof=risk_proof()
        hits=[]
        def provider(**params):
            hits.append((params["task_id"],params["attempt"]))
            return test_double(**params)
        with TemporaryDirectory() as d:
            path=Path(d)/"v45"
            result=execute(proof=proof,prose=prose,output_dir=path,
                           synthetic_source_reply=provider)
            replay=execute(proof=proof,prose=prose,output_dir=path,
                           synthetic_source_reply=lambda **kw: (_ for _ in ()
                              ).throw(AssertionError("must not call again")))
        self.assertEqual(result,replay)
        self.assertEqual(result["status"],
                         "SOURCE_BOUND_REPAIR_ADVISORIES_ONLY")
        self.assertEqual(len(hits),3)
        self.assertEqual(len(result["attempts"]),3)
        self.assertEqual(len(result["source_bound_advisories"]),2)
        self.assertTrue(all(x["world_state_transition_authorized"] is False
                            for x in result["source_bound_advisories"]))
        self.assertFalse(result["independent_semantic_qualification"])
        self.assertFalse(result["auto_reextraction_performed_for_real_scene"])
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(result["paid_provider_calls"],0)
        self.assertEqual(result["production_db_writes"],0)

    def test_consistently_wrong_answer_exhausts_without_world_mutation(self):
        prose,proof=risk_proof()
        def forged(**params):
            return {"source_quote":"teleport happened",
                    "interpretation":"PHYSICAL_ACTION_WITH_EXPLICIT_ACTOR",
                    "actor_id":"vane","transition_proven":True,
                    "reason":"unsupported synthetic claim"}
        with TemporaryDirectory() as d:
            result=execute(
                proof=proof,prose=prose,output_dir=Path(d)/"safe",
                synthetic_source_reply=forged,max_attempts_per_task=2,
            )
        self.assertEqual(result["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(result["reason_code"],
                         "V045_SOURCE_CHALLENGE_ATTEMPTS_EXHAUSTED")
        self.assertEqual(result["unresolved_task_ids"],["task_001","task_002"])
        self.assertFalse(result["requires_manual_intervention"])
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(result["production_db_writes"],0)

    def test_provider_double_unknown_result_is_not_resent_on_restart(self):
        prose,proof=risk_proof()
        calls=[]
        def lost(**params):
            calls.append(params["task_id"])
            raise ConnectionError("synthetic unknown after dispatch")
        with TemporaryDirectory() as d:
            root=Path(d)/"stage"
            first=execute(proof=proof,prose=prose,output_dir=root,
                          synthetic_source_reply=lost)
            replay=execute(proof=proof,prose=prose,output_dir=root,
                           synthetic_source_reply=lost)
        self.assertEqual(len(calls),1)
        self.assertEqual(first,replay)
        self.assertEqual(first["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(first["reason_code"],
                         "V045_SYNTHETIC_CALLBACK_FAILED_WITHOUT_RECEIPT")
        self.assertEqual(first["paid_provider_calls"],0)

    def test_restart_rebinds_existing_first_receipt_no_second_dispatch(self):
        prose,proof=risk_proof()
        calls=[]
        with TemporaryDirectory() as d:
            root=Path(d)/"stage"
            def first_call_only(**params):
                calls.append(params["task_id"])
                return test_double(**params)
            # Successfully archive two bounded tasks, then force crash
            # recovery by deleting FINAL and ensuring replies are reused.
            complete=execute(proof=proof,prose=prose,output_dir=root,
                             synthetic_source_reply=first_call_only)
            self.assertEqual(len(calls),3)
            (root/"final.json").unlink()
            replay=execute(proof=proof,prose=prose,output_dir=root,
                           synthetic_source_reply=lambda **kw: (_ for _ in ()
                                 ).throw(AssertionError("no resend")))
        self.assertEqual(replay["status"],
                         "SOURCE_BOUND_REPAIR_ADVISORIES_ONLY")
        self.assertEqual(replay["simulated_new_reply_count"],0)
        self.assertTrue(all(a["restored_receipt"]
                            for a in replay["attempts"]))
        self.assertEqual(replay["source_bound_advisories"],
                         complete["source_bound_advisories"])

    def test_tampered_risk_provenance_rejected_before_any_callback(self):
        prose,proof=risk_proof()
        proof["challenges"][0]["source_evidence_span"]["quote"]="forged"
        invoked=[]
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(
                CoverageError,"V045_CHALLENGE_SOURCE_SPAN_INVALID"
            ):
                execute(proof=proof,prose=prose,output_dir=Path(d)/"stage",
                        synthetic_source_reply=lambda **p:invoked.append(p))
        self.assertEqual(invoked,[])

    def test_model_self_approved_physical_motion_always_rejected(self):
        prose,proof=risk_proof()
        def unsupported(**params):
            source=json.loads(params["request"]["messages"][1]["content"])[
                "target_sentence"
            ]
            return {"source_quote":source,
                    "interpretation":"PHYSICAL_ACTION_WITH_EXPLICIT_ACTOR",
                    "actor_id":"mara","transition_proven":True,
                    "reason":"pretend the model can authorize world truth"}
        with TemporaryDirectory() as d:
            output=execute(proof=proof,prose=prose,
                           output_dir=Path(d)/"stage",
                           synthetic_source_reply=unsupported)
        self.assertEqual(output["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(output["paid_provider_calls"],0)
        self.assertEqual(output["production_db_writes"],0)


if __name__=="__main__":
    unittest.main()
