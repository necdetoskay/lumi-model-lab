"""SERA v0.13 isolated versioned reducer; all approvals are TEST FIXTURES."""
from __future__ import annotations

from copy import deepcopy
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.world_state_v02 import canonical
from experiments.sera.mara_s1_typed_live_v05 import entry_state
from experiments.sera.mara_s1_v04_audit import PATH
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.world_state_v013 import (
    SCHEMA,MODE,create,digest,apply_simulated,simulate_batch,verify_replay,
    restore_simulated_revision,validate,
)
import json

PROSE=json.loads(PATH.read_text(encoding="utf-8"))["prose"]

def base():
    return entry_state()

def seed():
    return create(base_world=base(),prose=PROSE,
                  openables=["vane_watch"],documents=["mara_notebook"])

def build_event(kind,quoted,owner,actor,payload,event_id=None):
    start=PROSE.index(quoted)
    row=next(x for x in sentences(PROSE)
             if x["start"]<=start and start+len(quoted)<=x["end"])
    return {
        "event_id":event_id or "fixture-"+kind.lower(),
        "type":kind,"actor_id":actor,"object_id":owner,
        "sentence_id":row["id"],
        "evidence":{"start":start,"end":start+len(quoted),"quote":quoted},
        "payload":payload,
    }

def three():
    return [
        build_event("OBSERVE_OPENABLE",
                    "pocket watch open in his palm",
                    "vane_watch","vane",
                    {"expected":"UNKNOWN","observed":"OPEN"},
                    "fixture-watch-open-baseline"),
        build_event("SET_OPENABLE","closed",
                    "vane_watch","vane",
                    {"expected":"OPEN","next":"CLOSED"},
                    "fixture-watch-closure"),
        build_event("APPEND_DOCUMENT_ENTRY",
                    "Discrepancy documented; explanation unknown.",
                    "mara_notebook","mara",
                    {"expected_append_count":0,
                     "text":"Discrepancy documented; explanation unknown."},
                    "fixture-notebook-append"),
    ]

def approvals(events):
    # Test-only permission; proves enforced interface, not external trust.
    return {e["event_id"]:digest(e) for e in events}

class WorldStateV013Tests(unittest.TestCase):
    def assert_denied(self,code,work):
        with self.assertRaisesRegex(CoverageError,code):
            work()

    def test_migration_is_copy_of_v02_no_canonical_db_write(self):
        original=base()
        source=deepcopy(original)
        state=create(base_world=original,prose=PROSE,
                     openables=["vane_watch"],documents=["mara_notebook"])
        self.assertEqual(state["schema"],SCHEMA)
        self.assertEqual(state["base_world"],source)
        self.assertEqual(original,source)
        self.assertEqual(state["base_world"]["schema"],"sera.world-state.v0.2")
        self.assertEqual(state["commit_mode"],"OFFLINE_APPROVAL_FIXTURE")
        self.assertFalse(state["production_commit_authorized"])
        self.assertTrue(verify_replay(state=state,prose=PROSE))

    def test_three_typed_events_cas_source_order_hash_and_determinism(self):
        initial=seed()
        original=deepcopy(initial)
        events=three()
        result=simulate_batch(
            state=initial,events=events,prose=PROSE,
            approvals=approvals(events),mode=MODE)
        self.assertEqual(initial,original)
        self.assertEqual(result["revision"],3)
        self.assertEqual(result["aspects"]["vane_watch"]["position"],"CLOSED")
        notebook=result["aspects"]["mara_notebook"]
        self.assertEqual(notebook["preexisting_content"],"UNKNOWN")
        self.assertEqual(len(notebook["observed_appends"]),1)
        self.assertEqual(notebook["observed_appends"][0]["text"],
                         "Discrepancy documented; explanation unknown.")
        self.assertEqual(result["base_world"],base())
        self.assertFalse(result["production_commit_authorized"])
        self.assertTrue(verify_replay(state=result,prose=PROSE))
        repeated=simulate_batch(state=initial,events=events,prose=PROSE,
                                approvals=approvals(events),mode=MODE)
        self.assertEqual(result,repeated)

    def test_failure_on_missing_approval_and_real_mode_and_replay(self):
        s=seed();event=three()[0]
        self.assert_denied("V013_SEPARATE_SIMULATED_APPROVAL_REQUIRED",
                           lambda:apply_simulated(
                               state=s,event=event,prose=PROSE,
                               approvals={},mode=MODE))
        self.assert_denied("V013_REAL_COMMIT_API_NOT_AVAILABLE",
                           lambda:apply_simulated(
                               state=s,event=event,prose=PROSE,
                               approvals=approvals([event]),mode="PRODUCTION"))
        complete=simulate_batch(
            state=s,events=three(),prose=PROSE,
            approvals=approvals(three()),mode=MODE)
        self.assert_denied("V013_EVENT_ID_REPLAY",
                           lambda:apply_simulated(
                               state=complete,event=event,prose=PROSE,
                               approvals=approvals([event]),mode=MODE))

    def test_cannot_close_when_old_is_unknown_or_wrong_version(self):
        events=three()
        self.assert_denied("V013_OPENABLE_COMPARE_AND_SWAP_INVALID",
                           lambda:apply_simulated(
                               state=seed(),event=events[1],prose=PROSE,
                               approvals=approvals(events),mode=MODE))
        state=apply_simulated(
            state=seed(),event=events[0],prose=PROSE,
            approvals=approvals(events),mode=MODE)
        bad=deepcopy(events[1])
        bad["payload"]["expected"]="UNKNOWN"
        self.assert_denied("V013_OPENABLE_COMPARE_AND_SWAP_INVALID",
                           lambda:apply_simulated(
                               state=state,event=bad,prose=PROSE,
                               approvals=approvals([bad]),mode=MODE))

    def test_cannot_forge_document_content_or_skip_expected_count(self):
        s=seed()
        e=three()[2]
        wrong=deepcopy(e);wrong["payload"]["text"]="The train physically arrived"
        self.assert_denied("V013_DOCUMENT_APPEND_CONTENT_OR_CAS_INVALID",
                           lambda:apply_simulated(
                               state=s,event=wrong,prose=PROSE,
                               approvals=approvals([wrong]),mode=MODE))
        wrong=deepcopy(e);wrong["payload"]["expected_append_count"]=1
        self.assert_denied("V013_DOCUMENT_APPEND_CONTENT_OR_CAS_INVALID",
                           lambda:apply_simulated(
                               state=s,event=wrong,prose=PROSE,
                               approvals=approvals([wrong]),mode=MODE))

    def test_recorded_train_claim_never_creates_physical_arrival(self):
        event=three()[2]
        bad=deepcopy(event);bad["type"]="TRAIN_ARRIVAL";bad["object_id"]="train_41"
        self.assert_denied("V013_EVENT_ID_OR_TYPE_INVALID",
                           lambda:apply_simulated(
                               state=seed(),event=bad,prose=PROSE,
                               approvals=approvals([bad]),mode=MODE))
        self.assertNotIn("train_41",seed()["aspects"])

    def test_no_fabricated_action_clock_or_extra_fields(self):
        original=three()[1]
        for key,value in [("at_minute",130),("world_authority",True),
                          ("signed_by","llm"),("canonical_commit_authorized",True)]:
            wrong=deepcopy(original);wrong[key]=value
            self.assert_denied("V013_EVENT_FIELDS_INVALID",
                               lambda:apply_simulated(
                                   state=seed(),event=wrong,prose=PROSE,
                                   approvals=approvals([wrong]),mode=MODE))

    def test_forged_quote_span_and_wrong_sentence_blocked(self):
        correct=three()[0]
        wrong=deepcopy(correct);wrong["evidence"]["quote"]="a new flying train"
        self.assert_denied("V013_EVENT_SOURCE_SPAN_INVALID",
                           lambda:apply_simulated(
                               state=seed(),event=wrong,prose=PROSE,
                               approvals=approvals([wrong]),mode=MODE))
        wrong=deepcopy(correct);wrong["sentence_id"]="s028"
        self.assert_denied("V013_EVIDENCE_OUTSIDE_NUMBERED_SENTENCE",
                           lambda:apply_simulated(
                               state=seed(),event=wrong,prose=PROSE,
                               approvals=approvals([wrong]),mode=MODE))

    def test_wrong_entity_actor_location_and_aspect_role_forbidden(self):
        event=three()[0]
        unknown=deepcopy(event);unknown["object_id"]="new:watch_case"
        self.assert_denied("V013_REGISTERED_ENTITY_REQUIRED",
                           lambda:apply_simulated(
                               state=seed(),event=unknown,prose=PROSE,
                               approvals=approvals([unknown]),mode=MODE))
        wrong=deepcopy(event);wrong["object_id"]="mara_notebook"
        self.assert_denied("V013_FACET_ROLE_MISMATCH",
                           lambda:apply_simulated(
                               state=seed(),event=wrong,prose=PROSE,
                               approvals=approvals([wrong]),mode=MODE))

    def test_broken_history_chain_and_mutated_snapshot_detected(self):
        state=simulate_batch(
            state=seed(),events=three(),prose=PROSE,
            approvals=approvals(three()),mode=MODE)
        altered=deepcopy(state);altered["events"][1]["prior_hash"]="0"*64
        self.assert_denied("V013_REPLAY_HASH_CHAIN_MISMATCH",
                           lambda:verify_replay(state=altered,prose=PROSE))
        altered=deepcopy(state)
        altered["aspects"]["vane_watch"]["position"]="OPEN"
        self.assert_denied("V013_REPLAY_SNAPSHOT_DIVERGENCE",
                           lambda:verify_replay(state=altered,prose=PROSE))
        altered=deepcopy(state)
        altered["events"][0]["event"]["payload"]["observed"]="CLOSED"
        self.assert_denied("V013_REPLAY_RECEIPT_MISMATCH",
                           lambda:verify_replay(state=altered,prose=PROSE))

    def test_detached_historical_restore_without_mutating_final(self):
        events=three()
        latest=simulate_batch(state=seed(),events=events,prose=PROSE,
                              approvals=approvals(events),mode=MODE)
        old=deepcopy(latest)
        baseline=restore_simulated_revision(
            state=latest,prose=PROSE,revision=0)
        first=restore_simulated_revision(
            state=latest,prose=PROSE,revision=1)
        second=restore_simulated_revision(
            state=latest,prose=PROSE,revision=2)
        self.assertEqual(baseline["aspects"]["vane_watch"]["position"],"UNKNOWN")
        self.assertEqual(first["aspects"]["vane_watch"]["position"],"OPEN")
        self.assertEqual(second["aspects"]["vane_watch"]["position"],"CLOSED")
        self.assertEqual(len(second["aspects"]["mara_notebook"]["observed_appends"]),0)
        self.assertEqual(latest,old)
        self.assert_denied("V013_REVISION_OUTSIDE_HISTORY",
                           lambda:restore_simulated_revision(
                               state=latest,prose=PROSE,revision=4))

    def test_bad_multi_event_batch_atomic_caller_input_untouched(self):
        original=seed()
        ev=three()
        wrong=deepcopy(ev[2]);wrong["payload"]["expected_append_count"]=2
        self.assert_denied("V013_DOCUMENT_APPEND_CONTENT_OR_CAS_INVALID",
                           lambda:simulate_batch(
                               state=original,events=[ev[0],ev[1],wrong],
                               prose=PROSE,
                               approvals=approvals([ev[0],ev[1],wrong]),
                               mode=MODE))
        self.assertEqual(original["revision"],0)
        self.assertEqual(original["events"],[])
        self.assertEqual(original["aspects"]["vane_watch"]["position"],"UNKNOWN")

if __name__=="__main__":
    unittest.main()
