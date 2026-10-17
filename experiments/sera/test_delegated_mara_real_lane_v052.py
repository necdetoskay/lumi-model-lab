"""No-network integration controls for v0.52 bounded Mara delegated lane."""
import base64
import tempfile
import time
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from experiments.sera.authorized_mara_real_lane_v052 import preflight
from experiments.sera.delegated_mara_real_lane_v052 import run_delegated_mara
from experiments.sera.delegated_scene_budget_v052 import SCOPE
from experiments.sera.provider_grant_journal_v052 import JournalBlocked, _canonical

MODELS=dict(extraction="real/test-extract", semantic="real/test-semantic",
            typed="real/test-typed", writer="real/test-writer")


class DelegatedMaraNoSpend(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.signer=Ed25519PrivateKey.generate()
        self.trust=self.signer.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        contract=preflight(models=MODELS)
        self.manifest=dict(
            scope=SCOPE, approval_id="specific-v052-mara-offline",
            source_sha256=contract["source_sha256"],
            world_sha256=contract["world_sha256"],
            scene_key=contract["scene_key"],
            policy_sha256=contract["policy_sha256"],
            approved_models=MODELS, max_calls=5,max_rewrites=2,
            observed_spend_guard_usd="0.05",
            expires_at=int(time.time())+600)
        self.posts=[]

    def approval(self):
        return {"manifest":dict(self.manifest),"signature":base64.b64encode(
            self.signer.sign(_canonical(self.manifest).encode("utf-8"))
            ).decode("ascii")}

    def opener(self, *args, **kwargs):
        self.posts.append((args,kwargs))
        raise AssertionError("Offline tests cannot POST to providers")

    def run(self, **kwargs):
        args=dict(models=MODELS,approval=self.approval(),
                  trusted_public_key=self.trust,
                  api_key="OFFLINE_PLACEHOLDER_NOT_A_SECRET",
                  journal_path=self.root/"delegate.db",
                  output_root=self.root/"scene",
                  max_rewrites=2,opener=self.opener)
        args.update(kwargs)
        return run_delegated_mara(**args)

    def test_missing_signature_no_journal_or_post(self):
        with self.assertRaises(JournalBlocked):
            self.run(approval=None)
        self.assertFalse((self.root/"delegate.db").exists())
        self.assertEqual(self.posts,[])

    def test_forged_signer_no_post(self):
        other=Ed25519PrivateKey.generate().public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        with self.assertRaisesRegex(JournalBlocked,"SIGNATURE_INVALID"):
            self.run(trusted_public_key=other)
        self.assertEqual(self.posts,[])

    def test_wrong_model_binding_no_post(self):
        manifest=dict(self.manifest)
        manifest["approved_models"]=dict(MODELS,writer="attacker/writer")
        signed={"manifest":manifest,"signature":base64.b64encode(
            self.signer.sign(_canonical(manifest).encode("utf-8"))
            ).decode("ascii")}
        with self.assertRaisesRegex(JournalBlocked,"BINDING_DRIFT"):
            self.run(approval=signed)
        self.assertEqual(self.posts,[])

    def test_policy_rewrite_limit_must_be_signed(self):
        with self.assertRaisesRegex(JournalBlocked,"REWRITE_POLICY_DRIFT"):
            self.run(max_rewrites=1)
        self.assertEqual(self.posts,[])

    def test_zero_granted_new_calls_safe_final_28_sentences(self):
        self.manifest["max_calls"]=1
        # This test deliberately blocks all HTTP calls by source-safe
        # transport. Unknown POST must never become false PASS.
        result=self.run()
        self.assertEqual(result["source_sentence_count"],28)
        self.assertEqual(result["status"],"FAILED_SAFE_FINAL")
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(result["production_db_writes"],0)
        self.assertFalse(result["semantic_quality_approved"])
        self.assertEqual(len(self.posts),1)

    def test_restart_never_rebills_unknown_call(self):
        self.manifest["max_calls"]=1
        a=self.run()
        b=self.run()
        self.assertEqual(a,b)
        self.assertEqual(len(self.posts),1)

    def test_expired_manifest_denied_before_post(self):
        self.manifest["expires_at"]=1
        with self.assertRaisesRegex(JournalBlocked,"EXPIRED"):
            self.run()
        self.assertEqual(self.posts,[])


if __name__=="__main__":
    unittest.main()
