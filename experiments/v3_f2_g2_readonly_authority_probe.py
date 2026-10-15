"""G2 story authority preflight using ONLY source snapshots.

No database connector, SQL executor, network, credential, or write path.
An input document, even internally consistent, is UNTRUSTED until a
separate authenticated read-only G2 adapter verifies its provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from experiments.v3_f2_g2_state_commit_preview import (
    PROJECT_LUMI_SHA, PROPOSAL_SHA, MODEL_PROPOSAL,
    ENGLISH, EXPECTED_EN, EXPECTED_TR, preview,
)

SCHEMA="lumi.v3-f2.g2-readonly-authority-snapshot.v1"
SCOPE=("householdId","profileId","universeId","worldInstanceId","primaryCharacterId")
UUID=re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
FINGERPRINT=re.compile(r"^[a-f0-9]{64,128}$")
# Verified read-only Project_LUMI Drizzle table names. This module
# does NOT build or issue any SQL query.
G2_SCHEMA_TABLES=(
    "story.story_contracts",
    "story.story_intents",
    "story.story_production_runs_g2",
    "story.accepted_story_artifacts_g2",
    "profile.universe_heads",
    "profile.world_instance_heads",
    "profile.character_story_state_snapshots",
    "profile.character_story_state_heads",
)
class ProbeStop(RuntimeError):
    pass


def _check(p,why):
    if not p: raise ProbeStop(why)


def _uuid(v)->bool:
    return isinstance(v,str) and UUID.fullmatch(v) is not None


def _fp(v)->bool:
    return isinstance(v,str) and FINGERPRINT.fullmatch(v) is not None


def _scope_match(row:dict,scope:dict,label:str):
    _check(isinstance(row,dict),"G2_"+label+"_MISSING")
    _check(all(row.get(key)==scope[key] for key in SCOPE),
           "G2_"+label+"_SCOPE_MISMATCH")


def validate_untrusted_snapshot(document:dict)->dict:
    """Validate supplied rows structurally, NEVER claim live existence.

    This function does not grant readiness even on a fully consistent
    snapshot. It prevents a plausible-looking JSON file being mistaken
    for an authenticated production read.
    """
    _check(isinstance(document,dict) and document.get("schema")==SCHEMA,
           "G2_PROBE_SCHEMA_INVALID")
    _check(document.get("repo_sha")==PROJECT_LUMI_SHA,
           "G2_PROBE_SCHEMA_VERSION_CHANGED")
    scope=document.get("scope")
    _check(isinstance(scope,dict) and all(_uuid(scope.get(k)) for k in SCOPE),
           "G2_PROBE_SCOPE_UUID_INVALID")
    ids=document.get("story_ids")
    _check(isinstance(ids,dict) and all(_uuid(ids.get(k)) for k in (
        "contractId","storyIntentId","productionRunId","acceptedStoryArtifactId")),
        "G2_PROBE_STORY_IDS_INVALID")
    contract=document.get("contract")
    _scope_match(contract,scope,"CONTRACT")
    _check(contract.get("id")==ids["contractId"]
           and contract.get("storyIntentId")==ids["storyIntentId"]
           and _uuid(contract.get("universeRevisionId"))
           and _uuid(contract.get("worldInstanceRevisionId"))
           and _fp(contract.get("universeFingerprint"))
           and _fp(contract.get("worldInstanceFingerprint")),
           "G2_PROBE_CONTRACT_FROZEN_HEAD_INVALID")
    intent=document.get("intent")
    _scope_match(intent,scope,"INTENT")
    _check(intent.get("id")==ids["storyIntentId"] and
           intent.get("status")=="STORY_STARTED",
           "G2_PROBE_INTENT_NOT_STARTED")
    run=document.get("production_run")
    _scope_match(run,scope,"PRODUCTION_RUN")
    _check(run.get("id")==ids["productionRunId"]
           and run.get("contractId")==ids["contractId"]
           and run.get("status")=="ACCEPTED",
           "G2_PROBE_PRODUCTION_RUN_NOT_ACCEPTED")
    story=document.get("accepted_story")
    _scope_match(story,scope,"ARTIFACT")
    _check(story.get("id")==ids["acceptedStoryArtifactId"]
           and story.get("contractId")==ids["contractId"]
           and story.get("productionRunId")==ids["productionRunId"]
           and _fp(story.get("storyFingerprint"))
           and isinstance(story.get("storyText"),str),
           "G2_PROBE_ACCEPTED_ARTIFACT_INVALID")
    # G2 storyFingerprint uses the production domain fingerprint routine
    # and is NOT necessarily the raw story bytes SHA-256.
    raw_sha=hashlib.sha256(story["storyText"].encode("utf-8")).hexdigest()
    _check(raw_sha==EXPECTED_EN and
           story["storyText"].encode("utf-8")==ENGLISH.read_bytes(),
           "G2_PROBE_ACCEPTED_STORY_CONTENT_MISMATCH")
    universe=document.get("universe_head")
    world=document.get("world_head")
    _check(isinstance(universe,dict) and
           universe.get("universeId")==scope["universeId"] and
           universe.get("householdId")==scope["householdId"] and
           universe.get("currentRevisionId")==contract["universeRevisionId"] and
           universe.get("currentFingerprint")==contract["universeFingerprint"],
           "G2_PROBE_UNIVERSE_STALE")
    _check(isinstance(world,dict) and
           world.get("worldInstanceId")==scope["worldInstanceId"] and
           all(world.get(k)==scope[k] for k in (
               "householdId","profileId","universeId")) and
           world.get("currentRevisionId")==contract["worldInstanceRevisionId"] and
           world.get("currentFingerprint")==contract["worldInstanceFingerprint"],
           "G2_PROBE_WORLD_STALE")
    character=document.get("character_before")
    _check(isinstance(character,dict)
           and character.get("householdId")==scope["householdId"]
           and character.get("profileId")==scope["profileId"]
           and character.get("characterId")==scope["primaryCharacterId"]
           and _uuid(character.get("snapshotId"))
           and _fp(character.get("fingerprint"))
           and isinstance(character.get("revisionNo"),int)
           and not isinstance(character.get("revisionNo"),bool)
           and character["revisionNo"]>0
           and isinstance(character.get("headVersion"),int)
           and not isinstance(character.get("headVersion"),bool)
           and character["headVersion"]>0
           and isinstance(character.get("statePayload"),dict)
           and isinstance(character["statePayload"].get("facts"),dict)
           and isinstance(character["statePayload"].get("emotions"),dict),
           "G2_PROBE_CHARACTER_BASELINE_INVALID")
    char_head=document.get("character_head")
    _check(isinstance(char_head,dict)
           and char_head.get("householdId")==scope["householdId"]
           and char_head.get("profileId")==scope["profileId"]
           and char_head.get("characterId")==scope["primaryCharacterId"]
           and char_head.get("currentSnapshotId")==character["snapshotId"]
           and char_head.get("currentRevisionNo")==character["revisionNo"]
           and char_head.get("currentFingerprint")==character["fingerprint"]
           and char_head.get("version")==character["headVersion"],
           "G2_PROBE_CHARACTER_HEAD_STALE")
    _check(document.get("sourceEnglishSha256")==EXPECTED_EN
           and document.get("sourceTurkishSha256")==EXPECTED_TR
           and document.get("modelProposalSha256")==PROPOSAL_SHA,
           "G2_PROBE_EXPERIMENT_SOURCE_MISMATCH")
    _check(document.get("production_write_authorized") is False
           and document.get("live_database_write_attempted") is False,
           "G2_PROBE_WRITE_REQUEST_FORBIDDEN")
    return {
        "schema":"lumi.v3-f2.g2-authority-consistency-check.v1",
        "snapshot_rows_structurally_consistent":True,
        "accepted_g2_story_bytes_match_f2":True,
        "g2_fingerprint_was_not_treated_as_raw_sha256":True,
        "contract_production_run_story_scope_linkage":"STRUCTURALLY_CONSISTENT",
        "universe_head":"CONSISTENT_WITH_CONTRACT",
        "world_head":"CONSISTENT_WITH_CONTRACT",
        "character_baseline":"PRESENT_IN_SUPPLIED_UNTRUSTED_DOCUMENT",
        "live_database_existence_verified":False,
        "snapshot_authenticated_against_production":False,
        "production_story_artifact_trusted":False,
        "remaining_gate":"AUTHENTICATED_READ_ONLY_G2_SOURCE_REQUIRED",
        "g2_commit_executable":False,
        "g2_commit_request":None,
        "world_state_committed":False,
        "publication_authorized":False,
        "new_provider_posts":0,
    }


def unresolved_report()->dict:
    earlier=preview()
    return {
        "schema":"lumi.v3-f2.g2-authority-resolution.v1",
        "status":"AUTHENTICATED_G2_BINDING_NOT_AVAILABLE",
        "reviewed_production_schema_commit":PROJECT_LUMI_SHA,
        "model_evaluated_earned":earlier["model_earned_count"],
        "model_proposal_sha256":PROPOSAL_SHA,
        "frozen_english_sha256":EXPECTED_EN,
        "frozen_turkish_sha256":EXPECTED_TR,
        "verified_prod_story_contract":False,
        "verified_prod_accepted_artifact":False,
        "verified_live_world_instance_head":False,
        "verified_live_universe_head":False,
        "verified_live_character_state":False,
        "missing_authoritative_bindings":earlier["missing_authoritative_bindings"],
        "read_only_authority_verification_order":[
            "authenticated G2 story contract in correct five-key profile/world scope",
            "accepted production StoryArtifact and its accepted production run",
            "exact UTF-8 English story content against accepted F2 master",
            "frozen and current universe/world revision/fingerprint match",
            "frozen and current character state snapshot and head version match",
            "qualified model-derived facts with bounded exact story quotations",
            "separate sandbox transaction, rollback and explicit commit authority",
        ],
        "no_production_ids_invented":True,
        "source_document_exists_locally":False,
        "live_database_connected":False,
        "world_state_committed":False,
        "no_publication":True,
        "operations_applied":[],
        "safe_to_execute_commit":False,
        "g2_commit_request":None,
        "new_paid_model_posts":0,
        "new_api_cost_usd":"0",
    }


def write_unresolved(out_dir:Path)->dict:
    _check(not out_dir.exists(),"G2_PROBE_OUTPUT_ALREADY_EXISTS")
    result=unresolved_report()
    out_dir.mkdir(parents=True,mode=0o700)
    with (out_dir/"authority-resolution.json").open("x",encoding="utf-8") as file:
        json.dump(result,file,ensure_ascii=False,indent=2)
        file.write("\n");file.flush();os.fsync(file.fileno())
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out-dir",required=True,type=Path)
    opts=parser.parse_args()
    result=write_unresolved(opts.out_dir)
    print(json.dumps({"status":result["status"],
                      "missing_bindings":len(result["missing_authoritative_bindings"]),
                      "g2_commit_request":None,"new_paid_model_posts":0,
                      "world_state_committed":False}))
