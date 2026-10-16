"""v0.30 safe restarts: previously charged stages never emit duplicate POST."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.artifact_scene_checker_v021 import create_checker
from experiments.sera.coverage import CoverageError
from experiments.sera.fresh_scene_evidence_worker_v022 import create_preparer
from experiments.sera.tests.test_fresh_scene_evidence_worker_v022 import (
    SOURCE_2, EXTRACT, SEMANTIC, TYPED, entry, fake_model,
)
from experiments.sera.unattended_scene_rewrite_v020 import execute


def preparer(root, provider, *, reconciler=None):
    return create_preparer(
        evidence_root=root/"evidence", work_root=root/"jobs",
        scene_key="v030-restart", registry={"ari":["Ari"],"box":["box"]},
        candidate_lexicon={},
        typed_registry={"openables":["box"],"documents":[]},
        api_key="synthetic", extraction_model=EXTRACT,
        semantic_model=SEMANTIC, typed_model=TYPED,
        provider_call=provider, reconciler=reconciler,
    )


def stage(root, provider, *, reconciler=None):
    return execute(
        prose=SOURCE_2, world=entry(),
        prepare_evidence=preparer(root,provider,reconciler=reconciler),
        evidence_policy_id="immutable-replay-v030",
        check_scene=create_checker(
            evidence_root=root/"evidence",full_qualification=True),
        rewrite_scene=lambda **kw: (_ for _ in ()).throw(
            AssertionError("No rewrite needed for qualified scene")),
        output_dir=root/"controller",max_rewrites=0,
        resume_reconciled_evidence=(reconciler is not None),
    )


class AutomaticReconciliationResumeV030Tests(unittest.TestCase):
    def test_unknown_provider_charge_stays_terminal_when_no_id(self):
        paid=[]
        def lost(**kw):
            paid.append(kw)
            return {"error":"TRANSPORT_UNAVAILABLE","raw":None}
        with TemporaryDirectory() as d:
            root=Path(d)
            before=stage(root,lost)
            still=stage(root,lambda **kw:self.fail("second POST"))
        self.assertEqual(before["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(before,still)
        self.assertEqual(len(paid),1)
        self.assertFalse(before["canonical_commit_authorized"])

    def test_authenticated_reconciled_receipt_unblocks_complete_scene(self):
        charged=[]
        def lost(**kw):
            charged.append(kw)
            return {"error":"TRANSPORT_UNAVAILABLE","raw":None}
        recovered=[]
        all_calls=[]
        local_model=fake_model(all_calls)
        with TemporaryDirectory() as d:
            root=Path(d)
            first=stage(root,lost)
            self.assertEqual(first["status"],"FAILED_SAFE_FINAL")
            def recon(*,model,request,request_sha256):
                recovered.append((model,request_sha256))
                # Simulates a fully authenticated, read-only generation
                # lookup. v0.30 resolver separately tests model, source
                # messages, signed ID, cost and GET-only operation.
                result=local_model(
                    key="synthetic",model=model,
                    prepared={"request":request},
                )
                return result
            def other_stages(**kw):
                # A pending signature MUST NOT be posted a second time.
                if (kw["model"] == charged[0]["model"] and
                    kw["prepared"]["request"] ==
                         charged[0]["prepared"]["request"]):
                    self.fail("Original billable POST repeated")
                return local_model(**kw)
            second=stage(root,other_stages,reconciler=recon)
            third=stage(root,lambda **kw:self.fail("finished replay billed"),
                        reconciler=recon)
            prior=root/"controller"/"pre_reconciliation_safe_stop.json"
            self.assertTrue(prior.is_file())
        self.assertEqual(second["status"],"SCENE_CANDIDATE_READY_NONCANONICAL")
        self.assertEqual(second,third)
        self.assertEqual(len(charged),1)
        self.assertEqual(len(recovered),1)
        self.assertGreaterEqual(len(all_calls),2)
        self.assertFalse(second["canonical_commit_authorized"])
        self.assertEqual(second["world_db_writes"],0)

    def test_reconciliation_disabled_on_mismatched_or_incomplete_evidence(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            outcome=stage(root,lambda **kw:{
                "error":"TRANSPORT_UNAVAILABLE","raw":None})
            calls=[]
            recovered=stage(
                root,
                lambda **kw:self.fail("should not dispatch another charge"),
                reconciler=lambda **kw: (
                    calls.append(kw) or (_ for _ in ()).throw(
                        CoverageError("V030_GENERATION_ID_UNAVAILABLE_NO_RESEND")
                    )
                ),
            )
        self.assertEqual(outcome,recovered)
        self.assertEqual(len(calls),1)
        self.assertFalse(recovered["canonical_commit_authorized"])


if __name__=="__main__":
    unittest.main()
