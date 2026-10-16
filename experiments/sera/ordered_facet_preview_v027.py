"""SERA v0.27: one ordered MOVEMENT / CUSTODY / KNOWLEDGE / FACET replay.

v0.13-compatible openable/document CAS semantics are executed against the
CURRENT detached v0.2 world after each earlier motion/handoff/learning
step. v0.13's independent-entry simulated approval is NOT reused as
production authority. No DB writes, model calls, human gates or invented
narrative timestamps. Mixed scenes require a complete app-owned timeline.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.spatial_preview_v024 import preview as spatial_preview
from experiments.sera.relation_knowledge_preview_v025 import preview as relation_preview
from experiments.sera.temporal_domains_v05 import solve_temporal_domains
from experiments.sera.world_state_v013 import (
    EVENT_KEYS, TYPES, OPENABLE_VALUES,
)
from experiments.sera.world_state_v02 import (
    canonical, validate as validate_world,
)
from experiments.sera.sentence_ledger_v06 import sentences

SCHEMA = "sera.ordered-facet-causal-preview.v0.27"
MOVEMENT = frozenset({"WORLD", "OBJECT"})
RELATIONS = frozenset({"TRANSFER", "LEARN_FACT", "KNOWLEDGE_UPDATE"})
RELATION_EFFECTS = frozenset({"WORLD", "OBJECT", "CHARACTER_KNOWLEDGE"})
KINDS = {
    "OBSERVE_OPENABLE": frozenset({"OBSERVE", "OPEN"}),
    "SET_OPENABLE": frozenset({"OPEN", "CLOSE", "CHANGE_STATE"}),
    "APPEND_DOCUMENT_ENTRY": frozenset({"WRITE"}),
}


def require(ok, code):
    if not ok:
        raise CoverageError(code)


def digest(value):
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def _facet_step(*, state, aspects, prose, original, candidate, registry):
    require(isinstance(candidate, dict) and
            set(candidate) == EVENT_KEYS and
            candidate.get("type") in TYPES and
            isinstance(candidate.get("payload"), dict) and
            set(candidate["payload"]) == TYPES[candidate["type"]],
            "V027_FACET_SCHEMA_INVALID")
    proof = candidate.get("evidence")
    require(isinstance(proof, dict) and
            set(proof) == {"start", "end", "quote"} and
            type(proof["start"]) is int and type(proof["end"]) is int and
            original["start"] <= proof["start"] < proof["end"] <=
                original["end"] and
            prose[proof["start"]:proof["end"]] == proof["quote"] and
            candidate.get("sentence_id") == original.get("sentence_id"),
            "V027_FACET_SOURCE_INVALID")
    allowed_effect = {
        "OBSERVE_OPENABLE": frozenset({"NONE", "OBJECT"}),
        "SET_OPENABLE": frozenset({"OBJECT"}),
        "APPEND_DOCUMENT_ENTRY": frozenset({"DOCUMENT"}),
    }
    require(original["kind"] in KINDS[candidate["type"]] and
            original.get("effect") in allowed_effect[candidate["type"]] and
            original["start"] < proof["end"] and
            proof["start"] < original["end"],
            "V027_FACET_INDEPENDENT_SWEEP_MISMATCH")
    actor_id, obj_id = candidate.get("actor_id"), candidate.get("object_id")
    actor = state["entities"].get(actor_id)
    obj = state["entities"].get(obj_id)
    require(isinstance(actor, dict) and actor.get("kind") == "CHARACTER"
            and actor.get("lifecycle") == "ACTIVE" and
            isinstance(obj, dict) and obj.get("kind") == "OBJECT"
            and obj.get("lifecycle") == "ACTIVE" and
            actor_id in original["entity_refs"] and
            obj_id in original["entity_refs"] and
            actor["location"] == obj["location"],
            "V027_FACET_CURRENT_STATE_OR_IDENTITY_INVALID")
    role = ("documents" if candidate["type"] == "APPEND_DOCUMENT_ENTRY"
            else "openables")
    require(obj_id in registry[role] and obj_id in aspects,
            "V027_FACET_REGISTERED_ROLE_INVALID")
    aspect = aspects[obj_id]
    expected_role = "DOCUMENT" if role == "documents" else "OPENABLE"
    require(aspect["type"] == expected_role,
            "V027_FACET_ROLE_INVALID")
    payload = candidate["payload"]
    if candidate["type"] == "OBSERVE_OPENABLE":
        require(aspect["position"] == "UNKNOWN" and
                aspect["baseline_observed"] is False and
                payload["expected"] == "UNKNOWN" and
                payload["observed"] in ("OPEN", "CLOSED"),
                "V027_OPENABLE_BASELINE_CAS_INVALID")
        aspect["position"] = payload["observed"]
        aspect["baseline_observed"] = True
    elif candidate["type"] == "SET_OPENABLE":
        require(aspect["baseline_observed"] is True and
                aspect["position"] in ("OPEN", "CLOSED") and
                payload["expected"] == aspect["position"] and
                payload["next"] in ("OPEN", "CLOSED") and
                payload["next"] != payload["expected"],
                "V027_OPENABLE_TRANSITION_CAS_INVALID")
        aspect["position"] = payload["next"]
    else:
        require(type(payload["expected_append_count"]) is int and
                payload["expected_append_count"] ==
                    len(aspect["observed_appends"]) and
                isinstance(payload["text"], str) and
                payload["text"].strip() and
                payload["text"] == proof["quote"],
                "V027_DOCUMENT_APPEND_CAS_INVALID")
        aspect["observed_appends"].append({
            "text": payload["text"],
            "sentence_id": candidate["sentence_id"],
            "evidence": deepcopy(proof),
        })
    return candidate["type"]


def preview(*, prose, world, extraction_report, temporal_case, relation_case,
            typed_candidates, typed_registry):
    validate_world(world)
    frozen = digest(world)
    require(isinstance(prose, str) and prose.strip() and
            isinstance(extraction_report, dict) and
            extraction_report.get("source_prose_sha256") ==
                prose_hash(prose) and
            isinstance(extraction_report.get("candidate_events"), list),
            "V027_SOURCE_REPORT_INVALID")
    require(isinstance(typed_registry, dict) and
            set(typed_registry) == {"openables", "documents"} and
            all(isinstance(typed_registry[k], list) and
                all(isinstance(x, str) and x for x in typed_registry[k])
                for k in ("openables", "documents")) and
            len(set(typed_registry["openables"] +
                    typed_registry["documents"])) ==
                len(typed_registry["openables"] +
                    typed_registry["documents"]) and
            isinstance(typed_candidates, list) and typed_candidates,
            "V027_TYPED_POLICY_REQUIRED")
    require(isinstance(temporal_case, dict) and
            temporal_case.get("entry") == world and
            set(temporal_case) == {
                "entry", "scene_key", "scene_window",
                "events", "travel_minutes",
            } and isinstance(temporal_case["events"], list),
            "V027_TRUSTED_TEMPORAL_POLICY_REQUIRED")
    require(isinstance(relation_case, dict) and
            relation_case.get("entry") == world and
            set(relation_case) == {
                "entry", "registered_aliases", "verified_fact_registry",
                "transitions", "policy_id",
            } and isinstance(relation_case["transitions"], list),
            "V027_TRUSTED_RELATION_POLICY_REQUIRED")

    evidence = extraction_report["candidate_events"]
    source_state = [e for e in evidence if isinstance(e, dict) and (
        (e.get("kind") == "MOVE" and e.get("effect") in MOVEMENT) or
        (e.get("kind") in RELATIONS and
         e.get("effect") in RELATION_EFFECTS) or
        e.get("kind") in {"OBSERVE", "OPEN", "CLOSE", "CHANGE_STATE", "WRITE"}
    )]
    require(any(e.get("kind") == "MOVE" for e in source_state) or
            any(e.get("kind") in RELATIONS for e in source_state),
            "V027_MIXED_FAMILIES_REQUIRED")
    ordered = sorted(source_state, key=lambda e: e.get("start", -1))
    require(all(type(e.get("start")) is int and
                type(e.get("end")) is int and
                0 <= e["start"] < e["end"] <= len(prose) and
                prose[e["start"]:e["end"]] == e.get("quote") and
                e.get("epistemic") == "OBSERVED_ACTION" and
                isinstance(e.get("event_id"), str) and e["event_id"] and
                isinstance(e.get("entity_refs"), list)
                for e in ordered) and
            all(ordered[i]["end"] <= ordered[i+1]["start"]
                for i in range(len(ordered)-1)),
            "V027_SOURCE_ORDER_OR_PROOF_INVALID")
    ids = [e["event_id"] for e in ordered]
    require(len(ids) == len(set(ids)), "V027_SOURCE_EVENT_DUPLICATE")
    sentence_by_id = {s["id"]: s for s in sentences(prose)}
    for e in ordered:
        sent = sentence_by_id.get(e.get("sentence_id"))
        require(sent is not None and
                sent["start"] <= e["start"] and e["end"] <= sent["end"],
                "V027_SOURCE_SENTENCE_INVALID")

    require(all(isinstance(x, dict) and
                isinstance(x.get("event_id"), str) and
                bool(x["event_id"].strip()) for x in typed_candidates) and
            len({x["event_id"] for x in typed_candidates}) ==
                len(typed_candidates) and
            not set(ids).intersection(
                {x["event_id"] for x in typed_candidates}),
            "V027_TYPED_EVENT_IDS_NOT_UNIQUE")
    used = set()
    facet_map = {}
    for event in ordered:
        if event["kind"] in ("MOVE", *RELATIONS):
            continue
        valid = [
            i for i, item in enumerate(typed_candidates)
            if isinstance(item, dict) and item.get("type") in KINDS and
            event["kind"] in KINDS[item["type"]] and
            item.get("sentence_id") == event["sentence_id"] and
            isinstance(item.get("evidence"), dict) and
            type(item["evidence"].get("start")) is int and
            type(item["evidence"].get("end")) is int and
            event["start"] < item["evidence"]["end"] and
            item["evidence"]["start"] < event["end"]
        ]
        require(len(valid) == 1 and valid[0] not in used,
                "V027_FACET_SOURCE_ONE_TO_ONE_INVALID")
        used.add(valid[0])
        facet_map[event["event_id"]] = typed_candidates[valid[0]]
    require(len(used) == len(typed_candidates),
            "V027_FACET_EXTRA_OR_UNACCOUNTED")

    for role in ("openables", "documents"):
        for item_id in typed_registry[role]:
            obj = world["entities"].get(item_id)
            require(isinstance(obj, dict) and
                    obj["kind"] == "OBJECT" and
                    obj["lifecycle"] == "ACTIVE",
                    "V027_FACET_REGISTRY_WORLD_MISMATCH")
    timeline = temporal_case["events"]
    require(len(timeline) == len(ordered) and
            all(isinstance(x, dict) for x in timeline) and
            [x.get("event_id") for x in timeline] == ids and
            [x.get("ordinal") for x in timeline] ==
                list(range(1, len(ordered)+1)),
            "V027_GLOBAL_TIMELINE_SOURCE_COVERAGE")
    relations = [e for e in ordered if e["kind"] in RELATIONS]
    mappings = relation_case["transitions"]
    require(all(isinstance(x, dict) and
                isinstance(x.get("source_event_id"), str)
                for x in mappings) and
            len(mappings) == len(relations),
            "V027_RELATION_COVERAGE")
    by_relation = {x["source_event_id"]: x for x in mappings}
    require(len(by_relation) == len(mappings) and
            set(by_relation) == {x["event_id"] for x in relations},
            "V027_RELATION_COVERAGE")

    for event, timed in zip(ordered, timeline):
        if event["kind"] == "MOVE":
            require(timed.get("kind") == "MOVEMENT" and
                    timed.get("actor_id") in event["entity_refs"],
                    "V027_MOVEMENT_TIMELINE_ACTOR_INVALID")
        else:
            operation = by_relation.get(event["event_id"])
            expected_actor = (
                (operation["from_id"] if
                 operation["operation"] == "TRANSFER_HOLDER"
                 else operation["to_id"])
                if operation is not None
                else facet_map[event["event_id"]].get("actor_id")
            )
            require(timed.get("kind") == "ACTION" and
                    timed.get("to_location") is None and
                    timed.get("actor_id") == expected_actor,
                    "V027_ACTION_TIMELINE_ACTOR_INVALID")
    temporal = solve_temporal_domains(
        entry=world, scene_key=temporal_case["scene_key"],
        scene_window=temporal_case["scene_window"],
        events=timeline, travel_minutes=temporal_case["travel_minutes"],
    )
    require(temporal.get("status") == "FEASIBLE_NOT_AUTHORIZED" and
            temporal.get("production_commit_authorized") is False and
            temporal.get("world_db_writes") == 0,
            "V027_TEMPORAL_NOT_QUALIFIED")

    aspects = {}
    for role in ("openables", "documents"):
        for ref in typed_registry[role]:
            if role == "openables":
                aspects[ref] = {
                    "type": "OPENABLE", "position": "UNKNOWN",
                    "baseline_observed": False,
                }
            else:
                aspects[ref] = {
                    "type": "DOCUMENT",
                    "preexisting_content": "UNKNOWN",
                    "observed_appends": [],
                }
    state = deepcopy(world)
    steps = []
    facet_head = "0" * 64
    covered_move = []
    covered_relation = []
    covered_facets = []
    for event, timed in zip(ordered, timeline):
        event_id = event["event_id"]
        before_world, before_aspects = digest(state), digest(aspects)
        partial = {
            "source_prose_sha256": prose_hash(prose),
            "candidate_events": [deepcopy(event)],
        }
        if event["kind"] == "MOVE":
            local = deepcopy(timed)
            local["ordinal"] = 1
            local["depends_on"] = []
            scoped = {
                "entry": deepcopy(state),
                "scene_key": temporal_case["scene_key"],
                "scene_window": deepcopy(temporal_case["scene_window"]),
                "events": [local],
                "travel_minutes": deepcopy(temporal_case["travel_minutes"]),
            }
            outcome = spatial_preview(
                prose=prose, world=state,
                extraction_report=partial, temporal_case=scoped,
            )
            require(outcome.get("world_db_writes") == 0 and
                    outcome.get("canonical_commit_authorized") is False and
                    outcome.get("world_sha256") == before_world and
                    outcome.get("movement_count") == 1,
                    "V027_MOVE_NOT_ISOLATED")
            state = outcome["isolated_preview_state"]
            covered_move.append(event_id)
            kind = "MOVE"
        elif event["kind"] in RELATIONS:
            policy = deepcopy(relation_case)
            policy["entry"] = deepcopy(state)
            policy["transitions"] = [deepcopy(by_relation[event_id])]
            outcome = relation_preview(
                prose=prose, world=state,
                extraction_report=partial, relation_case=policy,
            )
            require(outcome.get("world_db_writes") == 0 and
                    outcome.get("canonical_commit_authorized") is False and
                    outcome.get("world_sha256") == before_world and
                    outcome.get("transition_count") == 1,
                    "V027_RELATION_NOT_ISOLATED")
            state = outcome["isolated_preview_state"]
            covered_relation.append(event_id)
            kind = by_relation[event_id]["operation"]
        else:
            item = facet_map[event_id]
            kind = _facet_step(
                state=state, aspects=aspects, prose=prose, original=event,
                candidate=item, registry=typed_registry,
            )
            covered_facets.append(item["event_id"])
            facet_head = sha256((
                facet_head + ":" + digest(item) + ":" +
                digest(aspects)
            ).encode("utf-8")).hexdigest()
        validate_world(state)
        after_world, after_aspects = digest(state), digest(aspects)
        require((before_world, before_aspects) !=
                (after_world, after_aspects),
                "V027_CAUSAL_STEP_NOOP")
        steps.append({
            "source_event_id": event_id, "kind": kind,
            "before_world_sha256": before_world,
            "after_world_sha256": after_world,
            "before_facets_sha256": before_aspects,
            "after_facets_sha256": after_aspects,
            "facet_receipt_head_sha256": facet_head,
            "source_start": event["start"],
            "narrative_exact_minute_invented": False,
        })
    require(digest(world) == frozen, "V027_FROZEN_WORLD_MUTATED")
    return {
        "schema": SCHEMA,
        "status": "ORDERED_FACETS_AND_WORLD_FEASIBLE_NONCANONICAL",
        "prose_sha256": prose_hash(prose),
        "world_sha256": frozen,
        "report_sha256": digest(extraction_report),
        "temporal_policy_sha256": digest(temporal_case),
        "relation_policy_sha256": digest(relation_case),
        "typed_registry_sha256": digest(typed_registry),
        "typed_candidates_sha256": digest(typed_candidates),
        "steps": steps, "facet_receipt_head_sha256": facet_head,
        "facets": aspects,
        "covered_movement_ids": covered_move,
        "covered_relation_ids": covered_relation,
        "covered_facet_ids": covered_facets,
        "isolated_preview_state": state,
        "all_state_families_qualified": False,
        "semantic_truth_proven": False,
        "canonical_commit_authorized": False,
        "world_db_writes": 0,
        "requires_manual_intervention": False,
    }
