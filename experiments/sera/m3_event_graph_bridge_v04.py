"""SERA v0.4: bind M2 typed events + M3 JEV evidence into advisory graph drafts.

No database connection, no trusted application approval creation, no model calls.
This is a diagnostic bridge. Even all-green evidence NEVER commits world state.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256

from experiments.sera.coverage import CoverageError, reconcile, prose_hash
from experiments.sera.event_graph_v03 import (
    SCHEMA as GRAPH_SCHEMA, world_effects,
)
from experiments.sera.jev_verifier import (
    build_atomic_questions, adjudicate,
)
from experiments.sera.typed_event_bridge_v04 import (
    canonicalize_event, event_fingerprint, normalize_report, resolve_time,
)
from experiments.sera.world_state_v02 import (
    canonical, validate as validate_world, apply_event, fingerprint,
    WorldStateError,
)

SCHEMA = "sera.m3-graph-advisory.v0.4"
ACTION_MAP = {
    "INTERACT_ENTITY": ("OBSERVATION", "OBSERVED_ACTION"),
    "MOVE_CHARACTER": ("MOVEMENT", "OBSERVED_ACTION"),
    "TRANSFER_HOLDER": ("TRANSFER", "OBSERVED_ACTION"),
    "LEARN_FACT": ("TESTIMONY", "REPORTED_CLAIM"),
}


def verify_verdict(*, bundle: dict, verdict: dict) -> dict:
    """Re-adjudicate all exact claim IDs. No invented/missing JEV labels allowed.

    Verifies structural correspondence, not the origin or quality of a model.
    Live provider authenticity requires separate server-side attestation.
    """
    if not isinstance(verdict, dict) or not isinstance(verdict.get("judgments"), list):
        raise CoverageError("BRIDGE_JEV_VERDICT_INVALID")
    judgments = verdict["judgments"]
    if len(judgments) != len(bundle["questions"]):
        raise CoverageError("BRIDGE_JEV_CLAIM_COUNT_MISMATCH")
    if any(not isinstance(row, dict) or
           row.get("claim_id") not in bundle["questions"]
           for row in judgments):
        raise CoverageError("BRIDGE_JEV_CLAIM_UNKNOWN")
    answers = {}
    for row in judgments:
        qid = row["claim_id"]
        if qid in answers:
            raise CoverageError("BRIDGE_JEV_CLAIM_DUPLICATE")
        answers[qid] = {
            "choice": row.get("choice"),
            "confidence": row.get("confidence"),
        }
    expected = adjudicate(bundle=bundle, answers=answers)
    if canonical(expected) != canonical(verdict):
        raise CoverageError("BRIDGE_JEV_VERDICT_TAMPERED")
    return expected


def draft_graph(row: dict, *, entry: dict, scene_key: str) -> dict | None:
    """Create a NON-COMMITTABLE metadata draft from a complete typed row.

    Participant/object links are derived from reducer IDs, not invented by
    the language model. Any moved carried/worn items are included.
    """
    if row["world_type"] is None or row["payload"] is None:
        return None
    world_type = row["world_type"]
    event_type, epistemic = ACTION_MAP[world_type]
    arg = row["payload"]
    people = []
    objects = []

    if world_type == "INTERACT_ENTITY":
        people = [{"id": arg["actor_id"], "role": "ACTOR"}]
        objects = [{"id": arg["entity_id"], "role": "TOOL"}]
    elif world_type == "TRANSFER_HOLDER":
        people = [
            {"id": arg["from_id"], "role": "ACTOR"},
            {"id": arg["to_id"], "role": "RECIPIENT"},
        ]
        objects = [{"id": arg["entity_id"], "role": "AFFECTED"}]
    elif world_type == "MOVE_CHARACTER":
        people = [{"id": arg["character_id"], "role": "ACTOR"}]
        objects = [
            {"id": eid, "role": "AFFECTED"}
            for eid, e in sorted(entry["entities"].items())
            if e["holder"] == arg["character_id"] or
               e["worn_by"] == arg["character_id"]
        ]
    elif world_type == "LEARN_FACT":
        if row["source_event"]["type"] == "TELL_FACT":
            people = [
                {"id": row["source_event"]["arguments"]["from_id"],
                 "role": "SPEAKER"},
                {"id": arg["character_id"], "role": "LISTENER"},
            ]
        else:
            people = [{"id": arg["character_id"], "role": "AFFECTED"}]

    char = people[0]["id"] if people else None
    if char not in entry["entities"]:
        raise CoverageError("BRIDGE_LOCATION_ACTOR_UNKNOWN")
    location = entry["entities"][char]["location"]
    start, end = row["evidence"]["start"], row["evidence"]["end"]
    at = row["time"]["resolved_world_cursor"]
    if at is None:
        at = row["time"]["exact_minute"]
    return {
        "schema": GRAPH_SCHEMA,
        "event_id": "preview_" + row["id"],
        "event_type": event_type,
        "scene_id": scene_key,
        "location": location,
        "epistemic": epistemic,
        "participants": people,
        "objects": objects,
        "time": {
            "ordinal": row["ordinal"],
            "earliest_minute": None,
            "latest_minute": None,
            "exact_minute": row["time"]["exact_minute"],
        },
        "caused_by": [],
        "preconditions": [],
        "evidence": {
            "prose_sha256": row["prose_sha256"],
            "start": start, "end": end, "quote": row["evidence"]["quote"],
        },
        "world_event": None if at is None else {
            "event_id": "preview_" + row["id"],
            "type": world_type,
            "at_minute": at,
            "reason": "UNTRUSTED_DIAGNOSTIC_ONLY",
            "evidence_ref": f"{row['prose_sha256']}#{start}:{end}",
            "payload": arg,
        },
        "status": "DRAFT_NOT_AUTHORIZED",
        "commit_authorized": False,
    }


def inspect_scene(*, prose: str, scene_key: str, entry: dict,
                  registry: dict, writer: dict, independent: dict,
                  verdict: dict | None = None,
                  candidate_lexicon: dict | None = None) -> dict:
    """Produce an audit record, never a trusted grant.

    If one source omits or fabricates an event, the result stays HOLD.
    """
    validate_world(entry)
    coverage = reconcile(
        prose=prose, scene_key=scene_key, entry_revision=entry["revision"],
        registry=registry, writer=writer, independent=independent,
        candidate_lexicon=candidate_lexicon,
    )
    w = normalize_report(
        report=writer, role="WRITER", prose=prose,
        scene_key=scene_key, entry=entry,
    )
    independent_rows = normalize_report(
        report=independent, role="INDEPENDENT", prose=prose,
        scene_key=scene_key, entry=entry,
    )
    w_signatures = Counter(event_fingerprint(row) for row in w)
    i_signatures = Counter(event_fingerprint(row) for row in independent_rows)
    disagreements = []
    for signature in sorted(set(w_signatures) | set(i_signatures), key=canonical):
        if w_signatures[signature] != i_signatures[signature]:
            disagreements.append({
                "signature": list(signature),
                "writer_count": w_signatures[signature],
                "independent_count": i_signatures[signature],
            })

    bundle = build_atomic_questions(
        prose=prose, scene_key=scene_key, entry_revision=entry["revision"],
        coverage=coverage, registry=registry, writer=writer,
        independent=independent, candidate_lexicon=candidate_lexicon,
    )
    checked = (verify_verdict(bundle=bundle, verdict=verdict)
               if verdict is not None else None)
    # A structurally valid verdict can still have an unqualified provider
    # source. Do not promote it to an app-owned review.
    missing_semantic = (
        checked is None or checked["next_action"] !=
        "PENDING_DETERMINISTIC_AND_COMPLETENESS_REVIEW"
    )
    flags = []
    if coverage["status"] != "RECONCILED_PENDING_SEMANTIC":
        flags.append("M2_UNRESOLVED")
    if disagreements:
        flags.append("TYPED_EVENT_DISAGREEMENT")
    if any(row["blockers"] for row in w + independent_rows):
        flags.append("TYPED_EVENT_BLOCKERS")
    if missing_semantic:
        flags.append("JEV_NOT_CLEARED")
    if not w and not independent_rows:
        flags.append("NO_TYPED_EVENTS")

    return {
        "schema": SCHEMA, "scene_key": scene_key,
        "entry_revision": entry["revision"],
        "prose_sha256": prose_hash(prose),
        "m2_status": coverage["status"],
        "m2_findings": coverage["findings"],
        "jev_action": None if checked is None else checked["next_action"],
        "writer": w, "independent": independent_rows,
        "typed_disagreements": disagreements,
        "proposals": [draft_graph(row, entry=entry, scene_key=scene_key)
                      for row in w],
        "flags": flags,
        "status": ("PENDING_TRUSTED_HUMAN_AND_APP_REVIEW" if not flags else
                   "HOLD"),
        "commit_authorized": False,
        "application_review_issued": False,
        "production_db_writes": 0,
    }


def shadow_reduce(*, graph_draft: dict, entry: dict, travel_minutes: dict,
                  world_rules: frozenset[str] = frozenset()) -> dict:
    """Pure diagnostic replay of ONE typed candidate, never a database commit.

    An ephemeral fingerprint is supplied solely to exercise v0.2 reducer's
    physical checks. It is NOT an application approval or proof of narrative
    entailment; no approval token is stored, issued or returned.
    """
    validate_world(entry)
    if not isinstance(graph_draft, dict) or graph_draft.get("status") != (
        "DRAFT_NOT_AUTHORIZED"
    ) or graph_draft.get("commit_authorized") is not False:
        raise CoverageError("BRIDGE_SHADOW_NOT_UNAUTHORIZED_DRAFT")
    world_event = graph_draft.get("world_event")
    if not isinstance(world_event, dict):
        return {
            "status": "HOLD_WORLD_CURSOR_UNRESOLVED",
            "effects": None,
            "commit_authorized": False,
            "db_writes": 0,
        }
    # Self-signed ephemeral checksum here is an INPUT required by the pure
    # reducer. It grants nothing in EventGraphStore or any external runtime.
    try:
        after = apply_event(
            entry, world_event,
            approvals={world_event["event_id"]: fingerprint(world_event)},
            travel_minutes=travel_minutes, world_rules=world_rules,
        )
    except WorldStateError as exc:
        return {
            "status": "HOLD_PHYSICAL_INVARIANT",
            "error_code": exc.code,
            "effects": None,
            "commit_authorized": False,
            "db_writes": 0,
        }
    return {
        "status": "PHYSICAL_SHADOW_VALID_NOT_STORY_ACCEPTED",
        "entry_revision": entry["revision"],
        "exit_revision": after["revision"],
        "effects": world_effects(entry, after),
        "commit_authorized": False,
        "db_writes": 0,
    }
