"""Offline adversarial proof for bounded SERA v0.52 dynamic paid delegation.

Every transport here is a Python fake; absolutely NO network or live spend.
"""
import base64
import json
import tempfile
import time
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from experiments.sera.coverage import prose_hash
from experiments.sera.delegated_scene_budget_v052 import (
    DelegatedSceneBudget, SCOPE)
from experiments.sera.provider_grant_journal_v052 import JournalBlocked, _canonical

MODELS = dict(extraction="approved/extract", semantic="approved/semantic",
              typed="approved/typed", writer="approved/writer")
ROOT = "Ari watched the platform."
NEW = "Ari watched the platform clock."
NEXT = "Ari saw the station clock."
ROOT_SHA = prose_hash(ROOT)
WORLD_SHA = "b"*64
POLICY_SHA = "c"*64
SCENE_KEY = "mara-28-offline"


class DelegatedSceneBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db=Path(self.temp.name)/"ledger.sqlite3"
        self.signer=Ed25519PrivateKey.generate()
        self.trust=self.signer.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        self.calls=[]
        self.manifest=dict(scope=SCOPE,approval_id="sera-v052-unique-test",
                           source_sha256=ROOT_SHA,world_sha256=WORLD_SHA,
                           scene_key=SCENE_KEY,policy_sha256=POLICY_SHA,
                           approved_models=MODELS,max_calls=4,max_rewrites=2,
                           observed_spend_guard_usd="0.03",
                           expires_at=int(time.time())+3600)
        self.request={"messages":[{"role":"user","content":"blind source only"}]}
        self.writer_request={"messages":[{"role":"user","content":ROOT}]}

    def approval(self):
        return dict(manifest=dict(self.manifest),
                    signature=base64.b64encode(self.signer.sign(
                        _canonical(self.manifest).encode("utf-8"))).decode("ascii"))

    def budget(self, **kwargs):
        args=dict(db_path=self.db,approval=self.approval(),
                  trusted_public_key=self.trust,source_sha256=ROOT_SHA,
                  world_sha256=WORLD_SHA,scene_key=SCENE_KEY,
                  policy_sha256=POLICY_SHA,models=MODELS)
        args.update(kwargs)
        return DelegatedSceneBudget(**args)

    def transport(self, **kwargs):
        self.calls.append(kwargs)
        model=kwargs["model"]
        if model==MODELS["writer"]:
            content=json.dumps({"source_prose_sha256":ROOT_SHA,
                                "revised_scene_prose":NEW})
        else:
            content="{}"
        return {"raw":{"id":"generation-"+str(len(self.calls)),"model":model,
                       "choices":[{"finish_reason":"stop",
                                   "message":{"content":content}}],
                       "usage":{"cost":0.001,"prompt_tokens":12,
                                "completion_tokens":15}},"error":None}

    def call(self, budget, role="extraction", source_sha=ROOT_SHA, request=None,
             transport=None):
        return budget.call(source_sha=source_sha,role=role,
                           model=MODELS[role],request=request or self.request,
                           transport=transport or self.transport)

    def test_pinned_signature_required(self):
        other=Ed25519PrivateKey.generate().public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        with self.assertRaisesRegex(JournalBlocked,"SIGNATURE_INVALID"):
            self.budget(trusted_public_key=other)
        self.assertFalse(self.calls)

    def test_reuse_of_approval_id_with_new_manifest_rejected(self):
        self.budget()
        previous=self.approval()
        self.manifest["max_calls"]=5
        with self.assertRaisesRegex(JournalBlocked,"APPROVAL_ID_REUSED"):
            self.budget()
        self.assertFalse(self.calls)

    def test_one_request_one_charge_replay_and_crash_recovery(self):
        b=self.budget()
        a=self.call(b)
        b2=self.budget()
        returned=self.call(b2)
        self.assertEqual(a,returned)
        self.assertEqual(a,b2.recover_completed(source_sha=ROOT_SHA,
              role="extraction",model=MODELS["extraction"],
              request=self.request))
        self.assertEqual(len(self.calls),1)

    def test_unverified_new_scene_not_billable(self):
        with self.assertRaisesRegex(JournalBlocked,"UNPROVEN_SOURCE_REVISION"):
            self.call(self.budget(),source_sha=prose_hash(NEW))
        self.assertEqual(self.calls,[])

    def test_writer_receipt_proves_next_source_without_manual_edit(self):
        b=self.budget()
        writer=self.call(b,role="writer",request=self.writer_request)
        revision=b.accept_writer_revision(
            parent_sha=ROOT_SHA,revised_prose=NEW,
            writer_request=self.writer_request,
            generation_id=writer["raw"]["id"])
        self.assertEqual(revision,prose_hash(NEW))
        self.call(b,source_sha=revision)
        self.assertEqual(len(self.calls),2)
        b2=self.budget()
        self.assertEqual(b2.accept_writer_revision(
            parent_sha=ROOT_SHA,revised_prose=NEW,
            writer_request=self.writer_request,
            generation_id=writer["raw"]["id"]),revision)
        self.assertEqual(len(self.calls),2)

    def test_forged_revision_claim_denied(self):
        b=self.budget()
        writer=self.call(b,role="writer",request=self.writer_request)
        with self.assertRaisesRegex(JournalBlocked,"WRITER_LINEAGE_INVALID"):
            b.accept_writer_revision(parent_sha=ROOT_SHA,revised_prose=NEXT,
                writer_request=self.writer_request,
                generation_id=writer["raw"]["id"])
        with self.assertRaisesRegex(JournalBlocked,"WRITER_LINEAGE_INVALID"):
            b.accept_writer_revision(parent_sha=ROOT_SHA,revised_prose=NEW,
                writer_request=self.writer_request,generation_id="fake")
        self.assertEqual(len(self.calls),1)

    def test_forked_writer_generation_denied(self):
        b=self.budget()
        response=self.call(b,role="writer",request=self.writer_request)
        b.accept_writer_revision(parent_sha=ROOT_SHA,revised_prose=NEW,
            writer_request=self.writer_request,generation_id=response["raw"]["id"])
        # A second writer request for same parent can get a receipt but
        # it cannot replace the established child revision.
        new_request={"messages":[{"role":"user","content":"other defects"}]}
        other=self.call(b,role="writer",request=new_request)
        with self.assertRaisesRegex(JournalBlocked,"REVISION_FORK_BLOCKED"):
            b.accept_writer_revision(parent_sha=ROOT_SHA,revised_prose=NEW,
                writer_request=new_request,generation_id=other["raw"]["id"])

    def test_call_quota_shared_across_restarted_worker(self):
        self.manifest["max_calls"]=1
        b=self.budget()
        self.call(b)
        with self.assertRaisesRegex(JournalBlocked,"CALL_BUDGET_EXHAUSTED"):
            self.call(self.budget(),role="typed")
        self.assertEqual(len(self.calls),1)

    def test_observed_cost_budget_stops_new_requests(self):
        self.manifest["observed_spend_guard_usd"]="0.0001"
        b=self.budget()
        self.call(b)
        with self.assertRaisesRegex(JournalBlocked,"OBSERVED_BUDGET_EXHAUSTED"):
            self.call(b,role="typed")
        self.assertEqual(len(self.calls),1)

    def test_unknown_inflight_blocks_new_requests_and_repost(self):
        b=self.budget()
        def disconnected(**kwargs):
            self.calls.append(kwargs)
            raise TimeoutError("provider may have charged")
        with self.assertRaises(TimeoutError):
            self.call(b,transport=disconnected)
        with self.assertRaisesRegex(JournalBlocked,"UNSETTLED_CALL"):
            self.call(b,role="typed")
        with self.assertRaisesRegex(JournalBlocked,"UNKNOWN_INFLIGHT"):
            self.call(self.budget())
        self.assertEqual(len(self.calls),1)

    def test_expired_policy_denies_fresh_call_not_old_receipt(self):
        b=self.budget()
        self.call(b)
        self.manifest["expires_at"]=1
        # New approval must fail verification; the prior receipts remain on disk.
        with self.assertRaisesRegex(JournalBlocked,"EXPIRED"):
            self.budget()
        self.assertEqual(len(self.calls),1)

    def test_nested_output_cap_fails_before_grant_reservation(self):
        b=self.budget()
        with self.assertRaises(Exception):
            self.call(b,request={"config":{"max_completion_tokens":200}})
        self.assertFalse(self.calls)
        with self.assertRaisesRegex(JournalBlocked,"RECOVERY_ONLY_NO_NEW_GRANT"):
            b.recover_completed(source_sha=ROOT_SHA,role="typed",
                                model=MODELS["typed"],request=self.request)


if __name__=="__main__":
    unittest.main()
