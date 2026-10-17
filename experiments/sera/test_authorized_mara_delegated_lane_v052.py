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
        self.signed_test_expires_at=int(time.time())+2000
        self.ledger_path=self.root/"ledger.sqlite3"
        runtime=provision_local_journal(path=self.ledger_path)
        self.trust_config=self.root/"paid-trust.json"
        config=dict(schema=RUNTIME_SCHEMA,
                    trusted_raw_key_sha256=sha256(self.public).hexdigest(),
                    journal_path=str(self.ledger_path),
                    journal_id=runtime["journal_id"],
                    host_id_sha256=runtime["host_id_sha256"],
                    revoked_approval_ids=[])
        self.trust_config.write_text(json.dumps(config),encoding="utf-8")
        self.trust_config.chmod(0o600)

    def approval(self,**changes):
        p=self.contract
        manifest={
            "schema":SCHEMA,"scope":SCOPE,"approval_id":"mara-approval-offline",
            "expires_at":self.signed_test_expires_at,
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

    def test_real_wire_shape_28_sentence_mara_incomplete_evidence_is_failed_safe(self):
        """Signed, fully journaled mock OpenRouter POST on the real Mara source.

        The injected model deliberately omits its source rows, and v0.22 must
        refuse to treat the incomplete 28-sentence coverage as a qualified
        scene. Restart must use journal receipts; no second mock POST.
        """
        from experiments.sera.real_blind_benchmark_v040 import EXPECTED_SHA
        from experiments.sera.sentence_ledger_v06 import sentences
        from experiments.sera.real_blind_benchmark_v040 import prepare
        class MockHTTP:
            def __init__(self,body):
                self.body=body
            def __enter__(self):
                return self
            def __exit__(self,*args):
                return False
            def read(self):
                return self.body
        observed=[]
        def offline_open(req,timeout):
            payload=json.loads(req.data.decode("utf-8"))
            observed.append(payload)
            assert req.full_url=="https://openrouter.ai/api/v1/chat/completions"
            assert req.get_method()=="POST"
            assert payload["model"]==MODELS["extraction"]
            assert payload["stream"] is False
            assert not any(k in payload for k in (
                "max_tokens","max_completion_tokens","max_output_tokens",
                "max_generation_tokens","max_new_tokens"))
            mock=dict(
                id="offline-only-mara-g-"+str(len(observed)),
                model=MODELS["extraction"],
                choices=[{"finish_reason":"stop",
                          "message":{"content":json.dumps({"rows":[]})}}],
                usage={"cost":"0.001","prompt_tokens":400,
                       "completion_tokens":17})
            return MockHTTP(json.dumps(mock).encode("utf-8"))
        # Unlike safety-only tests with extraction quota=0, allow actual
        # stage execution through the EXACT real OpenRouter wire adapter.
        signed=self.approval(
            max_posts=2,max_posts_per_role=dict(
                extraction=2,semantic=0,typed=0,writer=0))
        first=self.launch(approval=signed,opener=offline_open)
        self.assertEqual(len(sentences(prepare()["prose"])),28)
        self.assertEqual(first["source_sha256"],EXPECTED_SHA)
        self.assertEqual(first["source_sentence_count"],28)
        self.assertEqual(first["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(first["automatic_rewrites"],0)
        self.assertFalse(first["full_scene_qualification_gate_invoked"])
        self.assertGreaterEqual(first["allocated_provider_requests"],1)
        self.assertFalse(first["canonical_commit_authorized"])
        self.assertEqual(first["production_db_writes"],0)
        self.assertEqual(len(observed),2)
        self.assertEqual(first["allocated_provider_requests"],2)
        original_user=json.loads(observed[0]["messages"][1]["content"])
        repaired_user=json.loads(observed[1]["messages"][1]["content"])
        self.assertEqual(original_user,repaired_user)
        self.assertEqual(original_user["source_prose_sha256"],EXPECTED_SHA)
        self.assertEqual(len(original_user["target_sentences"]),4)
        self.assertNotEqual(observed[0]["messages"][0]["content"],
                            observed[1]["messages"][0]["content"])
        self.assertIn("SOURCE-ONLY AUTOMATIC RE-EXTRACTION",
                      observed[1]["messages"][0]["content"])
        self.assertNotIn('"rows":[]',
                         json.dumps(observed[1],ensure_ascii=False))
        self.assertEqual(self.billable_rows(),len(observed))
        for model_request in observed:
            self.assertEqual(model_request["model"],MODELS["extraction"])
        with sqlite3.connect(self.ledger_path) as db:
            rows=db.execute("SELECT status,envelope_json FROM calls").fetchall()
            self.assertEqual(len(rows),len(observed))
            self.assertTrue(all(row[0]=="RECEIPTED" for row in rows))
            self.assertTrue(all(
                "wire_payload_b64" in json.loads(row[1]) for row in rows))
        second=self.launch(approval=signed,opener=lambda *_a,**_kw:
                           self.fail("restart must never re-POST"))
        self.assertEqual(first,second)
        self.assertEqual(len(observed),self.billable_rows())

    def test_all_28_rows_but_no_physical_events_cannot_fake_scene_success(self):
        """Seven signed real-wire batches, 28 source rows, unsafe omissions HOLD."""
        from experiments.sera.real_blind_benchmark_v040 import EXPECTED_SHA
        from experiments.sera.sentence_ledger_v06 import sentences
        from experiments.sera.real_blind_benchmark_v040 import prepare
        class MockHTTP:
            def __init__(self, body):
                self.body=body
            def __enter__(self):
                return self
            def __exit__(self,*_args):
                return False
            def read(self):
                return self.body
        seen={}
        requests=[]
        def fake_open(req,timeout):
            body=json.loads(req.data.decode("utf-8"))
            self.assertEqual(body["model"],MODELS["extraction"])
            requests.append(body)
            packet=json.loads(body["messages"][1]["content"])
            self.assertEqual(packet["source_prose_sha256"],EXPECTED_SHA)
            targets=packet["target_sentences"]
            self.assertEqual(len(targets),4)
            for sentence in targets:
                if sentence["id"] in seen:
                    self.assertEqual(seen[sentence["id"]],sentence["quote"])
                seen[sentence["id"]]=sentence["quote"]
            # All 28 IDs are accounted for, but the model falsely denies
            # every physical action, object and cause.
            rows=[{"sentence_id":s["id"],
                   "disposition":"NO_TRACKED_CHANGE",
                   "reason":"Deliberately incomplete adversarial model",
                   "mentions":[],"events":[]} for s in targets]
            raw={"id":"mara-fake-"+str(len(requests)), "model":MODELS["extraction"],
                 "choices":[{"finish_reason":"stop",
                             "message":{"content":json.dumps({"rows":rows})}}],
                 "usage":{"prompt_tokens":400,"completion_tokens":200,
                          "cost":"0.001"}}
            return MockHTTP(json.dumps(raw).encode("utf-8"))
        approval=self.approval(
            max_posts=14,
            max_posts_per_role={"extraction":14,"semantic":0,"typed":0,"writer":0},
            max_observed_usd="0.05")
        outcome=self.launch(approval=approval,opener=fake_open)
        self.assertEqual(len(seen),28)
        expected={s["id"]:s["quote"] for s in sentences(prepare()["prose"])}
        self.assertEqual(seen,expected)
        self.assertEqual(outcome["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(outcome["automatic_rewrites"],0)
        self.assertFalse(outcome["canonical_commit_authorized"])
        self.assertEqual(outcome["production_db_writes"],0)
        self.assertGreater(outcome["allocated_provider_requests"],7)
        self.assertLessEqual(outcome["allocated_provider_requests"],14)
        self.assertEqual(self.billable_rows(),len(requests))
        self.assertTrue(any(
            "SOURCE-ONLY AUTOMATIC RE-EXTRACTION" in
            r["messages"][0]["content"] for r in requests[7:]))
        for request in requests:
            packet=json.loads(request["messages"][1]["content"])
            self.assertEqual(packet["source_prose_sha256"],EXPECTED_SHA)
        self.assertFalse(outcome["full_scene_qualification_gate_invoked"])
        with sqlite3.connect(self.ledger_path) as db:
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM calls WHERE status='RECEIPTED'"
            ).fetchone()[0],len(requests))
        replay=self.launch(
            approval=approval,
            opener=lambda *_args,**_kw:self.fail("already receipted; NO re-POST"))
        self.assertEqual(replay,outcome)
        self.assertEqual(len(seen),28)

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
        with self.assertRaisesRegex(JournalBlocked,"PIN_MISMATCH"):
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

    def test_revoked_signed_approval_never_posts(self):
        self.trust_config.write_text(json.dumps({
            **json.loads(self.trust_config.read_text(encoding="utf-8")),
            "revoked_approval_ids":["mara-approval-offline"]
        }),encoding="utf-8")
        with self.assertRaisesRegex(JournalBlocked,"APPROVAL_REVOKED"):
            self.launch()
        self.assertEqual(self.billable_rows(),0)
        self.assertEqual(self.sent,[])

    def test_invalid_revocation_list_denied(self):
        cfg=json.loads(self.trust_config.read_text(encoding="utf-8"))
        cfg["revoked_approval_ids"]=["id","id"]
        self.trust_config.write_text(json.dumps(cfg),encoding="utf-8")
        with self.assertRaisesRegex(JournalBlocked,"REVOCATION_CONFIG_INVALID"):
            self.launch()
        self.assertEqual(self.billable_rows(),0)

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
