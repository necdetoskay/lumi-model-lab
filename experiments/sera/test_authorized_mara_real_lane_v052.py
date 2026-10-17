"""No-spend v0.52 signed real Mara runner integration smoke."""
import base64
import tempfile
import time
import unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from experiments.sera.authorized_mara_real_lane_v052 import (
    preflight,run_signed_mara)
from experiments.sera.provider_grant_journal_v052 import JournalBlocked, _canonical

MODELS=dict(extraction="google/test-extract",semantic="anthropic/test-semantic",
            typed="google/test-typed",writer="anthropic/test-writer")


class MaraRealLaneNoSpendTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.signer=Ed25519PrivateKey.generate()
        self.key=self.signer.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        self.sent=[]

    def approval(self,*,expiry=None):
        contract=preflight(models=MODELS)
        manifest={
            "scope":"SERA_V052_MARA_NONCANONICAL_PAID",
            "source_sha256":contract["source_sha256"],
            "world_sha256":contract["world_sha256"],
            "scene_key":contract["scene_key"],
            "policy_sha256":contract["policy_sha256"],
            "approved_models":MODELS,
            "grants":{},
            "approval_id":"isolated-zero-grant-offline",
            "expires_at":expiry or int(time.time())+1200,
        }
        return {"manifest":manifest,"signature":base64.b64encode(
            self.signer.sign(_canonical(manifest).encode("utf-8"))).decode("ascii")}

    def launch(self,**overrides):
        args=dict(models=MODELS,approval=self.approval(),
                  trusted_public_key=self.key,grants={},
                  api_key="NEVER_REAL_API_KEY",
                  journal_path=self.root/"journal.sqlite3",
                  output_root=self.root/"qualified",
                  opener=self.fail_if_post)
        args.update(overrides)
        return run_signed_mara(**args)

    def fail_if_post(self,*args,**kwargs):
        self.sent.append((args,kwargs))
        raise AssertionError("No test may call an HTTP provider")

    def test_preflight_frozen_28_source(self):
        report=preflight(models=MODELS)
        self.assertEqual(report["source_sentence_count"],28)
        self.assertEqual(len(report["source_sha256"]),64)
        self.assertFalse(report["canonical_commit_authorized"])
        self.assertFalse((self.root/"journal.sqlite3").exists())

    def test_unsigned_paid_run_stops_before_creating_journal(self):
        with self.assertRaises(JournalBlocked):
            self.launch(approval=None)
        self.assertFalse((self.root/"journal.sqlite3").exists())
        self.assertFalse(self.sent)

    def test_forged_public_key_refused_before_call(self):
        other=Ed25519PrivateKey.generate().public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        with self.assertRaisesRegex(JournalBlocked,"SIGNATURE_INVALID"):
            self.launch(trusted_public_key=other)
        self.assertEqual(self.sent,[])

    def test_expired_authorization_refused(self):
        with self.assertRaisesRegex(JournalBlocked,"APPROVAL_EXPIRED"):
            self.launch(approval=self.approval(expiry=1))
        self.assertEqual(self.sent,[])

    def test_signed_zero_grants_fail_closed_without_network(self):
        result=self.launch()
        self.assertEqual(result["source_sentence_count"],28)
        self.assertEqual(result["status"],"FAILED_SAFE_FINAL")
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(result["production_db_writes"],0)
        self.assertEqual(result["manual_story_or_json_edits"],0)
        self.assertEqual(self.sent,[])

    def test_restart_reuses_safe_final_without_network(self):
        before=self.launch()
        after=self.launch()
        self.assertEqual(before,after)
        self.assertFalse(self.sent)

    def test_synthetic_models_not_allowed(self):
        with self.assertRaisesRegex(JournalBlocked,"APPROVED_MODELS_INVALID"):
            preflight(models={**MODELS,"writer":"synthetic/v052-writer"})
        self.assertFalse(self.sent)


if __name__ == "__main__":
    unittest.main()
