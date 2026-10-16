"""v0.49 tests — fake receipt data cannot silently imply physical truth.

Full immutable 14-receipt verification is executed separately by the
self-hosted source-run CI using the actual v0.48 archived artifact.
"""
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from experiments.sera.coverage import CoverageError
from experiments.sera.real_blind_benchmark_v040 import MODELS
from experiments.sera.real_full_scene_blind_v048 import prepare
from experiments.sera.real_mara_recovery_queue_v049 import (
    DISAGREEMENTS,REEXTRACT_IDS,
    build_work_orders,execute_scripted,save_plan,
)


def candidate_fixture():
    source,_=prepare()
    ids=[s["id"] for s in source["plan"]["source_sentences"]]
    statuses={}
    for model in MODELS:
        statuses[model]={
            "source_bound_sentence_count":
                28 if model==MODELS[0] else 23,
            "quarantined_sentence_count":
                0 if model==MODELS[0] else 5,
            "unsampled_sentence_count":0,
            "source_risk_flags":([{
                "sentence_id":"s022",
                "risk_code":"PENCIL_MOTION_OBSERVED_BUT_CAUSAL_ACTOR_UNKNOWN",
            }] if model==MODELS[0] else [{
                "sentence_id":"s004",
                "risk_code":"STATIC_WATCH_PREDICATE_MISREAD_AS_TRANSITION_RISK",
            }]),
        }
    coverage={
        "model_results":statuses,
        "both_models_source_bound_sentence_count":23,
        "model_candidate_disagreement_sentence_ids":sorted(DISAGREEMENTS),
        "model_candidate_signature_disagreement_count":21,
        "canonical_commit_authorized":False,
    }
    receipts=[]
    for batch in source["plan"]["batches"]:
        for model in MODELS:
            rows=[{"sentence_id":sid}
                  for sid in batch["sentence_ids"] if sid in REEXTRACT_IDS
                  and model==MODELS[1]]
            receipts.append({"model":model,"batch_id":batch["batch_id"],
                             "assessment":{"quarantined_rows":rows}})
    return source,receipts,coverage


def untrusted_scripted_answer(*,task_id,prepared):
    data=json.loads(prepared["messages"][1]["content"])
    assert data["task_id"]==task_id
    assert len(data["exact_chronological_sentences"])==1
    quote=data["exact_chronological_sentences"][0]["quote"]
    return {"choices":[{
        "finish_reason":"stop",
        "message":{"content":json.dumps({
            "verdict":"UNCERTAIN",
            "operation_kind":"UNMAPPED",
            "effect":"UNKNOWN",
            "evidence_quote":quote,
            "reason":"synthetic v0.49 source quote check; not physical truth",
        })},
    }]}


class MaraRecoveryQueueV049Tests(TestCase):
    def test_26_distinct_blind_review_tasks_from_real_status_shape(self):
        source,receipts,coverage=candidate_fixture()
        audit,tasks=build_work_orders(
            source=source,receipts=receipts,coverage=coverage,
        )
        self.assertEqual(len(tasks),26)
        self.assertEqual(audit["targeted_task_count"],26)
        self.assertEqual({x["sentence_id"] for x in tasks},
                         REEXTRACT_IDS|DISAGREEMENTS)
        self.assertEqual(sum(x["action"].startswith("AUTO_REEXTRACT")
                             for x in tasks),5)
        self.assertEqual(sum(len(x["causal_risk_flags"]) for x in tasks),2)
        self.assertTrue(all(x["physical_transition_authorized"] is False
                            for x in tasks))
        self.assertTrue(all(x["model_truth_known"] is False for x in tasks))
        for task in tasks:
            request=task["request"]
            user=json.loads(request["messages"][1]["content"])
            self.assertEqual(user["exact_chronological_sentences"][0]
                             ["quote"],task["source_sentence"])
            self.assertNotIn("risk_code",str(user))
            self.assertNotIn("model_candidate",str(user))
            self.assertNotIn("google/gemini",str(user))
            self.assertNotIn("anthropic/claude",str(user))
            self.assertNotIn("max_tokens",str(request))
            self.assertNotIn("max_output_tokens",str(request))

    def test_26_scripted_reviewed_quotes_remain_noncanonical_and_restart_zero(self):
        source,receipts,coverage=candidate_fixture()
        audit,tasks=build_work_orders(
            source=source,receipts=receipts,coverage=coverage,
        )
        prepared={"audit":audit,"tasks":tasks}
        with TemporaryDirectory() as tmp:
            first=execute_scripted(
                prepared=prepared,output_root=Path(tmp),
                synthetic_reply=untrusted_scripted_answer,
            )
            second=execute_scripted(
                prepared=prepared,output_root=Path(tmp),
                synthetic_reply=lambda **kw:self.fail(
                    "never call synthetic provider on replay"),
            )
        self.assertEqual(first["status"],
                         "SOURCE_BOUND_MODEL_ADVISORIES_NONCANONICAL")
        self.assertEqual(first["bound_task_count"],26)
        self.assertEqual(first["scripted_model_calls_this_run"],26)
        self.assertEqual(second["bound_task_count"],26)
        self.assertEqual(second["scripted_model_calls_this_run"],0)
        self.assertEqual(first["task_advisories"],second["task_advisories"])
        self.assertFalse(first["semantic_truth_proven"])
        self.assertFalse(first["world_commit_authorized"])
        self.assertEqual(first["real_model_calls_this_run"],0)
        self.assertEqual(first["quarantined_rows_reextracted_by_real_provider"],0)
        self.assertEqual(first["production_db_writes"],0)

    def test_started_without_receipt_must_not_resend(self):
        source,receipts,coverage=candidate_fixture()
        audit,tasks=build_work_orders(
            source=source,receipts=receipts,coverage=coverage,
        )
        prepared={"audit":audit,"tasks":tasks}
        called=[]
        def missing(**kwargs):
            called.append(kwargs["task_id"])
            raise RuntimeError("undelivered")
        with TemporaryDirectory() as tmp:
            out=execute_scripted(
                prepared=prepared,output_root=tmp,synthetic_reply=missing,
            )
            repeat=execute_scripted(
                prepared=prepared,output_root=tmp,synthetic_reply=missing,
            )
        self.assertEqual(len(called),1)
        self.assertEqual(out["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(repeat["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(
            repeat["failure_code"],"V049_UNKNOWN_IN_FLIGHT_NO_RESEND",
        )

    def test_fabricated_quote_fails_without_repairing_it_into_truth(self):
        source,receipts,coverage=candidate_fixture()
        audit,tasks=build_work_orders(
            source=source,receipts=receipts,coverage=coverage,
        )
        def wrong(**kw):
            data=untrusted_scripted_answer(**kw)
            reply=json.loads(data["choices"][0]["message"]["content"])
            reply["evidence_quote"]="fabricated teleport outside source"
            data["choices"][0]["message"]["content"]=json.dumps(reply)
            return data
        with TemporaryDirectory() as tmp:
            failed=execute_scripted(
                prepared={"audit":audit,"tasks":tasks},
                output_root=tmp,synthetic_reply=wrong,
            )
        self.assertEqual(failed["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(failed["failure_code"],
                         "V049_INVALID_INDEPENDENT_SOURCE_QUOTE")
        self.assertEqual(failed["world_commit_authorized"],False)

    def test_source_model_counts_changed_fail_closed(self):
        source,receipts,coverage=candidate_fixture()
        changed=deepcopy(coverage)
        changed["model_results"][MODELS[1]][
            "source_bound_sentence_count"]=24
        with self.assertRaisesRegex(
            CoverageError,"V049_ARCHIVED_SCOPE_COUNTS_CHANGED",
        ):
            build_work_orders(
                source=source,receipts=receipts,coverage=changed,
            )

    def test_risk_tasks_cannot_be_suppressed(self):
        source,receipts,coverage=candidate_fixture()
        changed=deepcopy(coverage)
        changed["model_results"][MODELS[0]]["source_risk_flags"]=[]
        with self.assertRaisesRegex(
            CoverageError,"V049_INCOMPLETE_OR_CONFLATED_WORK_ORDERS",
        ):
            build_work_orders(
                source=source,receipts=receipts,coverage=changed,
            )

    def test_unverified_or_missing_archive_halts_before_creating_tasks(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaisesRegex(
                CoverageError,"V049_RECEIPT_FILE_UNREADABLE",
            ):
                save_plan(receipt_root=root,output_root=root/"work")
            self.assertFalse((root/"work"/"work_orders.json").exists())


if __name__=="__main__":
    import unittest
    unittest.main()
