"""Offline v0.53 signed physical entry-world reconciliation adversaries.

All Ed25519 keys and G2 snapshots here are TEST fixtures; never count
these signatures as deployment trust or as model-event truth.
"""
from __future__ import annotations

from copy import deepcopy
import unittest

from experiments.sera.coverage import CoverageError,prose_hash
from experiments.sera.g2_physical_projection_v033 import project
from experiments.sera.g2_readonly_scope_bridge_v032 import digest
from experiments.sera.source_chronology_v052 import build_source_chronology
from experiments.sera.signed_physical_reconciliation_v053 import (
    reconcile_signed_physical_source,
)
from experiments.sera.sentence_sweep_v010 import REPORT_SCHEMA
from experiments.sera.tests import test_g2_physical_pinned_reader_v036 as signed_fixture
from experiments.sera.tests.test_g2_physical_projection_v033 import BOX

SCENE="offline-signed-physical-source-join"
PROSE=("Ari moved the box. The timetable said train 41 arrived at 02:10.")


class PinnedSourceJoinTests(unittest.TestCase):
    def setUp(self):
        self.signer= signed_fixture.PinnedPhysicalTests(methodName=
            "test_signed_physical_source_is_shadow_only_and_replay_is_denied")
        self.signer.setUp()
        self.packet=self.signer.signed()
        self.source=PROSE
        self.world=project(
            authority=self.signer.authority,projection=self.packet,
            verify_projection=lambda _snapshot,_proof:True)["world"]
        self.registry={"actor":["Ari"],BOX:["box"]}
        self.chronology=build_source_chronology(
            prose=self.source,scene_key=SCENE,
            world_sha256=digest(self.world),
            registry=self.registry,candidate_lexicon={})

    def report(self,*,kind="TRANSFER",epistemic="OBSERVED_ACTION",
               refs=None,quote="moved the box"):
        original=self.chronology["source_sentences"]
        first=original[0]
        start=self.source.index(quote)
        sid=first["sentence_id"]
        event={
            "event_id":"model-proposed-event-0001",
            "sentence_id":sid,"start":start,"end":start+len(quote),
            "quote":quote,"kind":kind,"effect":"OBJECT",
            "epistemic":epistemic,
            "entity_refs":[BOX] if refs is None else refs,
        }
        rows=[{"sentence_id":s["sentence_id"],
               "disposition":"STATE_EVENT" if s["sentence_id"]==sid else
                             "CLAIM_ONLY",
               "event_ids":[event["event_id"]] if s["sentence_id"]==sid else [],
               "candidate_refs":[],"reason":"untrusted model candidate"}
              for s in original]
        return {
            "schema":REPORT_SCHEMA,
            "source_prose_sha256":prose_hash(self.source),
            "scene_key":SCENE,
            "sentences_accounted_for":len(rows),
            "canonical_commit_authorized":False,"world_state_writes":0,
            "semantic_recall_proven":False,
            "model_ledger":{"prose_sha256":prose_hash(self.source),
                            "rows":rows},
            "candidate_events":[event],"findings":[]
        }

    def args(self,*,report=None):
        chronology=(self.chronology if report is None else
                    build_source_chronology(
                        prose=self.source,scene_key=SCENE,
                        world_sha256=digest(self.world),
                        registry=self.registry,candidate_lexicon={},
                        model_report=report))
        return dict(prose=self.source,scene_key=SCENE,
                    chronology=chronology,
                    registry=self.registry,candidate_lexicon={},
                    authority=self.signer.authority,projection=self.packet,
                    public_key_pem=self.signer.pem,
                    raw_public_key_sha256=self.signer.fingerprint,
                    key_id=signed_fixture.KEY_ID,issuer=signed_fixture.ISSUER,audience=signed_fixture.AUDIENCE,
                    expected_nonce=signed_fixture.NONCE,consume_nonce=self.signer.consume,
                    now=signed_fixture.NOW+1,model_report=report)

    def test_signed_entry_baseline_with_no_model_events_is_still_hold(self):
        result=reconcile_signed_physical_source(**self.args())
        self.assertEqual(result["physical_baseline_status"],
                         "SIGNED_G2_ENTRY_ONLY")
        self.assertEqual(result["status"],
             "HOLD_NONCANONICAL_REQUIRES_INDEPENDENT_EVENT_PROOF")
        self.assertEqual(result["registered_physical_entry_entity_count"],
                         len(self.world["entities"]))
        facts={v["entity_id"]:v for v in result["registered_physical_entry"]}
        self.assertEqual(set(facts),set(self.world["entities"]))
        self.assertEqual(facts[BOX]["location_id"],
                         self.world["entities"][BOX]["location"])
        self.assertEqual(facts[BOX]["holder_id"],
                         self.world["entities"][BOX]["holder"])
        self.assertEqual(facts[BOX]["owner_id"],
                         self.world["entities"][BOX]["owner"])
        self.assertEqual(result["registered_route_count"],
                         len(self.packet["snapshot"]["registeredRoutes"]))
        self.assertEqual(result["source_sentence_count"],2)
        self.assertEqual(result["model_candidate_event_count"],0)
        self.assertEqual(result["verified_future_event_count"],0)
        self.assertFalse(result["source_order_is_event_clock"])
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(result["world_db_writes"],0)

    def test_registered_object_movement_is_not_auto_approved_transfer(self):
        unchanged=deepcopy(self.world)
        args=self.args(report=self.report())
        result=reconcile_signed_physical_source(**args)
        self.assertEqual(result["model_candidate_event_count"],1)
        event=result["model_event_proposals"][0]
        self.assertEqual(event["status"],
                         "REGISTERED_BASELINE_ONLY_EVENT_NOT_ATTESTED")
        self.assertEqual(event["registered_entity_refs"],[BOX])
        self.assertEqual(event["baseline"][BOX]["holder"],
                         unchanged["entities"][BOX]["holder"])
        self.assertIsNone(event["event_action_minute"])
        self.assertFalse(event["proposed_effect_allowed"])
        self.assertFalse(event["event_occurrence_verified"])
        self.assertEqual(unchanged,self.world)
        self.assertEqual(result["world_mutations_performed"],0)

    def test_reported_claim_cannot_become_train_arrival(self):
        # Even an event claiming to modify a registered object's state is
        # nonobjective if it is testimony or a document quote.
        report=self.report(epistemic="REPORTED_CLAIM")
        result=reconcile_signed_physical_source(**self.args(report=report))
        self.assertEqual(result["model_event_proposals"][0]["status"],
                         "CLAIM_OR_UNCERTAIN_NOT_OBJECTIVE")
        self.assertEqual(result["verified_future_event_count"],0)

    def test_unregistered_future_actor_cannot_inherit_physical_identity(self):
        report=self.report(refs=["new:train_41"])
        result=reconcile_signed_physical_source(**self.args(report=report))
        e=result["model_event_proposals"][0]
        self.assertEqual(e["registered_entity_refs"],[])
        self.assertEqual(e["unregistered_or_candidate_refs"],["new:train_41"])
        self.assertEqual(e["status"],
                         "ENTITY_IDENTITY_NOT_PHYSICALLY_REGISTERED")

    def test_invalid_nested_model_reference_fails_closed_not_typeerror(self):
        report=self.report(refs=[{"invented_identity":"forged"}])
        with self.assertRaisesRegex(CoverageError,
                                    "V053_MODEL_EVENT_ENTITY_REFS_INVALID"):
            reconcile_signed_physical_source(**self.args(report=report))

    def test_broken_signature_and_unpinned_key_fail_before_result(self):
        args=self.args()
        args["projection"]=self.signer.signed(bad_signature=True)
        with self.assertRaisesRegex(CoverageError,"PHYSICAL_SIGNATURE_INVALID"):
            reconcile_signed_physical_source(**args)
        self.assertEqual(self.signer.used,set())
        args=self.args()
        args["raw_public_key_sha256"]="f"*64
        with self.assertRaisesRegex(CoverageError,"PUBLIC_KEY_PIN_MISMATCH"):
            reconcile_signed_physical_source(**args)
        self.assertEqual(self.signer.used,set())

    def test_wrong_entry_world_sha_cannot_be_joined(self):
        args=self.args()
        args["chronology"]=build_source_chronology(
            prose=self.source,scene_key=SCENE,world_sha256="f"*64,
            registry=self.registry,candidate_lexicon={})
        with self.assertRaisesRegex(
            CoverageError,"CHRONOLOGY_NOT_BOUND_TO_PINNED_PHYSICAL_WORLD"):
            reconcile_signed_physical_source(**args)

    def test_fake_event_evidence_quote_rejected(self):
        report=self.report()
        report["candidate_events"][0]["quote"]="fabricated physical fact"
        with self.assertRaisesRegex(CoverageError,"EVENT_SPAN_INVALID"):
            self.args(report=report)
        self.assertEqual(self.signer.used,set())

    def test_real_mara_cannot_borrow_unrelated_signed_world_snapshot(self):
        """Correct Ed25519 signature does not bind an unrelated story world."""
        from experiments.sera.real_blind_benchmark_v040 import prepare
        from experiments.sera.mara_s1_typed_live_v05 import entry_state,REGISTRY
        from experiments.sera.real_blind_benchmark_v040 import LEXICON
        from pathlib import Path
        import json
        mara=prepare()["prose"]
        original=entry_state()
        aliases={k:v for k,v in REGISTRY.items() if k in original["entities"]}
        candidate_aliases=json.loads(LEXICON.read_text(
            encoding="utf-8"))["candidates"]
        timeline=build_source_chronology(
            prose=mara,scene_key="hook_empty_platform",
            world_sha256=digest(original),
            registry=aliases,candidate_lexicon=candidate_aliases)
        args=self.args()
        args.update(prose=mara,scene_key="hook_empty_platform",
                    chronology=timeline,
                    registry=aliases,candidate_lexicon=candidate_aliases)
        with self.assertRaisesRegex(
                CoverageError,"CHRONOLOGY_NOT_BOUND_TO_PINNED_PHYSICAL_WORLD"):
            reconcile_signed_physical_source(**args)

    def test_no_replay_of_same_physical_challenge(self):
        args=self.args()
        reconcile_signed_physical_source(**args)
        with self.assertRaisesRegex(CoverageError,"PHYSICAL_NONCE_REPLAY"):
            reconcile_signed_physical_source(**args)

    def test_model_cannot_self_sign_a_physical_baseline(self):
        args=self.args(report=self.report())
        args["projection"]={}
        with self.assertRaisesRegex(CoverageError,
                                    "PHYSICAL_SOURCE_NOT_AVAILABLE"):
            reconcile_signed_physical_source(**args)
        self.assertEqual(self.signer.used,set())


if __name__=="__main__":
    unittest.main()
