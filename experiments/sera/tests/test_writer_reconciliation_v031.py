"""v0.31: resume previously charged SCENE WRITER, never send it again.

All provider calls here use synthetic OpenRouter envelopes; an authenticated
generation reconciler is injected, never a real model billing or world write.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.composed_scene_runner_v023 import run
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.tests.test_composed_scene_runner_v023 import (
    SOURCE_1, SOURCE_2, WRITER, SWEEP, SEMANTIC, FACET,
    provider_fixture, entry,
)
from experiments.sera.openrouter_scene_writer_v021 import (
    create_writer, make_request,
)

POLICY = "v031-verified-generation-readonly-recovery"


def run_scene(root, provider, reconciler):
    return run(
        prose=SOURCE_1, world=entry(), scene_key="v031-writer-restart",
        work_root=root, api_key="synthetic-key",
        registry={"ari": ["Ari"], "box": ["box"]},
        candidate_lexicon={},
        typed_registry={"openables": ["box"], "documents": []},
        writer_model=WRITER, sweep_model=SWEEP,
        semantic_model=SEMANTIC, facet_model=FACET,
        provider_call=provider,
        immutable_story_context={"canonical": "never spawn train"},
        max_rewrites=2,
        reconciler=reconciler, reconciliation_policy_id=POLICY,
    )


def receipt(model, source):
    return {
        "error": None, "raw": {
            "id": "recovered-writer-v031",
            "model": model, "usage": {"cost": "0.002"},
            "choices": [{"finish_reason": "stop", "message": {"content":
                json.dumps({
                    "source_prose_sha256": prose_hash(source),
                    "revised_scene_prose": SOURCE_2,
                })}}],
        },
    }


class WriterResumeV031Tests(unittest.TestCase):
    def test_one_lost_writer_reply_reconciles_and_requalifies_scene(self):
        all_calls = []
        complete = provider_fixture(all_calls)
        paid_writer_posts = []
        recovered_gets = []
        def provider(*,key,model,prepared):
            if model == WRITER:
                paid_writer_posts.append(prepared)
                return {"error":"TRANSPORT_UNAVAILABLE","raw":None}
            return complete(key=key,model=model,prepared=prepared)
        def reconciler(*,model,request,request_sha256):
            recovered_gets.append((model,request_sha256))
            self.assertEqual(model,WRITER)
            self.assertEqual(request_sha256, __import__("hashlib").sha256(
                __import__("experiments.sera.world_state_v02",
                           fromlist=["canonical"]).canonical({
                    "model":model,"request":request,
                }).encode()).hexdigest())
            return receipt(model,SOURCE_1)
        with TemporaryDirectory() as d:
            root=Path(d)
            first=run_scene(root,provider,reconciler)
            self.assertEqual(first["status"],"FAILED_SAFE_FINAL")
            self.assertEqual(first["reason_code"],
                             "V020_REWRITE_PROVIDER_FAILED_SAFE")
            second=run_scene(
                root,
                lambda **kw: (self.fail("writer POST repeated")
                              if kw["model"] == WRITER else complete(**kw)),
                reconciler,
            )
            prior=(root/"scene_controller"/
                   "pre_reconciled_writer_safe_stop.json")
            self.assertTrue(prior.is_file())
            self.assertEqual(json.loads(prior.read_text()),first)
            archived=list((root/"writer_paid_receipts").glob(
                "*.response.json"))
            self.assertEqual(len(archived),1)
            third=run_scene(root,lambda **kw:self.fail(
                "Finished job issued duplicate provider call"),reconciler)
        self.assertEqual(second,third)
        self.assertEqual(second["status"],
                         "SCENE_CANDIDATE_READY_NONCANONICAL")
        self.assertEqual(second["rewrite_count"],1)
        self.assertEqual(second["candidate_prose_noncanonical"],SOURCE_2)
        self.assertEqual(len(paid_writer_posts),1)
        self.assertEqual(len(recovered_gets),1)
        self.assertFalse(second["canonical_commit_authorized"])
        self.assertEqual(second["world_db_writes"],0)
        self.assertFalse(second["requires_manual_intervention"])

    def test_unknown_generation_remains_terminal_without_resending_writer(self):
        all_calls=[]
        complete=provider_fixture(all_calls)
        attempts=[]
        def provider(*,key,model,prepared):
            if model == WRITER:
                attempts.append(1)
                return {"error":"TRANSPORT_UNAVAILABLE","raw":None}
            return complete(key=key,model=model,prepared=prepared)
        checks=[]
        def unknown(**kwargs):
            checks.append(kwargs)
            raise CoverageError("V030_GENERATION_ID_UNAVAILABLE_NO_RESEND")
        with TemporaryDirectory() as d:
            root=Path(d)
            first=run_scene(root,provider,unknown)
            again=run_scene(root,lambda **kw:self.fail(
                "NO paid provider call may be retried"),unknown)
            self.assertFalse((root/"scene_controller"/
                "pre_reconciled_writer_safe_stop.json").exists())
        self.assertEqual(first,again)
        self.assertEqual(first["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(len(attempts),1)
        self.assertEqual(len(checks),1)

    def test_recovery_only_writer_rejects_unstarted_or_unscoped_call(self):
        with TemporaryDirectory() as d:
            writer=create_writer(
                api_key="synthetic",model=WRITER,archive_dir=Path(d),
                story_context={"canonical":"never spawn train"},
                provider_call=lambda **kw:self.fail(
                    "recovery may not charge provider"),
                reconciler=lambda **kw:self.fail(
                    "No started record means no provider GET either"),
            )
            with self.assertRaisesRegex(CoverageError,
                                        "V031_NO_PRIOR_BILLABLE_ATTEMPT"):
                writer.recover_existing(
                    source=SOURCE_1,defects=["source has no open baseline"])
        with TemporaryDirectory() as d:
            writer=create_writer(api_key="synthetic",model=WRITER,
                                 archive_dir=Path(d))
            with self.assertRaisesRegex(CoverageError,
                                        "V031_RECOVERY_RECONCILER_REQUIRED"):
                writer.recover_existing(
                    source=SOURCE_1,defects=["defective"])

    def test_controller_saved_receipt_without_callback_response_never_rebills(self):
        # The model can have replied and been journaled even if controller
        # crashed before saving rewrite_00.json. A crash recovery is
        # an archive replay, not another model call.
        from experiments.sera.artifact_scene_checker_v021 import create_checker
        from experiments.sera.fresh_scene_evidence_worker_v022 import create_preparer
        from experiments.sera.unattended_scene_rewrite_v020 import execute
        from experiments.sera.tests.test_composed_scene_runner_v023 import (
            provider_fixture,
        )
        with TemporaryDirectory() as d:
            root=Path(d)
            stages=provider_fixture([])
            preparer=create_preparer(
                evidence_root=root/"evidence",work_root=root/"jobs",
                scene_key="v031-archived",registry={"ari":["Ari"],"box":["box"]},
                candidate_lexicon={},
                typed_registry={"openables":["box"],"documents":[]},
                api_key="synthetic",extraction_model=SWEEP,
                semantic_model=SEMANTIC,typed_model=FACET,provider_call=stages,
            )
            writer=create_writer(
                api_key="synthetic",model=WRITER,archive_dir=root/"receipts",
                story_context={"canonical":"never spawn train"},
                provider_call=stages,
                reconciler=lambda **kw:self.fail("archive already present"),
            )
            def interrupted(*,source,defects):
                writer(source=source,defects=defects)
                raise RuntimeError("crash before controller receipt")
            policy={"prose":SOURCE_1,"world":entry(),
                    "prepare_evidence":preparer,
                    "evidence_policy_id":"v031-archive-provenance",
                    "check_scene":create_checker(
                        evidence_root=root/"evidence",
                        full_qualification=True),
                    "output_dir":root/"controller","max_rewrites":2}
            first=execute(**policy,rewrite_scene=interrupted)
            self.assertEqual(first["reason_code"],
                             "V020_REWRITE_PROVIDER_FAILED_SAFE")
            second=execute(
                **policy,rewrite_scene=lambda **kw:self.fail(
                    "no fresh writer provider calls"),
                recover_rewrite_scene=writer.recover_existing,
            )
        self.assertEqual(second["status"],
                         "SCENE_CANDIDATE_READY_NONCANONICAL")
        self.assertEqual(second["rewrite_count"],1)
        self.assertEqual(second["world_db_writes"],0)


if __name__ == "__main__":
    unittest.main()
