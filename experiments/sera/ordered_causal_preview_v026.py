"""SERA v0.26 — ordered causal replay for movement, custody and knowledge.

Pure noncanonical simulation. Reuses v0.24 source/route movement checks,
v0.25 source/CAS/fact checks and v0.5 global temporal DAG. Each state
transition starts from the PREVIOUS verified simulation snapshot rather
than independently from the scene entry world.

This version does NOT replay v0.13 openable/document facets: mixed facet
scenes remain on the fail-safe gate. No invented narrative clock, model
approval, production WorldState write, human review or token output cap.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.relation_knowledge_preview_v025 import preview as relation_preview
from experiments.sera.spatial_preview_v024 import preview as spatial_preview
from experiments.sera.temporal_domains_v05 import solve_temporal_domains
from experiments.sera.world_state_v02 import canonical, validate as validate_world

SCHEMA = "sera.ordered-cross-family-preview.v0.26"
RELATION_KINDS = frozenset({"TRANSFER", "LEARN_FACT", "KNOWLEDGE_UPDATE"})
MOVE_EFFECTS = frozenset({"WORLD", "OBJECT"})
RELATION_EFFECTS = frozenset({"WORLD", "OBJECT", "CHARACTER_KNOWLEDGE"})


def ensure(condition, code):
    if not condition:
        raise CoverageError(code)


def digest(value):
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def preview(*, prose, world, extraction_report, temporal_case,
            relation_case, typed_candidates=None):
    validate_world(world)
    frozen_sha = digest(world)
    ensure(isinstance(prose, str) and prose.strip() and
           isinstance(extraction_report, dict) and
           extraction_report.get("source_prose_sha256") == prose_hash(prose)
           and isinstance(extraction_report.get("candidate_events"), list),
           "V026_SOURCE_REPORT_INVALID")
    ensure(typed_candidates == [], "V026_FACET_REPLAY_NOT_QUALIFIED")
    ensure(isinstance(temporal_case, dict) and
           temporal_case.get("entry") == world and
           set(temporal_case) == {
               "entry", "scene_key", "scene_window",
               "events", "travel_minutes",
           } and isinstance(temporal_case["events"], list) and
           isinstance(temporal_case["travel_minutes"], dict),
           "V026_APP_TEMPORAL_POLICY_REQUIRED")
    ensure(isinstance(relation_case, dict) and
           relation_case.get("entry") == world and
           set(relation_case) == {
               "entry", "registered_aliases", "verified_fact_registry",
               "transitions", "policy_id",
           } and isinstance(relation_case["transitions"], list),
           "V026_APP_RELATION_POLICY_REQUIRED")

    all_events = extraction_report["candidate_events"]
    state_events = [
        e for e in all_events if isinstance(e, dict) and (
            (e.get("kind") == "MOVE" and e.get("effect") in MOVE_EFFECTS) or
            (e.get("kind") in RELATION_KINDS and
             e.get("effect") in RELATION_EFFECTS)
        )
    ]
    movers = [e for e in state_events if e["kind"] == "MOVE"]
    relations = [e for e in state_events if e["kind"] in RELATION_KINDS]
    ensure(bool(movers) and bool(relations),
           "V026_REQUIRES_TWO_SUPPORTED_FAMILIES")
    ordered = sorted(state_events, key=lambda e: e.get("start", -1))
    ensure(all(type(e.get("start")) is int and
               type(e.get("end")) is int and
               0 <= e["start"] < e["end"] <= len(prose) and
               prose[e["start"]:e["end"]] == e.get("quote") and
               e.get("epistemic") == "OBSERVED_ACTION" and
               isinstance(e.get("event_id"), str) and e["event_id"] and
               isinstance(e.get("entity_refs"), list)
               for e in ordered),
           "V026_SOURCE_PROVENANCE_INVALID")
    ensure(all(ordered[i]["end"] <= ordered[i+1]["start"]
               for i in range(len(ordered)-1)),
           "V026_OVERLAPPING_STATE_EVENT_ORDER")
    ids = [e["event_id"] for e in ordered]
    ensure(len(set(ids)) == len(ids), "V026_DUPLICATE_SOURCE_EVENT")

    timeline = temporal_case["events"]
    ensure(len(timeline) == len(ordered) and
           all(isinstance(t, dict) for t in timeline) and
           [t.get("event_id") for t in timeline] == ids and
           [t.get("ordinal") for t in timeline] ==
              list(range(1, len(timeline)+1)),
           "V026_TIMELINE_DOES_NOT_COVER_SOURCE_ORDER")
    by_id = {t["source_event_id"]: t
             for t in relation_case["transitions"]
             if isinstance(t, dict) and "source_event_id" in t}
    relation_ids = {e["event_id"] for e in relations}
    ensure(len(by_id) == len(relations) and set(by_id) == relation_ids,
           "V026_RELATION_PROPOSAL_COVERAGE")

    # One global temporal solver checks the action DAG and travel windows;
    # nonmovement ACTION nodes keep the intervening causal ordering.
    for e, t in zip(ordered, timeline):
        if e["kind"] == "MOVE":
            ensure(t.get("kind") == "MOVEMENT" and
                   t.get("actor_id") in e["entity_refs"],
                   "V026_MOVE_TIMELINE_TYPE_OR_ACTOR")
        else:
            action = by_id[e["event_id"]]
            actor = (action.get("from_id") if
                     action.get("operation") == "TRANSFER_HOLDER"
                     else action.get("to_id"))
            ensure(t.get("kind") == "ACTION" and
                   t.get("to_location") is None and
                   t.get("actor_id") == actor,
                   "V026_RELATION_TIMELINE_TYPE_OR_ACTOR")
    temporal = solve_temporal_domains(
        entry=world, scene_key=temporal_case["scene_key"],
        scene_window=temporal_case["scene_window"],
        events=timeline, travel_minutes=temporal_case["travel_minutes"],
    )
    ensure(temporal["status"] == "FEASIBLE_NOT_AUTHORIZED" and
           temporal["production_commit_authorized"] is False and
           temporal["world_db_writes"] == 0,
           "V026_TEMPORAL_AUTHORITY_REJECTED")

    state = deepcopy(world)
    steps = []
    for original, timed in zip(ordered, timeline):
        source_id = original["event_id"]
        before = digest(state)
        partial_report = {
            "source_prose_sha256": prose_hash(prose),
            "candidate_events": [deepcopy(original)],
        }
        if original["kind"] == "MOVE":
            # A detached one-event temporal view is verified AGAIN from
            # the evolving state. Global full-DAG feasibility was proven
            # above; the per-event check enforces current-location route,
            # identity, held/worn co-movement and exact quoted destination.
            local_time = deepcopy(timed)
            local_time["ordinal"] = 1
            local_time["depends_on"] = []
            scoped = {
                "entry": deepcopy(state),
                "scene_key": temporal_case["scene_key"],
                "scene_window": deepcopy(temporal_case["scene_window"]),
                "events": [local_time],
                "travel_minutes": deepcopy(temporal_case["travel_minutes"]),
            }
            result = spatial_preview(
                prose=prose, world=state,
                extraction_report=partial_report, temporal_case=scoped,
            )
            step_kind = "MOVE"
        else:
            scoped = deepcopy(relation_case)
            scoped["entry"] = deepcopy(state)
            scoped["transitions"] = [deepcopy(by_id[source_id])]
            result = relation_preview(
                prose=prose, world=state,
                extraction_report=partial_report, relation_case=scoped,
            )
            step_kind = by_id[source_id]["operation"]
        ensure(result.get("canonical_commit_authorized") is False and
               result.get("world_db_writes") == 0 and
               result.get("world_sha256") == before and
               result.get("transition_count",
                          result.get("movement_count")) == 1,
               "V026_STEP_AUTHORITY_OR_COUNT_INVALID")
        state = result["isolated_preview_state"]
        validate_world(state)
        after = digest(state)
        ensure(after != before, "V026_NO_OP_REPLAY_STEP")
        steps.append({
            "source_event_id": source_id,
            "kind": step_kind,
            "source_start": original["start"],
            "before_world_sha256": before,
            "after_world_sha256": after,
            "narrative_exact_minute_invented": False,
        })
    ensure(digest(world) == frozen_sha,
           "V026_FROZEN_ENTRY_WORLD_MUTATED")
    return {
        "schema": SCHEMA,
        "status": "ORDERED_CAUSAL_PREVIEW_FEASIBLE_NONCANONICAL",
        "prose_sha256": prose_hash(prose),
        "world_sha256": frozen_sha,
        "report_sha256": digest(extraction_report),
        "temporal_policy_sha256": digest(temporal_case),
        "relation_policy_sha256": digest(relation_case),
        "temporal_feasibility": temporal,
        "steps": steps,
        "covered_movement_ids": [e["event_id"] for e in movers],
        "covered_relation_ids": [e["event_id"] for e in relations],
        "isolated_preview_state": state,
        "all_state_families_qualified": False,
        "semantic_truth_proven": False,
        "canonical_commit_authorized": False,
        "world_db_writes": 0,
        "requires_manual_intervention": False,
    }
