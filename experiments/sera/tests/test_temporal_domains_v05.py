"""M3.5 temporal DAG/interval constraints, no invented narrative clock."""
from __future__ import annotations

from copy import deepcopy
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.temporal_domains_v05 import solve_temporal_domains
from experiments.sera.tests.test_world_state_v02 import base

SCENE = "hook_empty_platform"
WINDOW = {
    "scene_key": SCENE, "entry_revision": 0,
    "earliest_minute": 135, "latest_minute": 175,
}
ROUTES = {"station->archive": 10, "archive->station": 10}


def evt(event_id, ordinal, *, actor="mara", kind="ACTION",
        to=None, early=None, late=None, exact=None, deps=()):
    return {
        "event_id": event_id, "ordinal": ordinal,
        "actor_id": actor, "kind": kind,
        "to_location": to, "earliest_minute": early,
        "latest_minute": late, "exact_minute": exact,
        "depends_on": [{"event_id": event, "min_gap_minutes": lag}
                       for event, lag in deps],
    }


def solve(events, *, window=None, simulate=False, routes=None):
    return solve_temporal_domains(
        entry=base(), scene_key=SCENE,
        scene_window=window or WINDOW, events=events,
        travel_minutes=routes if routes is not None else ROUTES,
        simulation_schedule=simulate,
    )


class TemporalDomainsV05Tests(unittest.TestCase):
    def fail(self, code, events, **kwargs):
        with self.assertRaisesRegex(CoverageError, code):
            solve(events, **kwargs)

    def test_events_have_order_but_no_invented_absolute_clock(self):
        out = solve([
            evt("witness", 1, actor="vane", kind="TESTIMONY"),
            evt("notebook", 2, kind="ACTION",
                deps=[("witness", 0)]),
            evt("decision", 3),
        ])
        self.assertEqual(out["status"], "FEASIBLE_NOT_AUTHORIZED")
        self.assertFalse(out["production_commit_authorized"])
        self.assertFalse(out["simulation_schedule"])
        self.assertEqual([x["narrative_exact_minute"] for x in out["domains"]],
                         [None, None, None])
        self.assertEqual([x["simulation_cursor"] for x in out["domains"]],
                         [None, None, None])
        self.assertEqual(out["domains"][0]["earliest_feasible_minute"], 135)
        self.assertEqual(out["domains"][-1]["latest_feasible_minute"], 175)

    def test_explicit_simulation_is_not_authorized_narrative_time(self):
        out = solve([
            evt("seen", 1, actor="vane"),
            evt("walk", 2, kind="MOVEMENT", to="archive", actor="mara"),
            evt("read", 3, actor="mara"),
        ], simulate=True)
        self.assertEqual(
            [x["simulation_cursor"] for x in out["domains"]],
            [135, 145, 145],
        )
        self.assertTrue(all(not x["simulated_time_is_narrative_fact"]
                            for x in out["domains"]))
        self.assertEqual(out["world_db_writes"], 0)

    def test_travel_interval_rejects_impossible_exact_arrival(self):
        self.fail(
            "TIME_EVENT_INFEASIBLE:walk", [
                evt("look", 1, actor="mara", exact=140),
                evt("walk", 2, actor="mara", kind="MOVEMENT",
                    to="archive", exact=145),
            ],
        )

    def test_travel_after_last_action_without_previous_scene_event(self):
        self.fail(
            "TIME_EVENT_INFEASIBLE:walk", [
                evt("walk", 1, actor="mara", kind="MOVEMENT",
                    to="archive", exact=139),
            ],
        )

    def test_backward_propagation_respects_fixed_later_action(self):
        out = solve([
            evt("a", 1, late=175),
            evt("b", 2, early=145, exact=145,
                deps=[("a", 8)]),
        ])
        self.assertEqual(out["domains"][0]["latest_feasible_minute"], 137)
        self.assertEqual(out["domains"][1]["earliest_feasible_minute"], 145)

    def test_contradictory_earliest_bound_with_later_exact_is_hold(self):
        self.fail("TIME_EVENT_INFEASIBLE:a", [
            evt("a", 1, early=155),
            evt("b", 2, exact=150, deps=[("a", 10)]),
        ])

    def test_wrong_order_and_duplicate_ids_are_invalid(self):
        self.fail("TIME_EVENT_SCHEMA_OR_ORDER_INVALID", [
            evt("a", 1), evt("b", 1),
        ])
        self.fail("TIME_EVENT_SCHEMA_OR_ORDER_INVALID", [
            evt("a", 1), evt("a", 2),
        ])

    def test_self_and_forward_causes_are_invalid(self):
        self.fail("TIME_CAUSAL_EDGE_INVALID", [
            evt("a", 1, deps=[("a", 0)]),
        ])
        self.fail("TIME_CAUSAL_EDGE_INVALID", [
            evt("a", 1, deps=[("future", 1)]),
            evt("future", 2),
        ])

    def test_valid_dependencies_propagate_minimum_gap(self):
        out = solve([
            evt("a", 1, actor="vane", exact=140),
            evt("b", 2, actor="mara", deps=[("a", 15)]),
        ])
        self.assertEqual(out["domains"][1]["earliest_feasible_minute"], 155)
        self.assertEqual(out["domains"][1]["narrative_exact_minute"], None)

    def test_unknown_route_is_not_silently_assumed(self):
        self.fail("TIME_ROUTE_UNKNOWN", [
            evt("walk", 1, kind="MOVEMENT", to="unknown_place"),
        ])

    def test_nonmovement_cannot_change_character_location(self):
        self.fail("TIME_NONMOVEMENT_DESTINATION", [
            evt("teleport", 1, kind="ACTION", to="archive"),
        ])

    def test_window_is_bound_to_entry_revision(self):
        invalid = dict(WINDOW, entry_revision=2)
        self.fail("TIME_WINDOW_INVALID",
                  [evt("a", 1)], window=invalid)

    def test_source_time_not_claimed_by_simulation(self):
        out = solve([
            evt("observe", 1, exact=136),
            evt("later", 2),
        ], simulate=True)
        self.assertEqual(out["domains"][0]["narrative_exact_minute"], 136)
        self.assertIsNone(out["domains"][1]["narrative_exact_minute"])
        self.assertEqual(out["domains"][1]["simulation_cursor"], 136)
        self.assertFalse(out["production_commit_authorized"])

    def test_route_destination_is_used_for_second_movement(self):
        result = solve([
            evt("out", 1, kind="MOVEMENT", to="archive"),
            evt("back", 2, kind="MOVEMENT", to="station"),
        ], simulate=True)
        self.assertEqual([x["simulation_cursor"] for x in result["domains"]],
                         [145, 155])


if __name__ == "__main__":
    unittest.main()
