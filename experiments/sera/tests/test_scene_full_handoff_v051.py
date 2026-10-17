"""SERA v0.51 complete no-human handoff tests: real SERA module calls only.

Real Mara source is always frozen and never substituted by the smaller Ari
control. Ari only tests a separately labelled 2-sentence positive path.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from experiments.sera.automated_row_recovery_v050 import STATUS_SOURCE
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.scene_full_handoff_v051 import handoff,run_real_mara_shadow
from experiments.sera.tests.test_fresh_scene_evidence_worker_v022 import (
    SOURCE_1,SOURCE_2,EXTRACT,SEMANTIC,TYPED,entry,fake_model,
)
from experiments.sera.tests.test_automated_row_recovery_v050 import (
    scripted_provider,
)
from experiments.sera.tests.test_real_mara_recovery_queue_v049 import (
    candidate_fixture as mara_fixture,
)


def ari_source_stage(prose=SOURCE_1):
    return {
        "schema":"sera.v050-unattended-source-bound-repair-controller",
        "status":"SOURCE_CANDIDATES_READY_FOR_FULL_REEXTRACTION_NONCANONICAL",
        "source_sha256":prose_hash(prose),
        "task_results":[{
            "sentence_id":"control_source_only",
            "status":STATUS_SOURCE,
            "semantic_truth_verified":False,
            "canonical_commit_authorized":False,
        }],
        "tasks_accounted_for":1,
        "repair_model_was_real":False,
        "full_scene_semantic_qualification_proven":False,
        "world_commit_authorized":False,
        "world_db_writes":0,
        "requires_manual_intervention":False,
    }


def ari_gate(root,stage,full_provider,writer,*,world=None):
    return handoff(
        stage=stage,prose=SOURCE_1,world=world or entry(),
        output_root=root,scene_key="v051-ari-two-sentence-positive-control",
        registry={"ari":["Ari"],"box":["box"]},
        candidate_lexicon={},
        typed_registry={"openables":["box"],"documents":[]},
        full_provider=full_provider,writer=writer,
        extraction_model=EXTRACT,semantic_model=SEMANTIC,
        typed_model=TYPED,expected_tasks=1,max_rewrites=2,
    )


def rewrite_box(log):
    def callback(*,source,defects):
        log.append({"source":source,"defects":deepcopy(defects)})
        assert source==SOURCE_1
        return {"prose":SOURCE_2,"receipt":{
            "source_prose_sha256":prose_hash(source),
            "response_id":"v051-synthetic-ari-auto-rewrite",
            "model":"synthetic/v051-writer",
            "finish_reason":"stop",
            "cost_usd":"0",
        }}
    return callback


def bad_mara_full_provider(log, *, missing_reply=False):
    """Send RECEIPTED malformed full-sweep rows to real v0.22 worker."""
    def callback(*,key,model,prepared):
        assert key=="SYNTHETIC_NO_EXTERNAL_KEY_FOR_V051"
        req=prepared["request"]
        assert not any(k in str(req) for k in (
            "max_tokens","max_output_tokens","max_completion_tokens",
            "max_new_tokens","max_generation_tokens",
        ))
        log.append(model)
        if missing_reply:
            raise ConnectionError("unknown synthetic provider request result")
        return {"error":None,"raw":{
            "id":f"scripted-incomplete-full-mara-{len(log)}",
            "model":model,"usage":{"cost":"0"},
            "choices":[{"finish_reason":"stop",
                        "message":{"content":'{"rows":[]}'}}],
        }}
    return callback


class V051SourceRepairToFullSceneHandoffTests(TestCase):
    def test_ari_positive_real_v022_v021_v020_auto_rewrite_and_replay(self):
        model_calls=[]
        writer_calls=[]
        stage=ari_source_stage()
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            first=ari_gate(
                root,stage,fake_model(model_calls),
                rewrite_box(writer_calls),
            )
            second=ari_gate(
                root,stage,
                lambda **kw:self.fail("v022 provider repeated on replay"),
                lambda **kw:self.fail("v020 writer repeated on replay"),
            )
            self.assertTrue((root/"evidence"/
                            (prose_hash(SOURCE_1)+".json")).exists())
            self.assertTrue((root/"evidence"/
                            (prose_hash(SOURCE_2)+".json")).exists())
        self.assertEqual(first,second)
        self.assertEqual(first["status"],
                         "FULL_SCENE_STRUCTURAL_CANDIDATE_NONCANONICAL")
        self.assertEqual(first["scene_status"],
                         "SCENE_CANDIDATE_READY_NONCANONICAL")
        self.assertEqual(first["automatic_rewrites"],1)
        self.assertEqual(first["scene_final_source_sha256"],
                         prose_hash(SOURCE_2))
        self.assertEqual(len(writer_calls),1)
        self.assertGreater(len(model_calls),1)
        self.assertFalse(first["canonical_commit_authorized"])
        self.assertFalse(first["independent_semantic_gold_verified"])
        self.assertEqual(first["production_world_db_writes"],0)

    def test_mara_real_frozen_source_enters_v050_then_full_scene_safe_stop(self):
        source,receipts,coverage=mara_fixture()
        older={"attempts_started":14,"observed_spend_usd":"0.10590625"}
        row_calls=[]
        full_calls=[]
        writer_calls=[]
        with TemporaryDirectory() as tmp:
            with patch(
                "experiments.sera.scene_full_handoff_v051.verified_real_receipts",
                return_value=(source,receipts,coverage,older),
            ):
                def unsafe_writer(**kwargs):
                    writer_calls.append(kwargs)
                    self.fail("Cannot rewrite scene without full evidence")
                out=run_real_mara_shadow(
                    receipt_root="unused",
                    output_root=tmp,
                    row_provider=scripted_provider(
                        row_calls,invalid_first={"s006","s004"},
                    ),
                    full_provider=bad_mara_full_provider(full_calls),
                    writer=unsafe_writer,
                )
                previous_count=(len(row_calls),len(full_calls))
                again=run_real_mara_shadow(
                    receipt_root="unused",output_root=tmp,
                    row_provider=lambda **kw:self.fail("row replay repost"),
                    full_provider=lambda **kw:self.fail("full replay repost"),
                    writer=lambda **kw:self.fail("rewrite replay repost"),
                )
        self.assertEqual(out,again)
        self.assertEqual(out["row_stage"]["candidate_source_rows_reextracted"],5)
        self.assertEqual(out["row_stage"]["source_blind_advisories"],21)
        self.assertEqual(out["row_stage"]["scripted_fallback_attempts_this_run"],2)
        self.assertEqual(previous_count[0],28)
        self.assertEqual(previous_count[1],2)
        self.assertEqual(writer_calls,[])
        self.assertEqual(out["full_stage"]["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(out["full_stage"]["scene_status"],"FAILED_SAFE_FINAL")
        self.assertEqual(out["full_stage"]["row_stage_task_count"],26)
        self.assertTrue(
            out["full_stage"]["stage_reached_actual_v020_v021_v022"]
        )
        self.assertEqual(out["full_stage"]["automatic_rewrites"],0)
        self.assertFalse(out["canonical_commit_authorized"])
        self.assertEqual(out["full_stage"]["production_world_db_writes"],0)

    def test_unknown_inflight_row_stops_before_full_scene_callbacks(self):
        source,receipts,coverage=mara_fixture()
        log=[]
        with TemporaryDirectory() as tmp:
            with patch(
                "experiments.sera.scene_full_handoff_v051.verified_real_receipts",
                return_value=(source,receipts,coverage,
                              {"attempts_started":14,
                               "observed_spend_usd":"0.10590625"}),
            ):
                def missing(*,key,model,prepared):
                    log.append(model)
                    raise RuntimeError("provider request uncertain")
                out=run_real_mara_shadow(
                    receipt_root="unused",output_root=tmp,
                    row_provider=missing,
                    full_provider=lambda **kw:self.fail(
                        "unsafe v022 full worker after uncertain row"),
                    writer=lambda **kw:self.fail("unsafe rewrite"),
                )
        self.assertEqual(log,["synthetic/v050-independent-primary"])
        self.assertEqual(out["row_stage"]["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(out["full_stage"]["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(out["full_stage"]["scene_status"],"NOT_STARTED")
        self.assertFalse(out["full_stage"]
                         ["stage_reached_actual_v020_v021_v022"])

    def test_source_mismatch_rejected_before_any_full_scene_model(self):
        stage=ari_source_stage(SOURCE_2)
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(
                CoverageError,"V051_ROW_STAGE_AUTHORITY_OR_SOURCE_INVALID",
            ):
                ari_gate(
                    Path(tmp),stage,
                    lambda **kw:self.fail("invalid source dispatched"),
                    lambda **kw:self.fail("invalid source rewritten"),
                )

    def test_row_stage_falsely_promoting_own_verdict_is_rejected(self):
        stage=ari_source_stage()
        stage["task_results"][0]["semantic_truth_verified"]=True
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(
                CoverageError,"V051_ROW_REPAIR_SOURCE_OR_TRUTH_MISMATCH",
            ):
                ari_gate(Path(tmp),stage,lambda **kw:None,lambda **kw:None)

    def test_incomplete_row_accounting_is_never_full_source_proof(self):
        stage=ari_source_stage()
        stage["tasks_accounted_for"]=0
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(
                CoverageError,"V051_INCOMPLETE_ROW_REPAIR_ACCOUNTING",
            ):
                ari_gate(Path(tmp),stage,lambda **kw:None,lambda **kw:None)

    def test_world_revision_drift_rejected_before_replay(self):
        stage=ari_source_stage()
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            ari_gate(root,stage,fake_model([]),rewrite_box([]))
            changed=entry()
            changed["revision"]+=1
            with self.assertRaisesRegex(
                CoverageError,"V051_RESTART_SOURCE_WORLD_OR_REPAIR_STAGE_DRIFT",
            ):
                ari_gate(root,stage,lambda **kw:self.fail("unsafe provider"),
                         lambda **kw:self.fail("unsafe writer"),world=changed)

    def test_full_scene_uncertain_first_provider_no_second_billed_post(self):
        stage=ari_source_stage()
        calls=[]
        def crash(*,key,model,prepared):
            calls.append(model)
            raise RuntimeError("inflight response unreceived")
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            initial=ari_gate(root,stage,crash,
                             lambda **kw:self.fail("unknown rewrite"))
            repeated=ari_gate(root,stage,
                             lambda **kw:self.fail("unknown resend"),
                             lambda **kw:self.fail("unknown rewrite"))
        self.assertEqual(initial,repeated)
        self.assertEqual(len(calls),1)
        self.assertEqual(initial["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(initial["scene_status"],"FAILED_SAFE_FINAL")
        self.assertEqual(initial["automatic_rewrites"],0)
        self.assertFalse(initial["requires_manual_intervention"])


if __name__=="__main__":
    import unittest
    unittest.main()
