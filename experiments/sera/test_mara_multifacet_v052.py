"""Frozen Mara 28 physical object multi-capability source-control.

These are isolated deterministic capabilities, NOT a successful model-created
scene. Test evidence is explicitly synthetic and is NEVER passed to Writer or
real provider as prior model opinion / gold. Real narrative qualification
still requires independent extraction and a whole-scene v0.23 PASS.
"""
from __future__ import annotations

from copy import deepcopy
import unittest

from experiments.sera.coverage import CoverageError,prose_hash
from experiments.sera.mara_s1_typed_live_v05 import entry_state
from experiments.sera.multifacet_physical_preview_v054 import preview
from experiments.sera.real_blind_benchmark_v040 import prepare, EXPECTED_SHA
from experiments.sera.sentence_ledger_v06 import sentences

ROLES={"openables":["vane_watch","mara_notebook"],
       "documents":["mara_notebook"]}


class MaraMultifacetLabControl(unittest.TestCase):
    def setUp(self):
        self.prose=prepare()["prose"]
        self.world=entry_state()
        self.source=sentences(self.prose)
        self.assertEqual(len(self.source),28)
        self.assertEqual(prose_hash(self.prose),EXPECTED_SHA)

    def event(self,number,kind,actor,obj,evidence,payload,sweep_quote=None):
        start=self.prose.index(evidence)
        s=next(s for s in self.source
               if s["start"]<=start and start+len(evidence)<=s["end"])
        # Test-only handwritten *source-bound example*. Independent sweep
        # events are likewise mock, not qualified provider evidence.
        sweep_quote=sweep_quote or evidence
        position=self.prose.index(sweep_quote,s["start"],s["end"])
        return (
            {
                "event_id":"fixture-"+str(number),"type":kind,
                "actor_id":actor,"object_id":obj,"sentence_id":s["id"],
                "evidence":{"start":start,"end":start+len(evidence),
                            "quote":evidence},
                "payload":payload,
            },
            {
                "event_id":"blind-example-"+str(number),
                "sentence_id":s["id"],
                "kind":("OPEN" if kind=="SET_OPENABLE" and
                        payload["next"]=="OPEN" else
                        {"OBSERVE_OPENABLE":"OBSERVE",
                         "SET_OPENABLE":"CLOSE",
                         "APPEND_DOCUMENT_ENTRY":"WRITE"}[kind]),
                "effect":"DOCUMENT" if kind=="APPEND_DOCUMENT_ENTRY" else
                          "OBJECT",
                "epistemic":"OBSERVED_ACTION",
                "entity_refs":[actor,obj],
                "start":position,"end":position+len(sweep_quote),
                "quote":sweep_quote,
            },
        )

    def controls(self):
        pairs=[
            self.event(1,"OBSERVE_OPENABLE","vane","vane_watch",
                 "pocket watch open in his palm",
                 {"expected":"UNKNOWN","observed":"OPEN"}),
            self.event(2,"SET_OPENABLE","vane","vane_watch",
                 "Vane closed the case with his thumb",
                 {"expected":"OPEN","next":"CLOSED"}),
            self.event(3,"SET_OPENABLE","mara","mara_notebook",
                 "Mara opened her notebook",
                 {"expected":"UNKNOWN","next":"OPEN"}),
            self.event(4,"APPEND_DOCUMENT_ENTRY","mara","mara_notebook",
                 "Archive telegram: arrival recorded at 02:10.",
                 {"expected_append_count":0,
                  "text":"Archive telegram: arrival recorded at 02:10."},
                 sweep_quote="Mara opened her notebook and wrote: “Archive telegram: arrival recorded at 02:10."),
        ]
        proposals=[p for p,_ in pairs]
        report={
            "source_prose_sha256":prose_hash(self.prose),
            "canonical_commit_authorized":False,
            "world_state_writes":0,
            "candidate_events":[p for _,p in pairs],
        }
        return proposals,report

    def run_preview(self,*,changes=None,report_changes=None,roles=None):
        operations,report=self.controls()
        if changes: changes(operations)
        if report_changes: report_changes(report)
        return preview(prose=self.prose,world=self.world,
                       registry=ROLES if roles is None else roles,
                       candidates=operations,extraction_report=report)

    def test_watch_and_notebook_dual_capabilities_replay_without_world_writes(self):
        before=deepcopy(self.world)
        result=self.run_preview()
        self.assertEqual(result["status"],"TYPED_MULTIFACET_SIMULATED_NONCANONICAL")
        data=result["multifacet_preview"]
        self.assertEqual(data["event_count"],4)
        self.assertEqual(data["facets"]["vane_watch"]["openables"]["position"],
                         "CLOSED")
        self.assertEqual(data["facets"]["mara_notebook"]["openables"]["position"],
                         "OPEN")
        self.assertIs(data["facets"]["mara_notebook"]["openables"]
                      ["baseline_observed"], False)
        self.assertEqual(
            data["facets"]["mara_notebook"]["documents"]["observed_appends"][0]["text"],
            "Archive telegram: arrival recorded at 02:10.")
        self.assertTrue(all(x["action_minute"] is None for x in data["receipts"]))
        self.assertEqual(before,self.world)
        self.assertEqual(result,self.run_preview())
        self.assertEqual(result["world_db_writes"],0)
        self.assertFalse(result["canonical_commit_authorized"])

    def test_explicit_open_cannot_be_silently_recast_as_observation(self):
        # An action ("opened") must remain a source-backed SET from
        # an UNKNOWN prior state; model can't drop the actual movement.
        def corrupt(proposals):
            proposals[2]["type"]="OBSERVE_OPENABLE"
            proposals[2]["payload"]={"expected":"UNKNOWN",
                                     "observed":"OPEN"}
        with self.assertRaisesRegex(
            CoverageError,"V054_NOT_BACKED_BY_INDEPENDENT_SOURCE_EVENT"):
            self.run_preview(changes=corrupt)
        def invented_baseline(proposals):
            proposals[2]["payload"]["expected"]="CLOSED"
        with self.assertRaisesRegex(
            CoverageError,"V054_OPENABLE_COMPARE_AND_SWAP_INVALID"):
            self.run_preview(changes=invented_baseline)

    def test_missing_model_sweep_event_blocks_notebook_open(self):
        def change(report):
            report["candidate_events"]=[e for e in report["candidate_events"]
                                        if e["event_id"]!="blind-example-3"]
        with self.assertRaisesRegex(
            CoverageError,"V054_NOT_BACKED_BY_INDEPENDENT_SOURCE_EVENT"):
            self.run_preview(report_changes=change)

    def test_invented_document_line_and_forged_physical_identity_fail(self):
        def corrupt(operations):
            operations[-1]["evidence"]["quote"]="The train definitely arrived"
        with self.assertRaisesRegex(CoverageError,"V054_SOURCE_SPAN_OR_ORDER_INVALID"):
            self.run_preview(changes=corrupt)
        def corrupt_ref(operations):
            operations[2]["object_id"]="new:ghost_notebook"
        with self.assertRaisesRegex(CoverageError,"V054_UNREGISTERED_OBJECT_CAPABILITY"):
            self.run_preview(changes=corrupt_ref)

    def test_openable_facet_must_be_observed_before_cas_change(self):
        def change(operations):
            operations.pop(0)
        with self.assertRaisesRegex(CoverageError,"V054_OPENABLE_COMPARE_AND_SWAP_INVALID"):
            self.run_preview(changes=change)

    def test_open_evidence_cannot_authorize_closing_watch_case(self):
        def reverse(report):
            event=next(e for e in report["candidate_events"]
                       if e["event_id"]=="blind-example-2")
            event["kind"]="OPEN"
        with self.assertRaisesRegex(
            CoverageError,"V054_NOT_BACKED_BY_INDEPENDENT_SOURCE_EVENT"):
            self.run_preview(report_changes=reverse)

    def test_multi_facet_roles_are_explicit_not_assumed(self):
        with self.assertRaisesRegex(CoverageError,"V054_MULTIFACET_REQUIRES_SHARED_OBJECT"):
            self.run_preview(roles={
                "openables":["vane_watch"],"documents":["mara_notebook"]})
        def change(operations):
            operations[-1]["payload"]["expected_append_count"]=42
        with self.assertRaisesRegex(
            CoverageError,"V054_DOCUMENT_APPEND_COMPARE_AND_SWAP_INVALID"):
            self.run_preview(changes=change)


if __name__=="__main__":
    unittest.main()
