"""No-network delegated Mara 28-sentence integration + revision lineage."""
import base64
import json
import sqlite3
from hashlib import sha256
import tempfile
import time
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from experiments.sera.authorized_mara_delegated_lane_v052 import run_delegated_mara
from experiments.sera.authorized_mara_real_lane_v052 import preflight
from experiments.sera.coverage import prose_hash
from experiments.sera.delegated_paid_budget_v052 import (
    DelegatedBudget, SCOPE, SCHEMA)
from experiments.sera.delegated_provider_bridge_v052 import create_delegated_provider
from experiments.sera.provider_grant_journal_v052 import (
    ProviderJournal, JournalBlocked, _canonical)
from experiments.sera.paid_runtime_boundary_v052 import (
    provision_local_journal, SCHEMA as RUNTIME_SCHEMA)

MODELS={"extraction":"test/real-extract","semantic":"test/real-semantic",
        "typed":"test/real-typed","writer":"test/real-writer"}


class DelegatedMaraNoSpend(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.signer=Ed25519PrivateKey.generate()
        self.public=self.signer.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        self.sent=[]
        self.contract=preflight(models=MODELS)
        self.ledger_path=self.root/"ledger.sqlite3"
        runtime=provision_local_journal(path=self.ledger_path)
        self.trust_config=self.root/"paid-trust.json"
        config=dict(schema=RUNTIME_SCHEMA,
                    trusted_raw_key_sha256=sha256(self.public).hexdigest(),
                    journal_path=str(self.ledger_path),
                    journal_id=runtime["journal_id"],
                    host_id_sha256=runtime["host_id_sha256"])
        self.trust_config.write_text(json.dumps(config),encoding="utf-8")
        self.trust_config.chmod(0o600)

    def approval(self,**changes):
        p=self.contract
        manifest={
            "schema":SCHEMA,"scope":SCOPE,"approval_id":"mara-approval-offline",
            "expires_at":int(time.time())+2000,
            "source_sha256":p["source_sha256"],
            "world_sha256":p["world_sha256"],
            "scene_key":p["scene_key"],
            "policy_sha256":p["policy_sha256"],
            "approved_models":MODELS,"max_rewrites":2,
            "max_posts":3,
            "max_posts_per_role":{"extraction":0,"semantic":1,"typed":1,"writer":1},
            "max_observed_usd":"0.010",
        }
        manifest.update(changes)
        return {"manifest":manifest,"signature":base64.b64encode(
            self.signer.sign(_canonical(manifest).encode("utf-8"))).decode("ascii")}

    def no_http(self,*args,**kwargs):
        self.sent.append((args,kwargs))
        raise AssertionError("network forbidden")

    def launch(self,**kwargs):
        args=dict(models=MODELS,approval=self.approval(),
                  trusted_public_key=self.public,
                  trusted_raw_key_sha256=sha256(self.public).hexdigest(),
                  api_key="FAKE_OFFLINE_ONLY",
                  journal_path=self.ledger_path,
                  runtime_trust_config_path=self.trust_config,
                  output_root=self.root/"mara-run",
                  opener=self.no_http)
        args.update(kwargs)
        return run_delegated_mara(**args)

    def billable_rows(self):
        with sqlite3.connect(self.ledger_path) as db:
            return db.execute("SELECT COUNT(*) FROM calls").fetchone()[0]

    def test_bounded_zero_extraction_cap_is_safe_final_with_no_post(self):
        result=self.launch()
        self.assertEqual(result["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(result["allocated_provider_requests"],0)
        self.assertEqual(result["source_sentence_count"],28)
        self.assertEqual(result["production_db_writes"],0)
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(self.sent,[])

    def test_restart_does_not_spend_after_failed_safe_final(self):
        a=self.launch()
        b=self.launch()
        self.assertEqual(a,b)
        self.assertEqual(self.sent,[])

    def test_unsigned_approval_rejected_before_journal_created(self):
        with self.assertRaises(JournalBlocked):
            self.launch(approval={})
        self.assertEqual(self.billable_rows(),0)
        self.assertFalse(self.sent)

    def test_approval_cost_tamper_fails_signature(self):
        a=self.approval()
        a["manifest"]["max_observed_usd"]="999999"
        with self.assertRaisesRegex(JournalBlocked,"SIGNATURE_INVALID"):
            self.launch(approval=a)
        self.assertFalse(self.sent)

    def test_untrusted_signer_key_rejected(self):
        other=Ed25519PrivateKey.generate().public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        with self.assertRaisesRegex(JournalBlocked,"TRUST_OVERRIDE_FORBIDDEN"):
            self.launch(trusted_public_key=other)
        self.assertFalse(self.sent)

    def test_substituted_deployment_pin_rejected_before_journal(self):
        with self.assertRaisesRegex(JournalBlocked,"TRUST_OVERRIDE_FORBIDDEN"):
            self.launch(trusted_raw_key_sha256="f"*64)
        self.assertEqual(self.billable_rows(),0)
        self.assertFalse(self.sent)

    def test_missing_deployment_pin_rejected_before_journal(self):
        with self.assertRaisesRegex(JournalBlocked,"TRUST_OVERRIDE_FORBIDDEN"):
            self.launch(trusted_raw_key_sha256=None)
        self.assertEqual(self.billable_rows(),0)
        self.assertFalse(self.sent)

    def test_untrusted_runtime_config_is_rejected(self):
        self.trust_config.chmod(0o666)
        with self.assertRaisesRegex(JournalBlocked,"TRUST_FILE_INSECURE"):
            self.launch()
        self.assertEqual(self.billable_rows(),0)
        self.assertEqual(self.sent,[])

    def test_duplicate_journal_copy_refused(self):
        import shutil
        copied=self.root/"copy.sqlite3"
        shutil.copy2(self.ledger_path,copied)
        with self.assertRaisesRegex(JournalBlocked,"TRUST_OVERRIDE_FORBIDDEN"):
            self.launch(journal_path=copied)
        self.assertEqual(self.billable_rows(),0)

    def test_live_runtime_cannot_create_fresh_missing_journal(self):
        self.ledger_path.unlink()
        with self.assertRaisesRegex(JournalBlocked,"PAID_JOURNAL_MISSING"):
            self.launch()
        self.assertFalse(self.ledger_path.exists())
        self.assertEqual(self.sent,[])

    def test_generated_revision_rebind_without_writer_receipt_is_forbidden(self):
        approval=self.approval()
        j=ProviderJournal(self.root/"budget.db")
        b=DelegatedBudget(j,approval=approval,trusted_public_key=self.public,
                          source_sha256=self.contract["source_sha256"],
                          world_sha256=self.contract["world_sha256"],
                          scene_key=self.contract["scene_key"],
                          policy_sha256=self.contract["policy_sha256"],
                          approved_models=MODELS,max_rewrites=2)
        cb=create_delegated_provider(budget=b,transport=self.no_http)
        with self.assertRaisesRegex(JournalBlocked,"SOURCE_LINEAGE_NOT_PROVEN"):
            cb.use_source("Manually altered fake Mara revision.")
        self.assertEqual(self.sent,[])

    def test_wrong_world_fingerprint_refused_before_paid_post(self):
        altered=self.approval(world_sha256="d"*64)
        with self.assertRaisesRegex(JournalBlocked,"SCOPE_DRIFT"):
            self.launch(approval=altered)
        self.assertEqual(self.sent,[])


if __name__=="__main__":
    unittest.main()
