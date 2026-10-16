"""v0.24 pure spatial movement: sourced routes, chronology, carried objects."""
from copy import deepcopy
import unittest

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.spatial_preview_v024 import preview
from experiments.sera.tests.test_world_state_v02 import base
from experiments.sera.world_state_v02 import entity_template, validate
from experiments.sera.temporal_domains_v05 import KEYS

TEXT = "Mara walked to archive. Mara returned to station."
SCENE = "source-bound-spatial-scene"
WINDOW = {"scene_key": SCENE, "entry_revision": 0,
          "earliest_minute": 135, "latest_minute": 175}
ROUTES = {"station->archive": 10, "archive->station": 10}


def extracted(source=TEXT):
    result = []
    for idx, (src, text) in enumerate((
        ("m1", "Mara walked to archive"),
        ("m2", "Mara returned to station"),
    )):
        start = source.index(text)
        result.append({
            "event_id": src, "sentence_id": f"s{idx+1:03d}",
            "kind": "MOVE", "effect": "WORLD",
            "epistemic": "OBSERVED_ACTION",
            "entity_refs": ["mara"],
            "start": start, "end": start + len(text),
            "quote": text, "reason": "synthetic original source binding",
        })
    return {"source_prose_sha256": prose_hash(source),
            "candidate_events": result}


def event(ident, ordinal, dest, *, exact=None):
    return {"event_id": ident, "ordinal": ordinal, "actor_id": "mara",
            "kind": "MOVEMENT", "to_location": dest,
            "earliest_minute": None, "latest_minute": None,
            "exact_minute": exact, "depends_on": []}


def case(world, *, events=None, routes=None, window=None):
    return {"entry": deepcopy(world), "scene_key": SCENE,
            "scene_window": window or dict(WINDOW),
            "events": events or [event("m1", 1, "archive"),
                                 event("m2", 2, "station")],
            "travel_minutes": ROUTES if routes is None else routes}


def compute(*, world=None, report=None, temporal=None, prose=TEXT):
    state = world or base()
    return preview(prose=prose, world=state,
                   extraction_report=report or extracted(prose),
                   temporal_case=temporal or case(state))


class SpatialSourcePreviewV024Tests(unittest.TestCase):
    def test_two_real_source_bound_moves_round_trip_with_carried_items(self):
        world = base()
        original = deepcopy(world)
        result = compute(world=world)
        self.assertEqual(world, original)
        self.assertEqual(result["movement_count"], 2)
        self.assertEqual(result["status"], "SPATIAL_ROUTE_FEASIBLE_NONCANONICAL")
        self.assertEqual(result["temporal_domains"]["status"],
                         "FEASIBLE_NOT_AUTHORIZED")
        self.assertIsNone(result["temporal_domains"]["domains"][0]
                          ["narrative_exact_minute"])
        self.assertFalse(result["observed_narrative_arrival_time_invented"])
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(result["world_db_writes"], 0)
        move = result["transitions"][0]
        self.assertEqual((move["from_location"], move["to_location"]),
                         ("station", "archive"))
        self.assertIn("mara_notebook", move["co_moving_registered_items"])
        self.assertIn("mara_coat", move["co_moving_registered_items"])
        snapshot = result["isolated_preview_state"]
        self.assertEqual(snapshot["entities"]["mara"]["location"], "station")
        self.assertEqual(snapshot["entities"]["mara_notebook"]["location"],
                         "station")
        self.assertEqual(snapshot["entities"]["vane_watch"]["location"],
                         "station")

    def test_single_move_requires_only_one_source_event(self):
        source = "Mara walked to archive."
        world = base()
        report = {"source_prose_sha256": prose_hash(source),
                  "candidate_events": [{
                      "event_id": "m1", "sentence_id": "s001",
                      "kind": "MOVE", "effect": "WORLD",
                      "epistemic": "OBSERVED_ACTION",
                      "entity_refs": ["mara"], "start": 0, "end": 22,
                      "quote": source[:22],
                  }]}
        temporal = case(world, events=[event("m1", 1, "archive")])
        result = compute(world=world, report=report,
                         temporal=temporal, prose=source)
        self.assertEqual(result["movement_count"], 1)
        self.assertEqual(result["isolated_preview_state"]
                         ["entities"]["mara"]["location"], "archive")
        self.assertEqual(result["isolated_preview_state"]
                         ["entities"]["mara_notebook"]["location"], "archive")

    def test_too_fast_arrival_is_rejected_without_synthetic_clock(self):
        world = base()
        temporal = case(world, events=[
            event("m1", 1, "archive", exact=139),
            event("m2", 2, "station"),
        ])
        with self.assertRaisesRegex(
            CoverageError, "TIME_EVENT_INFEASIBLE:m1"
        ):
            compute(world=world, temporal=temporal)

    def test_nested_belongings_must_not_be_left_behind_by_partial_reducer(self):
        world = base()
        world["entities"]["sealed_letter"] = entity_template(
            "sealed_letter", "OBJECT", "station",
            parent_id="mara_notebook",
        )
        validate(world)
        original = deepcopy(world)
        with self.assertRaisesRegex(
            CoverageError, "V024_NESTED_CARRIED_GRAPH_UNQUALIFIED"
        ):
            compute(world=world)
        self.assertEqual(world, original)

    def test_missing_unknown_route_rejected(self):
        world = base()
        with self.assertRaisesRegex(CoverageError, "TIME_ROUTE_UNKNOWN"):
            compute(world=world, temporal=case(world, routes={}))

    def test_destination_cannot_be_assigned_from_model_if_not_in_prose(self):
        world = base()
        timed = case(world)
        timed["events"][0]["to_location"] = "station"
        with self.assertRaises(CoverageError):
            compute(world=world, temporal=timed)

    def test_registered_but_unmentioned_destination_cannot_be_inferred(self):
        world = base()
        timed = case(world)
        # "station" exists in world but not in the first move source.
        timed["events"][0]["to_location"] = "station"
        timed["events"][1]["to_location"] = "archive"
        with self.assertRaisesRegex(CoverageError,
                                    "TIME_MOVEMENT_DESTINATION_INVALID"):
            compute(world=world, temporal=timed)

    def test_reported_claim_does_not_become_physical_move(self):
        result = extracted()
        result["candidate_events"][0]["epistemic"] = "REPORTED_CLAIM"
        with self.assertRaisesRegex(
            CoverageError, "V024_UNTRUSTED_MOVEMENT_ACTOR_OR_EPISTEMIC"
        ):
            compute(report=result)

    def test_actor_not_source_bound_blocks_move(self):
        report = extracted()
        report["candidate_events"][0]["entity_refs"] = ["vane"]
        with self.assertRaisesRegex(
            CoverageError, "V024_UNTRUSTED_MOVEMENT_ACTOR_OR_EPISTEMIC"
        ):
            compute(report=report)

    def test_tampered_word_quote_and_old_world_block(self):
        report = extracted()
        report["candidate_events"][0]["quote"] = "Ari walked to archive"
        with self.assertRaisesRegex(
            CoverageError, "V024_MOVEMENT_SOURCE_QUOTE_INVALID"
        ):
            compute(report=report)
        world = base()
        stale = case(world)
        stale["entry"]["revision"] += 1
        with self.assertRaisesRegex(
            CoverageError, "V024_UNTRUSTED_TEMPORAL_WORLD"
        ):
            compute(world=world, temporal=stale)

    def test_missing_source_move_or_out_of_order_temporal_moves_fail(self):
        result = extracted()
        result["candidate_events"].pop()
        with self.assertRaisesRegex(
            CoverageError, "V024_MOVEMENT_EVIDENCE_COVERAGE"
        ):
            compute(report=result)
        world = base()
        t = case(world, events=[
            event("m2", 1, "archive"), event("m1", 2, "station"),
        ])
        with self.assertRaisesRegex(
            CoverageError, "V024_SOURCE_CHRONOLOGY_CONFLICT"
        ):
            compute(temporal=t)

    def test_absent_source_effect_cannot_grant_movement(self):
        result = extracted()
        result["candidate_events"][0]["effect"] = "NONE"
        with self.assertRaisesRegex(
            CoverageError, "V024_MOVE_WITHOUT_OBJECTIVE_EFFECT"
        ):
            compute(report=result)


if __name__ == "__main__":
    unittest.main()
