"""SERA v0.39: unattended BLIND synthetic extractor -> v0.38 SQLite scenes.

This is an OFFLINE model-double qualification test, never actual LLM truth.
Reuses v0.10 source-bound sentence sweep and v0.38 source-bound temporal/
custody simulation. A separate lab fixture owns expected physical outcomes,
the exact reducer event and approval; model outputs cannot grant themselves
an approval, and writer data never contains the validator-only full world.

The fixed reply budget here is a synthetic extraction ATTEMPT count, NOT a
model generation/output-token ceiling. Real paid transport MUST additionally
use durable request-ID/receipt reconciliation; it is not implemented here.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.sentence_sweep_v010 import (
    create_plan, bind_batch, aggregate,
)
from experiments.sera.story_scene_rehearsal_v038 import rehearsal
from experiments.sera.world_state_v02 import (
    WorldStateError, canonical, fingerprint,
)

SCHEMA = "sera.blind-synthetic-scene-worker.v0.39"
BLOCKING_PREFIXES = (
    "SWEEP_MISSING_ENTITY_HINT:", "SWEEP_UNACCOUNTED_ACTION_CUE:",
    "SWEEP_EXPECTED_EVENT_NOT_EXTRACTED:",
    "SWEEP_DISPOSITION_EVENT_CONFLICT:",
    "SWEEP_EVENT_DISPOSITION_CONFLICT:",
    "SWEEP_UNRESOLVED_SENTENCE:",
    "SWEEP_POSSIBLY_MISCLASSIFIED:",
    "SWEEP_CLAIM_PROMOTED_TO_WORLD:",
    "SWEEP_UNMAPPED_EVENT:",
    "SWEEP_MODEL_GRAMMAR_ROLE_REVIEW:",
    "SWEEP_BODY_PART_CANDIDATE_REVIEW:",
)


def ensure(ok, code):
    if not ok:
        raise CoverageError(code)


def source_event_id(*, world_id, scene_key, prose, sweep_event_id):
    """One name per WORLD+scene+source; no event IDs collide across scenes."""
    domain = canonical([world_id, scene_key, prose_hash(prose)])
    return ("v039-" + sha256(domain.encode("utf-8")).hexdigest()[:24] +
            ":" + sweep_event_id)


def blind_recover(*, prose, scene_key, entry_revision, aliases, lexicon,
                  reply_for_blind_batch, max_attempts=2):
    """Source-only v0.10 automatic re-extraction with adversarial report gate.

    A model double sees only the v0.10 blind source-batch request + its
    feedback; it is NEVER passed a reducer event, fixture approval, world
    validator state or writer's previous event interpretation.
    """
    ensure(callable(reply_for_blind_batch) and
           type(max_attempts) is int and 1 <= max_attempts <= 4,
           "V039_REPLY_POLICY_INVALID")
    plan = create_plan(prose=prose, scene_key=scene_key,
                       entry_revision=entry_revision, registry=aliases,
                       candidate_lexicon=lexicon)
    ensure(plan["prior_writer_report_included"] is False and
           plan["prior_analyst_events_included"] is False and
           plan["canonical_commit_authorized"] is False,
           "V039_BLIND_SOURCE_POLICY_INVALID")
    attempts = []
    findings = ()
    for attempt in range(1, max_attempts + 1):
        try:
            bound = []
            for batch in plan["batches"]:
                request = {
                    "batch_id": batch["batch_id"],
                    "messages": deepcopy(batch["messages"]),
                    "response_format": deepcopy(batch["response_format"]),
                    "request_sha256": batch["request_sha256"],
                }
                raw = reply_for_blind_batch(
                    request=deepcopy(request), attempt=attempt,
                    previous_findings=tuple(findings),
                )
                ensure(isinstance(raw, dict),
                       "V039_SYNTHETIC_RESPONSE_NOT_RECEIVED")
                bound.append(bind_batch(
                    plan=plan, batch_id=batch["batch_id"],
                    raw=raw, prose=prose,
                ))
            report = aggregate(plan=plan, bound_batches=bound, prose=prose)
            blocking = sorted(
                x for x in report["findings"]
                if x.startswith(BLOCKING_PREFIXES)
            )
            events = report["candidate_events"]
            if len(events) != 1:
                blocking.append("V039_SINGLE_EVENT_SCENE_NOT_EXTRACTED")
            elif (events[0]["epistemic"] != "OBSERVED_ACTION" or
                  events[0]["kind"] not in ("TRANSFER", "MOVE") or
                  events[0]["effect"] not in ("WORLD", "OBJECT") or
                  len(set(events[0]["entity_refs"])) !=
                  len(events[0]["entity_refs"]) or
                  events[0]["start"] != 0 or
                  events[0]["end"] != len(prose) or
                  events[0]["quote"] != prose or
                  events[0]["sentence_id"] != "s001"):
                blocking.append("V039_SOURCE_EVENT_NOT_QUALIFIED")
            if report["sentences_accounted_for"] != 1 or (
                len(plan["source_sentences"]) != 1
            ):
                blocking.append("V039_SOURCE_SCOPE_NOT_SINGLE_SENTENCE")
            if blocking:
                findings = tuple(sorted(set(blocking)))
                attempts.append({
                    "attempt": attempt, "status": "REEXTRACTION_REQUIRED",
                    "findings": list(findings),
                })
                continue
            attempts.append({
                "attempt": attempt, "status": "SOURCE_BOUND_CANDIDATE",
                "findings": [], "report_sha256":
                    sha256(canonical(report).encode()).hexdigest(),
            })
            return {
                "schema": SCHEMA,
                "status": "BLIND_SOURCE_BOUND_SYNTHETIC_ONLY",
                "event": deepcopy(events[0]),
                "attempts": attempts,
                "source_prose_sha256": prose_hash(prose),
                "report_status": report["status"],
                "independent_semantic_qualification": False,
                "canonical_commit_authorized": False,
                "production_db_writes": 0,
            }
        except (CoverageError, ValueError, TypeError, KeyError) as error:
            findings = ("V039_EXTRACTION_BIND_FAILED:" +
                        (str(error) if isinstance(error, CoverageError)
                         else type(error).__name__),)
            attempts.append({
                "attempt": attempt, "status": "REEXTRACTION_REQUIRED",
                "findings": list(findings),
            })
    return {
        "schema": SCHEMA,
        "status": "FAILED_SAFE_FINAL",
        "event": None,
        "attempts": attempts,
        "last_findings": list(findings),
        "source_prose_sha256": prose_hash(prose),
        "independent_semantic_qualification": False,
        "canonical_commit_authorized": False,
        "production_db_writes": 0,
    }


def _run_scene(*, lab, run_id, scene_key, prose, approved_fixture_event,
              fixture_approvals, aliases, lexicon, reply_for_blind_batch,
              scene_window=None, max_attempts=2):
    """v0.10 extracted event must match preapproved fixture, then v0.38 checks.

    NOTE: All approvals are supplied by synthetic fixture outside this
    method; no model output yields permission or a guessed timestamp.
    """
    # Read the CURRENT shared-world revision. Story run start_revision may
    # be older after another character has finished a scene.
    current_revision = lab.context(run_id)["revision"]
    inp = lab.scene_inputs(run_id, expected_revision=current_revision)
    entry = inp["validator_world"]
    start_revision = entry["revision"]
    ensure(isinstance(approved_fixture_event, dict) and
           isinstance(fixture_approvals, dict) and
           isinstance(aliases, dict) and isinstance(lexicon, dict),
           "V039_TRUSTED_FIXTURE_INPUT_INVALID")
    result = blind_recover(
        prose=prose, scene_key=scene_key, entry_revision=start_revision,
        aliases=deepcopy(aliases), lexicon=deepcopy(lexicon),
        reply_for_blind_batch=reply_for_blind_batch,
        max_attempts=max_attempts,
    )
    if result["status"] == "FAILED_SAFE_FINAL":
        return {**result, "run_id": run_id,
                "entry_revision": start_revision, "exit_revision": start_revision,
                "provider_calls": 0, "g2_commit_request": None}
    source = result["event"]
    stable_id = source_event_id(
        world_id=inp["writer_context"]["world_id"],
        scene_key=scene_key, prose=prose,
        sweep_event_id=source["event_id"],
    )
    source["event_id"] = stable_id
    # This action is from an independent, exact test fixture. Never
    # rewrite it from a provider's claimed actor/object or inferred clock.
    ev = deepcopy(approved_fixture_event)
    if not (
        ev.get("event_id") == stable_id and
        ev.get("evidence_ref") ==
            "synthetic-scene:" + scene_key + ":" + prose_hash(prose) and
        fixture_approvals.get(stable_id) == fingerprint(ev)
    ):
        return {
            **result, "status": "FAILED_SAFE_FINAL",
            "event": None, "last_findings": ["V039_FIXTURE_ACTION_UNPINNED"],
            "run_id": run_id,
            "entry_revision": start_revision,
            "exit_revision": start_revision,
            "provider_calls": 0, "g2_commit_request": None,
        }
    kind = source["kind"]
    payload = ev.get("payload")
    routes_row = lab.db.execute(
        "SELECT rules_json FROM world_streams WHERE stream_id=?",
        (inp["writer_context"]["world_id"],),
    ).fetchone()
    ensure(routes_row is not None, "V039_SQLITE_ROUTES_UNKNOWN")
    routes = json.loads(routes_row[0])["routes"]
    temporal = None
    relation = None
    if kind == "TRANSFER":
        ensure(ev["type"] == "TRANSFER_HOLDER" and isinstance(payload, dict) and
               {payload.get("entity_id"), payload.get("from_id"),
                payload.get("to_id")} == set(source["entity_refs"]),
               "V039_TRANSFER_ENTITY_SET_MISMATCH")
        relation = {
            "entry": deepcopy(entry), "registered_aliases": deepcopy(aliases),
            "verified_fact_registry": {},
            "policy_id": "fixture:v038:blind-v039-" + scene_key,
            "transitions": [{
                "source_event_id": stable_id,
                "operation": "TRANSFER_HOLDER",
                "object_id": payload["entity_id"],
                "from_id": payload["from_id"], "to_id": payload["to_id"],
                "fact_id": None,
            }],
        }
    elif kind == "MOVE":
        ensure(ev["type"] == "MOVE_CHARACTER" and isinstance(payload, dict) and
               payload.get("character_id") in source["entity_refs"],
               "V039_MOVEMENT_ACTOR_MISMATCH")
        ensure(isinstance(scene_window, dict) and
               set(scene_window) == {"earliest_minute", "latest_minute"},
               "V039_TEMPORAL_WINDOW_REQUIRED")
        temporal = {
            "entry": deepcopy(entry), "scene_key": scene_key,
            "scene_window": {
                "scene_key": scene_key,
                "entry_revision": start_revision,
                **deepcopy(scene_window),
            },
            "events": [{
                "event_id": stable_id, "ordinal": 1,
                "actor_id": payload["character_id"],
                "kind": "MOVEMENT",
                "to_location": payload["to_location"],
                "earliest_minute": None, "latest_minute": None,
                "exact_minute": None, "depends_on": [],
            }],
            "travel_minutes": deepcopy(routes),
        }
    else:
        raise CoverageError("V039_UNQUALIFIED_SOURCE_EVENT_KIND")
    try:
        scene = rehearsal(
            lab=lab, run_id=run_id, expected_revision=start_revision,
            scene_key=scene_key, prose=prose, source_event=source,
            reducer_event=ev, registered_aliases=deepcopy(aliases),
            candidate_lexicon=deepcopy(lexicon),
            temporal_case=temporal, relation_case=relation,
            fixture_grants=deepcopy(fixture_approvals),
        )
    except (CoverageError, WorldStateError, ValueError, KeyError) as exc:
        return {
            **result, "status": "FAILED_SAFE_FINAL", "event": None,
            "last_findings": ["V039_SOURCE_BOUND_SCENE_REJECTED:" +
                              type(exc).__name__ + ":" + str(exc)],
            "run_id": run_id, "entry_revision": start_revision,
            "exit_revision": start_revision,
            "provider_calls": 0, "g2_commit_request": None,
        }
    return {
        "schema": SCHEMA,
        "status": "SYNTHETIC_STORY_SCENE_COMMITTED_NONCANONICAL",
        "run_id": run_id, "scene_key": scene_key,
        "entry_revision": start_revision,
        "exit_revision": scene["exit_revision"],
        "blind_extraction_attempts": deepcopy(result["attempts"]),
        "scene_assurance_status": scene["scene_assurance_status"],
        "independent_semantic_qualification": False,
        "provider_calls": 0,
        "production_db_writes": 0,
        "canonical_commit_authorized": False,
        "g2_commit_request": None,
    }


def run_scene(*, lab, run_id, scene_key, prose, approved_fixture_event,
              fixture_approvals, aliases, lexicon, reply_for_blind_batch,
              scene_window=None, max_attempts=2):
    """Automatic FAIL-SAFE boundary for untrusted source/fixture mismatches.

    Never turn an invalid model candidate into a persisted world event.
    Unexpected committed revisions in an error path are NOT disguised as a
    safe failure; they are raised as invariant violations.
    """
    original_revision = lab.context(run_id)["revision"]
    try:
        return _run_scene(
            lab=lab, run_id=run_id, scene_key=scene_key, prose=prose,
            approved_fixture_event=approved_fixture_event,
            fixture_approvals=fixture_approvals, aliases=aliases,
            lexicon=lexicon, reply_for_blind_batch=reply_for_blind_batch,
            scene_window=scene_window, max_attempts=max_attempts,
        )
    except (CoverageError, WorldStateError) as exc:
        current_revision = lab.context(run_id)["revision"]
        if current_revision != original_revision:
            raise CoverageError("V039_ERROR_AFTER_UNEXPECTED_WORLD_WRITE") from exc
        return {
            "schema": SCHEMA, "status": "FAILED_SAFE_FINAL",
            "run_id": run_id, "scene_key": scene_key,
            "entry_revision": original_revision,
            "exit_revision": original_revision,
            "source_prose_sha256": prose_hash(prose),
            "last_findings": [str(exc)],
            "independent_semantic_qualification": False,
            "provider_calls": 0, "production_db_writes": 0,
            "canonical_commit_authorized": False,
            "g2_commit_request": None,
        }
