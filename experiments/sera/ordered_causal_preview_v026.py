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
from experiments.sera.world_state_v013 import EVENT_KEYS, TYPES
from experiments.sera.sentence_ledger_v06 import sentences

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
            relation_case, typed_candidates=None,
            typed_registry=None):
    validate_world(world)
    frozen_sha = digest(world)
    ensure(isinstance(prose, str) and prose.strip() and
           isinstance(extraction_report, dict) and
           extraction_report.get("source_prose_sha256") == prose_hash(prose)
           and isinstance(extraction_report.get("candidate_events"), list),
           "V026_SOURCE_REPORT_INVALID")
    facets = [] if typed_candidates is None else typed_candidates
    ensure(isinstance(facets, list), "V027_FACET_LIST_INVALID")
    if facets:
        ensure(isinstance(typed_registry, dict) and
               set(typed_registry) == {"openables", "documents"} and
               all(isinstance(v, list) for v in typed_registry.values()),
               "V027_FACET_REGISTRY_REQUIRED")
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
    # v0.27 typed facet events do not replace the independent source
    # events: they are exact source-anchored proposals cross-checked with
    # independent OPEN/CLOSE/WRITE candidates by the v0.23 gate.
    by_facet_id = {}
    facet_events = []
    numbered = {v["id"]: v for v in sentences(prose)}
    for e in facets:
        ensure(isinstance(e, dict) and set(e) == EVENT_KEYS and
               e.get("type") in TYPES and
               isinstance(e.get("payload"), dict) and
               set(e["payload"]) == TYPES[e["type"]] and
               isinstance(e.get("evidence"), dict) and
               set(e["evidence"]) == {"start", "end", "quote"},
               "V027_FACET_EVENT_SCHEMA_INVALID")
        p = e["evidence"]
        ensure(type(p["start"]) is int and type(p["end"]) is int and
               0 <= p["start"] < p["end"] <= len(prose) and
               prose[p["start"]:p["end"]] == p["quote"] and
               isinstance(e.get("event_id"), str) and e["event_id"] and
               e["event_id"] not in by_facet_id and
               e.get("sentence_id") in numbered and
               numbered[e["sentence_id"]]["start"] <= p["start"] and
               p["end"] <= numbered[e["sentence_id"]]["end"],
               "V027_FACET_SOURCE_SPAN_INVALID")
        by_facet_id[e["event_id"]] = e
        facet_events.append({
            "event_id": e["event_id"], "start": p["start"],
            "end": p["end"], "kind": "FACET",
            "effect": "OBJECT", "epistemic": "OBSERVED_ACTION",
            "quote": p["quote"], "entity_refs": [e["actor_id"],e["object_id"]],
        })
    ordered = sorted(state_events + facet_events,
                     key=lambda e: e.get("start", -1))
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
        elif e["kind"] == "FACET":
            ensure(t.get("kind") == "ACTION" and
                   t.get("to_location") is None and
                   t.get("actor_id") == by_facet_id[e["event_id"]]["actor_id"],
                   "V027_FACET_TEMPORAL_ACTOR_INVALID")
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
    aspect_state = {}
    if facets:
        ensure(len(set(typed_registry["openables"] +
                       typed_registry["documents"])) ==
               len(typed_registry["openables"] +
                   typed_registry["documents"]),
               "V027_DUPLICATE_FACET_REGISTRY")
        for obj in typed_registry["openables"]:
            ensure(obj in state["entities"] and
                   state["entities"][obj]["kind"] == "OBJECT",
                   "V027_OPENABLE_OBJECT_UNREGISTERED")
            aspect_state[obj] = {"role": "OPENABLE",
                                 "position": "UNKNOWN",
                                 "observed": False}
        for obj in typed_registry["documents"]:
            ensure(obj in state["entities"] and
                   state["entities"][obj]["kind"] == "OBJECT",
                   "V027_DOCUMENT_OBJECT_UNREGISTERED")
            aspect_state[obj] = {"role": "DOCUMENT", "entries": []}
    for original, timed in zip(ordered, timeline):
        source_id = original["event_id"]
        before = digest(state)
        partial_report = {
            "source_prose_sha256": prose_hash(prose),
            "candidate_events": [deepcopy(original)],
        }
        if original["kind"] == "FACET":
            facet = by_facet_id[source_id]
            actor = state["entities"].get(facet["actor_id"])
            obj = state["entities"].get(facet["object_id"])
            ensure(isinstance(actor, dict) and
                   actor.get("lifecycle") == "ACTIVE" and
                   actor.get("kind") == "CHARACTER" and
                   isinstance(obj, dict) and
                   obj.get("lifecycle") == "ACTIVE" and
                   obj.get("kind") == "OBJECT" and
                   actor["location"] == obj["location"],
                   "V027_FACET_CURRENT_WORLD_COLOCATION_FAILED")
            facet_state = aspect_state.get(facet["object_id"])
            ensure(isinstance(facet_state, dict),
                   "V027_UNREGISTERED_FACET_OBJECT")
            payload = facet["payload"]
            if facet["type"] == "OBSERVE_OPENABLE":
                ensure(facet_state["role"] == "OPENABLE" and
                       facet_state["position"] == "UNKNOWN" and
                       not facet_state["observed"] and
                       payload["expected"] == "UNKNOWN" and
                       payload["observed"] in ("OPEN", "CLOSED"),
                       "V027_FACET_OBSERVATION_CAS_FAILED")
                facet_state["position"] = payload["observed"]
                facet_state["observed"] = True
            elif facet["type"] == "SET_OPENABLE":
                ensure(facet_state["role"] == "OPENABLE" and
                       facet_state["observed"] and
                       payload["expected"] == facet_state["position"] and
                       payload["next"] in ("OPEN", "CLOSED") and
                       payload["next"] != payload["expected"],
                       "V027_FACET_STATE_CAS_FAILED")
                facet_state["position"] = payload["next"]
            else:
                ensure(facet_state["role"] == "DOCUMENT" and
                       type(payload["expected_append_count"]) is int and
                       payload["expected_append_count"] ==
                         len(facet_state["entries"]) and
                       payload["text"] == facet["evidence"]["quote"] and
                       isinstance(payload["text"], str) and
                       payload["text"].strip(),
                       "V027_DOCUMENT_APPEND_CAS_FAILED")
                facet_state["entries"].append(payload["text"])
            result = {"isolated_preview_state": deepcopy(state),
                      "canonical_commit_authorized": False,
                      "world_db_writes": 0, "world_sha256": before,
                      "transition_count": 1}
            step_kind = facet["type"]
        elif original["kind"] == "MOVE":
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
        if original["kind"] != "FACET":
            ensure(after != before, "V026_NO_OP_REPLAY_STEP")
        steps.append({
            "source_event_id": source_id,
            "kind": step_kind,
            "source_start": original["start"],
            "before_world_sha256": before,
            "after_world_sha256": after,
            "facet_state_sha256": digest(aspect_state),
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
        "covered_facet_ids": [e["event_id"] for e in facets],
        "facet_state": deepcopy(aspect_state),
        "isolated_preview_state": state,
        "all_state_families_qualified": False,
        "semantic_truth_proven": False,
        "canonical_commit_authorized": False,
        "world_db_writes": 0,
        "requires_manual_intervention": False,
    }
