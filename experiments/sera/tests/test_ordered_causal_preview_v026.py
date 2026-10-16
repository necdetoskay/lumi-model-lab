"""v0.26 ordered causal replay: movement → transfer → verified learning."""
from copy import deepcopy
import unittest

from experiments.sera.artifact_scene_checker_v021 import digest
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.full_scene_qualification_v023 import qualify
from experiments.sera.ordered_causal_preview_v026 import preview
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.tests.test_world_state_v02 import base
from experiments.sera.tests.test_relation_knowledge_v025 import FACTS, ALIASES

SCENE = "mixed-relations-spatial-v026"
SOURCE = (
    "Vane walked to archive. "
    "Mara walked to archive. "
    "Vane handed the watch to Mara. "
    "Mara learned the station clock stopped."
)
EARLY_HANDOFF = (
    "Vane handed the watch to Mara. "
    "Mara walked to archive. "
    "Mara learned the station clock stopped."
)
IMPOSSIBLE_HANDOFF = (
    "Vane walked to archive. "
    "Vane handed the watch to Mara. "
    "Mara walked to archive."
)


def make_events(prose):
    rows = []
    names = []
    for part in prose.split(". "):
        quote = part.rstrip(".")
        start = prose.index(quote)
        if "walked" in quote:
            actor = "vane" if quote.startswith("Vane") else "mara"
            rows.append({
                "event_id": f"move-{len(rows)}", "kind": "MOVE",
                "effect": "WORLD", "epistemic": "OBSERVED_ACTION",
                "entity_refs": [actor],
                "start": start, "end": start + len(quote),
                "quote": quote,
            })
            names.append(("MOVEMENT", actor))
        elif "handed" in quote:
            rows.append({
                "event_id": "handoff", "kind": "TRANSFER",
                "effect": "OBJECT", "epistemic": "OBSERVED_ACTION",
                "entity_refs": ["vane", "mara", "vane_watch"],
                "start": start, "end": start + len(quote),
                "quote": quote,
            })
            names.append(("ACTION", "vane"))
        else:
            rows.append({
                "event_id": "learn", "kind": "KNOWLEDGE_UPDATE",
                "effect": "CHARACTER_KNOWLEDGE",
                "epistemic": "OBSERVED_ACTION",
                "entity_refs": ["mara"],
                "start": start, "end": start + len(quote),
                "quote": quote,
            })
            names.append(("ACTION", "mara"))
    ledger = sentences(prose)
    for row in rows:
        row["sentence_id"] = next(s["id"] for s in ledger
            if s["start"] <= row["start"] and row["end"] <= s["end"])
    return rows, names


def inputs(prose=SOURCE):
    world = base()
    rows, kinds = make_events(prose)
    report = {
        "schema": "sera.blind-sweep-bound.v0.10",
        "source_prose_sha256": prose_hash(prose),
        "candidate_events": rows,
        "sentences_accounted_for": len(sentences(prose)),
        "findings": [], "canonical_commit_authorized": False,
        "world_state_writes": 0,
    }
    timeline = {
        "entry": deepcopy(world), "scene_key": SCENE,
        "scene_window": {
            "scene_key": SCENE, "entry_revision": world["revision"],
            "earliest_minute": 135, "latest_minute": 175,
        },
        "events": [
            {
                "event_id": e["event_id"], "ordinal": i+1,
                "actor_id": kinds[i][1], "kind": kinds[i][0],
                "to_location": "archive" if kinds[i][0] == "MOVEMENT"
                               else None,
                "earliest_minute": None, "latest_minute": None,
                "exact_minute": None, "depends_on": [],
            }
            for i,e in enumerate(rows)
        ],
        "travel_minutes": {"station->archive": 10},
    }
    specs = []
    for e in rows:
        if e["kind"] == "TRANSFER":
            specs.append({
                "source_event_id": e["event_id"],
                "operation": "TRANSFER_HOLDER", "object_id": "vane_watch",
                "from_id": "vane", "to_id": "mara", "fact_id": None,
            })
        if e["kind"] == "KNOWLEDGE_UPDATE":
            specs.append({
                "source_event_id": e["event_id"],
                "operation": "LEARN_FACT", "object_id": None,
                "from_id": None, "to_id": "mara",
                "fact_id": "station_clock_stopped",
            })
    relation = {
        "entry": deepcopy(world), "policy_id": "trusted-identity-facts-v1",
        "registered_aliases": deepcopy(ALIASES),
        "verified_fact_registry": deepcopy(FACTS),
        "transitions": specs,
    }
    return world, report, timeline, relation


def run(prose=SOURCE, *, mutate=None):
    world, report, timeline, relation = inputs(prose)
    if mutate:
        mutate(world, report, timeline, relation)
    return preview(
        prose=prose, world=world, extraction_report=report,
        temporal_case=timeline, relation_case=relation,
        typed_candidates=[],
    )


def full_gate(prose=SOURCE, *, mutate=None, typed_candidates=None):
    world, report, timeline, relation = inputs(prose)
    if mutate:
        mutate(world, report, timeline, relation)
    facets = [] if typed_candidates is None else typed_candidates
    bundle = {
        "schema": "sera.recheck-evidence-bundle.v0.21",
        "prose_sha256": prose_hash(prose), "world_sha256": digest(world),
        "extraction_report": report,
        "relation_case": relation, "temporal_case": timeline,
        "typed_candidates": facets, "typed_registry": {
            "openables": [], "documents": [],
        },
    }
    projection = {
        "schema": "sera.event-candidate-repair.v0.19",
        "prose_sha256": prose_hash(prose),
        "original_report_sha256": digest(report),
        "canonical_commit_authorized": False, "world_db_writes": 0,
        "remaining_semantic_task_codes": [],
        "unsupported_semantic_tasks": [], "temporal_failure": None,
    }
    typed = {
        "schema": "sera.typed-aspect-candidate-recovery.v0.20",
        "prose_sha256": prose_hash(prose),
        "world_sha256": digest(world),
        "original_candidates_sha256": digest(facets),
        "status": "NO_APPLICABLE_TYPED_FACETS_NONCANONICAL" if not facets
                  else "TYPED_FACETS_SIMULATED_NONCANONICAL",
        "empty_facet_scope_requires_full_gate": not facets,
        "canonical_commit_authorized": False,
        "world_db_writes": 0, "blocker_codes": [],
    }
    return qualify(prose=prose, world=world, bundle=bundle,
                   projection=projection, typed=typed)


class OrderedCrossFamilyV026Tests(unittest.TestCase):
    def test_actor_relocation_before_handoff_and_learning_uses_evolving_world(self):
        world, report, timeline, relation = inputs()
        original = deepcopy(world)
        result = preview(
            prose=SOURCE, world=world, extraction_report=report,
            temporal_case=timeline, relation_case=relation,
            typed_candidates=[],
        )
        self.assertEqual(world, original)
        self.assertEqual(result["status"],
                         "ORDERED_CAUSAL_PREVIEW_FEASIBLE_NONCANONICAL")
        self.assertEqual(len(result["steps"]), 4)
        self.assertEqual([s["kind"] for s in result["steps"]], [
            "MOVE", "MOVE", "TRANSFER_HOLDER", "LEARN_FACT",
        ])
        for a, b in zip(result["steps"], result["steps"][1:]):
            self.assertEqual(a["after_world_sha256"],
                             b["before_world_sha256"])
        snap = result["isolated_preview_state"]["entities"]
        self.assertEqual(snap["vane"]["location"], "archive")
        self.assertEqual(snap["mara"]["location"], "archive")
        self.assertEqual(snap["vane_watch"]["location"], "archive")
        self.assertEqual(snap["vane_watch"]["holder"], "mara")
        self.assertEqual(snap["vane_watch"]["owner"], "vane")
        self.assertIn("station_clock_stopped", snap["mara"]["knowledge"])
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(result["world_db_writes"], 0)

    def test_handoff_then_move_makes_new_receiver_carry_item(self):
        result = run(EARLY_HANDOFF)
        entities = result["isolated_preview_state"]["entities"]
        self.assertEqual(entities["mara"]["location"], "archive")
        self.assertEqual(entities["vane"]["location"], "station")
        self.assertEqual(entities["vane_watch"]["location"], "archive")
        self.assertEqual(entities["vane_watch"]["holder"], "mara")
        self.assertEqual(entities["vane_watch"]["owner"], "vane")

    def test_handoff_before_receiver_arrives_cannot_teleport_possession(self):
        with self.assertRaisesRegex(
            CoverageError, "V025_HOLDER_CAS_OR_COLOCATION_FAILED"
        ):
            run(IMPOSSIBLE_HANDOFF)
        result = full_gate(IMPOSSIBLE_HANDOFF)
        self.assertIn("ORDERED_CAUSAL_REPLAY_UNQUALIFIED",
                      [d["code"] for d in result["defects"]])
        self.assertIsNone(result["ordered_preview"])
        self.assertFalse(result["canonical_commit_authorized"])

    def test_global_temporal_dag_prohibits_impossible_movement(self):
        def invalid(w, r, t, rel):
            t["events"][0]["exact_minute"] = 136
        with self.assertRaisesRegex(CoverageError, "TIME_EVENT_INFEASIBLE"):
            run(mutate=invalid)

    def test_missing_registered_route_and_forged_source_never_replay(self):
        def no_route(w, r, t, rel):
            t["travel_minutes"] = {}
        with self.assertRaisesRegex(CoverageError, "TIME_ROUTE_UNKNOWN"):
            run(mutate=no_route)
        def fabricated(w, r, t, rel):
            r["candidate_events"][2]["quote"] = "fake handoff"
        with self.assertRaisesRegex(
            CoverageError, "V026_SOURCE_PROVENANCE_INVALID"
        ):
            run(mutate=fabricated)

    def test_reported_claim_and_rumor_block_objective_effects(self):
        def hearsay(w, r, t, rel):
            r["candidate_events"][2]["epistemic"] = "REPORTED_CLAIM"
        with self.assertRaisesRegex(CoverageError, "V026_SOURCE_PROVENANCE_INVALID"):
            run(mutate=hearsay)
        def rumor(w, r, t, rel):
            rel["verified_fact_registry"]["station_clock_stopped"][
                "truth_status"] = "RUMORED"
        with self.assertRaisesRegex(
            CoverageError, "V025_FACT_UNVERIFIED_OR_UNGROUNDED"
        ):
            run(mutate=rumor)

    def test_missing_relation_action_or_changed_story_order_is_rejected(self):
        def lost(w, r, t, rel):
            rel["transitions"].pop()
        with self.assertRaisesRegex(
            CoverageError, "V026_RELATION_PROPOSAL_COVERAGE"
        ):
            run(mutate=lost)
        def swapped(w, r, t, rel):
            t["events"][1], t["events"][2] = t["events"][2], t["events"][1]
        with self.assertRaisesRegex(
            CoverageError, "V026_TIMELINE_DOES_NOT_COVER_SOURCE_ORDER"
        ):
            run(mutate=swapped)

    def test_full_gate_unblocks_only_verified_joint_order_noncanonical(self):
        result = full_gate()
        self.assertEqual(result["status"],
                         "FULL_SCENE_COVERAGE_CANDIDATE_NONCANONICAL")
        self.assertEqual(result["defects"], [])
        self.assertEqual(len(result["ordered_preview"]["steps"]), 4)
        self.assertIsNone(result["spatial_preview"])
        self.assertIsNone(result["relation_preview"])
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertFalse(result["semantic_truth_proven"])

    def test_mixed_openable_facets_remain_unqualified(self):
        extra = [{
            "event_id": "invented-facet", "type": "OBSERVE_OPENABLE",
            "object_id": "vane_watch", "actor_id": "vane",
            "sentence_id": "s001",
            "evidence": {"start": 0, "end": 4, "quote": "Vane"},
            "payload": {"expected": "UNKNOWN", "observed": "OPEN"},
        }]
        with self.assertRaisesRegex(CoverageError, "V026_FACET_REPLAY_NOT_QUALIFIED"):
            world, report, timeline, relation = inputs()
            preview(prose=SOURCE, world=world, extraction_report=report,
                    temporal_case=timeline, relation_case=relation,
                    typed_candidates=extra)
        gate = full_gate(typed_candidates=extra)
        self.assertEqual(gate["status"],
                         "REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL")
        self.assertIn("CROSS_FAMILY_STATE_ORDER_UNQUALIFIED",
                      [d["code"] for d in gate["defects"]])


if __name__ == "__main__":
    unittest.main()
