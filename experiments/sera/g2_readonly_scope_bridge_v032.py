"""SERA v0.32 — read-only production G2 authority boundary for StoryForge.

Resolves a REAL Project_LUMI G2 contract from an injected, authorized
read-only service, not from generated names or arbitrary client JSON.
A separate application-owned attestor must authenticate the exact
retrieved rows and authoritative source. Structural consistency ALONE
never becomes production authority. No connection/SQL/writes here.

This module may authorize ONLY a lab-scoped SOURCE PREFLIGHT; it never
requests or grants G2 StoryOutcome commit. Production integration
requires a real read-only adapter and a signed/fresh source attestor.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import re

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.storyforge_bridge_v028 import run as run_storyforge
from experiments.sera.world_state_v02 import canonical, validate as validate_world

SCHEMA = "sera.project-lumi-g2-readonly-binding.v0.32"
SCOPE = ("householdId", "profileId", "universeId",
         "worldInstanceId", "primaryCharacterId")
UUID = re.compile(r"^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$")
FP = re.compile(r"^[a-f0-9]{64,128}$")


def need(ok, code):
    if not ok:
        raise CoverageError(code)


def digest(value):
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def _uuid(v):
    return isinstance(v, str) and UUID.fullmatch(v) is not None


def _fp(v):
    return isinstance(v, str) and FP.fullmatch(v) is not None


def _scope(row, expected, label):
    need(isinstance(row, dict) and all(
        row.get(key) == expected[key] for key in SCOPE
    ), "V032_" + label + "_SCOPE_MISMATCH")


def resolve(*, contract_id, expected_scope, request, result, world,
            readonly_lookup, verify_source):
    """Authenticate and structurally verify a G2 read-only StoryContract.

    readonly_lookup(contract_id=...) MUST read true Project_LUMI data.
    verify_source(snapshot, context) MUST verify a freshness-bound
    signature/attestation independently from the client-supplied JSON.
    Inject these from application trust boundary, never a model.
    """
    validate_world(world)
    need(_uuid(contract_id) and isinstance(expected_scope, dict) and
         set(expected_scope) == set(SCOPE) and
         all(_uuid(expected_scope[k]) for k in SCOPE),
         "V032_G2_SCOPE_OR_CONTRACT_INVALID")
    need(isinstance(request, dict) and isinstance(result, dict) and
         isinstance(result.get("english_story"), str) and
         result["english_story"] and
         request.get("active_world_id") == expected_scope["worldInstanceId"] and
         isinstance(request.get("request_id"), str) and
         request["request_id"] == result.get("request_id"),
         "V032_STORYFORGE_G2_WORLD_OR_REQUEST_MISMATCH")
    need(callable(readonly_lookup) and callable(verify_source),
         "V032_AUTHENTICATED_READONLY_SOURCE_REQUIRED")

    document = readonly_lookup(contract_id=contract_id)
    need(isinstance(document, dict) and document.get("schema") == SCHEMA
         and isinstance(document.get("rows"), dict) and
         isinstance(document.get("provenance"), dict),
         "V032_G2_READ_DOCUMENT_INVALID")
    rows = deepcopy(document["rows"])
    provenance = deepcopy(document["provenance"])
    need(provenance.get("source") == "PROJECT_LUMI_G2_READONLY" and
         provenance.get("contract_id") == contract_id and
         provenance.get("rows_sha256") == digest(rows) and
         isinstance(provenance.get("snapshot_id"), str) and
         bool(provenance["snapshot_id"].strip()) and
         verify_source(deepcopy(rows), deepcopy(provenance)) is True,
         "V032_G2_SOURCE_NOT_AUTHENTICATED")
    need(set(rows) == {"contract", "intent", "production_run",
                       "accepted_story", "universe_head", "world_head",
                       "character_before", "character_head",
                       "snapshot_refs"},
         "V032_G2_AUTHORITY_ROWS_INCOMPLETE")
    for label in ("contract", "intent", "production_run", "accepted_story"):
        _scope(rows[label], expected_scope, label.upper())
    con, intent = rows["contract"], rows["intent"]
    run, artifact = rows["production_run"], rows["accepted_story"]
    need(con.get("id") == contract_id and
         _uuid(con.get("storyIntentId")) and
         intent.get("id") == con["storyIntentId"] and
         intent.get("status") == "STORY_STARTED",
         "V032_G2_CONTRACT_OR_INTENT_INVALID")
    need(_uuid(run.get("id")) and run.get("contractId") == contract_id
         and run.get("status") == "ACCEPTED",
         "V032_G2_PRODUCTION_NOT_ACCEPTED")
    need(_uuid(artifact.get("id")) and
         artifact.get("contractId") == contract_id and
         artifact.get("productionRunId") == run["id"] and
         _fp(artifact.get("storyFingerprint")) and
         artifact.get("storyText") == result["english_story"] and
         prose_hash(artifact["storyText"]) == prose_hash(result["english_story"]),
         "V032_G2_ACCEPTED_ENGLISH_BYTES_MISMATCH")
    # G2 domain storyFingerprint is NOT raw English SHA256.
    need(_uuid(con.get("universeRevisionId")) and
         _uuid(con.get("worldInstanceRevisionId")) and
         _fp(con.get("universeFingerprint")) and
         _fp(con.get("worldInstanceFingerprint")),
         "V032_G2_FROZEN_WORLD_HEADS_INVALID")
    universe, whead = rows["universe_head"], rows["world_head"]
    need(isinstance(universe, dict) and
         universe.get("universeId") == expected_scope["universeId"] and
         universe.get("householdId") == expected_scope["householdId"] and
         universe.get("currentRevisionId") == con["universeRevisionId"] and
         universe.get("currentFingerprint") == con["universeFingerprint"],
         "V032_G2_UNIVERSE_HEAD_STALE")
    need(isinstance(whead, dict) and
         all(whead.get(key) == expected_scope[key] for key in
             ("householdId", "profileId", "universeId")) and
         whead.get("worldInstanceId") == expected_scope["worldInstanceId"] and
         whead.get("currentRevisionId") ==
             con["worldInstanceRevisionId"] and
         whead.get("currentFingerprint") ==
             con["worldInstanceFingerprint"],
         "V032_G2_WORLD_HEAD_STALE")
    char = rows["character_before"]
    head = rows["character_head"]
    need(isinstance(char, dict) and isinstance(head, dict) and
         char.get("householdId") == expected_scope["householdId"] and
         char.get("profileId") == expected_scope["profileId"] and
         char.get("characterId") == expected_scope["primaryCharacterId"] and
         _uuid(char.get("snapshotId")) and
         type(char.get("revisionNo")) is int and
         char["revisionNo"] > 0 and
         type(char.get("headVersion")) is int and
         char["headVersion"] > 0 and _fp(char.get("fingerprint")) and
         isinstance(char.get("statePayload"), dict) and
         isinstance(char["statePayload"].get("facts"), dict) and
         isinstance(char["statePayload"].get("emotions"), dict) and
         head.get("householdId") == expected_scope["householdId"] and
         head.get("profileId") == expected_scope["profileId"] and
         head.get("characterId") == expected_scope["primaryCharacterId"] and
         head.get("currentSnapshotId") == char["snapshotId"] and
         head.get("currentRevisionNo") == char["revisionNo"] and
         head.get("currentFingerprint") == char["fingerprint"] and
         head.get("version") == char["headVersion"],
         "V032_G2_CHARACTER_STATE_STALE")
    refs = rows["snapshot_refs"]
    need(isinstance(refs, list) and
         sum(1 for ref in refs if isinstance(ref, dict) and
             ref.get("snapshotKind") == "CHARACTER_STATE") == 1,
         "V032_G2_CHARACTER_REF_NOT_UNIQUE")
    ref = next(x for x in refs if x["snapshotKind"] == "CHARACTER_STATE")
    _scope(ref, expected_scope, "CHARACTER_REF")
    need(ref.get("contractId") == contract_id and
         ref.get("sourceRef") ==
             "character-story-state:" + char["snapshotId"] and
         ref.get("sourceFingerprint") == char["fingerprint"],
         "V032_G2_CHARACTER_REF_MISMATCH")

    authority = {
        "schema": SCHEMA, "source_snapshot_id": provenance["snapshot_id"],
        "g2_contract_id": contract_id, "g2_story_intent_id": intent["id"],
        "g2_run_id": run["id"], "g2_accepted_story_id": artifact["id"],
        "scope": deepcopy(expected_scope),
        "accepted_english_sha256": prose_hash(result["english_story"]),
        "g2_domain_story_fingerprint": artifact["storyFingerprint"],
        "frozen_universe_revision_id": con["universeRevisionId"],
        "frozen_universe_fingerprint": con["universeFingerprint"],
        "frozen_world_revision_id": con["worldInstanceRevisionId"],
        "frozen_world_fingerprint": con["worldInstanceFingerprint"],
        "character_snapshot_id": char["snapshotId"],
        "character_revision_no": char["revisionNo"],
        "character_head_version": char["headVersion"],
        "character_fingerprint": char["fingerprint"],
        "read_source_sha256": digest(rows),
        "read_attestation_sha256": digest(provenance),
        "local_simulated_world_sha256": digest(world),
        "authenticated_source_preflight": True,
        "canonical_commit_authorized": False, "world_db_writes": 0,
        "g2_commit_request": None,
    }
    return authority


def run_readonly_g2(*, contract_id, expected_scope, readonly_lookup,
                    verify_source, request, result, world, **storyforge_kwargs):
    """Bind an authenticated G2 read preflight into the v0.28 LAB bridge.

    Strictly dry-run ONLY: even a verified accepted G2 artifact is not
    authorization to use production data for a paid experiment or to
    change production StoryOutcome. This is no release/deploy operation.
    """
    need(storyforge_kwargs.get("paid_authorized", False) is False,
         "V032_G2_PAID_WORKER_NOT_AUTHORIZED")
    authority = resolve(
        contract_id=contract_id, expected_scope=expected_scope,
        request=request, result=result, world=world,
        readonly_lookup=readonly_lookup, verify_source=verify_source,
    )
    scope = {
        "active_world_id": expected_scope["worldInstanceId"],
        "entry_world_sha256": digest(world),
        "storyforge_request_id": request["request_id"],
        "policy_version": "PROJECT_LUMI_G2_AUTHENTICATED_READONLY_V032",
        "g2_authority_sha256": digest(authority),
    }
    def verify_scoped_value(value):
        return value == scope and authority["authenticated_source_preflight"]
    return {
        "status": "G2_AUTHENTICATED_READONLY_PREFLIGHT_NONCANONICAL",
        "authority": authority,
        "storyforge": run_storyforge(
            request=request, result=result, world=world,
            trusted_scope=scope, verify_scope=verify_scoped_value,
            **storyforge_kwargs,
        ),
        "canonical_commit_authorized": False,
        "world_db_writes": 0, "g2_commit_request": None,
        "requires_manual_intervention": False,
    }
