"""SERA v0.50: zero-human, zero-real-provider single-row repair safety tests."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from experiments.sera.automated_row_recovery_v050 import (
    execute, request_for, MODELS,
)
from experiments.sera.coverage import CoverageError
from experiments.sera.real_mara_recovery_queue_v049 import build_work_orders
from experiments.sera.tests.test_real_mara_recovery_queue_v049 import (
    candidate_fixture,
)


def scripted_provider(calls, *, invalid_first=None,
                      invalid_all=None, crash_task=None):
    invalid_first=set(invalid_first or [])
    invalid_all=set(invalid_all or [])
    def provider(*,key,model,prepared):
        assert key=="OFFLINE_TEST_DOUBLE_NOT_AN_OPENROUTER_KEY"
        req=prepared["request"]
        data=json.loads(req["messages"][1]["content"])
        task_id=data["task_id"]
        sid=(data["target_sentences"][0]["id"]
             if "target_sentences" in data else
             data["exact_chronological_sentences"][0]["sentence_id"])
        assert not any(n in json.dumps(req) for n in (
            "max_tokens","max_output_tokens","max_completion_tokens",
            "max_generation_tokens","max_new_tokens",
        ))
        assert "previous_model_answer" not in json.dumps(data)
        assert "risk_code" not in json.dumps(data)
        calls.append({"task_id":task_id,"sentence_id":sid,
                      "model":model})
        if crash_task==sid:
            raise RuntimeError("uncertain in-flight provider response")
        invalid=(sid in invalid_all or
                 (sid in invalid_first and model==MODELS[0]))
        if "target_sentences" in data:
            row={
                "sentence_id":sid,
                "disposition":"NO_TRACKED_CHANGE",
                "reason":"Synthetic candidate ONLY; no semantic correctness",
                "mentions":[],"events":[],
            }
            if invalid:
                row["mentions"]=[{
                    "entity_ref":"new:phantom",
                    "role":"MENTIONED",
                    "evidence_quote":"a robot teleported here from nowhere",
                    "occurrence":0,
                }]
            content={"rows":[row]}
        else:
            sentence=data["exact_chronological_sentences"][0]["quote"]
            content={
                "verdict":"UNCERTAIN","operation_kind":"UNMAPPED",
                "effect":"UNKNOWN",
                "evidence_quote":(
                    "a robot teleported here from nowhere"
                    if invalid else sentence
                ),
                "reason":"Synthetic source-bound advisor, not world truth",
            }
        return {"error":None,"raw":{
            "id":f"offline-v050-{len(calls)}",
            "model":model,"usage":{"cost":"0"},
            "choices":[{"finish_reason":"stop",
                        "message":{"content":json.dumps(content)}}],
        }}
    return provider


def fixture():
    source,receipts,coverage=candidate_fixture()
    audit,tasks=build_work_orders(
        source=source,receipts=receipts,coverage=coverage,
    )
    return source,audit,tasks


class AutomatedRowRecoveryV050Tests(TestCase):
    def test_5_reextractions_21_advisories_zero_manual_and_zero_world_writes(self):
        source,audit,tasks=fixture()
        calls=[]
        with TemporaryDirectory() as tmp:
            result=execute(source=source,audit=audit,tasks=tasks,
                           output_root=tmp,
                           scripted_provider=scripted_provider(calls))
            before=len(calls)
            replay=execute(source=source,audit=audit,tasks=tasks,
                           output_root=tmp,
                           scripted_provider=lambda **kw:self.fail(
                               "must not call model on restart"))
        self.assertEqual(result["status"],
             "SOURCE_CANDIDATES_READY_FOR_FULL_REEXTRACTION_NONCANONICAL")
        self.assertEqual(result["candidate_source_rows_reextracted"],5)
        self.assertEqual(result["source_blind_advisories"],21)
        self.assertEqual(result["tasks_accounted_for"],26)
        self.assertEqual(len(calls),26)
        self.assertEqual(before,len(calls))
        self.assertEqual(result,replay)
        self.assertEqual(result["world_db_writes"],0)
        self.assertEqual(result["real_new_paid_calls"],0)
        self.assertFalse(result["world_commit_authorized"])
        self.assertFalse(result["full_scene_semantic_qualification_proven"])
        self.assertFalse(result["requires_manual_intervention"])
        self.assertEqual(result["next_automatic_action"],
                         "AUTOMATIC_FULL_SCENE_REEXTRACTION_AND_VALIDATION")

    def test_complete_bad_source_quote_automatically_invokes_distinct_fallback(self):
        source,audit,tasks=fixture()
        calls=[]
        with TemporaryDirectory() as tmp:
            output=execute(
                source=source,audit=audit,tasks=tasks,output_root=tmp,
                scripted_provider=scripted_provider(
                    calls,invalid_first={"s006","s004"},
                ))
        self.assertEqual(output["status"],
             "SOURCE_CANDIDATES_READY_FOR_FULL_REEXTRACTION_NONCANONICAL")
        self.assertEqual(output["scripted_fallback_attempts_this_run"],2)
        self.assertEqual(len(calls),28)
        affected=[x for x in output["task_results"]
                  if x["sentence_id"] in {"s006","s004"}]
        self.assertTrue(all(x["model"]==MODELS[1] for x in affected))
        self.assertFalse(output["world_commit_authorized"])

    def test_two_receipted_invalid_model_answers_auto_replan_not_manual(self):
        source,audit,tasks=fixture()
        calls=[]
        with TemporaryDirectory() as tmp:
            output=execute(
                source=source,audit=audit,tasks=tasks,output_root=tmp,
                scripted_provider=scripted_provider(
                    calls,invalid_all={"s006"},
                ))
        self.assertEqual(output["status"],"REPLAN_REQUIRED_NONCANONICAL")
        self.assertEqual(output["scripted_fallback_attempts_this_run"],1)
        self.assertEqual(len(calls),27)
        self.assertEqual(output["candidate_source_rows_reextracted"],4)
        self.assertEqual(output["source_blind_advisories"],21)
        self.assertEqual(output["tasks_accounted_for"],26)
        self.assertEqual(output["next_automatic_action"],
                         "AUTO_REPLAN_REWRITE_OR_FULL_SCENE_REEXTRACTION")
        self.assertFalse(output["requires_manual_intervention"])
        self.assertEqual(output["world_db_writes"],0)

    def test_unknown_unreceipted_request_stops_no_backup_model_no_resend(self):
        source,audit,tasks=fixture()
        calls=[]
        with TemporaryDirectory() as tmp:
            first=execute(
                source=source,audit=audit,tasks=tasks,output_root=tmp,
                scripted_provider=scripted_provider(
                    calls,crash_task="s001",
                ))
            replay=execute(
                source=source,audit=audit,tasks=tasks,output_root=tmp,
                scripted_provider=lambda **kw:self.fail(
                    "unsafe repeat"))
        self.assertEqual(first["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(first["failure_code"],
                         "V050_UNKNOWN_PROVIDER_EXCEPTION_NO_RESEND")
        self.assertEqual(len(calls),1)
        self.assertEqual(replay,first)
        self.assertEqual(first["world_db_writes"],0)

    def test_blind_prompts_never_embed_original_bad_model_proposals(self):
        source,audit,tasks=fixture()
        for task in tasks:
            wire=request_for(source=source,task=task,audit=audit)
            user=json.loads(wire["messages"][1]["content"])
            self.assertEqual(user["task_id"],task["task_id"])
            self.assertNotIn("Gemini",json.dumps(user))
            self.assertNotIn("Haiku",json.dumps(user))
            self.assertNotIn("model_candidate",json.dumps(user))
            self.assertNotIn("risk_code",json.dumps(user))
            self.assertNotIn("previous",json.dumps(user))
        self.assertEqual(sum("target_sentences" in json.loads(
            request_for(source=source,task=task,audit=audit)
            ["messages"][1]["content"]) for task in tasks),5)

    def test_policy_and_source_drift_denied_before_substitution(self):
        source,audit,tasks=fixture()
        tampered=[dict(x) for x in tasks]
        tampered[0]={**tampered[0],"source_sentence":"false changed text"}
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(
                CoverageError,"V050_INVALID_OR_CHANGED_SOURCE_SPAN",
            ):
                execute(source=source,audit=audit,tasks=tampered,
                        output_root=tmp,
                        scripted_provider=scripted_provider([]))

    def test_duplicate_model_profile_not_independent(self):
        source,audit,tasks=fixture()
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(
                CoverageError,"V050_INDEPENDENT_MODELS_REQUIRED",
            ):
                execute(source=source,audit=audit,tasks=tasks,
                        output_root=tmp,scripted_provider=scripted_provider([]),
                        model_profiles=("same","same"))


if __name__=="__main__":
    import unittest
    unittest.main()
