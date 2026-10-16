"""SERA v0.20 — generic, zero-manual, typed aspect candidate recovery.

A source-bound model opinion is never canonical truth. This module consumes
UNTRUSTED typed aspect proposals, performs a complete exact-source,
registered-entity, actor/object co-location, monotonic-order and compare-
and-swap *simulation* through the existing v0.13 reducer.

No Mara-specific references, prose rewrites, provider calls, token ceilings,
human approvals, WorldStore modifications or production writes occur here.
On conflict, the WHOLE candidate batch is held and automatically routes to
upstream re-extraction/replanning rather than silently losing an event.
The reducer's 'approvals' are explicitly simulation-only fixtures, not
external authorization. They must NEVER be forwarded to production.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.world_state_v02 import canonical, validate as validate_world
from experiments.sera.world_state_v013 import (
    MODE, EVENT_KEYS, TYPES, create, digest, simulate_batch, verify_replay,
)

SCHEMA = "sera.typed-aspect-candidate-recovery.v0.20"
PERMITTED = frozenset(TYPES)
REGISTRY_KEYS = frozenset({"openables", "documents"})
MAX_CANDIDATES = 256


def ensure(condition, code):
    if not condition:
        raise CoverageError(code)


def fingerprint(value):
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def _validate_registry(world, registry):
    ensure(isinstance(registry, dict) and
           set(registry) == REGISTRY_KEYS, "V020_REGISTRY_SCHEMA_INVALID")
    refs = []
    for role in ("openables", "documents"):
        values = registry[role]
        ensure(isinstance(values, list) and all(
            isinstance(x, str) and x for x in values
        ), "V020_REGISTRY_REFS_INVALID")
        refs.extend(values)
    ensure(len(set(refs)) == len(refs),
           "V020_REGISTRY_DUPLICATE_OBJECT")
    # A scene may contain only one facet family. Never invent missing roles.
    ensure(bool(refs), "V020_NO_REGISTERED_FACET_OBJECTS")
    for ident in refs:
        e = world.get("entities", {}).get(ident)
        ensure(isinstance(e, dict) and e.get("kind") == "OBJECT" and
               e.get("lifecycle") == "ACTIVE",
               "V020_UNREGISTERED_OR_INACTIVE_OBJECT")
    return refs


def _validate_projection(prose, projection):
    if projection is None:
        return None
    ensure(isinstance(projection, dict) and
           projection.get("schema") == "sera.event-candidate-repair.v0.19" and
           projection.get("prose_sha256") == prose_hash(prose) and
           projection.get("canonical_commit_authorized") is False and
           projection.get("world_db_writes") == 0 and
           projection.get("next_automatic_action") in (
               "AUTO_EVENT_REEXTRACTION_OR_REPLAN",
               "CONTINUE_FULL_SCENE_GATES",
           ), "V020_PROJECTION_SOURCE_OR_AUTHORITY_INVALID")
    return projection["next_automatic_action"]


def recover(*, prose, world, registry, candidates, projection=None):
    """Pure automatic trial of ALL typed aspect proposals; all-or-none.

    A successful trial is a NONCANONICAL preview, not a semantically
    approved set of world events. Runtime still needs independent meaning
    qualification, authenticated commit permission and transaction safety.
    """
    validate_world(world)
    original_world = fingerprint(world)
    refs = _validate_registry(world, registry)
    upstream = _validate_projection(prose, projection)
    ensure(isinstance(prose, str) and prose.strip() and
           isinstance(candidates, list) and
           len(candidates) <= MAX_CANDIDATES,
           "V020_CANDIDATE_INPUT_INVALID")

    state = create(
        base_world=world, prose=prose,
        openables=registry["openables"],
        documents=registry["documents"],
    )
    before = fingerprint(state)
    # Never trust provider-generated canonical authorization or a fake
    # application approval. The exact v0.13 event schema has no such field.
    seen = set()
    for index, event in enumerate(candidates):
        ensure(isinstance(event, dict) and set(event) == EVENT_KEYS,
               "V020_EVENT_FIELDS_INVALID")
        ident = event.get("event_id")
        ensure(isinstance(ident, str) and ident and ident not in seen,
               "V020_EVENT_ID_MISSING_OR_DUPLICATE")
        seen.add(ident)
        ensure(event.get("type") in PERMITTED and
               event.get("object_id") in refs,
               "V020_EVENT_UNKNOWN_ROLE")
        role = ("documents" if event["type"] == "APPEND_DOCUMENT_ENTRY"
                else "openables")
        ensure(event["object_id"] in registry[role],
               "V020_EVENT_OBJECT_ROLE_CONFLICT")

    reasons = []
    preview = None
    if candidates:
        # Exactly the existing v0.13 OFFLINE simulation boundary. The
        # map is an internal test-fixture capability: no production write.
        simulated = {event["event_id"]: digest(event)
                     for event in candidates}
        try:
            result = simulate_batch(
                state=state, events=deepcopy(candidates), prose=prose,
                approvals=simulated, mode=MODE,
            )
            ensure(verify_replay(state=result, prose=prose),
                   "V020_REPLAY_VERIFY_FAILED")
            preview = {
                "state_schema": result["schema"],
                "reducer_mode": MODE,
                "simulated_revision": result["revision"],
                "head_hash": result["head_hash"],
                "aspects": deepcopy(result["aspects"]),
                "simulated_world_state": deepcopy(result),
                "simulation_is_not_canonical_authority": True,
                "world_db_writes": 0,
            }
        except CoverageError as exc:
            reasons.append(str(exc))
    else:
        reasons.append("V020_NO_TYPED_EVENTS_PROPOSED")

    if upstream == "AUTO_EVENT_REEXTRACTION_OR_REPLAN":
        reasons.append("V020_V019_UPSTREAM_SCENE_DEFECTS_UNRESOLVED")
    ensure(fingerprint(world) == original_world and
           fingerprint(state) == before,
           "V020_PRODUCTION_INPUT_MUTATED")

    blocked = bool(reasons)
    return {
        "schema": SCHEMA,
        "prose_sha256": prose_hash(prose),
        "world_sha256": original_world,
        "registry_sha256": fingerprint(registry),
        "original_candidates_sha256": fingerprint(candidates),
        "candidate_count": len(candidates),
        "source_bound_candidate_count": (
            len(candidates) if preview is not None else 0
        ),
        "typed_preview": preview,
        "blocker_codes": reasons,
        "status": (
            "AUTO_REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL"
            if blocked else "TYPED_FACETS_SIMULATED_NONCANONICAL"
        ),
        "next_automatic_action": (
            "AUTO_REEXTRACT_OR_REPLAN_SCENE"
            if blocked else "CONTINUE_INDEPENDENT_SCENE_QUALIFICATION"
        ),
        "requires_manual_intervention": False,
        "human_approval_required": False,
        "simulation_is_not_world_truth": True,
        "canonical_commit_authorized": False,
        "auto_entity_creations": 0,
        "world_db_writes": 0,
    }
