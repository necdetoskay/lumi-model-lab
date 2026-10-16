"""v0.27 ordered movement, custody, facets, knowledge: regression and safety."""
from __future__ import annotations

from copy import deepcopy
import unittest

from experiments.sera.artifact_scene_checker_v021 import digest
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.full_scene_qualification_v023 import qualify
from experiments.sera.ordered_facet_preview_v027 import preview
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.tests.test_relation_knowledge_v025 import ALIASES, FACTS
from experiments.sera.tests.test_world_state_v02 import base

SCENE = "v027-generic-mixed-causal-scene"
SOURCE = (
    "Vane walked to archive. "
    "Mara walked to archive. "
    "Vane handed the watch to Mara. "
    "Mara observed the watch open. "
    "Mara closed the watch. "
    "Mara wrote Checked in the notebook. "
    "Mara learned the station clock stopped."
)
KINDS = ("MOVE", "MOVE", "TRANSFER", "OBSERVE", "CLOSE", "WRITE",
         "KNOWLEDGE_UPDATE")
EFFECTS = ("WORLD", "WORLD", "OBJECT", "NONE", "OBJECT", "DOCUMENT",
           "CHARACTER_KNOWLEDGE")
NAMES = ("vane", "mara", "vane", "mara", "mara", "mara", "mara")


def material():
    world = base()
    rows = []
    t = []
    parts = SOURCE.split(". ")
    for n, part in enumerate(parts):
        quote = part.rstrip(".")
        at = SOURCE.index(quote)
        sid = next(x["id"] for x in sentences(SOURCE)
                   if x["start"] <= at and
                   at+len(quote) <= x["end"])
        refs = (
            [NAMES[n], "vane_watch"] if n in (3,4)
            else ["mara", "mara_notebook"] if n == 5
            else ["vane", "mara", "vane_watch"] if n == 2
            else [NAMES[n]]
        )
        ident = f"source-{n}"
        rows.append({
            "event_id": ident, "sentence_id": sid,
            "kind": KINDS[n], "epistemic": "OBSERVED_ACTION",
            "effect": EFFECTS[n], "entity_refs": refs,
            "start": at, "end": at+len(quote), "quote": quote,
            "reason": "Synthetic blind original prose binding",
        })
        t.append({
            "event_id": ident, "ordinal": n+1,
            "actor_id": NAMES[n], "kind": (
                "MOVEMENT" if n < 2 else "ACTION"
            ),
            "to_location": "archive" if n < 2 else None,
            "earliest_minute": None, "latest_minute": None,
            "exact_minute": None, "depends_on": [],
        })
    report = {
        "schema": "sera.blind-sweep-bound.v0.10",
        "source_prose_sha256": prose_hash(SOURCE),
        "sentences_accounted_for": len(sentences(SOURCE)),
        "candidate_events": rows, "findings": [],
        "canonical_commit_authorized": False, "world_state_writes": 0,
    }
    temporal = {
        "entry": deepcopy(world), "scene_key": SCENE,
        "scene_window": {
            "scene_key": SCENE,
            "entry_revision": world["revision"],
            "earliest_minute": 135, "latest_minute": 175,
        },
        "events": t, "travel_minutes": {"station->archive": 10},
    }
    relation = {
        "entry": deepcopy(world), "policy_id": "synthetic-trusted-v027",
        "registered_aliases": deepcopy(ALIASES),
        "verified_fact_registry": deepcopy(FACTS),
        "transitions": [
            {"source_event_id": "source-2",
             "operation": "TRANSFER_HOLDER", "object_id": "vane_watch",
             "from_id": "vane", "to_id": "mara", "fact_id": None},
            {"source_event_id": "source-6",
             "operation": "LEARN_FACT", "object_id": None,
             "from_id": None, "to_id": "mara",
             "fact_id": "station_clock_stopped"},
        ],
    }
    def typed(i, kind, span, object_id, payload):
        at = SOURCE.index(span)
        return {
            "event_id": f"typed-{i}", "type": kind,
            "actor_id": "mara", "object_id": object_id,
            "sentence_id": rows[i]["sentence_id"],
            "evidence": {
                "start": at, "end": at+len(span), "quote": span,
            },
            "payload": payload,
        }
    candidates = [
        typed(3, "OBSERVE_OPENABLE", "watch open", "vane_watch",
              {"expected": "UNKNOWN", "observed": "OPEN"}),
        typed(4, "SET_OPENABLE", "closed the watch", "vane_watch",
              {"expected": "OPEN", "next": "CLOSED"}),
        typed(5, "APPEND_DOCUMENT_ENTRY", "Checked", "mara_notebook",
              {"expected_append_count": 0, "text": "Checked"}),
    ]
    registry = {
        "openables": ["vane_watch"], "documents": ["mara_notebook"],
    }
    return world, report, temporal, relation, candidates, registry


def direct(*, mutate=None):
    world, report, temporal, relation, typed, roles = material()
    if mutate is not None:
        mutate(world, report, temporal, relation, typed, roles)
    return preview(
        prose=SOURCE, world=world, extraction_report=report,
        temporal_case=temporal, relation_case=relation,
        typed_candidates=typed, typed_registry=roles,
    )


def gate(*, mutate=None, deferred=True):
    world, report, temporal, relation, typed, roles = material()
    if mutate is not None:
        mutate(world, report, temporal, relation, typed, roles)
    bundle = {
        "schema": "sera.recheck-evidence-bundle.v0.21",
        "prose_sha256": prose_hash(SOURCE),
        "world_sha256": digest(world),
        "extraction_report": report,
        "temporal_case": temporal, "relation_case": relation,
        "typed_candidates": typed, "typed_registry": roles,
    }
    projection = {
        "schema": "sera.event-candidate-repair.v0.19",
        "prose_sha256": prose_hash(SOURCE),
        "original_report_sha256": digest(report),
        "canonical_commit_authorized": False, "world_db_writes": 0,
        "remaining_semantic_task_codes": [],
        "unsupported_semantic_tasks": [], "temporal_failure": None,
    }
    assessment = {
        "schema": "sera.typed-aspect-candidate-recovery.v0.20",
        "status": ("DEFERRED_TO_V027_ORDERED_FACETS_NONCANONICAL"
                   if deferred else "TYPED_FACETS_SIMULATED_NONCANONICAL"),
        "ordered_facet_scope_requires_full_gate": deferred,
        "prose_sha256": prose_hash(SOURCE), "world_sha256": digest(world),
        "original_candidates_sha256": digest(typed),
        "blocker_codes": [], "canonical_commit_authorized": False,
        "world_db_writes": 0,
    }
    return qualify(prose=SOURCE, world=world, bundle=bundle,
                   projection=projection, typed=assessment)


class OrderedFacetsV027Tests(unittest.TestCase):
    def test_movement_transfer_facet_and_fact_use_same_current_world(self):
        world,report,temporal,relation,typed,roles = material()
        entry = deepcopy(world)
        result = preview(
            prose=SOURCE, world=world, extraction_report=report,
            temporal_case=temporal, relation_case=relation,
            typed_candidates=typed, typed_registry=roles,
        )
        self.assertEqual(world, entry)
        self.assertEqual(result["status"],
                         "ORDERED_FACETS_AND_WORLD_FEASIBLE_NONCANONICAL")
        self.assertEqual(len(result["steps"]), 7)
        self.assertEqual([s["kind"] for s in result["steps"]], [
            "MOVE", "MOVE", "TRANSFER_HOLDER", "OBSERVE_OPENABLE",
            "SET_OPENABLE", "APPEND_DOCUMENT_ENTRY", "LEARN_FACT",
        ])
        self.assertEqual(result["facets"]["vane_watch"]["position"], "CLOSED")
        self.assertEqual(len(
            result["facets"]["mara_notebook"]["observed_appends"]), 1)
        self.assertEqual(result["facets"]["mara_notebook"][
            "observed_appends"][0]["text"], "Checked")
        entities = result["isolated_preview_state"]["entities"]
        self.assertEqual(entities["vane_watch"]["holder"], "mara")
        self.assertEqual(entities["vane_watch"]["owner"], "vane")
        self.assertEqual(entities["vane_watch"]["location"], "archive")
        self.assertEqual(entities["mara_notebook"]["location"], "archive")
        self.assertIn("station_clock_stopped", entities["mara"]["knowledge"])
        for prior, next_step in zip(result["steps"], result["steps"][1:]):
            self.assertEqual(prior["after_world_sha256"],
                             next_step["before_world_sha256"])
            self.assertEqual(prior["after_facets_sha256"],
                             next_step["before_facets_sha256"])
        self.assertEqual(result["covered_facet_ids"],
                         ["typed-3", "typed-4", "typed-5"])
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(result["world_db_writes"], 0)

    def test_full_scene_gate_no_longer_blocks_successful_mixed_families(self):
        out = gate()
        self.assertEqual(out["status"],
                         "FULL_SCENE_COVERAGE_CANDIDATE_NONCANONICAL")
        self.assertEqual(out["defects"], [])
        self.assertEqual(len(out["ordered_facet_preview"]["steps"]), 7)
        self.assertFalse(out["semantic_truth_proven"])

    def test_object_used_before_reaching_actor_is_rejected(self):
        def bad(w,r,t,rel,c,roles):
            # Mara moves only at the END; she cannot access Vane's watch
            # while it is still in his possession or other location.
            t["events"][1]["actor_id"] = "vane"
        with self.assertRaises(CoverageError):
            direct(mutate=bad)

    def test_wrong_expected_openable_state_cannot_close(self):
        def bad(w,r,t,rel,c,roles):
            c[1]["payload"]["expected"] = "CLOSED"
        with self.assertRaisesRegex(
            CoverageError, "V027_OPENABLE_TRANSITION_CAS_INVALID"
        ):
            direct(mutate=bad)
        result = gate(mutate=bad)
        self.assertIn("ORDERED_FACET_CAUSAL_REPLAY_UNQUALIFIED",
                      [d["code"] for d in result["defects"]])
        self.assertEqual(result["world_db_writes"], 0)

    def test_missing_source_observation_or_extra_facet_is_not_accepted(self):
        def missing(w,r,t,rel,c,roles):
            c.pop(0)
        with self.assertRaisesRegex(
            CoverageError, "V027_FACET_SOURCE_ONE_TO_ONE_INVALID"
        ):
            direct(mutate=missing)
        def extra(w,r,t,rel,c,roles):
            c.append(deepcopy(c[-1]))
        with self.assertRaisesRegex(
            CoverageError, "V027_TYPED_EVENT_IDS_NOT_UNIQUE"
        ):
            direct(mutate=extra)

    def test_document_append_cannot_be_fabricated_or_wrong_cas(self):
        def forged(w,r,t,rel,c,roles):
            c[-1]["payload"]["text"] = "Fabricated train fact"
        with self.assertRaisesRegex(
            CoverageError, "V027_DOCUMENT_APPEND_CAS_INVALID"
        ):
            direct(mutate=forged)
        def duplicate(w,r,t,rel,c,roles):
            c[-1]["payload"]["expected_append_count"] = 1
        with self.assertRaisesRegex(
            CoverageError, "V027_DOCUMENT_APPEND_CAS_INVALID"
        ):
            direct(mutate=duplicate)

    def test_document_or_physical_state_cannot_be_promoted_from_none_effect(self):
        def fake_write(w,r,t,rel,c,roles):
            r["candidate_events"][5]["effect"] = "NONE"
        with self.assertRaisesRegex(
            CoverageError, "V027_FACET_INDEPENDENT_SWEEP_MISMATCH"
        ):
            direct(mutate=fake_write)
        def fake_closed(w,r,t,rel,c,roles):
            r["candidate_events"][4]["effect"] = "NONE"
        with self.assertRaisesRegex(
            CoverageError, "V027_FACET_INDEPENDENT_SWEEP_MISMATCH"
        ):
            direct(mutate=fake_closed)

    def test_duplicate_or_colliding_facet_receipt_ids_fail_closed(self):
        def duplicate(w,r,t,rel,c,roles):
            c[1]["event_id"] = c[0]["event_id"]
        with self.assertRaisesRegex(
            CoverageError, "V027_TYPED_EVENT_IDS_NOT_UNIQUE"
        ):
            direct(mutate=duplicate)
        def colliding(w,r,t,rel,c,roles):
            c[0]["event_id"] = "source-3"
        with self.assertRaisesRegex(
            CoverageError, "V027_TYPED_EVENT_IDS_NOT_UNIQUE"
        ):
            direct(mutate=colliding)

    def test_unrelated_location_policy_or_forged_actor_blocks_replay(self):
        def lost_route(w,r,t,rel,c,roles):
            t["travel_minutes"] = {}
        with self.assertRaisesRegex(CoverageError, "TIME_ROUTE_UNKNOWN"):
            direct(mutate=lost_route)
        def forged_actor(w,r,t,rel,c,roles):
            c[0]["actor_id"] = "vane"
        with self.assertRaisesRegex(
            CoverageError, "V027_ACTION_TIMELINE_ACTOR_INVALID"
        ):
            direct(mutate=forged_actor)

    def test_unverified_fact_and_reported_handoff_are_not_promoted(self):
        def rumor(w,r,t,rel,c,roles):
            rel["verified_fact_registry"]["station_clock_stopped"][
                "truth_status"] = "RUMORED"
        with self.assertRaisesRegex(
            CoverageError, "V025_FACT_UNVERIFIED_OR_UNGROUNDED"
        ):
            direct(mutate=rumor)
        def reported(w,r,t,rel,c,roles):
            r["candidate_events"][2]["epistemic"] = "REPORTED_CLAIM"
        with self.assertRaisesRegex(
            CoverageError, "V027_SOURCE_ORDER_OR_PROOF_INVALID"
        ):
            direct(mutate=reported)

    def test_true_facet_receipts_are_noncanonical_only(self):
        out = direct()
        self.assertEqual(len(out["facet_receipt_head_sha256"]), 64)
        self.assertTrue(all(len(s["facet_receipt_head_sha256"]) == 64
                            for s in out["steps"]))
        self.assertFalse(out["all_state_families_qualified"])
        self.assertFalse(out["semantic_truth_proven"])
        self.assertFalse(out["requires_manual_intervention"])


if __name__ == "__main__":
    unittest.main()
