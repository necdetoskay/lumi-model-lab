"""SERA M3.4: strict model event -> typed v0.2 candidate normalization.

NEVER a commit authorizer. Does not infer missing event arguments, facts, people,
object IDs, durations, world rules, scene times or before/after state. In
particular, an empty model argument dictionary must fail closed.
"""
from __future__ import annotations

from hashlib import sha256
import json

from experiments.sera.coverage import (
    CoverageError, SUPPORTED_MODALITIES, validate_report, prose_hash,
)
from experiments.sera.world_state_v02 import (
    WorldStateError, TYPE_FIELDS, validate as validate_world, canonical,
)

SCHEMA = "sera.typed-event-candidate.v0.4"
# The only mappings supported in the initial bridge have lossless, exact keys.
MAPPINGS = {
    "INTERACT_OBJECT": (
        frozenset({"actor_id", "object_id", "interaction"}),
        "INTERACT_ENTITY",
    ),
    "MOVE_CHARACTER": (
        frozenset({"character_id", "to"}),
        "MOVE_CHARACTER",
    ),
    "TRANSFER_OBJECT": (
        frozenset({"object_id", "from_id", "to_id"}),
        "TRANSFER_HOLDER",
    ),
    "LEARN_FACT": (
        frozenset({"character_id", "fact_id"}),
        "LEARN_FACT",
    ),
    "TELL_FACT": (
        frozenset({"from_id", "to_id", "fact_id"}),
        "LEARN_FACT",
    ),
}
UNMAPPED = frozenset({
    "CREATE_ENTITY", "UPDATE_OBJECT", "RECORD_FACT", "OPEN_THREAD",
    "RESOLVE_THREAD", "MOVE_OBJECT", "UNMAPPED_STATE_CHANGE",
})


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _id(digest_payload):
    return "candidate_" + sha256(
        canonical(digest_payload).encode("utf-8")
    ).hexdigest()[:24]


def canonicalize_event(event: dict, *, entry: dict) -> dict:
    """Strict per-type argument contract and canonical reducer mapping.

    Does NOT grant model permission to call apply_event or mutate world state.
    The output contains no absolute world cursor and no state effects.
    """
    validate_world(entry)
    kind = event["type"]
    args = event["arguments"]
    if kind not in MAPPINGS:
        raise CoverageError(f"EVENT_V04_UNSUPPORTED:{kind}")
    required, target_type = MAPPINGS[kind]
    if set(args) != required:
        raise CoverageError(f"EVENT_V04_REQUIRED_ARGUMENTS:{kind}")
    if not all(_text(args[key]) for key in required):
        raise CoverageError(f"EVENT_V04_ARGUMENT_VALUE_INVALID:{kind}")
    entities = entry["entities"]
    persons = {"actor_id", "character_id", "from_id", "to_id"}
    objects = {"object_id"}
    for key in required & persons:
        ident = args[key]
        if ident not in entities or entities[ident]["kind"] != "CHARACTER":
            raise CoverageError(f"EVENT_V04_CHARACTER_UNKNOWN:{key}:{ident}")
    for key in required & objects:
        ident = args[key]
        if ident not in entities or entities[ident]["kind"] == "CHARACTER":
            raise CoverageError(f"EVENT_V04_OBJECT_UNKNOWN:{ident}")

    if kind == "INTERACT_OBJECT":
        if args["interaction"] not in (
            "LOOK_AT", "OBSERVE", "LISTEN_TO", "TOUCH", "EXAMINE"
        ):
            raise CoverageError("EVENT_V04_INTERACTION_UNKNOWN")
        return {"world_type": target_type,
                "payload": {"actor_id": args["actor_id"],
                            "entity_id": args["object_id"],
                            "interaction": args["interaction"]},
                "participant_ids": [args["actor_id"]],
                "object_ids": [args["object_id"]]}
    if kind == "MOVE_CHARACTER":
        if args["to"] == entities[args["character_id"]]["location"]:
            raise CoverageError("EVENT_V04_NO_OP_MOVE")
        return {"world_type": target_type,
                "payload": {"character_id": args["character_id"],
                            "to_location": args["to"]},
                "participant_ids": [args["character_id"]],
                "object_ids": []}
    if kind == "TRANSFER_OBJECT":
        if args["from_id"] == args["to_id"]:
            raise CoverageError("EVENT_V04_TRANSFER_TO_SELF")
        return {"world_type": target_type,
                "payload": {"entity_id": args["object_id"],
                            "from_id": args["from_id"],
                            "to_id": args["to_id"]},
                "participant_ids": [args["from_id"], args["to_id"]],
                "object_ids": [args["object_id"]]}
    if kind == "LEARN_FACT":
        # The v0.2 reducer has no signed/typed ontology of objective facts.
        # Restrict this pilot to explicitly attributed, already named claims.
        if not args["fact_id"].startswith("claim:"):
            raise CoverageError("EVENT_V04_UNATTRIBUTED_FACT")
        return {"world_type": target_type,
                "payload": dict(args),
                "participant_ids": [args["character_id"]],
                "object_ids": []}
    if kind == "TELL_FACT":
        if not args["fact_id"].startswith("claim:"):
            raise CoverageError("EVENT_V04_UNATTRIBUTED_FACT")
        if args["fact_id"] not in entities[args["from_id"]]["knowledge"]:
            raise CoverageError("EVENT_V04_SPEAKER_DOES_NOT_KNOW_CLAIM")
        return {"world_type": target_type,
                "payload": {"character_id": args["to_id"],
                            "fact_id": args["fact_id"]},
                "participant_ids": [args["from_id"], args["to_id"]],
                "object_ids": []}
    raise CoverageError("EVENT_V04_UNREACHABLE")


def normalize_report(*, report: dict, role: str, prose: str,
                     scene_key: str, entry: dict) -> list[dict]:
    """Normalize a REPORT but never silently drop malformed/unsupported events.

    Status HOLD and error code are returned for every discovered event.
    Only explicitly compatible operations produce reducer-ready proposals.
    """
    validate_world(entry)
    validate_report(report, role=role, prose=prose, scene_key=scene_key,
                    entry_revision=entry["revision"])
    rows = []
    for ordinal, event in enumerate(report["events"], start=1):
        quote = prose[event["start"]:event["end"]]
        original = {
            "type": event["type"],
            "arguments": event["arguments"],
            "at": event["at"],
            "modality": event["modality"],
        }
        row = {
            "schema": SCHEMA,
            "id": _id({
                "scene": scene_key, "original": original,
                "start": event["start"], "end": event["end"],
            }),
            "source": role,
            "scene_key": scene_key,
            "entry_revision": entry["revision"],
            "prose_sha256": prose_hash(prose),
            "ordinal": ordinal,
            "evidence": {
                "start": event["start"], "end": event["end"],
                "quote": quote,
            },
            "source_event": original,
            "time": {
                "exact_minute": event["at"],
                "scene_ordinal": ordinal,
                "resolved_world_cursor": None,
                "time_resolution": "UNRESOLVED",
            },
            "world_type": None, "payload": None,
            "participant_ids": [], "object_ids": [],
            "status": "HOLD", "blockers": [],
        }
        try:
            mapped = canonicalize_event(event, entry=entry)
            row.update(mapped)
        except CoverageError as exc:
            row["blockers"].append(exc.code)
        if event["modality"] != "ASSERTED":
            row["blockers"].append("EVENT_V04_NON_ASSERTED_MODALITY")
        if event["at"] is None:
            row["blockers"].append("EVENT_V04_RELATIVE_TIME_UNRESOLVED")
        # Even a fully mapped event is not semantic/DB authorization.
        if not row["blockers"]:
            row["status"] = "TYPED_PENDING_SEMANTIC_AND_AUTHORITY"
        rows.append(row)
    return rows


def event_fingerprint(row: dict) -> tuple:
    """Signature for two independently normalized proposals.

    Ignore model source IDs and quote offsets, but NEVER ignore payload,
    modality or time. Duplicate signatures require separate disambiguation.
    """
    return (
        row["world_type"],
        canonical(row["payload"]),
        row["source_event"]["modality"],
        row["time"]["exact_minute"],
    )


def _time_consistent(row: dict, *, scene_window: dict,
                     previous_cursor: int, resolution: dict) -> dict:
    """Validate an APPLICATION-supplied world cursor.

    An unknown prose clock time REMAINS null. The resolved cursor is a
    simulation/ordering index, not a claim that the character acted at it.
    """
    needed = {"candidate_id", "authority", "resolved_world_cursor",
              "basis", "scene_window_sha256"}
    if not isinstance(resolution, dict) or set(resolution) != needed:
        raise CoverageError("EVENT_V04_TIME_RESOLUTION_SCHEMA_INVALID")
    if resolution["candidate_id"] != row["id"] or (
        resolution["authority"] != "APPLICATION"
    ):
        raise CoverageError("EVENT_V04_TIME_AUTHORITY_INVALID")
    bounds = scene_window
    if not isinstance(bounds, dict) or set(bounds) != {
        "scene_key", "earliest_minute", "latest_minute", "entry_revision"
    }:
        raise CoverageError("EVENT_V04_WINDOW_SCHEMA_INVALID")
    if bounds["scene_key"] != row["scene_key"] or (
        bounds["entry_revision"] != row["entry_revision"]
    ):
        raise CoverageError("EVENT_V04_WINDOW_SCENE_MISMATCH")
    if resolution["scene_window_sha256"] != sha256(
        canonical(bounds).encode("utf-8")
    ).hexdigest():
        raise CoverageError("EVENT_V04_WINDOW_HASH_MISMATCH")
    minute = resolution["resolved_world_cursor"]
    low, high = bounds["earliest_minute"], bounds["latest_minute"]
    if not all(type(x) is int and x >= 0 for x in (low, high, minute)) or low > high:
        raise CoverageError("EVENT_V04_WINDOW_RANGE_INVALID")
    if minute < max(low, previous_cursor) or minute > high:
        raise CoverageError("EVENT_V04_CURSOR_OUT_OF_WINDOW")
    if row["time"]["exact_minute"] is not None and (
        row["time"]["exact_minute"] != minute
    ):
        raise CoverageError("EVENT_V04_EXACT_TIME_CONFLICT")
    if not _text(resolution["basis"]) or resolution["basis"].startswith("MODEL"):
        raise CoverageError("EVENT_V04_CURSOR_BASIS_INVALID")
    answer = dict(row["time"])
    answer["resolved_world_cursor"] = minute
    answer["time_resolution"] = "APPLICATION_CURSOR_NOT_NARRATIVE_FACT"
    return answer


def resolve_time(*, row: dict, scene_window: dict,
                 previous_cursor: int, resolution: dict) -> dict:
    result = dict(row)
    result["time"] = _time_consistent(row, scene_window=scene_window,
                                      previous_cursor=previous_cursor,
                                      resolution=resolution)
    # This is still just a proposed world event, not an authorization.
    result["blockers"] = [
        blocker for blocker in row["blockers"]
        if blocker != "EVENT_V04_RELATIVE_TIME_UNRESOLVED"
    ]
    result["status"] = (
        "TYPED_PENDING_SEMANTIC_AND_AUTHORITY" if not result["blockers"]
        else "HOLD"
    )
    return result
