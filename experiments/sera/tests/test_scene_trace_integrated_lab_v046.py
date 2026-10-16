"""SERA v0.46 v0.18 + v0.22 genuine code-path composition — all offline.

These are policy/protocol tests, not independent real-model correctness.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from experiments.sera.coverage import CoverageError
from experiments.sera.scene_trace_evidence_challenge_v044 import build_challenges
from experiments.sera.scene_trace_integrated_lab_v046 import (
    _audit_from_real_challenges, _source_bound_semantics, orchestrate,
)
from experiments.sera.scene_trace_real_challenge_smoke_v045 import (
    synthetic_source_only_double,
)
from experiments.sera.scene_trace_integrated_smoke_v046 import (
    synthetic_v018_semantic, intentionally_incomplete_full_sweep,
    COUNTER,
)
from experiments.sera.tests.test_scene_trace_evidence_challenge_v044 import (
    simulated_v043_envelope,
)
from experiments.sera.semantic_risks_v011 import make_task_request


def historical_risks():
    prose,comparison=simulated_v043_envelope()
    return prose,build_challenges(
        archived_comparison=comparison,frozen_prose=prose,
    )


class IntegratedSceneTraceV046Tests(TestCase):
    def setUp(self):
        COUNTER["semantic"]=0
        COUNTER["full"]=0

    def test_actual_v011_requests_are_source_only_and_not_model_outcomes(self):
        source,proof=historical_risks()
        audit=_audit_from_real_challenges(
            risk_proof=proof,prose=source,
        )
        self.assertEqual(audit["targeted_task_count"],2)
        for row in audit["targeted_tasks"]:
            request=make_task_request(
                audit=audit,task_id=row["task_id"],
            )
            decoded=json.loads(request["messages"][1]["content"])
            self.assertIn("exact_chronological_sentences",decoded)
            self.assertNotIn("CHANGE_STATE",str(decoded))
            self.assertNotIn("PENCIL_MOTION_OBSERVED_BUT_CAUSAL_ACTOR_UNKNOWN",
                             str(decoded))
            self.assertNotIn("previous_model",str(decoded))
            self.assertEqual(request["model_output_token_limit"],
                             "NOT_SET_BY_APPLICATION")
            self.assertFalse(request["commit_authorized"])

    def test_existing_v018_binder_replies_persist_and_restart_without_model(self):
        source,proof=historical_risks()
        with TemporaryDirectory() as tmp:
            root=Path(tmp)/"semantic"
            initial=_source_bound_semantics(
                risk_proof=proof,prose=source,output_root=root,
                synthetic_reply=synthetic_v018_semantic,
            )
            self.assertEqual(COUNTER["semantic"],2)
            repeat=_source_bound_semantics(
                risk_proof=proof,prose=source,output_root=root,
                synthetic_reply=lambda **kw: self.fail("unnecessary model call"),
            )
        self.assertEqual(initial,repeat)
        self.assertEqual(repeat["status"],
                         "TWO_SOURCE_BOUND_ADVISORIES_NONCANONICAL")
        self.assertEqual(repeat["scripted_dispatches_current_run"],0)
        self.assertTrue(all(x["status"]=="HOLD_MODEL_RESPONSE_NOT_AUTHORITY"
                            for x in repeat["bound_advisories"]))
        self.assertFalse(repeat["canonical_commit_authorized"])

    def test_started_unreceipted_request_fails_safe_without_resend(self):
        source,proof=historical_risks()
        invoked=[]
        def missing(**kwargs):
            invoked.append(1)
            raise ConnectionError("unknown")
        with TemporaryDirectory() as tmp:
            root=Path(tmp)/"semantic"
            first=_source_bound_semantics(
                risk_proof=proof,prose=source,output_root=root,
                synthetic_reply=missing,
            )
            next_try=_source_bound_semantics(
                risk_proof=proof,prose=source,output_root=root,
                synthetic_reply=missing,
            )
        self.assertEqual(invoked,[1])
        self.assertEqual(first["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(next_try["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(next_try["reason_code"],
                         "V046_STARTED_WITHOUT_RECEIPT_NO_RESEND")
        self.assertFalse(next_try["canonical_commit_authorized"])

    def test_forged_quote_never_source_bound(self):
        source,proof=historical_risks()
        def bad(*,prepared,task_id):
            return {"choices":[{"finish_reason":"stop",
                        "message":{"content":json.dumps({
                            "verdict":"STATE_OBSERVATION",
                            "operation_kind":"OBSERVE","effect":"NONE",
                            "evidence_quote":"an invented pencil teleport",
                            "reason":"do not trust this model",
                        })}}]}
        with TemporaryDirectory() as tmp:
            result=_source_bound_semantics(
                risk_proof=proof,prose=source,
                output_root=Path(tmp)/"semantic",synthetic_reply=bad,
            )
        self.assertEqual(result["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(result["reason_code"],
                         "V046_SEMANTIC_SOURCE_BIND_FAILED")

    def test_real_v022_full_sweep_rejects_incomplete_synthetic_scene(self):
        source,proof=historical_risks()
        with TemporaryDirectory() as tmp:
            with patch(
                "experiments.sera.scene_trace_integrated_lab_v046.compare_receipts",
                return_value=proof,
            ):
                result=orchestrate(
                    bench_dir="/not-used",pencil_dir="/not-used",
                    work_root=Path(tmp)/"integration",
                    synthetic_repair_reply=synthetic_source_only_double,
                    synthetic_semantic_reply=synthetic_v018_semantic,
                    synthetic_full_extraction_reply=intentionally_incomplete_full_sweep,
                )
        self.assertEqual(result["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(result["repair_stage_status"],
                         "SOURCE_BOUND_REPAIR_ADVISORIES_ONLY")
        self.assertEqual(result["targeted_semantic_stage_status"],
                         "TWO_SOURCE_BOUND_ADVISORIES_NONCANONICAL")
        self.assertEqual(result["full_fresh_v022_stage_status"],
                         "FAILED_SAFE_FINAL")
        self.assertEqual(result["paid_provider_calls_new"],0)
        self.assertEqual(result["production_db_writes"],0)
        self.assertFalse(result["independent_semantic_qualification"])
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertGreater(COUNTER["full"],0)

    def test_repair_failure_prevents_later_full_evidence_dispatch(self):
        source,proof=historical_risks()
        def forged(**params):
            return {"source_quote":"someone teleported the watch",
                    "interpretation":"PHYSICAL_ACTION_WITH_EXPLICIT_ACTOR",
                    "actor_id":"mara","transition_proven":True,
                    "reason":"synthetic known wrong"}
        with TemporaryDirectory() as tmp:
            with patch(
                "experiments.sera.scene_trace_integrated_lab_v046.compare_receipts",
                return_value=proof,
            ):
                result=orchestrate(
                    bench_dir="/not-used",pencil_dir="/not-used",
                    work_root=Path(tmp)/"integration",
                    synthetic_repair_reply=forged,
                    synthetic_semantic_reply=lambda **kw:self.fail(
                        "semantic stage must not execute"),
                    synthetic_full_extraction_reply=lambda **kw:self.fail(
                        "full worker must not execute"),
                )
        self.assertEqual(result["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(result["targeted_semantic_stage_status"],
                         "NOT_STARTED")
        self.assertEqual(result["full_fresh_v022_stage_status"],
                         "NOT_STARTED")
        self.assertEqual(COUNTER["semantic"],0)
        self.assertEqual(COUNTER["full"],0)

    def test_tampered_source_input_denied_before_any_provider_callback(self):
        prose,proof=historical_risks()
        proof["challenges"][0]["source_evidence_span"]["quote"]="tampered"
        with self.assertRaisesRegex(
            CoverageError,"V045_CHALLENGE_SOURCE_SPAN_INVALID",
        ):
            _audit_from_real_challenges(
                risk_proof=proof,prose=prose,
            )
        self.assertEqual(COUNTER["semantic"],0)


if __name__=="__main__":
    import unittest
    unittest.main()
