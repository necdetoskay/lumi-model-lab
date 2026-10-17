"""SERA v0.52 delegated budget: real rules, offline fake transport ONLY."""
import base64
import concurrent.futures
from decimal import Decimal
import tempfile
import time
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from experiments.sera.coverage import prose_hash
from experiments.sera.delegated_paid_budget_v052 import (
    DelegatedBudget, JournalBlocked, SCOPE, SCHEMA, verify_delegated_approval)
from experiments.sera.provider_grant_journal_v052 import ProviderJournal, _canonical

MODELS={"extraction":"test/extractor","semantic":"test/semantic",
        "typed":"test/typed","writer":"test/writer"}
PARENT="Mara crossed the platform. Vane held the pocket watch."
REVISED="Mara crossed the platform. Vane held his stopped pocket watch."
SOURCE=prose_hash(PARENT)
CONTEXT=dict(source_sha256=SOURCE,world_sha256="b"*64,
             scene_key="v052-mara-test",policy_sha256="c"*64,
             approved_models=MODELS,max_rewrites=2)


class DelegatedBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"durable.db"
        self.journal=ProviderJournal(self.path)
        self.signer=Ed25519PrivateKey.generate()
        self.public=self.signer.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        self.calls=[]
        self.payload={"messages":[{"role":"user","content":"source-only"}],
                      "response_format":{"type":"json_object"}}
        self.writer_payload={"messages":[{"role":"user","content":"repair"}],
                             "response_format":{"type":"json_object"}}
        self.approval=self.sign()
        self.budget=self.construct()

    def sign(self,**changes):
        m=dict(schema=SCHEMA,scope=SCOPE,approval_id="signed-mara-budget",
               expires_at=int(time.time())+3600,
               max_posts=5,max_posts_per_role={
                   "extraction":3,"semantic":0,"typed":0,"writer":2},
               max_observed_usd="0.010",**CONTEXT)
        m.update(changes)
        return {"manifest":m,"signature":base64.b64encode(
            self.signer.sign(_canonical(m).encode("utf-8"))).decode("ascii")}

    def construct(self,**changes):
        kw=dict(journal=self.journal,approval=self.approval,
                trusted_public_key=self.public,**CONTEXT)
        kw.update(changes)
        return DelegatedBudget(**kw)

    def transport(self,**args):
        self.calls.append(args)
        model=args["model"]
        if model == MODELS["writer"]:
            content=_canonical({"source_prose_sha256":SOURCE,
                                "revised_scene_prose":REVISED})
        else:
            content="{}"
        return {"raw":{"model":model,"id":"gen-"+str(len(self.calls)),
                       "choices":[{"finish_reason":"stop",
                                   "message":{"content":content}}],
                       "usage":{"prompt_tokens":20,"completion_tokens":12,
                                "cost":0.003}},"error":None}

    def invoke(self,role="extraction",revision=SOURCE,payload=None,
               transport=None):
        return self.budget.invoke(
            role=role,revision_sha=revision,
            model=MODELS[role],payload=payload or self.payload,
            transport=transport or self.transport)

    def test_signature_and_binding_fail_closed(self):
        forged=dict(self.approval,signature="invalid")
        with self.assertRaises(JournalBlocked):
            self.construct(approval=forged)
        with self.assertRaisesRegex(JournalBlocked,"SCOPE_DRIFT"):
            self.construct(source_sha256="d"*64)
        with self.assertRaisesRegex(JournalBlocked,"EXPIRED"):
            self.construct(approval=self.sign(expires_at=1))
        self.assertEqual(self.calls,[])

    def test_once_even_on_restart(self):
        a=self.invoke()
        self.budget=self.construct()
        b=self.invoke()
        self.assertEqual(a,b)
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.journal.status(
            self.budget.allocate(role="extraction",revision_sha=SOURCE,
                                 model=MODELS["extraction"],
                                 payload=self.payload)[1]),"RECEIPTED")

    def test_request_change_spends_new_slot_only_after_priced_receipt(self):
        self.invoke()
        other={"messages":[{"role":"user","content":"second batch"}]}
        self.invoke(payload=other)
        self.assertEqual(len(self.calls),2)

    def test_unknown_inflight_freezes_future_spend(self):
        def timeout(**args):
            self.calls.append(args)
            raise TimeoutError("ambiguous wire")
        with self.assertRaises(TimeoutError):
            self.invoke(transport=timeout)
        with self.assertRaisesRegex(JournalBlocked,"PREVIOUS_REQUEST_NOT_RECEIPTED"):
            self.invoke(payload={"messages":[{"role":"user","content":"next"}]})
        with self.assertRaisesRegex(JournalBlocked,"UNKNOWN_INFLIGHT"):
            self.invoke()
        self.assertEqual(len(self.calls),1)

    def test_observed_cost_stops_new_request_without_rebilling(self):
        def expensive(**args):
            self.calls.append(args)
            return {"raw":{"model":args["model"],"id":"gen-cost",
                           "choices":[],"usage":{"cost":"0.011"}},
                    "error":None}
        self.invoke(transport=expensive)
        with self.assertRaisesRegex(JournalBlocked,"OBSERVED_COST_GUARD"):
            self.invoke(payload={"messages":[{"role":"user","content":"new"}]})
        self.assertEqual(len(self.calls),1)

    def test_missing_cost_fails_closed(self):
        def unpriced(**args):
            self.calls.append(args)
            return {"raw":{"model":args["model"],"id":"id-1",
                           "choices":[],"usage":{}},"error":None}
        self.invoke(transport=unpriced)
        with self.assertRaisesRegex(JournalBlocked,"PRICE_MISSING"):
            self.invoke(payload={"messages":[{"role":"user","content":"new"}]})
        self.assertEqual(len(self.calls),1)

    def test_per_role_count_limit_and_no_overallocation(self):
        self.invoke(role="writer",payload=self.writer_payload)
        self.invoke(role="writer",payload={"messages":[{"role":"user",
                                                        "content":"again"}]})
        with self.assertRaisesRegex(JournalBlocked,"ROLE_COUNT_EXHAUSTED"):
            self.invoke(role="writer",payload={"messages":[{"role":"user",
                                                            "content":"third"}]})
        self.assertEqual(len(self.calls),2)

    def test_unsigned_and_unknown_revision_rejected(self):
        with self.assertRaisesRegex(JournalBlocked,"UNPROVEN_REVISION"):
            self.invoke(revision=prose_hash(REVISED))
        self.assertEqual(self.calls,[])

    def test_writer_receipt_proves_future_revision(self):
        output=self.invoke(role="writer",payload=self.writer_payload)
        writer_id=output["raw"]["id"]
        new_sha=self.budget.register_model_revision(
            parent_prose=PARENT,revised_prose=REVISED,
            writer_payload=self.writer_payload,writer_response_id=writer_id)
        self.assertEqual(new_sha,prose_hash(REVISED))
        self.invoke(role="extraction",revision=new_sha)
        self.assertEqual(len(self.calls),2)

    def test_manual_or_mismatched_revision_blocked(self):
        output=self.invoke(role="writer",payload=self.writer_payload)
        with self.assertRaisesRegex(JournalBlocked,"REVISION_UNPROVEN"):
            self.budget.register_model_revision(
                parent_prose=PARENT,revised_prose="Hand-edited story",
                writer_payload=self.writer_payload,
                writer_response_id=output["raw"]["id"])
        with self.assertRaisesRegex(JournalBlocked,"RECEIPT_ID_MISMATCH"):
            self.budget.register_model_revision(
                parent_prose=PARENT,revised_prose=REVISED,
                writer_payload=self.writer_payload,writer_response_id="fake")
        self.assertEqual(len(self.calls),1)

    def test_output_ceiling_forbidden_before_spend(self):
        with self.assertRaises(Exception):
            self.invoke(payload={"max_tokens":8,"messages":[]})
        self.assertEqual(self.calls,[])

    def test_concurrent_same_request_single_post(self):
        def run(_):
            return self.invoke()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            values=list(pool.map(run,range(4)))
        self.assertEqual(len(values),4)
        self.assertEqual(len(self.calls),1)

    def test_approval_id_cannot_be_rebound(self):
        other=self.sign(max_posts=4)
        with self.assertRaisesRegex(JournalBlocked,"APPROVAL_ID_REUSED"):
            self.construct(approval=other)

    def test_attempted_signed_budget_cannot_rewrite_canon(self):
        self.assertEqual(self.budget.manifest["scope"],SCOPE)
        self.assertEqual(self.budget.manifest["source_sha256"],SOURCE)
        self.assertNotIn("canonical_commit_authorized",self.budget.manifest)


if __name__=="__main__":
    unittest.main()
