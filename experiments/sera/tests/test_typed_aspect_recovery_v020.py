"""SERA v0.20 generic typed aspect recovery without model/provider calls."""
from __future__ import annotations

from copy import deepcopy
import unittest

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.typed_aspect_recovery_v020 import recover
from experiments.sera.tests.test_world_state_v013 import (
    PROSE, base, three,
)


def registry():
    return {"openables": ["vane_watch"], "documents": ["mara_notebook"]}


def run(*, events=None, world=None, typed=None, projection=None, prose=None):
    return recover(
        prose=PROSE if prose is None else prose,
        world=base() if world is None else world,
        registry=registry() if typed is None else typed,
        candidates=three() if events is None else events,
        projection=projection,
    )


def projected_source(prose, action):
    return {
        "schema": "sera.event-candidate-repair.v0.19",
        "prose_sha256": prose_hash(prose),
        "canonical_commit_authorized": False,
        "world_db_writes": 0,
        "next_automatic_action": action,
    }


class TypedAspectRecoveryV020Tests(unittest.TestCase):
    def test_generic_registered_watch_and_notebook_replay_no_canon(self):
        world = base()
        before = deepcopy(world)
        input_events = three()
        original_events = deepcopy(input_events)
        output = run(events=input_events, world=world)
        self.assertEqual(world, before)
        self.assertEqual(input_events, original_events)
        self.assertEqual(output["status"],
                         "TYPED_FACETS_SIMULATED_NONCANONICAL")
        self.assertEqual(output["candidate_count"], 3)
        self.assertEqual(output["source_bound_candidate_count"], 3)
        simulated = output["typed_preview"]
        self.assertEqual(simulated["reducer_mode"], "OFFLINE_APPROVAL_FIXTURE")
        self.assertEqual(simulated["simulated_revision"], 3)
        self.assertEqual(simulated["aspects"]["vane_watch"]["position"], "CLOSED")
        self.assertEqual(simulated["aspects"]["mara_notebook"]
                         ["preexisting_content"], "UNKNOWN")
        self.assertEqual(len(simulated["aspects"]["mara_notebook"]
                             ["observed_appends"]), 1)
        self.assertFalse(output["canonical_commit_authorized"])
        self.assertFalse(output["human_approval_required"])
        self.assertFalse(output["requires_manual_intervention"])
        self.assertEqual(output["world_db_writes"], 0)

    def test_works_with_non_mara_registered_role_ids_from_world(self):
        world = base()
        # Same world, renamed registered ids and all three source-linked
        # candidates; proves no Mara ref is a hard-coded rule in the engine.
        world["entities"]["story_watch"] = world["entities"].pop("vane_watch")
        world["entities"]["journal_object"] = world["entities"].pop("mara_notebook")
        for entry in world["entities"].values():
            if isinstance(entry, dict):
                for key in ("object_id", "ref", "id"):
                    if entry.get(key) == "vane_watch":
                        entry[key] = "story_watch"
                    elif entry.get(key) == "mara_notebook":
                        entry[key] = "journal_object"
        new_events = three()
        for item in new_events:
            item["object_id"] = ("story_watch" if item["object_id"] ==
                                 "vane_watch" else "journal_object")
        output = run(
            world=world, events=new_events,
            typed={"openables": ["story_watch"],
                   "documents": ["journal_object"]},
        )
        self.assertEqual(output["status"],
                         "TYPED_FACETS_SIMULATED_NONCANONICAL")
        self.assertEqual(output["typed_preview"]["aspects"]["story_watch"]
                         ["position"], "CLOSED")

    def test_cas_rejects_closing_unknown_before_open_baseline(self):
        output = run(events=three()[1:])
        self.assertEqual(output["status"],
                         "AUTO_REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL")
        self.assertIn("V013_OPENABLE_COMPARE_AND_SWAP_INVALID",
                      output["blocker_codes"][0])
        self.assertIsNone(output["typed_preview"])
        self.assertEqual(output["source_bound_candidate_count"], 0)
        self.assertFalse(output["canonical_commit_authorized"])

    def test_invalid_narrative_event_order_triggers_auto_replan(self):
        events = three()
        events[0], events[1] = events[1], events[0]
        result = run(events=events)
        self.assertEqual(result["next_automatic_action"],
                         "AUTO_REEXTRACT_OR_REPLAN_SCENE")
        self.assertTrue(result["blocker_codes"])
        self.assertEqual(result["world_db_writes"], 0)

    def test_fabricated_quote_is_not_used_to_change_world(self):
        items = three()
        items[1]["evidence"]["quote"] = "the spaceship arrived"
        output = run(events=items)
        self.assertIn("V013_EVENT_SOURCE_SPAN_INVALID",
                      output["blocker_codes"][0])
        self.assertIsNone(output["typed_preview"])

    def test_reported_train_cannot_be_added_as_object(self):
        items = three()
        items[1]["object_id"] = "new:train_41"
        with self.assertRaisesRegex(
            CoverageError, "V020_EVENT_UNKNOWN_ROLE"
        ):
            run(events=items)

    def test_models_cannot_smuggle_commit_flag_or_action_clock(self):
        items = three()
        items[0]["canonical_commit_authorized"] = True
        with self.assertRaisesRegex(
            CoverageError, "V020_EVENT_FIELDS_INVALID"
        ):
            run(events=items)
        items = three()
        items[1]["action_time_minute"] = 138
        with self.assertRaisesRegex(
            CoverageError, "V020_EVENT_FIELDS_INVALID"
        ):
            run(events=items)

    def test_duplicate_event_id_blocked_before_reducer(self):
        items = three()
        items[1]["event_id"] = items[0]["event_id"]
        with self.assertRaisesRegex(
            CoverageError, "V020_EVENT_ID_MISSING_OR_DUPLICATE"
        ):
            run(events=items)

    def test_spoofed_registry_or_missing_role_never_inferred(self):
        with self.assertRaisesRegex(
            CoverageError, "V020_REGISTRY_DUPLICATE_OBJECT"
        ):
            run(typed={"openables": ["vane_watch"],
                       "documents": ["vane_watch"]})
        with self.assertRaisesRegex(
            CoverageError, "V020_V013_REDUCER_ROLE_COVERAGE_MISSING"
        ):
            run(typed={"openables": ["vane_watch"], "documents": []})

    def test_unresolved_v019_scene_defect_holds_even_if_facets_simulate(self):
        source = projected_source(PROSE, "AUTO_EVENT_REEXTRACTION_OR_REPLAN")
        output = run(projection=source)
        self.assertEqual(output["status"],
                         "AUTO_REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL")
        self.assertIn("V020_V019_UPSTREAM_SCENE_DEFECTS_UNRESOLVED",
                      output["blocker_codes"])
        self.assertIsNotNone(output["typed_preview"])
        self.assertFalse(output["canonical_commit_authorized"])

    def test_structurally_clean_projection_still_does_not_authorize_commit(self):
        projection = projected_source(PROSE, "CONTINUE_FULL_SCENE_GATES")
        out = run(projection=projection)
        self.assertEqual(out["status"],
                         "TYPED_FACETS_SIMULATED_NONCANONICAL")
        self.assertEqual(out["next_automatic_action"],
                         "CONTINUE_INDEPENDENT_SCENE_QUALIFICATION")
        self.assertFalse(out["canonical_commit_authorized"])

    def test_tampered_source_fingerprint_is_rejected_before_simulation(self):
        projection = projected_source(PROSE, "CONTINUE_FULL_SCENE_GATES")
        with self.assertRaisesRegex(
            CoverageError, "V020_PROJECTION_SOURCE_OR_AUTHORITY_INVALID"
        ):
            run(projection=projection, prose=PROSE + " added untrusted words")

    def test_conflicting_role_binding_denied_without_canonical_change(self):
        items = three()
        items[1]["object_id"] = "mara_notebook"
        with self.assertRaisesRegex(
            CoverageError, "V020_EVENT_OBJECT_ROLE_CONFLICT"
        ):
            run(events=items)

    def test_empty_candidates_go_to_automatic_reextraction(self):
        out = run(events=[])
        self.assertEqual(out["next_automatic_action"],
                         "AUTO_REEXTRACT_OR_REPLAN_SCENE")
        self.assertIn("V020_NO_TYPED_EVENTS_PROPOSED", out["blocker_codes"])
        self.assertEqual(out["world_db_writes"], 0)


if __name__ == "__main__":
    unittest.main()
