"""SERA v0.33 — conservative physically registered G2→SERA projection.

G2 CharacterStoryState facts alone DO NOT reveal an entity's location,
custody, wear state, physical properties or route network. Hence they
cannot be projected into SERA's physical simulator by guessing.

Only an additional app-attested, world-snapshot-bound physical registry
can yield a noncanonical simulation. Missing, stale or untrusted
physical state fails closed before any model or billing call.
"""
from __future__ import annotations
from copy import deepcopy

from experiments.sera.coverage import CoverageError
from experiments.sera.g2_readonly_scope_bridge_v032 import _uuid, digest
from experiments.sera.world_state_v02 import (
    entity_template, initial_state, environment_template, validate,
)

SCHEMA = "sera.g2-physical-readonly-projection.v0.33"


def need(condition, code):
    if not condition:
        raise CoverageError(code)


def project(*, authority, projection, verify_projection):
    need(isinstance(authority, dict) and
         authority.get("authenticated_source_preflight") is True and
         authority.get("canonical_commit_authorized") is False and
         isinstance(authority.get("scope"), dict) and
         isinstance(authority.get("read_source_sha256"), str),
         "V033_G2_SCOPE_UNQUALIFIED")
    need(isinstance(projection, dict) and
         projection.get("schema") == SCHEMA and
         isinstance(projection.get("snapshot"), dict) and
         isinstance(projection.get("provenance"), dict) and
         callable(verify_projection),
         "V033_PHYSICAL_REGISTRY_NOT_AVAILABLE")
    snap = deepcopy(projection["snapshot"])
    proof = deepcopy(projection["provenance"])
    scope = authority["scope"]
    need(snap.get("scope") == scope and
         snap.get("g2ContractId") == authority["g2_contract_id"] and
         snap.get("worldRevisionId") ==
            authority["frozen_world_revision_id"] and
         snap.get("worldFingerprint") ==
            authority["frozen_world_fingerprint"] and
         snap.get("characterSnapshotId") ==
            authority["character_snapshot_id"] and
         proof.get("source") == "PROJECT_LUMI_G2_PHYSICAL_READONLY" and
         proof.get("snapshot_sha256") == digest(snap) and
         proof.get("g2_authority_sha256") == digest(authority) and
         verify_projection(deepcopy(snap),deepcopy(proof)) is True,
         "V033_PHYSICAL_SNAPSHOT_NOT_AUTHENTICATED_OR_STALE")
    rows = snap.get("entities")
    regions = snap.get("regions")
    facts = snap.get("verifiedFactRegistry")
    routes = snap.get("registeredRoutes")
    need(isinstance(rows, list) and rows and
         isinstance(regions, list) and regions and
         isinstance(facts, dict) and isinstance(routes, list),
         "V033_PHYSICAL_REGISTRY_INCOMPLETE")
    locations = {}
    for reg in regions:
        need(isinstance(reg, dict) and
             set(reg) == {"id", "weather"} and
             _uuid(reg["id"]) and
             reg["id"] not in locations and
             reg["weather"] in (
                 "UNKNOWN","CLEAR","CLOUDY","RAIN","SNOW","STORM"
             ), "V033_PHYSICAL_REGION_INVALID")
        # Only UNKNOWN is legitimate without an app-owned weather
        # measurement. No fabricated temperature, rain, or humidity.
        need(reg["weather"] == "UNKNOWN",
             "V033_WEATHER_REQUIRES_TYPED_MEASUREMENT")
        locations[reg["id"]] = environment_template(weather="UNKNOWN")
    entities = {}
    for e in rows:
        need(isinstance(e, dict) and set(e) == {
            "id","kind","locationId","lifecycle","ownerId","holderId",
            "wornById","knowledgeFactIds",
        } and _uuid(e["id"]) and
             e["id"] not in entities and
             e["kind"] in ("CHARACTER","OBJECT","WEARABLE") and
             e["lifecycle"] == "ACTIVE" and
             _uuid(e["locationId"]) and
             e["locationId"] in locations and
             all(ref is None or _uuid(ref) for ref in (
                 e["ownerId"],e["holderId"],e["wornById"],
             )) and isinstance(e["knowledgeFactIds"], list) and
             len(e["knowledgeFactIds"]) ==
                len(set(e["knowledgeFactIds"])),
             "V033_G2_ENTITY_ROLE_OR_LOCATION_UNQUALIFIED")
        known=[]
        if e["kind"] == "CHARACTER":
            need(e["holderId"] is None and
                 e["wornById"] is None,
                 "V033_CHARACTER_CUSTODY_INVALID")
            for fact_id in e["knowledgeFactIds"]:
                fact=facts.get(fact_id)
                need(isinstance(fact, dict) and
                     fact.get("truth_status") == "VERIFIED" and
                     fact.get("knowledge_scope") == e["id"],
                     "V033_G2_FACT_NOT_VERIFIED_OR_OUT_OF_SCOPE")
                known.append(fact_id)
        else:
            need(not e["knowledgeFactIds"],
                 "V033_NONCHARACTER_KNOWLEDGE_INVALID")
        entities[e["id"]] = entity_template(
            e["id"], e["kind"], e["locationId"],
            owner=e["ownerId"],holder=e["holderId"],
            worn_by=e["wornById"],knowledge=known,
            # All unobserved appearance/measurements remain UNKNOWN.
        )
    need(scope["primaryCharacterId"] in entities and
         entities[scope["primaryCharacterId"]]["kind"] == "CHARACTER",
         "V033_PRIMARY_CHARACTER_MISSING")
    # Entity graph validation rejects invented holder/wear/location
    # combinations and missing ownership references.
    world = initial_state(entities=entities, regions=locations)
    validate(world)
    covered = set()
    for item in routes:
        need(isinstance(item, dict) and
             set(item) == {"fromLocationId","toLocationId","minTravelMinutes"}
             and item["fromLocationId"] in locations and
             item["toLocationId"] in locations and
             item["fromLocationId"] != item["toLocationId"] and
             type(item["minTravelMinutes"]) is int and
             item["minTravelMinutes"] > 0,
             "V033_TRAVEL_ROUTE_UNREGISTERED")
        leg=(item["fromLocationId"],item["toLocationId"])
        need(leg not in covered, "V033_DUPLICATE_TRAVEL_ROUTE")
        covered.add(leg)
    return {
        "schema": SCHEMA,
        "status": "REGISTERED_PHYSICAL_PREVIEW_NONCANONICAL",
        "world": world,
        "world_sha256": digest(world),
        "native_g2_world_fingerprint":
            authority["frozen_world_fingerprint"],
        "native_g2_character_snapshot_id":
            authority["character_snapshot_id"],
        "registered_routes": deepcopy(routes),
        "g2_authority_sha256": digest(authority),
        "physical_snapshot_sha256": digest(snap),
        "physical_attestation_sha256": digest(proof),
        "canonical_commit_authorized": False,
        "world_db_writes": 0,
        "g2_commit_request": None,
    }
