"""SERA M3.5 temporal constraint solver: orders actions without inventing times.

Computes feasible EARLIEST/LATEST domains and an optional explicitly labeled
simulation schedule. Never claims a missing timestamp was observed in prose.
No authority, network call, or world/database mutation.
"""
from __future__ import annotations

from collections import defaultdict

from experiments.sera.coverage import CoverageError
from experiments.sera.world_state_v02 import validate as validate_world

SCHEMA = "sera.temporal-domains.v0.5"
KEYS = frozenset({
    "event_id", "ordinal", "actor_id", "kind", "to_location",
    "earliest_minute", "latest_minute", "exact_minute", "depends_on",
})
KINDS = frozenset({"ACTION", "MOVEMENT", "OBSERVATION", "TESTIMONY"})


def fail(code):
    raise CoverageError(code)


def _minute(x):
    return x is None or (type(x) is int and x >= 0)


def solve_temporal_domains(*, entry: dict, scene_key: str,
                           scene_window: dict, events: list[dict],
                           travel_minutes: dict[str, int] | None = None,
                           simulation_schedule: bool = False) -> dict:
    """Bounded DAG constraint propagation (scene order + causal + travel).

    All constraints are APPLICATION-adjudicated input, not untrusted provider
    statements. Simulation schedule is explicitly noncanonical and never
    supplies a trusted v0.2 approval.
    """
    validate_world(entry)
    if not isinstance(scene_key, str) or not scene_key:
        fail("TIME_SCENE_KEY_INVALID")
    if not isinstance(scene_window, dict) or set(scene_window) != {
        "earliest_minute", "latest_minute", "scene_key", "entry_revision"
    }:
        fail("TIME_WINDOW_SCHEMA_INVALID")
    low = scene_window["earliest_minute"]
    high = scene_window["latest_minute"]
    if (scene_window["scene_key"] != scene_key or
        scene_window["entry_revision"] != entry["revision"] or
        type(low) is not int or type(high) is not int or
        low < entry["minute"] or low > high):
        fail("TIME_WINDOW_INVALID")
    if not isinstance(events, list) or not events:
        fail("TIME_EVENTS_REQUIRED")
    routes = travel_minutes or {}
    if not isinstance(routes, dict) or any(
        not isinstance(k, str) or type(v) is not int or v < 0
        for k, v in routes.items()
    ):
        fail("TIME_ROUTES_INVALID")
    if type(simulation_schedule) is not bool:
        fail("TIME_SIMULATION_FLAG_INVALID")

    ordered = sorted(events, key=lambda x: x.get("ordinal", -1)
                     if isinstance(x, dict) and
                     type(x.get("ordinal")) is int else -1)
    ids = [x.get("event_id") for x in ordered]
    if (any(not isinstance(e, dict) or set(e) != KEYS for e in ordered)
        or any(not isinstance(x, str) or not x for x in ids)
        or len(set(ids)) != len(ids)
        or [e["ordinal"] for e in ordered] !=
        list(range(1, len(events)+1))):
        fail("TIME_EVENT_SCHEMA_OR_ORDER_INVALID")

    actors = {}
    for name, item in entry["entities"].items():
        if item["kind"] == "CHARACTER":
            actors[name] = {
                "location": item["location"],
                "last_event": None,
                "last_action_minute": item["last_action_minute"],
            }

    by_id = {e["event_id"]: e for e in ordered}
    preceding = {}
    edges = defaultdict(list)
    first_ids = set()
    prev = None
    movement_minimums = {}
    for e in ordered:
        eid, actor, kind = e["event_id"], e["actor_id"], e["kind"]
        if kind not in KINDS or actor not in actors:
            fail("TIME_ACTOR_OR_KIND_INVALID")
        for key in ("earliest_minute", "latest_minute", "exact_minute"):
            if not _minute(e[key]):
                fail("TIME_EVENT_BOUNDS_INVALID")
        if e["earliest_minute"] is not None and (
            e["latest_minute"] is not None and
            e["earliest_minute"] > e["latest_minute"]
        ):
            fail("TIME_EVENT_BOUNDS_INVALID")
        if e["exact_minute"] is not None and (
            (e["earliest_minute"] is not None and
             e["exact_minute"] < e["earliest_minute"]) or
            (e["latest_minute"] is not None and
             e["exact_minute"] > e["latest_minute"])
        ):
            fail("TIME_EVENT_EXACT_OUTSIDE_BOUNDS")
        deps = e["depends_on"]
        if (not isinstance(deps, list) or
            any(not isinstance(d, dict) or set(d) !=
                {"event_id", "min_gap_minutes"} for d in deps)):
            fail("TIME_DEPENDENCIES_SCHEMA_INVALID")
        predecessors = {}
        if prev:
            predecessors[prev] = 0
        for d in deps:
            source = d["event_id"]
            gap = d["min_gap_minutes"]
            if (source not in preceding or type(gap) is not int or
                gap < 0 or source == eid):
                fail("TIME_CAUSAL_EDGE_INVALID")
            predecessors[source] = max(predecessors.get(source, 0), gap)

        if kind == "MOVEMENT":
            dest = e["to_location"]
            old = actors[actor]["location"]
            if not isinstance(dest, str) or not dest or dest == old:
                fail("TIME_MOVEMENT_DESTINATION_INVALID")
            journey = routes.get(f"{old}->{dest}")
            if type(journey) is not int or journey < 0:
                fail("TIME_ROUTE_UNKNOWN")
            previous_actor_event = actors[actor]["last_event"]
            if previous_actor_event:
                predecessors[previous_actor_event] = max(
                    predecessors.get(previous_actor_event, 0), journey
                )
            else:
                movement_minimums[eid] = (
                    actors[actor]["last_action_minute"] + journey
                )
            actors[actor]["location"] = dest
        elif e["to_location"] is not None:
            fail("TIME_NONMOVEMENT_DESTINATION")
        for source, gap in predecessors.items():
            edges[source].append((eid, gap))
        preceding[eid] = predecessors
        actors[actor]["last_event"] = eid
        prev = eid

    earliest = {}
    latest = {}
    for e in ordered:
        eid = e["event_id"]
        minimum = max(low, movement_minimums.get(eid, low),
                      e["earliest_minute"] if
                      e["earliest_minute"] is not None else low)
        for src, gap in preceding[eid].items():
            minimum = max(minimum, earliest[src] + gap)
        maximum = min(high, e["latest_minute"] if
                      e["latest_minute"] is not None else high)
        if e["exact_minute"] is not None:
            minimum = max(minimum, e["exact_minute"])
            maximum = min(maximum, e["exact_minute"])
        if minimum > maximum:
            fail(f"TIME_EVENT_INFEASIBLE:{eid}")
        earliest[eid] = minimum
        latest[eid] = maximum

    # Backward propagation tightens earlier event windows when a later event
    # has a fixed time (including nonzero travel duration).
    for e in reversed(ordered):
        eid = e["event_id"]
        for child, gap in edges[eid]:
            latest[eid] = min(latest[eid], latest[child] - gap)
        if latest[eid] < earliest[eid]:
            fail(f"TIME_EVENT_INFEASIBLE:{eid}")

    domains = []
    for e in ordered:
        eid = e["event_id"]
        domains.append({
            "event_id": eid, "ordinal": e["ordinal"],
            "narrative_exact_minute": e["exact_minute"],
            "earliest_feasible_minute": earliest[eid],
            "latest_feasible_minute": latest[eid],
            "simulation_cursor": earliest[eid] if simulation_schedule else None,
            "simulated_time_is_narrative_fact": False,
            "depends_on": sorted(preceding[eid]),
        })
    return {
        "schema": SCHEMA, "scene_key": scene_key,
        "entry_revision": entry["revision"],
        "status": "FEASIBLE_NOT_AUTHORIZED",
        "domains": domains,
        "simulation_schedule": simulation_schedule,
        "production_commit_authorized": False,
        "world_db_writes": 0,
    }
