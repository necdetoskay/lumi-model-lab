"""Frozen Mara 28: actual registered facets, evidence-CAS replay, NO model authority.

This is a deterministic PHYSICAL SUBSET control, NOT semantic qualification
or a successful 28-sentence model-run. All evidence quotes are sourced from
the unchanged original SHA; source text is never edited and never fed as
handwritten gold to a provider. Simulated approval is test-only.
"""
from __future__ import annotations

from copy import deepcopy
import unittest

from experiments.sera.authorized_mara_delegated_lane_v052 import registered_mara_facets
from experiments.sera.coverage import CoverageError,prose_hash
from experiments.sera.mara_s1_typed_live_v05 import entry_state
from experiments.sera.real_blind_benchmark_v040 import prepare,EXPECTED_SHA
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.world_state_v013 import (
    create,digest,simulate_batch,verify_replay,restore_simulated_revision,MODE,
)


class FrozenMaraFacetControl(unittest.TestCase):
    def setUp(self):
        self.prose=prepare()["prose"]
        self.world=entry_state()
        self.roles=registered_mara_facets(self.world)
        self.units=sentences(self.prose)

    def event(self,number,event_type,actor,object_id,quote,payload):
        start=self.prose.index(quote)
        unit=next(x for x in self.units if
                  x["start"]<=start and start+len(quote)<=x["end"])
        return {
            "event_id":"control-"+str(number),
            "type":event_type,"actor_id":actor,"object_id":object_id,
            "sentence_id":unit["id"],
            "evidence":{"start":start,"end":start+len(quote),"quote":quote},
            "payload":payload,
        }

    def baseline(self):
        return create(base_world=self.world,prose=self.prose,
                      openables=["vane_watch"],
                      documents=self.roles["documents"])

    def controls(self):
        return [
            self.event(1,"OBSERVE_OPENABLE","vane","vane_watch",
                       "pocket watch open in his palm",
                       {"expected":"UNKNOWN","observed":"OPEN"}),
            self.event(2,"SET_OPENABLE","vane","vane_watch",
                       "Vane closed the case with his thumb",
                       {"expected":"OPEN","next":"CLOSED"}),
            self.event(3,"APPEND_DOCUMENT_ENTRY","mara","mara_notebook",
                       "Archive telegram: arrival recorded at 02:10.",
                       {"expected_append_count":0,
                        "text":"Archive telegram: arrival recorded at 02:10."}),
        ]

    def test_frozen_source_and_registered_capabilities_without_auto_event_authority(self):
        self.assertEqual(prose_hash(self.prose),EXPECTED_SHA)
        self.assertEqual(len(self.units),28)
        self.assertEqual(self.roles,{"openables":["vane_watch","mara_notebook"],
                                     "documents":["mara_notebook"]})
        before=self.baseline()
        self.assertEqual(before["revision"],0)
        self.assertEqual(before["aspects"]["vane_watch"]["position"],"UNKNOWN")
        self.assertEqual(before["aspects"]["mara_notebook"]["observed_appends"],[])
        self.assertFalse(before["production_commit_authorized"])

    def test_source_bound_watch_case_and_notebook_replay_is_safe_offline(self):
        source_before=deepcopy(self.world)
        events=self.controls()
        for e in events:
            a,b=e["evidence"]["start"],e["evidence"]["end"]
            self.assertEqual(self.prose[a:b],e["evidence"]["quote"])
        self.assertEqual([x["evidence"]["start"] for x in events],
                         sorted(x["evidence"]["start"] for x in events))
        result=simulate_batch(
            state=self.baseline(),events=events,prose=self.prose,
            approvals={e["event_id"]:digest(e) for e in events},mode=MODE)
        self.assertTrue(verify_replay(state=result,prose=self.prose))
        self.assertEqual(result["revision"],3)
        self.assertEqual(result["aspects"]["vane_watch"]["position"],"CLOSED")
        self.assertEqual(len(result["aspects"]["mara_notebook"]["observed_appends"]),1)
        self.assertEqual(source_before,self.world)
        self.assertEqual(result["base_world"],source_before)
        self.assertFalse(result["production_commit_authorized"])
        historical=restore_simulated_revision(state=result,prose=self.prose,revision=1)
        self.assertEqual(historical["aspects"]["vane_watch"]["position"],"OPEN")
        self.assertEqual(historical["aspects"]["mara_notebook"]["observed_appends"],[])

    def test_fake_document_quote_does_not_write_anything(self):
        events=self.controls()
        fake=deepcopy(events[2])
        fake["evidence"]["quote"]="the model fabricated an arrival"
        with self.assertRaisesRegex(CoverageError,"V013_EVENT_SOURCE_SPAN_INVALID"):
            simulate_batch(
                state=self.baseline(),events=[fake],prose=self.prose,
                approvals={fake["event_id"]:digest(fake)},mode=MODE)
        self.assertEqual(self.baseline()["aspects"]["mara_notebook"]["observed_appends"],[])

    def test_watch_notebook_capabilities_must_be_registered_and_in_custody(self):
        bad=deepcopy(self.world)
        del bad["entities"]["mara_notebook"]
        with self.assertRaisesRegex(CoverageError,"V052_MARA_REGISTERED_FACET_MISSING"):
            registered_mara_facets(bad)
        bad=deepcopy(self.world)
        bad["entities"]["vane_watch"]["holder"]=None
        with self.assertRaisesRegex(CoverageError,"V052_MARA_FACET_CUSTODY_MISMATCH"):
            registered_mara_facets(bad)

    def test_bad_authority_or_duplicate_physical_action_is_not_committed(self):
        events=self.controls()
        with self.assertRaisesRegex(CoverageError,"V013_SEPARATE_SIMULATED_APPROVAL_REQUIRED"):
            simulate_batch(state=self.baseline(),events=events,
                           prose=self.prose,approvals={},mode=MODE)
        with self.assertRaisesRegex(CoverageError,"V013_EVENT_ID_REPLAY|V013_EVENT_NARRATIVE_ORDER_OR_DUPLICATE"):
            simulate_batch(
                state=self.baseline(),events=[events[0],events[0]],
                prose=self.prose,
                approvals={events[0]["event_id"]:digest(events[0])},
                mode=MODE)


if __name__=="__main__":
    unittest.main()
