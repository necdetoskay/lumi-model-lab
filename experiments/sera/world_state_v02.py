"""SERA v0.2 experimental typed world/entity state.

Deterministic pure reducer. No model may directly mutate an entity or a DB.
UNKNOWN is explicit; no speculative color, size, weather or clothing defaults.
Does not replace the existing v0.1 pipeline until separately qualified.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math

SCHEMA = "sera.world-state.v0.2"
KINDS = frozenset({"CHARACTER", "OBJECT", "WEARABLE"})
LIFECYCLES = frozenset({"ACTIVE", "DAMAGED", "DESTROYED"})
COLORS = frozenset({
    "UNKNOWN", "BLACK", "WHITE", "RED", "BLUE", "GREEN", "YELLOW",
    "BROWN", "GRAY", "SILVER", "GOLD", "PURPLE", "ORANGE", "PINK",
})
FUNCTIONS = frozenset({"UNKNOWN", "WORKING", "STOPPED", "BROKEN", "INOPERABLE"})
AGES = frozenset({"UNKNOWN", "NEW", "USED", "OLD"})
WEATHER = frozenset({"UNKNOWN", "CLEAR", "CLOUDY", "RAIN", "SNOW", "STORM"})
SIZES = frozenset({"UNKNOWN", "XS", "S", "M", "L", "XL"})
DIM_FIELDS = frozenset({"width_cm", "height_cm", "depth_cm", "mass_kg"})
APPEARANCE_FIELDS = frozenset({"color", "material", "markings"})
CONDITION_FIELDS = frozenset({"integrity_pct", "functional", "age"})
EVENT_FIELDS = frozenset({"event_id", "type", "at_minute", "reason", "evidence_ref", "payload"})
TYPE_FIELDS = {
    "INTRODUCE_ENTITY": frozenset({"entity_id", "entity", "parent_id"}),
    "CHANGE_APPEARANCE": frozenset({"entity_id", "field", "old", "new"}),
    "CHANGE_CONDITION": frozenset({"entity_id", "field", "old", "new"}),
    "CHANGE_DIMENSION": frozenset({"entity_id", "field", "old", "new", "world_rule_id"}),
    "MOVE_CHARACTER": frozenset({"character_id", "to_location"}),
    "TRANSFER_HOLDER": frozenset({"entity_id", "from_id", "to_id"}),
    "WEAR": frozenset({"entity_id", "character_id"}),
    "REMOVE_WEAR": frozenset({"entity_id", "character_id"}),
    "LEARN_FACT": frozenset({"character_id", "fact_id"}),
    "UPDATE_CHARACTER_TRAIT": frozenset({"character_id", "trait", "old", "new"}),
    "SET_WEATHER": frozenset({
        "region_id", "old_weather", "new_weather", "temperature_c",
        "wind_kph", "cloud_cover_pct", "precip_mm_h", "ground_wet",
        "exception_rule_id",
    }),
    "RETIRE_ENTITY": frozenset({"entity_id"}),
    "INTERACT_ENTITY": frozenset({"entity_id", "actor_id", "interaction"}),
    "ADVANCE_SCENE": frozenset({"scene_key"}),
}


class WorldStateError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def check(ok: bool, code: str) -> None:
    if not ok:
        raise WorldStateError(code)


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def fingerprint(event: dict) -> str:
    return hashlib.sha256(canonical(event).encode("utf-8")).hexdigest()


def number(value, *, minval=0, maxval=None, null_ok=False) -> bool:
    if null_ok and value is None:
        return True
    return (type(value) in (int, float) and math.isfinite(value)
            and value >= minval and (maxval is None or value <= maxval))


def exact_keys(value, expected, code) -> None:
    check(isinstance(value, dict) and set(value) == set(expected), code)


def entity_template(entity_id: str, kind: str, location: str, *,
                    owner=None, holder=None, worn_by=None, color="UNKNOWN",
                    material="UNKNOWN", markings="UNKNOWN",
                    width_cm=None, height_cm=None, depth_cm=None, mass_kg=None,
                    integrity_pct=None, functional="UNKNOWN", age="UNKNOWN",
                    size="UNKNOWN", traits=None, knowledge=None,
                    last_action_minute=0, parent_id=None) -> dict:
    """Typed, fully populated entity (physical object / wearable / character)."""
    check(kind in KINDS, "ENTITY_KIND_INVALID")
    return {
        "entity_id": entity_id, "kind": kind, "lifecycle": "ACTIVE",
        "location": location, "owner": owner, "holder": holder,
        "worn_by": worn_by, "parent_id": parent_id,
        "appearance": {"color": color, "material": material,
                       "markings": markings},
        "dimensions": {"width_cm": width_cm, "height_cm": height_cm,
                       "depth_cm": depth_cm, "mass_kg": mass_kg},
        "condition": {"integrity_pct": integrity_pct,
                      "functional": functional, "age": age},
        "size": size, "traits": deepcopy(traits or {}),
        "knowledge": list(knowledge or []),
        "last_action_minute": last_action_minute,
    }


def environment_template(weather="UNKNOWN", *, temperature_c=None,
                         wind_kph=None, cloud_cover_pct=None,
                         precip_mm_h=None, ground_wet=None,
                         last_change_minute=0) -> dict:
    return {
        "weather": weather, "temperature_c": temperature_c,
        "wind_kph": wind_kph, "cloud_cover_pct": cloud_cover_pct,
        "precip_mm_h": precip_mm_h, "ground_wet": ground_wet,
        "last_change_minute": last_change_minute,
    }


def validate(state: dict) -> None:
    exact_keys(state, {"schema", "revision", "scene_index", "minute",
                       "entities", "regions", "events"}, "STATE_SCHEMA_INVALID")
    check(state["schema"] == SCHEMA, "STATE_VERSION_INVALID")
    check(type(state["minute"]) is int and state["minute"] >= 0,
          "STATE_MINUTE_INVALID")
    check(type(state["revision"]) is int and state["revision"] >= 0,
          "STATE_REVISION_INVALID")
    check(type(state["scene_index"]) is int and state["scene_index"] >= 0,
          "STATE_SCENE_INDEX_INVALID")
    check(isinstance(state["entities"], dict) and
          isinstance(state["regions"], dict) and
          isinstance(state["events"], list), "STATE_COLLECTIONS_INVALID")
    event_ids = []
    for e in state["events"]:
        exact_keys(e, EVENT_FIELDS, "STATE_EVENT_FORMAT_INVALID")
        event_ids.append(e["event_id"])
    check(len(set(event_ids)) == len(event_ids), "DUPLICATE_EVENT_ID")
    for entity_id, e in state["entities"].items():
        exact_keys(e, {
            "entity_id", "kind", "lifecycle", "location", "owner", "holder",
            "worn_by", "parent_id", "appearance", "dimensions", "condition",
            "size", "traits", "knowledge", "last_action_minute",
        }, f"ENTITY_SCHEMA_INVALID:{entity_id}")
        check(isinstance(entity_id, str) and entity_id and
              e["entity_id"] == entity_id, f"ENTITY_ID_INVALID:{entity_id}")
        check(e["kind"] in KINDS, f"ENTITY_KIND_INVALID:{entity_id}")
        check(e["lifecycle"] in LIFECYCLES, f"LIFECYCLE_INVALID:{entity_id}")
        check(isinstance(e["location"], str) and e["location"],
              f"ENTITY_LOCATION_INVALID:{entity_id}")
        for ref_field in ("owner", "holder", "worn_by", "parent_id"):
            ref = e[ref_field]
            check(ref is None or (
                isinstance(ref, str) and ref in state["entities"]
            ), f"ENTITY_REFERENCE_INVALID:{entity_id}:{ref_field}")
        check(e["owner"] != entity_id and e["holder"] != entity_id
              and e["worn_by"] != entity_id and e["parent_id"] != entity_id,
              f"ENTITY_SELF_REFERENCE:{entity_id}")
        a = e["appearance"]
        exact_keys(a, APPEARANCE_FIELDS, f"APPEARANCE_SCHEMA_INVALID:{entity_id}")
        check(a["color"] in COLORS and
              all(isinstance(a[key], str) and a[key]
                  for key in APPEARANCE_FIELDS),
              f"APPEARANCE_INVALID:{entity_id}")
        d = e["dimensions"]
        exact_keys(d, DIM_FIELDS, f"DIMENSIONS_SCHEMA_INVALID:{entity_id}")
        check(all(number(d[key], null_ok=True) for key in DIM_FIELDS),
              f"DIMENSIONS_INVALID:{entity_id}")
        condition = e["condition"]
        exact_keys(condition, CONDITION_FIELDS,
                   f"CONDITION_SCHEMA_INVALID:{entity_id}")
        check(number(condition["integrity_pct"], maxval=100, null_ok=True)
              and condition["functional"] in FUNCTIONS and
              condition["age"] in AGES,
              f"CONDITION_INVALID:{entity_id}")
        check(e["size"] in SIZES, f"SIZE_INVALID:{entity_id}")
        check(isinstance(e["traits"], dict) and all(
            isinstance(k, str) and k for k in e["traits"]
        ), f"TRAITS_INVALID:{entity_id}")
        check(isinstance(e["knowledge"], list) and
              len(e["knowledge"]) == len(set(e["knowledge"])) and
              all(isinstance(k, str) and k for k in e["knowledge"]),
              f"KNOWLEDGE_INVALID:{entity_id}")
        check(type(e["last_action_minute"]) is int and
              0 <= e["last_action_minute"] <= state["minute"],
              f"ENTITY_TIME_INVALID:{entity_id}")
        if e["kind"] != "CHARACTER":
            check(not e["knowledge"] and not e["traits"],
                  f"NONCHARACTER_PROFILE_INVALID:{entity_id}")
        if e["kind"] == "CHARACTER":
            check(e["holder"] is None and e["worn_by"] is None,
                  f"CHARACTER_OWNERSHIP_INVALID:{entity_id}")
        if e["kind"] != "WEARABLE":
            check(e["worn_by"] is None, f"NOT_WEARABLE:{entity_id}")
        check(not (e["holder"] is not None and e["worn_by"] is not None),
              f"ITEM_HELD_AND_WORN:{entity_id}")
        if e["lifecycle"] == "DESTROYED":
            check(e["holder"] is None and e["worn_by"] is None,
                  f"DESTROYED_STILL_IN_USE:{entity_id}")
        if e["holder"]:
            h = state["entities"][e["holder"]]
            check(h["kind"] == "CHARACTER" and
                  h["lifecycle"] != "DESTROYED" and
                  h["location"] == e["location"],
                  f"HOLDER_LOCATION_MISMATCH:{entity_id}")
        if e["worn_by"]:
            c = state["entities"][e["worn_by"]]
            check(c["kind"] == "CHARACTER" and
                  c["lifecycle"] != "DESTROYED" and
                  c["location"] == e["location"],
                  f"WORN_LOCATION_MISMATCH:{entity_id}")
            check(e["size"] == "UNKNOWN" or c["size"] == "UNKNOWN" or
                  e["size"] == c["size"],
                  f"CLOTHING_SIZE_MISMATCH:{entity_id}")
        if e["parent_id"]:
            check(e["parent_id"] in state["entities"], "PARENT_ENTITY_MISSING")
    for region, env in state["regions"].items():
        check(isinstance(region, str) and region,
              "REGION_ID_INVALID")
        exact_keys(env, {
            "weather", "temperature_c", "wind_kph", "cloud_cover_pct",
            "precip_mm_h", "ground_wet", "last_change_minute",
        }, f"ENVIRONMENT_SCHEMA_INVALID:{region}")
        check(env["weather"] in WEATHER, f"WEATHER_INVALID:{region}")
        check(number(env["temperature_c"], minval=-100, maxval=80, null_ok=True)
              and number(env["wind_kph"], maxval=400, null_ok=True)
              and number(env["cloud_cover_pct"], maxval=100, null_ok=True)
              and number(env["precip_mm_h"], maxval=300, null_ok=True),
              f"ENVIRONMENT_VALUES_INVALID:{region}")
        check(env["ground_wet"] is None or type(env["ground_wet"]) is bool,
              f"GROUND_WET_INVALID:{region}")
        check(type(env["last_change_minute"]) is int and
              0 <= env["last_change_minute"] <= state["minute"],
              f"ENVIRONMENT_TIME_INVALID:{region}")
        if env["weather"] in ("RAIN", "STORM"):
            check(env["ground_wet"] is True,
                  f"RAIN_REQUIRES_WET_GROUND:{region}")
    canonical(state)  # Reject non-JSON serializable or NaN stored traits.


def initial_state(*, entities: dict, regions: dict, minute=0) -> dict:
    state = {
        "schema": SCHEMA, "revision": 0, "scene_index": 0,
        "minute": minute, "entities": deepcopy(entities),
        "regions": deepcopy(regions), "events": [],
    }
    validate(state)
    return state


def loadout(state: dict, character_id: str) -> dict:
    """Derived graph prevents stale denormalized inventory and clothing lists."""
    validate(state)
    person = state["entities"].get(character_id)
    check(person is not None and person["kind"] == "CHARACTER",
          "LOADOUT_CHARACTER_UNKNOWN")
    return {
        "character_id": character_id,
        "worn": sorted(k for k, v in state["entities"].items()
                       if v["worn_by"] == character_id and
                       v["lifecycle"] != "DESTROYED"),
        "held": sorted(k for k, v in state["entities"].items()
                       if v["holder"] == character_id and
                       v["lifecycle"] != "DESTROYED"),
        "owned": sorted(k for k, v in state["entities"].items()
                        if v["owner"] == character_id),
        "knowledge": list(person["knowledge"]),
        "traits": deepcopy(person["traits"]),
    }


def event_contract(event: dict) -> None:
    exact_keys(event, EVENT_FIELDS, "EVENT_SCHEMA_INVALID")
    check(isinstance(event["event_id"], str) and event["event_id"],
          "EVENT_ID_INVALID")
    check(event["type"] in TYPE_FIELDS, "EVENT_TYPE_UNSUPPORTED")
    check(type(event["at_minute"]) is int and event["at_minute"] >= 0,
          "EVENT_TIME_INVALID")
    check(isinstance(event["reason"], str) and event["reason"].strip(),
          "EVENT_CAUSE_MISSING")
    check(isinstance(event["evidence_ref"], str) and
          event["evidence_ref"].strip(), "EVENT_EVIDENCE_MISSING")
    exact_keys(event["payload"], TYPE_FIELDS[event["type"]],
               f"EVENT_PAYLOAD_INVALID:{event['type']}")
    fingerprint(event)


def _entity(state, entity_id, kind=None):
    e = state["entities"].get(entity_id)
    check(isinstance(e, dict), f"ENTITY_NOT_FOUND:{entity_id}")
    if kind:
        check(e["kind"] == kind, f"ENTITY_KIND_MISMATCH:{entity_id}")
    check(e["lifecycle"] != "DESTROYED",
          f"ENTITY_DESTROYED:{entity_id}")
    return e


def _change(fieldset, payload, valid_fieldset, code):
    field = payload["field"]
    check(field in valid_fieldset and fieldset[field] == payload["old"], code)
    check(fieldset[field] != payload["new"], "NO_OP_CHANGE")
    fieldset[field] = deepcopy(payload["new"])


def apply_event(state: dict, event: dict, *,
                approvals: dict[str, str],
                travel_minutes: dict[str, int] | None = None,
                world_rules: frozenset[str] = frozenset()) -> dict:
    """One atomic, authorized, deterministic event -> one snapshot revision."""
    validate(state)
    event_contract(event)
    eid = event["event_id"]
    check(isinstance(approvals, dict) and approvals.get(eid) == fingerprint(event),
          f"EVENT_NOT_APPROVED:{eid}")
    check(all(item["event_id"] != eid for item in state["events"]),
          f"EVENT_ID_REPLAY:{eid}")
    check(event["at_minute"] >= state["minute"], "WORLD_TIME_BACKWARDS")
    out = deepcopy(state)
    out["minute"] = event["at_minute"]
    p = event["payload"]
    typ = event["type"]

    if typ == "INTRODUCE_ENTITY":
        entity_id = p["entity_id"]
        check(entity_id not in out["entities"], "ENTITY_ALREADY_EXISTS")
        check(isinstance(entity_id, str) and entity_id, "NEW_ID_INVALID")
        check(isinstance(p["entity"], dict) and
              p["entity"].get("entity_id") == entity_id,
              "INTRODUCED_ENTITY_INVALID")
        check(p["parent_id"] is None or p["parent_id"] in out["entities"],
              "ANCESTOR_UNKNOWN")
        copy = deepcopy(p["entity"])
        copy["parent_id"] = p["parent_id"]
        out["entities"][entity_id] = copy

    elif typ in ("CHANGE_APPEARANCE", "CHANGE_CONDITION", "CHANGE_DIMENSION"):
        entity = _entity(out, p["entity_id"])
        check(entity["kind"] != "CHARACTER" or typ != "CHANGE_DIMENSION",
              "CHARACTER_DIMENSION_CHANGE_REQUIRES_NEW_PROTOCOL")
        target, allowed, code = {
            "CHANGE_APPEARANCE": (
                entity["appearance"], APPEARANCE_FIELDS, "APPEARANCE_CAS_MISMATCH"),
            "CHANGE_CONDITION": (
                entity["condition"], CONDITION_FIELDS, "CONDITION_CAS_MISMATCH"),
            "CHANGE_DIMENSION": (
                entity["dimensions"], DIM_FIELDS, "DIMENSION_CAS_MISMATCH"),
        }[typ]
        if typ == "CHANGE_DIMENSION":
            check(isinstance(p["world_rule_id"], str) and
                  p["world_rule_id"] in world_rules,
                  "DIMENSION_CHANGE_WORLD_RULE_REQUIRED")
        _change(target, p, allowed, code)

    elif typ == "MOVE_CHARACTER":
        char_id = p["character_id"]
        char = _entity(out, char_id, "CHARACTER")
        destination = p["to_location"]
        check(isinstance(destination, str) and destination,
              "MOVE_DESTINATION_INVALID")
        origin = char["location"]
        check(origin != destination, "NO_OP_MOVE")
        minutes = (travel_minutes or {}).get(f"{origin}->{destination}")
        check(type(minutes) is int and minutes >= 0,
              "MOVE_UNKNOWN_ROUTE")
        check(event["at_minute"] - char["last_action_minute"] >= minutes,
              "MOVE_TRAVEL_TOO_FAST")
        char["location"] = destination
        char["last_action_minute"] = event["at_minute"]
        for entity in out["entities"].values():
            if entity["holder"] == char_id or entity["worn_by"] == char_id:
                entity["location"] = destination

    elif typ == "TRANSFER_HOLDER":
        obj = _entity(out, p["entity_id"])
        check(obj["kind"] != "CHARACTER", "TRANSFER_CHARACTER_FORBIDDEN")
        from_id, to_id = p["from_id"], p["to_id"]
        check(obj["holder"] == from_id and from_id != to_id,
              "TRANSFER_SOURCE_INVALID")
        check(obj["worn_by"] is None, "TRANSFER_ITEM_WORN")
        recipient = _entity(out, to_id, "CHARACTER")
        check(recipient["location"] == obj["location"],
              "TRANSFER_RECIPIENT_NOT_COLOCATED")
        if from_id is not None:
            sender = _entity(out, from_id, "CHARACTER")
            check(sender["location"] == obj["location"],
                  "TRANSFER_SENDER_NOT_COLOCATED")
        obj["holder"] = to_id

    elif typ == "WEAR":
        obj = _entity(out, p["entity_id"], "WEARABLE")
        char = _entity(out, p["character_id"], "CHARACTER")
        check(obj["worn_by"] is None, "ALREADY_WORN")
        check(obj["holder"] in (None, p["character_id"]),
              "WEAR_NOT_IN_POSSESSION")
        check(obj["location"] == char["location"], "WEAR_NOT_COLOCATED")
        check(obj["size"] == "UNKNOWN" or char["size"] == "UNKNOWN" or
              obj["size"] == char["size"], "WEAR_SIZE_MISMATCH")
        obj["holder"] = None
        obj["worn_by"] = p["character_id"]

    elif typ == "REMOVE_WEAR":
        obj = _entity(out, p["entity_id"], "WEARABLE")
        _entity(out, p["character_id"], "CHARACTER")
        check(obj["worn_by"] == p["character_id"], "REMOVE_WRONG_WEARER")
        obj["worn_by"] = None
        obj["holder"] = p["character_id"]

    elif typ == "LEARN_FACT":
        person = _entity(out, p["character_id"], "CHARACTER")
        check(isinstance(p["fact_id"], str) and p["fact_id"],
              "FACT_ID_INVALID")
        check(p["fact_id"] not in person["knowledge"], "FACT_ALREADY_KNOWN")
        person["knowledge"].append(p["fact_id"])

    elif typ == "UPDATE_CHARACTER_TRAIT":
        person = _entity(out, p["character_id"], "CHARACTER")
        trait = p["trait"]
        check(isinstance(trait, str) and trait in person["traits"],
              "CHARACTER_TRAIT_NOT_DECLARED")
        check(person["traits"][trait] == p["old"] and
              p["old"] != p["new"], "CHARACTER_TRAIT_CAS_MISMATCH")
        person["traits"][trait] = deepcopy(p["new"])

    elif typ == "SET_WEATHER":
        region = p["region_id"]
        env = out["regions"].get(region)
        check(isinstance(env, dict), "REGION_UNKNOWN")
        check(env["weather"] == p["old_weather"] and
              p["old_weather"] != p["new_weather"],
              "WEATHER_CAS_MISMATCH")
        delta = event["at_minute"] - env["last_change_minute"]
        exception = p["exception_rule_id"]
        if exception is None:
            check(delta >= 15, "WEATHER_CHANGE_TOO_ABRUPT")
            old_temp = env["temperature_c"]
            new_temp = p["temperature_c"]
            if old_temp is not None and new_temp is not None:
                check(abs(new_temp - old_temp) <= max(1.0, delta / 10 * 2),
                      "WEATHER_TEMPERATURE_JUMP")
        else:
            check(isinstance(exception, str) and
                  exception in world_rules, "WEATHER_EXCEPTION_NOT_AUTHORIZED")
        out["regions"][region] = environment_template(
            p["new_weather"], temperature_c=p["temperature_c"],
            wind_kph=p["wind_kph"], cloud_cover_pct=p["cloud_cover_pct"],
            precip_mm_h=p["precip_mm_h"], ground_wet=p["ground_wet"],
            last_change_minute=event["at_minute"],
        )

    elif typ == "RETIRE_ENTITY":
        obj = _entity(out, p["entity_id"])
        check(obj["kind"] != "CHARACTER", "CHARACTER_RETIRE_NOT_SUPPORTED")
        check(obj["holder"] is None and obj["worn_by"] is None,
              "RETIRE_ITEM_IN_USE")
        obj["lifecycle"] = "DESTROYED"

    elif typ == "INTERACT_ENTITY":
        item = _entity(out, p["entity_id"])
        actor = _entity(out, p["actor_id"], "CHARACTER")
        check(actor["location"] == item["location"], "INTERACTION_NOT_COLOCATED")
        check(isinstance(p["interaction"], str) and p["interaction"].strip(),
              "INTERACTION_INVALID")
        check(p["interaction"] in ("OBSERVE", "LOOK_AT") or
              item["holder"] in (None, p["actor_id"]),
              "INTERACTION_ITEM_HELD_BY_OTHER")

    elif typ == "ADVANCE_SCENE":
        check(isinstance(p["scene_key"], str) and p["scene_key"],
              "SCENE_KEY_MISSING")
        out["scene_index"] += 1

    out["revision"] += 1
    out["events"].append(deepcopy(event))
    validate(out)
    return out
