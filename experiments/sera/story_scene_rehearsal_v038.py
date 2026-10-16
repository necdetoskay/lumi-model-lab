"""SERA v0.38 — source-bound, two-stage STORY rehearsal on v0.37 SQLite.

Reuses the real v0.6 sentence assurance, v0.24 spatial and v0.25 relation
projections and v0.2 reducer/transaction store. Only a lab fixture may
grant a SIMULATION mutation; none of those gates is canonical or semantic gold.
This is NOT a billable writer/StoryForge provider runner.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.multi_character_world_lab_v037 import require
from experiments.sera.scene_assurance_v06 import audit_scene
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.spatial_preview_v024 import preview as spatial_preview
from experiments.sera.relation_knowledge_preview_v025 import preview as relation_preview
from experiments.sera.world_state_v02 import (
    apply_event, canonical, fingerprint,
)

SCHEMA = "sera.synthetic-scene-rehearsal.v0.38"


def _sha(value):
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def _physics(state):
    """Time and append-only event metadata are distinct from physical graph."""
    copy = deepcopy(state)
    copy.pop("revision", None)
    copy.pop("minute", None)
    copy.pop("events", None)
    for entity in copy["entities"].values():
        entity.pop("last_action_minute", None)
    return copy


def rehearsal(*, lab, run_id, expected_revision, scene_key, prose,
              source_event, reducer_event, registered_aliases,
              candidate_lexicon, temporal_case=None, relation_case=None,
              fixture_grants=None):
    """Run real offline source/cause previews, then fixture-only SQLite CAS.

    The caller supplies a synthetic source event and an independent exact
    fixture grant. Neither model prose nor a passing preview is authorization
    to create that grant. All checks happen before SQLite is mutated.
    """
    require(isinstance(scene_key, str) and bool(scene_key.strip()) and
            isinstance(prose, str) and bool(prose.strip()) and
            isinstance(source_event, dict) and
            isinstance(reducer_event, dict) and
            isinstance(registered_aliases, dict) and
            isinstance(candidate_lexicon, dict) and
            isinstance(fixture_grants, dict),
            "V038_REHEARSAL_INPUT_INVALID")
    inp = lab.scene_inputs(run_id, expected_revision=expected_revision)
    world = inp["validator_world"]
    writer_context = inp["writer_context"]
    require(inp["source"] == "SYNTHETIC_SQLITE_WORLD" and
            inp["canonical_commit_authorized"] is False and
            writer_context["world_id"] == inp["writer_context"]["world_id"] and
            writer_context["revision"] == expected_revision,
            "V038_SYNTHETIC_ENTRY_REQUIRED")
    # Bound one actual sentence and one event per scene in the first pilot.
    # Multi-event scene expansion is deferred; do not assert recall on a
    # partial source report or quietly ignore a second sentence.
    full_sentences = sentences(prose)
    require(len(full_sentences) == 1 and
            source_event.get("sentence_id") == full_sentences[0]["id"] and
            type(source_event.get("start")) is int and
            type(source_event.get("end")) is int and
            source_event["start"] == full_sentences[0]["start"] and
            source_event["end"] == full_sentences[0]["end"] and
            source_event.get("quote") == full_sentences[0]["quote"] and
            source_event.get("epistemic") == "OBSERVED_ACTION" and
            isinstance(source_event.get("entity_refs"), list) and
            len(source_event["entity_refs"]) == len(set(source_event["entity_refs"])) and
            all(isinstance(x, str) and x in world["entities"]
                for x in source_event["entity_refs"]) and
            source_event.get("event_id") == reducer_event.get("event_id") and
            reducer_event.get("evidence_ref") ==
                "synthetic-scene:" + scene_key + ":" + prose_hash(prose) and
            fixture_grants.get(reducer_event["event_id"]) ==
                fingerprint(reducer_event),
            "V038_SOURCE_OR_FIXTURE_GRANT_INVALID")
    require(set(registered_aliases) == set(world["entities"]) and
            all(isinstance(names, list) and bool(names) and
                all(isinstance(x, str) and bool(x.strip()) for x in names)
                for names in registered_aliases.values()),
            "V038_REGISTERED_ALIASES_INCOMPLETE")
    # This audit remains HOLD without an independent semantic extractor.
    # No shortcut to PASS is introduced to make the synthetic fixture green.
    audit = audit_scene(
        prose=prose, scene_key=scene_key, entry_revision=expected_revision,
        registry=deepcopy(registered_aliases),
        candidate_lexicon=deepcopy(candidate_lexicon),
    )
    require(audit["status"] == "HOLD" and
            audit["canonical_commit_authorized"] is False and
            audit["world_db_writes"] == 0,
            "V038_ASSURANCE_ELEVATION_FORBIDDEN")
    report = {
        "source_prose_sha256": prose_hash(prose),
        "candidate_events": [deepcopy(source_event)],
    }
    rules_row = lab.db.execute(
        "SELECT rules_json FROM world_streams WHERE stream_id=?",
        (writer_context["world_id"],),
    ).fetchone()
    require(rules_row is not None, "V038_WORLD_RULES_NOT_AVAILABLE")
    rules = json.loads(rules_row[0])
    require(isinstance(rules.get("routes"), dict) and
            isinstance(rules.get("rules"), list),
            "V038_WORLD_RULES_INVALID")

    kind = source_event.get("kind")
    payload = reducer_event.get("payload")
    require(isinstance(payload, dict), "V038_REDUCER_PAYLOAD_INVALID")
    if kind == "TRANSFER":
        require(temporal_case is None and
                reducer_event.get("type") == "TRANSFER_HOLDER" and
                isinstance(relation_case, dict) and
                relation_case.get("entry") == world and
                relation_case.get("registered_aliases") == registered_aliases and
                relation_case.get("verified_fact_registry") == {} and
                isinstance(relation_case.get("policy_id"), str) and
                relation_case["policy_id"].startswith("fixture:v038:") and
                isinstance(relation_case.get("transitions"), list) and
                len(relation_case["transitions"]) == 1 and
                relation_case["transitions"][0] == {
                    "source_event_id": source_event["event_id"],
                    "operation": "TRANSFER_HOLDER",
                    "object_id": payload.get("entity_id"),
                    "from_id": payload.get("from_id"),
                    "to_id": payload.get("to_id"),
                    "fact_id": None,
                }, "V038_TRANSFER_POLICY_MISMATCH")
        preview = relation_preview(
            prose=prose, world=world,
            extraction_report=report, relation_case=deepcopy(relation_case),
        )
        require(preview["transition_count"] == 1,
                "V038_TRANSFER_COVERAGE_MISSING")
    elif kind == "MOVE":
        require(relation_case is None and
                reducer_event.get("type") == "MOVE_CHARACTER" and
                isinstance(temporal_case, dict) and
                temporal_case.get("entry") == world and
                temporal_case.get("scene_key") == scene_key and
                temporal_case.get("travel_minutes") == rules["routes"] and
                isinstance(temporal_case.get("events"), list) and
                len(temporal_case["events"]) == 1 and
                temporal_case["events"][0].get("kind") == "MOVEMENT" and
                temporal_case["events"][0].get("event_id") ==
                    source_event["event_id"] and
                temporal_case["events"][0].get("actor_id") ==
                    payload.get("character_id") and
                temporal_case["events"][0].get("to_location") ==
                    payload.get("to_location"),
                "V038_SPATIAL_POLICY_MISMATCH")
        preview = spatial_preview(
            prose=prose, world=world,
            extraction_report=report, temporal_case=deepcopy(temporal_case),
        )
        require(preview["movement_count"] == 1,
                "V038_MOVEMENT_COVERAGE_MISSING")
        domain = preview["temporal_domains"]["domains"][0]
        require(domain["earliest_feasible_minute"] <=
                reducer_event["at_minute"] <=
                domain["latest_feasible_minute"] and
                (domain["narrative_exact_minute"] is None or
                 domain["narrative_exact_minute"] == reducer_event["at_minute"]),
                "V038_SIMULATED_TIME_OUTSIDE_DOMAIN")
    else:
        raise CoverageError("V038_EVENT_FAMILY_NOT_QUALIFIED")

    require(preview.get("canonical_commit_authorized") is False and
            preview.get("world_db_writes") == 0 and
            preview.get("world_sha256") == _sha(world),
            "V038_PREVIEW_AUTHORITY_INVALID")
    # Independently run the v0.2 reducer in memory before any INSERT to
    # assert physical parity between the legacy preview and v0.2 semantics.
    simulated = apply_event(
        world, reducer_event, approvals=fixture_grants,
        travel_minutes=rules["routes"],
        world_rules=frozenset(rules["rules"]),
    )
    require(_physics(simulated) == _physics(preview["isolated_preview_state"]),
            "V038_REDUCER_PREVIEW_PHYSICAL_DIVERGENCE")
    committed = lab.commit_story_fixture(
        run_id=run_id, expected_revision=expected_revision,
        events=[reducer_event], fixture_approvals=fixture_grants,
    )
    require(committed["revision"] == expected_revision + 1 and
            committed["canonical_commit_authorized"] is False and
            committed["production_db_writes"] == 0,
            "V038_FIXTURE_COMMIT_RESULT_INVALID")
    return {
        "schema": SCHEMA,
        "status": "SYNTHETIC_SCENE_REHEARSED_NONCANONICAL",
        "scene_key": scene_key,
        "run_id": run_id,
        "world_id": writer_context["world_id"],
        "actor_id": writer_context["primary_character_id"],
        "entry_revision": expected_revision,
        "exit_revision": committed["revision"],
        "entry_world_sha256": _sha(world),
        "exit_world_sha256": committed["state_sha256"],
        "source_prose_sha256": prose_hash(prose),
        "source_event_id": source_event["event_id"],
        "preview_kind": preview["schema"],
        "scene_assurance_status": audit["status"],
        "scene_assurance_findings": deepcopy(audit["findings"]),
        "independent_semantic_qualification": False,
        "event_provenance_type": "SYNTHETIC_FIXTURE_NOT_MODEL",
        "simulated_arrival_time_is_narrative_fact": False,
        "provider_calls": 0,
        "canonical_commit_authorized": False,
        "production_db_writes": 0,
        "g2_commit_request": None,
    }
