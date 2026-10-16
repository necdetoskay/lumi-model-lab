"""SERA v0.24 — source- and route-bound spatial preview, NEVER a canon move.

A MOVE from the independent v0.10 sentence sweep must be matched to an
application-supplied temporal MOVEMENT with the identical event ID, a
registered actor and a destination literally present in its source quote.
The v0.5 solver proves temporal feasibility against an application-owned
route table and world revision. Only then an isolated character+carried
inventory snapshot is projected. No invented arrival minute, paid request,
operator approval, event commit or production WorldState mutation.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import re

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.temporal_domains_v05 import solve_temporal_domains
from experiments.sera.world_state_v02 import (
    canonical, validate as validate_world,
)

SCHEMA = "sera.spatial-preview.v0.24"
PHYSICAL = frozenset({"WORLD", "OBJECT"})


def _require(ok, code):
    if not ok:
        raise CoverageError(code)


def _sha(item):
    return sha256(canonical(item).encode("utf-8")).hexdigest()


def preview(*, prose, world, extraction_report, temporal_case):
    """Pure, noncanonical location/carry graph feasibility preview.

    This proves only consistency of the supplied interpretation. It is
    NOT proof that a physical move took place, nor a grant to write canon.
    """
    validate_world(world)
    before = _sha(world)
    _require(isinstance(prose, str) and prose.strip() and
             isinstance(extraction_report, dict) and
             extraction_report.get("source_prose_sha256") ==
                 prose_hash(prose) and
             isinstance(extraction_report.get("candidate_events"), list),
             "V024_REPORT_SOURCE_INVALID")
    _require(isinstance(temporal_case, dict) and
             set(temporal_case) == {
                 "entry", "scene_key", "scene_window",
                 "events", "travel_minutes",
             } and temporal_case.get("entry") == world,
             "V024_UNTRUSTED_TEMPORAL_WORLD")
    _require(isinstance(temporal_case["events"], list) and
             isinstance(temporal_case["travel_minutes"], dict),
             "V024_TEMPORAL_CASE_INVALID")

    observed = [
        x for x in extraction_report["candidate_events"]
        if isinstance(x, dict) and x.get("kind") == "MOVE" and
        x.get("effect") in PHYSICAL
    ]
    # Invalid/ambiguous MOVE with NONE or UNKNOWN effect cannot be
    # promoted to real motion by a temporal model.
    unqualified = [
        x for x in extraction_report["candidate_events"]
        if isinstance(x, dict) and x.get("kind") == "MOVE" and
        x.get("effect") not in PHYSICAL
    ]
    _require(not unqualified, "V024_MOVE_WITHOUT_OBJECTIVE_EFFECT")
    moves = [
        x for x in temporal_case["events"]
        if isinstance(x, dict) and x.get("kind") == "MOVEMENT"
    ]
    _require(observed and len(observed) == len(moves),
             "V024_MOVEMENT_EVIDENCE_COVERAGE")
    by_id = {x.get("event_id"): x for x in observed}
    _require(len(by_id) == len(observed) and
             all(isinstance(k, str) and k for k in by_id),
             "V024_DUPLICATE_OR_INVALID_SOURCE_EVENT")
    moving_ids = [x.get("event_id") for x in moves]
    _require(len(set(moving_ids)) == len(moving_ids) and
             set(moving_ids) == set(by_id),
             "V024_MOVEMENT_EVENT_BINDING_MISMATCH")

    projected = deepcopy(world)
    transitions = []
    # The v0.5 temporal solver validates DAG, route legs, monotonic
    # source order, minimum travel times and feasible application clock
    # windows. Do NOT use its earliest feasible time as observed fact.
    temporal = solve_temporal_domains(
        entry=world, scene_key=temporal_case["scene_key"],
        scene_window=temporal_case["scene_window"],
        events=temporal_case["events"],
        travel_minutes=temporal_case["travel_minutes"],
    )
    _require(temporal["status"] == "FEASIBLE_NOT_AUTHORIZED" and
             temporal["production_commit_authorized"] is False,
             "V024_TIME_NOT_NONCANONICAL")
    ordered = sorted(temporal_case["events"], key=lambda x: x["ordinal"])
    movements_in_source = sorted(observed, key=lambda x: x["start"])
    bound_temporal_moves = [x for x in ordered if x["kind"] == "MOVEMENT"]
    _require([x["event_id"] for x in bound_temporal_moves] ==
             [x["event_id"] for x in movements_in_source],
             "V024_SOURCE_CHRONOLOGY_CONFLICT")

    for row in bound_temporal_moves:
        original = by_id[row["event_id"]]
        actor_id = row["actor_id"]
        to = row["to_location"]
        _require(original.get("epistemic") == "OBSERVED_ACTION" and
                 isinstance(original.get("entity_refs"), list) and
                 actor_id in original["entity_refs"],
                 "V024_UNTRUSTED_MOVEMENT_ACTOR_OR_EPISTEMIC")
        _require(type(original.get("start")) is int and
                 type(original.get("end")) is int and
                 0 <= original["start"] < original["end"] <= len(prose) and
                 prose[original["start"]:original["end"]] ==
                    original.get("quote"),
                 "V024_MOVEMENT_SOURCE_QUOTE_INVALID")
        actor = projected["entities"].get(actor_id)
        _require(isinstance(actor, dict) and
                 actor["kind"] == "CHARACTER" and
                 actor["lifecycle"] == "ACTIVE",
                 "V024_MOVEMENT_ACTOR_NOT_REGISTERED")
        _require(isinstance(to, str) and to in world["regions"] and
                 to != actor["location"],
                 "V024_MOVEMENT_DESTINATION_UNREGISTERED")
        # Conservative initial implementation: destination ID must occur
        # as a whole word in the exact MOVE source span. Place-alias
        # resolution belongs to a future trusted registry, never inference.
        _require(re.search(r"(?<!\w)" + re.escape(to) + r"(?!\w)",
                           original["quote"], re.IGNORECASE) is not None,
                 "V024_DESTINATION_NOT_SUPPORTED_BY_PROSE")
        prior = actor["location"]
        carried = sorted(
            key for key, item in projected["entities"].items()
            if item["holder"] == actor_id or item["worn_by"] == actor_id
        )
        # An item nested inside a carried container has a separate
        # location dependency not yet represented by this one-level
        # reducer. Fail closed instead of leaving its contents behind.
        carried_ids = set(carried)
        nested = [key for key, item in projected["entities"].items()
                  if item["parent_id"] in carried_ids and
                  key not in carried_ids]
        _require(not nested, "V024_NESTED_CARRIED_GRAPH_UNQUALIFIED")
        # All carried things must already be co-located with the actor.
        _require(all(projected["entities"][key]["location"] == prior
                     for key in carried),
                 "V024_CARRIED_LOCATION_PRECONDITION_FAILED")
        actor["location"] = to
        for key in carried:
            projected["entities"][key]["location"] = to
        transitions.append({
            "source_event_id": row["event_id"],
            "actor_id": actor_id,
            "from_location": prior, "to_location": to,
            "co_moving_registered_items": carried,
            "earliest_feasible_minute_is_not_narrative_time": True,
        })

    validate_world(projected)
    _require(_sha(world) == before, "V024_ENTRY_WORLD_MUTATED")
    # A pure snapshot is not a valid committed WorldState event stream.
    # It is a fenced simulation projection only.
    return {
        "schema": SCHEMA,
        "status": "SPATIAL_ROUTE_FEASIBLE_NONCANONICAL",
        "prose_sha256": prose_hash(prose),
        "world_sha256": before,
        "source_report_sha256": _sha(extraction_report),
        "temporal_case_sha256": _sha(temporal_case),
        "temporal_domains": temporal,
        "movement_count": len(transitions),
        "transitions": transitions,
        "isolated_preview_state": projected,
        "observed_narrative_arrival_time_invented": False,
        "model_semantic_truth_proven": False,
        "canonical_commit_authorized": False,
        "world_db_writes": 0,
        "requires_manual_intervention": False,
    }
