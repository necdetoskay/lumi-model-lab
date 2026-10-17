"""No-network receipt audit verification; no model API calls."""
import base64
import tempfile
import time
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from experiments.sera.coverage import prose_hash
from experiments.sera.delegated_paid_budget_v052 import DelegatedBudget, SCOPE, SCHEMA
from experiments.sera.delegated_receipt_audit_v052 import audit_delegated_receipts
from experiments.sera.provider_grant_journal_v052 import ProviderJournal, _canonical

MODELS=dict(extraction="model/extract",semantic="model/semantic",
            typed="model/typed",writer="model/writer")


class ReceiptAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.journal=ProviderJournal(Path(self.temp.name)/"ledger.db")
        self.signer=Ed25519PrivateKey.generate()
        self.public=self.signer.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        self.source=prose_hash("Frozen source, noncanonical.")
        self.context=dict(source_sha256=self.source,world_sha256="b"*64,
                          scene_key="mara-28",policy_sha256="c"*64,
                          approved_models=MODELS,max_rewrites=2)
        self.manifest=dict(schema=SCHEMA,scope=SCOPE,approval_id="audit-test",
                           expires_at=int(time.time())+3600,**self.context,
                           max_posts=3,max_posts_per_role=dict(
                               extraction=2,semantic=1,typed=0,writer=0),
                           max_observed_usd="0.1")
        self.approval=dict(manifest=self.manifest,signature=base64.b64encode(
            self.signer.sign(_canonical(self.manifest).encode("utf-8"))
            ).decode("ascii"))
        self.budget=DelegatedBudget(
            self.journal,approval=self.approval,
            trusted_public_key=self.public,**self.context)
        self.count=0

    def payload(self,idx):
        return {"messages":[{"role":"user","content":"blind-"+str(idx)}]}

    def answer(self,*,model,identifier=None,tokens=True,cost=True,
               complete=True, duration=True):
        self.count+=1
        usage={"completion_tokens_details":{"reasoning_tokens":2}}
        if tokens:
            usage.update(prompt_tokens=21,completion_tokens=15)
        if cost:
            usage["cost"]="0.002"
        return {"raw":{
            "id":identifier or "gen-"+str(self.count),
            "model":model,
            "usage":usage,
            "choices":[{"finish_reason":"stop" if complete else "length",
                        "message":{"content":"{}"}}]},
            "error":None,
            **({"duration_ms":25.2} if duration else {})}

    def invoke(self,idx=1,role="extraction",**changes):
        model=MODELS[role]
        return self.budget.invoke(
            role=role,revision_sha=self.source,model=model,
            payload=self.payload(idx),
            transport=lambda **kwargs:self.answer(model=model,**changes))

    def audit(self):
        return audit_delegated_receipts(
            journal=self.journal,approval_id="audit-test")

    def test_valid_two_distinct_receipts_and_cost_total(self):
        self.invoke()
        self.invoke(idx=2,role="semantic")
        report=self.audit()
        self.assertEqual(report["status"],"COMPLETE_NONCANONICAL")
        self.assertEqual(report["total_observed_usd"],"0.004")
        self.assertEqual(report["provider_attempts_qualified"],2)
        self.assertEqual({x["input_tokens"] for x in report["receipts"]},{21})
        self.assertEqual({x["reasoning_tokens"] for x in report["receipts"]},{2})
        self.assertFalse(report["canonical_commit_authorized"])

    def test_duplicate_generation_ids_rejected(self):
        self.invoke(identifier="same-id")
        self.invoke(idx=2,role="semantic",identifier="same-id")
        self.assertEqual(self.audit()["status"],"INCOMPLETE_EVIDENCE_HOLD")

    def test_missing_token_usage_rejected(self):
        self.invoke(tokens=False)
        self.assertFalse(self.audit()["all_provider_receipts_qualified"])

    def test_missing_latency_rejected(self):
        self.invoke(duration=False)
        self.assertEqual(self.audit()["status"],"INCOMPLETE_EVIDENCE_HOLD")

    def test_model_incomplete_does_not_become_qualified(self):
        self.invoke(complete=False)
        self.assertEqual(self.audit()["status"],"INCOMPLETE_EVIDENCE_HOLD")

    def test_unknown_inflight_no_false_audit_pass(self):
        def outage(**kwargs):
            raise TimeoutError("unknown billable outcome")
        with self.assertRaises(TimeoutError):
            self.budget.invoke(
                role="extraction",revision_sha=self.source,
                model=MODELS["extraction"],payload=self.payload(1),
                transport=outage)
        report=self.audit()
        self.assertFalse(report["all_provider_receipts_qualified"])
        self.assertEqual(report["provider_attempts_reserved"],1)

    def test_missing_cost_rejected(self):
        self.invoke(cost=False)
        self.assertFalse(self.audit()["all_provider_receipts_qualified"])

    def test_empty_approval_is_not_qualified(self):
        self.assertEqual(self.audit()["status"],"INCOMPLETE_EVIDENCE_HOLD")


if __name__=="__main__":
    unittest.main()
