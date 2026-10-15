"""Real G2 contract shape; synthetic rows NEVER establish live DB authority."""
from __future__ import annotations
import copy
import hashlib
import json
import pytest

from experiments import v3_f2_g2_readonly_authority_probe as p

IDS={
    "householdId":"11111111-1111-4111-8111-111111111111",
    "profileId":"22222222-2222-4222-8222-222222222222",
    "universeId":"33333333-3333-4333-8333-333333333333",
    "worldInstanceId":"44444444-4444-4444-8444-444444444444",
    "primaryCharacterId":"55555555-5555-4555-8555-555555555555",
}
STORY_IDS={
    "contractId":"66666666-6666-4666-8666-666666666666",
    "storyIntentId":"77777777-7777-4777-8777-777777777777",
    "productionRunId":"88888888-8888-4888-8888-888888888888",
    "acceptedStoryArtifactId":"99999999-9999-4999-8999-999999999999",
}
U_REV="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
W_REV="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
CHAR_SNAPSHOT="cccccccc-cccc-4ccc-8ccc-cccccccccccc"


def synthetic_snapshot():
    c={"id":STORY_IDS["contractId"],"storyIntentId":STORY_IDS["storyIntentId"],
       "universeRevisionId":U_REV,"universeFingerprint":"1"*64,
       "worldInstanceRevisionId":W_REV,"worldInstanceFingerprint":"2"*64,**IDS}
    return {
        "schema":p.SCHEMA,"repo_sha":p.PROJECT_LUMI_SHA,
        "scope":copy.deepcopy(IDS),
        "story_ids":copy.deepcopy(STORY_IDS),
        "contract":c,
        "intent":{"id":STORY_IDS["storyIntentId"],"status":"STORY_STARTED",**IDS},
        "production_run":{"id":STORY_IDS["productionRunId"],
                          "contractId":STORY_IDS["contractId"],
                          "status":"ACCEPTED",**IDS},
        "accepted_story":{
            "id":STORY_IDS["acceptedStoryArtifactId"],
            "contractId":STORY_IDS["contractId"],
            "productionRunId":STORY_IDS["productionRunId"],
            # Domain-specific G2 fingerprint must not be confused with raw SHA.
            "storyFingerprint":"d"*64,
            "storyText":p.ENGLISH.read_text(encoding="utf-8"),
            **IDS,
        },
        "universe_head":{
            "householdId":IDS["householdId"],"universeId":IDS["universeId"],
            "currentRevisionId":U_REV,"currentFingerprint":"1"*64,
        },
        "world_head":{
            "worldInstanceId":IDS["worldInstanceId"],
            "householdId":IDS["householdId"],
            "profileId":IDS["profileId"],
            "universeId":IDS["universeId"],
            "currentRevisionId":W_REV,"currentFingerprint":"2"*64,
        },
        "character_before":{
            "householdId":IDS["householdId"],"profileId":IDS["profileId"],
            "characterId":IDS["primaryCharacterId"],"snapshotId":CHAR_SNAPSHOT,
            "revisionNo":2,"headVersion":4,
            "fingerprint":"3"*64,
            "statePayload":{"facts":{},"emotions":{},"goals":[],"experiences":[]},
        },
        "character_head":{
            "householdId":IDS["householdId"],"profileId":IDS["profileId"],
            "characterId":IDS["primaryCharacterId"],
            "currentSnapshotId":CHAR_SNAPSHOT,
            "currentRevisionNo":2,"currentFingerprint":"3"*64,
            "version":4,
        },
        "sourceEnglishSha256":p.EXPECTED_EN,
        "sourceTurkishSha256":p.EXPECTED_TR,
        "modelProposalSha256":p.PROPOSAL_SHA,
        "production_write_authorized":False,
        "live_database_write_attempted":False,
    }


def test_unresolved_actual_lumi_g2_binding_report_fail_closed():
    report=p.unresolved_report()
    assert report["status"]=="AUTHENTICATED_G2_BINDING_NOT_AVAILABLE"
    assert len(report["missing_authoritative_bindings"])==16
    assert report["model_evaluated_earned"]==5
    assert not report["verified_prod_story_contract"]
    assert not report["verified_prod_accepted_artifact"]
    assert report["g2_commit_request"] is None
    assert not report["safe_to_execute_commit"]
    assert not report["live_database_connected"]
    assert not report["world_state_committed"]
    assert report["new_api_cost_usd"]=="0"


def test_synthetic_consistent_rows_still_do_not_prove_real_production():
    result=p.validate_untrusted_snapshot(synthetic_snapshot())
    assert result["snapshot_rows_structurally_consistent"] is True
    assert result["accepted_g2_story_bytes_match_f2"] is True
    assert result["g2_fingerprint_was_not_treated_as_raw_sha256"] is True
    assert result["production_story_artifact_trusted"] is False
    assert result["live_database_existence_verified"] is False
    assert result["snapshot_authenticated_against_production"] is False
    assert result["g2_commit_executable"] is False
    assert result["g2_commit_request"] is None
    assert result["world_state_committed"] is False


@pytest.mark.parametrize("path,value,reason",[
    (("scope","profileId"),"not-uuid","G2_PROBE_SCOPE_UUID_INVALID"),
    (("contract","profileId"),"ffffffff-ffff-4fff-8fff-ffffffffffff","G2_CONTRACT_SCOPE_MISMATCH"),
    (("intent","status"),"COMPLETED","G2_PROBE_INTENT_NOT_STARTED"),
    (("production_run","status"),"STARTED","G2_PROBE_PRODUCTION_RUN_NOT_ACCEPTED"),
    (("production_run","contractId"),"ffffffff-ffff-4fff-8fff-ffffffffffff","G2_PROBE_PRODUCTION_RUN_NOT_ACCEPTED"),
    (("accepted_story","contractId"),"ffffffff-ffff-4fff-8fff-ffffffffffff","G2_PROBE_ACCEPTED_ARTIFACT_INVALID"),
    (("accepted_story","storyText"),"fake text","G2_PROBE_ACCEPTED_STORY_CONTENT_MISMATCH"),
    (("universe_head","currentFingerprint"),"8"*64,"G2_PROBE_UNIVERSE_STALE"),
    (("world_head","currentRevisionId"),"ffffffff-ffff-4fff-8fff-ffffffffffff","G2_PROBE_WORLD_STALE"),
    (("character_before","headVersion"),-1,"G2_PROBE_CHARACTER_BASELINE_INVALID"),
    (("character_head","version"),5,"G2_PROBE_CHARACTER_HEAD_STALE"),
    (("character_before","revisionNo"),0,"G2_PROBE_CHARACTER_BASELINE_INVALID"),
    (("sourceEnglishSha256",),"8"*64,"G2_PROBE_EXPERIMENT_SOURCE_MISMATCH"),
    (("production_write_authorized",),True,"G2_PROBE_WRITE_REQUEST_FORBIDDEN"),
    (("repo_sha",),"0"*40,"G2_PROBE_SCHEMA_VERSION_CHANGED"),
])
def test_invalid_or_conflicting_g2_evidence_fails_closed(path,value,reason):
    row=synthetic_snapshot()
    dest=row
    for key in path[:-1]:
        dest=dest[key]
    dest[path[-1]]=value
    with pytest.raises(p.ProbeStop,match=reason):
        p.validate_untrusted_snapshot(row)


def test_missing_accepted_artifact_and_production_run_cannot_pass():
    for k in ("accepted_story","production_run","contract","character_before","character_head","world_head"):
        document=synthetic_snapshot()
        document.pop(k)
        with pytest.raises(p.ProbeStop):
            p.validate_untrusted_snapshot(document)


def test_experiment_master_is_unchanged_by_synthetic_provenance_probe(tmp_path):
    original=p.ENGLISH.read_bytes()
    sample=synthetic_snapshot()
    p.validate_untrusted_snapshot(sample)
    assert p.ENGLISH.read_bytes()==original
    assert hashlib.sha256(original).hexdigest()==p.EXPECTED_EN


def test_output_generated_once_only_is_deterministic(tmp_path):
    x=p.write_unresolved(tmp_path/"a")
    y=p.write_unresolved(tmp_path/"b")
    assert x==y
    assert (tmp_path/"a"/"authority-resolution.json").read_bytes()==(
        tmp_path/"b"/"authority-resolution.json").read_bytes()
    with pytest.raises(p.ProbeStop,match="G2_PROBE_OUTPUT_ALREADY_EXISTS"):
        p.write_unresolved(tmp_path/"a")
