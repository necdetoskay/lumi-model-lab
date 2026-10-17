"""SERA v0.52 independently signed *positive* model pipeline, OFFLINE.

Exercises actual v0.22 -> v0.23 -> v0.21 Writer -> fresh v0.22/v0.23
through the immutable signed DelegatedBudget, durable ProviderJournal and
real-wire bytes adapter SHAPE. The provider is a scripted mock, not a model.
Ari is a two-sentence positive CONTROL, not evidence Mara 28 has passed.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import time
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from experiments.sera.artifact_scene_checker_v021 import create_checker, digest
from experiments.sera.coverage import prose_hash
from experiments.sera.delegated_paid_budget_v052 import DelegatedBudget, SCOPE, SCHEMA
from experiments.sera.delegated_provider_bridge_v052 import create_delegated_provider
from experiments.sera.fresh_scene_evidence_worker_v022 import create_preparer
from experiments.sera.openrouter_scene_writer_v021 import create_writer, make_request
from experiments.sera.provider_grant_journal_v052 import _canonical
from experiments.sera.paid_runtime_boundary_v052 import (
    provision_local_journal,open_bound_paid_journal,SCHEMA as RUNTIME_SCHEMA)
from experiments.sera.tests.test_fresh_scene_evidence_worker_v022 import (
    SOURCE_1,SOURCE_2,entry,fake_model)
from experiments.sera.unattended_scene_rewrite_v020 import execute as scene_loop

MODELS=dict(extraction="test/signed-sweep",
            semantic="test/signed-semantic",
            typed="test/signed-typed",
            writer="test/signed-source-bound-writer")
SCENE="v052-positive-ari-signed-model-control"


class SignedAutorepairPositiveControl(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.path=self.root/"shared-grants.db"
        runtime=provision_local_journal(path=self.path)
        self.runtime=dict(schema=RUNTIME_SCHEMA,
                          journal_path=runtime["journal_path"],
                          journal_id=runtime["journal_id"],
                          host_id_sha256=runtime["host_id_sha256"],
                          revoked_approval_ids=[])
        self.signer=Ed25519PrivateKey.generate()
        self.public=self.signer.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        self.runtime["trusted_raw_key_sha256"]=sha256(self.public).hexdigest()
        self.policy_sha="d"*64
        self.world=entry()
        self.signed=self.approval()
        self.sent=[]
        self.provider_rows=[]
        self.fake=fake_model(self.provider_rows)

    def approval(self):
        manifest=dict(schema=SCHEMA,scope=SCOPE,
            approval_id="ari-v052-positive-signed-lab-only",
            expires_at=int(time.time())+3600,
            source_sha256=prose_hash(SOURCE_1),
            world_sha256=digest(self.world),
            scene_key=SCENE,policy_sha256=self.policy_sha,
            approved_models=MODELS,max_rewrites=1,
            max_posts=24,
            max_posts_per_role=dict(extraction=10,semantic=8,typed=4,writer=2),
            max_observed_usd="0.20")
        return dict(manifest=manifest,signature=base64.b64encode(
            self.signer.sign(_canonical(manifest).encode("utf-8"))).decode("ascii"))

    def fake_wire(self,*,model,payload,request_id):
        packet=json.loads(payload["messages"][1]["content"])
        self.assertNotIn("max_tokens",payload)
        self.assertNotIn("max_completion_tokens",payload)
        if model==MODELS["writer"]:
            self.assertEqual(packet["scene_prose"],SOURCE_1)
            self.assertEqual(packet["source_prose_sha256"],prose_hash(SOURCE_1))
            content=json.dumps(dict(source_prose_sha256=prose_hash(SOURCE_1),
                                    revised_scene_prose=SOURCE_2))
        else:
            reply=self.fake(key="SIGNED_OFFLINE_ONLY",model=model,
                            prepared={"request":payload})
            content=reply["raw"]["choices"][0]["message"]["content"]
        self.sent.append((model,request_id,packet))
        body=dict(id="signed-offline-"+str(len(self.sent)),
                  model=model,
                  usage=dict(prompt_tokens=41,completion_tokens=26,cost="0.001"),
                  choices=[dict(finish_reason="stop",
                                message=dict(content=content))])
        return dict(wire_payload_b64=base64.b64encode(
                        json.dumps(body,ensure_ascii=False).encode("utf-8")
                    ).decode("ascii"),
                    http_status=200,duration_ms=13)

    def lane(self,*,fail_if_post=False):
        journal=open_bound_paid_journal(self.runtime)
        budget=DelegatedBudget(
            journal,approval=self.signed,trusted_public_key=self.public,
            source_sha256=prose_hash(SOURCE_1),
            world_sha256=digest(self.world),scene_key=SCENE,
            policy_sha256=self.policy_sha,approved_models=MODELS,
            max_rewrites=1)
        def no_rebill(**kwargs):
            self.fail("replay tried an additional mock-provider POST")
        callback=create_delegated_provider(
            budget=budget,transport=no_rebill if fail_if_post else self.fake_wire)
        location=self.root/"lane"
        def preparer(*,prose,world):
            callback.use_source(prose)
            return evidence(prose=prose,world=world)
        def reconcile(*,model,request,request_sha256):
            return callback.recover_completed(
                model=model,request=request,request_sha256=request_sha256)
        evidence=create_preparer(
            evidence_root=location/"evidence",
            work_root=location/"evidence-work",scene_key=SCENE,
            registry={"ari":["Ari"],"box":["box"]},
            candidate_lexicon={},
            typed_registry=dict(openables=["box"],documents=[]),
            api_key="SIGNED_OFFLINE_ONLY",
            extraction_model=MODELS["extraction"],
            semantic_model=MODELS["semantic"],typed_model=MODELS["typed"],
            provider_call=callback,reconciler=reconcile,
            max_model_requests=24,observed_spend_guard_usd="0.30")
        context=dict(scene_key=SCENE,entry_world_sha256=digest(self.world),
                     fresh_source_sha_required_after_each_rewrite=True)
        actual_writer=create_writer(
            api_key="SIGNED_OFFLINE_ONLY",model=MODELS["writer"],
            provider_call=callback,reconciler=reconcile,
            archive_dir=location/"writer-receipts",
            observed_spend_guard_usd="0.15",story_context=context)
        def writer(*,source,defects,recovery=False):
            callback.use_source(source)
            answer=(actual_writer.recover_existing(source=source,defects=defects)
                    if recovery else actual_writer(source=source,defects=defects))
            budget.register_model_revision(
                parent_prose=source,revised_prose=answer["prose"],
                writer_payload=make_request(
                    source=source,defects=defects,story_context=context),
                writer_response_id=answer["receipt"]["response_id"])
            return answer
        def recover(*,source,defects):
            return writer(source=source,defects=defects,recovery=True)
        outcome=scene_loop(
            prose=SOURCE_1,world=deepcopy(self.world),
            check_scene=create_checker(
                evidence_root=location/"evidence",full_qualification=True),
            rewrite_scene=writer,
            output_dir=location/"controller",prepare_evidence=preparer,
            evidence_policy_id="v052-signed-ari-positive-full-v023",
            max_rewrites=1,observed_spend_guard_usd="0.15",
            resume_reconciled_evidence=True,recover_rewrite_scene=recover)
        return outcome,budget

    def test_signed_writer_repaired_source_reextracted_and_v023_qualified(self):
        out,budget=self.lane()
        self.assertEqual(out["status"],"SCENE_CANDIDATE_READY_NONCANONICAL")
        self.assertEqual(out["rewrite_count"],1)
        self.assertEqual(out["final_prose_sha256"],prose_hash(SOURCE_2))
        self.assertEqual([x[0] for x in self.sent].count(MODELS["writer"]),1)
        self.assertGreaterEqual([x[0] for x in self.sent].count(
            MODELS["extraction"]),2)
        self.assertTrue(budget.revision_registered(prose_hash(SOURCE_2)))
        self.assertTrue((self.root/"lane"/"evidence"/
                         (prose_hash(SOURCE_1)+".json")).exists())
        self.assertTrue((self.root/"lane"/"evidence"/
                         (prose_hash(SOURCE_2)+".json")).exists())
        self.assertTrue((self.root/"lane"/"controller"/"check_01.json").exists())
        self.assertFalse(out["canonical_commit_authorized"])
        self.assertEqual(out["world_db_writes"],0)
        before=len(self.sent)
        again,_=self.lane(fail_if_post=True)
        self.assertEqual(out,again)
        self.assertEqual(len(self.sent),before)

    def test_no_manual_or_unreceipted_prose_registered(self):
        _,budget=self.lane()
        self.assertFalse(budget.revision_registered(
            prose_hash("An invented editor intervention.")))
        self.assertFalse(budget.revision_registered(
            prose_hash(SOURCE_1+" Added sentence without Writer.")))


if __name__=="__main__":
    unittest.main()
