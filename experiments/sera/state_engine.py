"""SERA M1: deterministic, isolated scene-state reducer (stdlib only).

Not an NLP extractor. Evidence-span presence is necessary, not semantic proof.
No production database access or model calls.
"""
from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

STATE_SCHEMA = "sera.scene-state.v0.1"
EVENT_TYPES = frozenset({
    "CREATE_ENTITY", "MOVE_CHARACTER", "TRANSFER_OBJECT", "UPDATE_OBJECT",
    "LEARN_FACT", "TELL_FACT", "RECORD_FACT", "OPEN_THREAD", "RESOLVE_THREAD",
})
FACT_CERTAINTY = frozenset({"OBSERVED", "INFERRED", "HYPOTHESIS", "UNKNOWN"})


class StateError(ValueError):
    """Fail-closed violation with a stable machine-readable code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def need(ok: bool, code: str) -> None:
    if not ok:
        raise StateError(code)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _character(state: dict, entity_id: str) -> dict:
    entity = state["entities"].get(entity_id)
    need(isinstance(entity, dict) and entity.get("kind") == "CHARACTER",
         f"UNKNOWN_CHARACTER:{entity_id}")
    return entity


def _object(state: dict, entity_id: str) -> dict:
    entity = state["entities"].get(entity_id)
    need(isinstance(entity, dict) and entity.get("kind") == "OBJECT",
         f"UNKNOWN_OBJECT:{entity_id}")
    return entity


def _fact(state: dict, fact_id: str) -> dict:
    fact = state["facts"].get(fact_id)
    need(isinstance(fact, dict), f"UNKNOWN_FACT:{fact_id}")
    return fact


def validate_snapshot(state: dict, forbidden_locations: tuple[str, ...] = ()) -> None:
    """Validate a *complete* snapshot, including unchanged entities."""
    need(isinstance(state, dict), "SNAPSHOT_NOT_OBJECT")
    need(state.get("schema") == STATE_SCHEMA, "SCHEMA_INVALID")
    need(type(state.get("minute")) is int and state["minute"] >= 0, "TIME_INVALID")
    need(type(state.get("revision")) is int and state["revision"] >= 0,
         "REVISION_INVALID")
    need(type(state.get("scene_index")) is int and state["scene_index"] >= 0,
         "SCENE_INDEX_INVALID")
    for key in ("entities", "facts", "threads"):
        need(isinstance(state.get(key), dict), f"{key.upper()}_INVALID")
    need(isinstance(state.get("event_log"), list), "EVENT_LOG_INVALID")
    need(isinstance(state.get("scene_key"), str), "SCENE_KEY_INVALID")
    ids = []
    for item in state["event_log"]:
        need(isinstance(item, dict) and isinstance(item.get("event_id"), str),
             "EVENT_LOG_ENTRY_INVALID")
        ids.append(item["event_id"])
    need(len(ids) == len(set(ids)), "DUPLICATE_EVENT_ID")

    for fact_id, fact in state["facts"].items():
        need(isinstance(fact_id, str) and fact_id and isinstance(fact, dict),
             "FACT_FORMAT_INVALID")
        need(fact.get("certainty") in FACT_CERTAINTY, f"FACT_CERTAINTY_INVALID:{fact_id}")
        need(isinstance(fact.get("claim"), str) and fact["claim"].strip(),
             f"FACT_CLAIM_INVALID:{fact_id}")

    for entity_id, entity in state["entities"].items():
        need(isinstance(entity_id, str) and entity_id and isinstance(entity, dict),
             "ENTITY_FORMAT_INVALID")
        kind = entity.get("kind")
        need(kind in ("CHARACTER", "OBJECT"), f"ENTITY_KIND_INVALID:{entity_id}")
        location = entity.get("location")
        need(isinstance(location, str) and location, f"LOCATION_MISSING:{entity_id}")
        need(location not in forbidden_locations, f"FORBIDDEN_LOCATION:{entity_id}")
        if kind == "CHARACTER":
            need(type(entity.get("last_action_minute")) is int and
                 0 <= entity["last_action_minute"] <= state["minute"],
                 f"CHARACTER_CLOCK_INVALID:{entity_id}")
            knowledge = entity.get("knowledge")
            need(isinstance(knowledge, list) and
                 all(isinstance(x, str) and x in state["facts"] for x in knowledge) and
                 len(knowledge) == len(set(knowledge)),
                 f"KNOWLEDGE_INVALID:{entity_id}")
        else:
            need(isinstance(entity.get("properties"), dict),
                 f"OBJECT_PROPERTIES_INVALID:{entity_id}")
            recorded = entity.get("recorded_facts")
            need(isinstance(recorded, list) and
                 all(isinstance(x, str) and x in state["facts"] for x in recorded) and
                 len(recorded) == len(set(recorded)),
                 f"OBJECT_RECORDS_INVALID:{entity_id}")
            holder = entity.get("holder")
            if holder is not None:
                owner = _character(state, holder)
                need(owner["location"] == location,
                     f"HELD_OBJECT_LOCATION_MISMATCH:{entity_id}")

    for thread_id, thread in state["threads"].items():
        need(isinstance(thread_id, str) and thread_id and
             isinstance(thread, dict) and thread.get("status") in ("OPEN", "RESOLVED"),
             f"THREAD_INVALID:{thread_id}")


def _event_evidence(event: dict, prose: str) -> None:
    quote = event.get("evidence_text")
    need(isinstance(quote, str) and norm(quote), "EVIDENCE_MISSING")
    # Exact normalized substring = deterministic pointer validity, NOT entailment.
    need(norm(quote) in norm(prose), f"EVIDENCE_SPAN_NOT_FOUND:{event['event_id']}")


def _actor_available(character: dict, at: int, actor_id: str) -> None:
    need(at >= character["last_action_minute"], f"ACTOR_TIME_BACKWARDS:{actor_id}")


def apply_scene(
    entry_state: dict[str, Any],
    events: list[dict[str, Any]],
    *,
    scene_key: str,
    prose: str,
    travel_minutes: dict[str, int],
    forbidden_locations: tuple[str, ...] = ("sealed_dispatch_office",),
    allowed_new_entity_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Compute exit state from entry + validated ordered events; never mutate entry.

    Event time represents action completion; movement time represents arrival.
    New entity IDs require explicit authorization. All events need literal evidence
    spans from current prose; semantic entailment is a separate judge task.
    """
    validate_snapshot(entry_state, forbidden_locations)
    need(isinstance(scene_key, str) and scene_key, "SCENE_KEY_REQUIRED")
    need(isinstance(prose, str) and prose.strip(), "SCENE_PROSE_REQUIRED")
    need(isinstance(events, list), "EVENTS_NOT_LIST")
    need(isinstance(travel_minutes, dict), "ROUTES_INVALID")
    state = deepcopy(entry_state)
    seen = {e["event_id"] for e in state["event_log"]}
    last_time = state["minute"]

    for event in events:
        need(isinstance(event, dict), "EVENT_NOT_OBJECT")
        eid = event.get("event_id")
        kind = event.get("type")
        at = event.get("at")
        need(isinstance(eid, str) and eid, "EVENT_ID_MISSING")
        need(eid not in seen, f"DUPLICATE_EVENT_ID:{eid}")
        need(kind in EVENT_TYPES, f"EVENT_TYPE_INVALID:{eid}")
        need(type(at) is int and at >= last_time, f"EVENT_TIME_INVALID:{eid}")
        _event_evidence(event, prose)
        seen.add(eid)

        if kind == "CREATE_ENTITY":
            entity_id = event.get("entity_id")
            entity = event.get("entity")
            need(isinstance(entity_id, str) and entity_id, "CREATE_ENTITY_ID_INVALID")
            need(entity_id not in state["entities"], f"ENTITY_ALREADY_EXISTS:{entity_id}")
            need(entity_id in allowed_new_entity_ids,
                 f"ENTITY_CREATION_NOT_AUTHORIZED:{entity_id}")
            need(isinstance(entity, dict), f"CREATED_ENTITY_INVALID:{entity_id}")
            state["entities"][entity_id] = deepcopy(entity)

        elif kind == "MOVE_CHARACTER":
            char_id = event.get("character_id")
            person = _character(state, char_id)
            dest = event.get("to")
            need(isinstance(dest, str) and dest, f"MOVE_DEST_INVALID:{eid}")
            need(dest not in forbidden_locations, f"FORBIDDEN_DESTINATION:{dest}")
            origin = person["location"]
            need(origin != dest, f"NO_OP_MOVE:{char_id}")
            route = f"{origin}->{dest}"
            minimum = travel_minutes.get(route)
            need(type(minimum) is int and minimum >= 0,
                 f"UNKNOWN_ROUTE:{route}")
            _actor_available(person, at, char_id)
            need(at - person["last_action_minute"] >= minimum,
                 f"TRAVEL_TOO_FAST:{char_id}")
            person["location"] = dest
            person["last_action_minute"] = at
            # Held objects move with their holder; no separate object event needed.
            for obj in state["entities"].values():
                if obj["kind"] == "OBJECT" and obj.get("holder") == char_id:
                    obj["location"] = dest

        elif kind == "TRANSFER_OBJECT":
            obj = _object(state, event.get("object_id"))
            sender_id, recipient_id = event.get("from_id"), event.get("to_id")
            sender = _character(state, sender_id)
            recipient = _character(state, recipient_id)
            need(sender_id != recipient_id, f"TRANSFER_TO_SELF:{eid}")
            need(obj.get("holder") == sender_id, f"NOT_CURRENT_HOLDER:{eid}")
            need(sender["location"] == recipient["location"] ==
                 obj["location"], f"TRANSFER_NOT_COLOCATED:{eid}")
            _actor_available(sender, at, sender_id)
            _actor_available(recipient, at, recipient_id)
            obj["holder"] = recipient_id
            obj["location"] = recipient["location"]
            sender["last_action_minute"] = at
            recipient["last_action_minute"] = at

        elif kind == "UPDATE_OBJECT":
            obj = _object(state, event.get("object_id"))
            actor_id = event.get("actor_id")
            actor = _character(state, actor_id)
            _actor_available(actor, at, actor_id)
            need(actor["location"] == obj["location"], f"OBJECT_OUT_OF_REACH:{eid}")
            field = event.get("property")
            need(isinstance(field, str) and field, f"OBJECT_FIELD_INVALID:{eid}")
            # Only object properties can be changed this way; identity/holder/location
            # are protected and require other typed events.
            need(field not in ("id", "kind", "holder", "location"),
                 f"OBJECT_FIELD_PROTECTED:{eid}")
            obj["properties"][field] = deepcopy(event.get("value"))
            actor["last_action_minute"] = at

        elif kind == "LEARN_FACT":
            char_id, fact_id = event.get("character_id"), event.get("fact_id")
            char = _character(state, char_id)
            _fact(state, fact_id)
            _actor_available(char, at, char_id)
            if fact_id not in char["knowledge"]:
                char["knowledge"].append(fact_id)
            char["last_action_minute"] = at

        elif kind == "TELL_FACT":
            source_id, dest_id = event.get("from_id"), event.get("to_id")
            fact_id = event.get("fact_id")
            source = _character(state, source_id)
            dest = _character(state, dest_id)
            _fact(state, fact_id)
            need(source_id != dest_id, f"TELL_TO_SELF:{eid}")
            need(source["location"] == dest["location"],
                 f"TELL_NOT_COLOCATED:{eid}")
            need(fact_id in source["knowledge"],
                 f"UNAUTHORIZED_KNOWLEDGE_SOURCE:{eid}")
            _actor_available(source, at, source_id)
            _actor_available(dest, at, dest_id)
            if fact_id not in dest["knowledge"]:
                dest["knowledge"].append(fact_id)
            source["last_action_minute"] = at
            dest["last_action_minute"] = at

        elif kind == "RECORD_FACT":
            char_id, obj_id = event.get("character_id"), event.get("object_id")
            fact_id = event.get("fact_id")
            char = _character(state, char_id)
            obj = _object(state, obj_id)
            _fact(state, fact_id)
            need(fact_id in char["knowledge"], f"RECORD_UNKNOWN_FACT:{eid}")
            need(obj.get("holder") == char_id, f"RECORD_NOT_HOLDER:{eid}")
            _actor_available(char, at, char_id)
            if fact_id not in obj["recorded_facts"]:
                obj["recorded_facts"].append(fact_id)
            char["last_action_minute"] = at

        elif kind == "OPEN_THREAD":
            thread_id = event.get("thread_id")
            need(isinstance(thread_id, str) and thread_id, "THREAD_ID_MISSING")
            need(thread_id not in state["threads"], f"THREAD_ALREADY_EXISTS:{thread_id}")
            state["threads"][thread_id] = {"status": "OPEN"}

        elif kind == "RESOLVE_THREAD":
            thread_id = event.get("thread_id")
            need(thread_id in state["threads"], f"THREAD_UNKNOWN:{thread_id}")
            need(state["threads"][thread_id]["status"] == "OPEN",
                 f"THREAD_NOT_OPEN:{thread_id}")
            state["threads"][thread_id]["status"] = "RESOLVED"

        last_time = at
        state["minute"] = at
        state["event_log"].append(deepcopy(event))
        # Validate after EACH transition, not just final state.
        validate_snapshot(state, forbidden_locations)

    state["scene_index"] += 1
    state["revision"] += 1
    state["scene_key"] = scene_key
    validate_snapshot(state, forbidden_locations)
    return state


def verify_exit_state(
    entry_state: dict,
    events: list[dict],
    submitted_exit: dict,
    **kwargs: Any,
) -> None:
    """Reject model-submitted snapshots that silently edit or drop entities."""
    computed = apply_scene(entry_state, events, **kwargs)
    need(submitted_exit == computed, "EXIT_STATE_NOT_REDUCER_RESULT")


def base_snapshot(*, minute: int, entities: dict, facts: dict | None = None,
                  threads: dict | None = None) -> dict:
    """Construct a complete initial state; caller must supply all known entities."""
    snapshot = {
        "schema": STATE_SCHEMA,
        "scene_index": 0,
        "scene_key": "",
        "revision": 0,
        "minute": minute,
        "entities": deepcopy(entities),
        "facts": deepcopy(facts or {}),
        "threads": deepcopy(threads or {}),
        "event_log": [],
    }
    validate_snapshot(snapshot)
    return snapshot
