"""Read-only F2 -> Project_LUMI G2 state mapping and synthetic rollback lab.

NO production database, no model, no HTTP, no SQL, no GitHub mutation.
A model verdict is not a UUID-bound accepted G2 StoryArtifact or commit.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from pathlib import Path

from experiments.v3_f2_world_outcome_offline_replay import SOURCE_SHA as LUNA_SOURCE_SHA
from experiments.v3_f2_world_outcome_evidence_gate import EXPECTED_EN, EXPECTED_TR
from experiments.v3_f2_final_delivery_stage import verify_sources
from src.frozen_lane_verify import verify_frozen_lane

MODEL_PROPOSAL=Path("evidence/v3-f2-world-outcome-verified-replay-20261015/world-outcome-proposal.json")
REPLAY=Path("evidence/v3-f2-world-outcome-verified-replay-20261015/offline-replay-manifest.json")
ENGLISH=Path("evidence/v3-f2-final-delivery-staging-20261015/story.en.txt")
PROFILE=Path("data/specifications/story_lab/age18_story_lane_profile_v2_frozen.json")
PROPOSAL_SHA="0797f6e55804b6969eb07dab04bfcfd02b693294f4ed531a40bf6f07bec5ff93"
PROJECT_LUMI_SHA="64fe6a7201978d09ce5c3a8f38e79f05f8e7f5f0"
G2_SCOPE_KEYS=(
    "householdId","profileId","universeId","worldInstanceId",
    "primaryCharacterId","contractId","storyIntentId",
    "acceptedStoryArtifactId",
)
G2_FROZEN_HEAD_KEYS=(
    "worldBeforeRevisionId","worldBeforeFingerprint",
    "universeRevisionId","universeFingerprint",
    "characterBeforeSnapshotId","characterBeforeFingerprint",
    "characterBeforeRevisionNo","characterBeforeHeadVersion",
)
G2_MUTATIONS=("NODE_STATE_SET","EDGE_STATE_SET")
G2_MUTATION_STATUSES={
    "NODE_STATE_SET":{"active","inactive","blocked","destroyed","unknown"},
    "EDGE_STATE_SET":{"open","restricted","blocked","inaccessible"},
}
FIXTURE_MARKER="SYNTHETIC_G2_IN_MEMORY_TEST_ONLY"
UUID_RE=re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class G2PreviewStop(RuntimeError):
    pass


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(obj)->str:
    return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,
                                   separators=(",",":")).encode()).hexdigest()


def _check(value,reason):
    if not value: raise G2PreviewStop(reason)


def verify_model_proposal()->dict:
    verify_sources()
    frozen=verify_frozen_lane(PROFILE)
    _check(frozen["verified_files"]==43,"FROZEN_SOURCE_MISMATCH")
    _check(sha(ENGLISH)==EXPECTED_EN,"ENGLISH_MASTER_CHANGED")
    _check(sha(MODEL_PROPOSAL)==PROPOSAL_SHA,"MODEL_VERDICT_TAMPERED")
    model=json.loads(MODEL_PROPOSAL.read_text())
    replay=json.loads(REPLAY.read_text())
    _check(replay["status"]=="MODEL_EVALUATED_WORLD_DELTA_UNCOMMITTED"
           and replay["original_provider_response_sha256"]==LUNA_SOURCE_SHA
           and replay["additional_provider_posts"]==0
           and replay["original_provider_run_id"]==38726200623
           and replay["world_state_committed"] is False,
           "REPLAY_PROVENANCE_INVALID")
    _check(model["status"]=="MODEL_EVALUATED_WORLD_DELTA_UNCOMMITTED"
           and model["case_id"]=="age18.forbidden-cartographer.fantasy.frozen-01"
           and model["english_sha256"]==EXPECTED_EN
           and model["turkish_sha256"]==EXPECTED_TR
           and model["model_selected_branch"]=="seal_bounded_report"
           and model["world_state_transaction"] is None
           and model["applied_operations"]==[]
           and model["world_state_committed"] is False
           and model["world_state_commit_authorized"] is False
           and model["publication_authorized"] is False,
           "NONCOMMITTING_PROPOSAL_REQUIRED")
    rows=model["approved_persistent_candidates"]
    _check(len(rows)==5 and {x["candidate_id"] for x in rows}
           =={"f2-outcome-0"+str(i) for i in range(1,6)},
           "FIVE_MODEL_CANDIDATES_REQUIRED")
    _check(all(x["model_condition_verdict"]=="EARNED"
               and x["commit_authorized"] is False
               and x["applied"] is False
               for x in rows),"MODEL_EARNED_BUT_UNCOMMITTED_REQUIRED")
    return model


# An explicit inventory of the writable V1 G2 StoryOutcome envelope,
# verified from Project_LUMI G2 source, NOT invented production mutations.
# G2 world mutations can only target pre-existing universe node/edge IDs.
# Relationship, reputation and generic facts need a frozen CharacterState
# before/after mapping, and may not be translated to a fake node/edge.
KIND_TO_REVIEW={
    "f2-outcome-01":("CHARACTER_STATE_FACT_CANDIDATE","CHARACTER_FACT_KEY_AND_BEFORE_SNAPSHOT_MISSING"),
    "f2-outcome-02":("FOLLOW_UP_ACCESS_ELIGIBILITY_ONLY","NOT_A_GRANTED_ROUTE_OR_EDGE_ACCESS_CHANGE"),
    "f2-outcome-03":("COMMUNITY_PERCEPTION_REVIEW","NO_G2_REPUTATION_WORLD_MUTATION_KIND"),
    "f2-outcome-04":("CHARACTER_RELATIONSHIP_REVIEW","NO_BOUNDED_G2_RELATIONSHIP_DELTA_WITH_BASELINE"),
    "f2-outcome-05":("CHARACTER_STATE_FACT_CANDIDATE","CHARACTER_FACT_KEY_AND_BEFORE_SNAPSHOT_MISSING"),
}


def missing_bindings(binding:dict|None)->list[str]:
    """Never synthesize authoritative UUIDs, head revisions or fingerprints."""
    if not isinstance(binding,dict):
        return list(G2_SCOPE_KEYS+G2_FROZEN_HEAD_KEYS)
    missing=[]
    for k in G2_SCOPE_KEYS+("worldBeforeRevisionId","universeRevisionId",
                            "characterBeforeSnapshotId"):
        val=binding.get(k)
        if not isinstance(val,str) or not UUID_RE.fullmatch(val):
            missing.append(k)
    for k in ("worldBeforeFingerprint","universeFingerprint",
              "characterBeforeFingerprint"):
        val=binding.get(k)
        if not isinstance(val,str) or not re.fullmatch("[a-f0-9]{64,128}",val):
            missing.append(k)
    for k in ("characterBeforeRevisionNo","characterBeforeHeadVersion"):
        if (not isinstance(binding.get(k),int)
            or isinstance(binding[k],bool) or binding[k]<0):
            missing.append(k)
    return missing


def preferred_proof_quote(row:dict,story:str)->str:
    """Choose only existing contiguous literal quotes <=280 chars for G2."""
    for quote in row["evidence_quotes"]:
        if isinstance(quote,str) and 4<=len(quote)<=280 and quote in story:
            return quote
    raise G2PreviewStop("G2_EXACT_BOUNDED_EVIDENCE_QUOTE_MISSING")


def preview(binding:dict|None=None)->dict:
    model=verify_model_proposal()
    _check(binding is None or isinstance(binding,dict),"INVALID_G2_BINDING_INPUT")
    story=ENGLISH.read_text(encoding="utf-8")
    unbound=missing_bindings(binding)
    records=[]
    for row in model["approved_persistent_candidates"]:
        cid=row["candidate_id"]
        kind,reason=KIND_TO_REVIEW[cid]
        if cid.startswith("f2-outcome-0") and cid in ("f2-outcome-02","f2-outcome-03"):
            _check(row["kind"] in ("ACCESS","REPUTATION"),"MODEL_KIND_CONFLICT")
        evidence=preferred_proof_quote(row,story)
        records.append({
            "candidate_id":cid,
            "model_verdict":row["model_condition_verdict"],
            "source_model_explanation":row["model_explanation"],
            "narrative_kind":row["kind"],
            "proposed_g2_class":kind,
            "g2_executable_mutation":None,
            "g2_fact_key":None,
            "g2_delta":None,
            "reason_blocked":reason,
            "exact_evidence_quote":evidence,
            "exact_evidence_sha256":hashlib.sha256(evidence.encode()).hexdigest(),
            "mapping_status":"NEEDS_AUTHORITATIVE_SCOPE_AND_BASELINE",
            "ready_to_commit":False,
            "applied":False,
        })
    # G2 StoryOutcome requires an accepted production StoryArtifact and
    # either a CharacterStoryState payload or world node/edge mutations.
    # The experimental F2 bundle is NOT a production G2 StoryArtifact.
    result={
        "schema":"lumi.v3-f2.g2-world-state-dry-run.v1",
        "source_model_outcome_sha256":PROPOSAL_SHA,
        "accepted_english_sha256":EXPECTED_EN,
        "accepted_turkish_sha256":EXPECTED_TR,
        "source_g2_repository":"necdetoskay/Project_LUMI",
        "source_g2_commit":PROJECT_LUMI_SHA,
        "model_selected_branch":model["model_selected_branch"],
        "model_earned_count":5,
        "model_evaluated_saga_milestone":model["proposed_saga_milestone"]["key"],
        "g2_mapping_status":"BLOCKED_PENDING_AUTHORITATIVE_BINDINGS",
        "missing_authoritative_bindings":unbound,
        "production_g2_accepted_story_artifact_verified":False,
        "production_story_contract_verified":False,
        "production_world_heads_verified":False,
        "production_character_snapshot_verified":False,
        "narrative_outcome_mappings":records,
        "permitted_world_mutation_kinds":list(G2_MUTATIONS),
        "world_node_edge_mutations":[],
        "character_state_delta":None,
        "g2_commit_request":None,
        "g2_commit_executable":False,
        "proposed_executable_operations":[],
        "dry_run_only":True,
        "live_database_connected":False,
        "live_transaction_attempted":False,
        "publication_authorized":False,
        "world_state_commit_authorized":False,
        "world_state_committed":False,
        "applied_operations":[],
    }
    return result


def _fixture(snapshot:dict)->dict:
    _check(isinstance(snapshot,dict)
           and snapshot.get("marker")==FIXTURE_MARKER
           and isinstance(snapshot.get("scope"),dict)
           and isinstance(snapshot.get("nodes"),dict)
           and isinstance(snapshot.get("edges"),dict)
           and isinstance(snapshot.get("ledger"),dict)
           and isinstance(snapshot.get("revision"),int),
           "SYNTHETIC_FIXTURE_REQUIRED")
    return snapshot


def _operation(op:dict,snapshot:dict)->tuple[str,str,dict]:
    _check(isinstance(op,dict) and op.get("kind") in G2_MUTATIONS,
           "G2_OPERATION_KIND_UNSUPPORTED")
    kind=op["kind"]
    entity_key="nodeId" if kind=="NODE_STATE_SET" else "edgeId"
    table="nodes" if kind=="NODE_STATE_SET" else "edges"
    field="status" if kind=="NODE_STATE_SET" else "availability"
    entity=op.get(entity_key)
    _check(isinstance(entity,str) and UUID_RE.fullmatch(entity) is not None,
           "G2_OPERATION_TARGET_UUID_INVALID")
    _check(entity in snapshot[table],"G2_OPERATION_TARGET_NOT_FOUND")
    target=snapshot[table][entity]
    _check(target.get("scope")==snapshot["scope"],
           "G2_OPERATION_CROSS_SCOPE_DENIED")
    val=op.get(field)
    _check(val in G2_MUTATION_STATUSES[kind],"G2_OPERATION_STATE_INVALID")
    _check(isinstance(op.get("evidenceQuote"),str)
           and 4<=len(op["evidenceQuote"])<=280
           and op["evidenceQuote"] in ENGLISH.read_text(encoding="utf-8"),
           "G2_OPERATION_EVIDENCE_NOT_IN_STORY")
    return table,entity,{**target,field:val}


def simulate_fixture_atomic_commit(snapshot:dict,*,contract_id:str,
                                   expected_revision:int,ops:list[dict])->dict:
    """ALL OR NOTHING on a Python COPY, never a database transaction."""
    s=copy.deepcopy(_fixture(snapshot))
    _check(isinstance(contract_id,str) and UUID_RE.fullmatch(contract_id) is not None,
           "G2_FIXTURE_CONTRACT_INVALID")
    _check(isinstance(expected_revision,int) and not isinstance(expected_revision,bool),
           "G2_FIXTURE_EXPECTED_REVISION_INVALID")
    _check(isinstance(ops,list) and bool(ops),"G2_FIXTURE_MUTATIONS_REQUIRED")
    intent=fingerprint(ops)
    if contract_id in s["ledger"]:
        _check(s["ledger"][contract_id]["operation_fingerprint"]==intent,
               "G2_FIXTURE_REPLAY_CONFLICT")
        return {"status":"IDEMPOTENT_SYNTHETIC_REPLAY",
                "before":copy.deepcopy(s),"after":s,
                "rollback":None,"applied_operations":[],
                "live_db_writes":0}
    _check(s["revision"]==expected_revision,"G2_FIXTURE_STALE_REVISION")
    staged=[]
    seen=set()
    for op in ops:
        table,key,next_value=_operation(op,s)
        _check((table,key) not in seen,"G2_FIXTURE_DUPLICATE_MUTATION")
        seen.add((table,key))
        staged.append((table,key,next_value))
    before=copy.deepcopy(s)
    for table,key,value in staged:
        s[table][key]=value
    s["revision"]+=1
    s["ledger"][contract_id]={
        "operation_fingerprint":intent,"before_fingerprint":fingerprint(before),
        "expected_revision":expected_revision,
    }
    proof={
        "schema":"lumi.g2.synthetic-compensation-proof.v1",
        "before_state":before,
        "post_fingerprint":fingerprint(s),
        "contract_id":contract_id,
    }
    return {
        "status":"SYNTHETIC_COMMIT_SIMULATED",
        "before":before,
        "after":s,
        "rollback":proof,
        "applied_operations":[{"kind":op["kind"],"synthetic_only":True} for op in ops],
        "live_db_writes":0,
    }


def simulate_fixture_compensation(after:dict,proof:dict)->dict:
    """A stale post-state blocks compensation; no hidden live rollback."""
    _fixture(after)
    _check(isinstance(proof,dict) and proof.get("schema")==
           "lumi.g2.synthetic-compensation-proof.v1",
           "G2_FIXTURE_ROLLBACK_PROOF_INVALID")
    _check(fingerprint(after)==proof.get("post_fingerprint"),
           "G2_FIXTURE_ROLLBACK_STALE_POST_STATE")
    before=proof.get("before_state")
    _fixture(before)
    _check(proof["contract_id"] in after["ledger"],
           "G2_FIXTURE_ROLLBACK_CONTRACT_NOT_APPLIED")
    return {
        "status":"SYNTHETIC_COMPENSATION_SIMULATED",
        "restored":copy.deepcopy(before),
        "restored_fingerprint":fingerprint(before),
        "live_db_writes":0,
    }


def synthetic_transaction_report()->dict:
    """Synthetic-only memory check; this is NOT a G2 PostgreSQL test."""
    scope={
        "householdId":"11111111-1111-4111-8111-111111111111",
        "profileId":"22222222-2222-4222-8222-222222222222",
        "worldInstanceId":"33333333-3333-4333-8333-333333333333",
    }
    node="44444444-4444-4444-8444-444444444444"
    edge="55555555-5555-4555-8555-555555555555"
    contract="66666666-6666-4666-8666-666666666666"
    quote=preview()["narrative_outcome_mappings"][0]["exact_evidence_quote"]
    start={
        "marker":FIXTURE_MARKER,"scope":scope,"revision":4,
        "nodes":{node:{"scope":copy.deepcopy(scope),"status":"inactive"}},
        "edges":{edge:{"scope":copy.deepcopy(scope),"availability":"blocked"}},
        "ledger":{},
    }
    ops=[
        {"kind":"NODE_STATE_SET","nodeId":node,"status":"active",
         "statePayload":{},"evidenceQuote":quote},
        {"kind":"EDGE_STATE_SET","edgeId":edge,"availability":"restricted",
         "conditionPayload":{},"validFromTick":None,"expectedUntilTick":None,
         "evidenceQuote":quote},
    ]
    baseline=fingerprint(start)
    done=simulate_fixture_atomic_commit(
        start,contract_id=contract,expected_revision=4,ops=ops
    )
    copied=fingerprint(start)==baseline
    redo=simulate_fixture_atomic_commit(
        done["after"],contract_id=contract,expected_revision=4,ops=ops
    )
    undo=simulate_fixture_compensation(done["after"],done["rollback"])
    stale_rejected=False
    try:
        simulate_fixture_atomic_commit(
            start,contract_id=contract,expected_revision=3,ops=ops
        )
    except G2PreviewStop as exc:
        stale_rejected=str(exc)=="G2_FIXTURE_STALE_REVISION"
    conflict_rejected=False
    try:
        simulate_fixture_atomic_commit(
            done["after"],contract_id=contract,expected_revision=5,
            ops=[{**ops[0],"status":"destroyed"}]
        )
    except G2PreviewStop as exc:
        conflict_rejected=str(exc)=="G2_FIXTURE_REPLAY_CONFLICT"
    checks={
        "original_snapshot_unchanged":copied,
        "both_synthetic_operations_committed_together":
            len(done["applied_operations"])==2,
        "idempotent_replay_created_no_extra_operations":
            redo["status"]=="IDEMPOTENT_SYNTHETIC_REPLAY"
            and not redo["applied_operations"]
            and redo["after"]==done["after"],
        "stale_snapshot_denied":stale_rejected,
        "conflicting_contract_replay_denied":conflict_rejected,
        "compensation_restored_exact_baseline":
            undo["restored_fingerprint"]==baseline
            and undo["restored"]==start,
        "live_database_writes_zero":
            done["live_db_writes"]==redo["live_db_writes"]
            ==undo["live_db_writes"]==0,
    }
    _check(all(checks.values()),"G2_SYNTHETIC_TRANSACTION_SELF_TEST_FAILED")
    return {
        "schema":"lumi.v3-f2.g2.synthetic-transaction-report.v1",
        "status":"SYNTHETIC_IN_MEMORY_TEST_PASS",
        "is_actual_g2_postgres_test":False,
        "has_g2_db_connector":False,
        "has_real_project_lumi_scope":False,
        "node_edge_identifiers_are_synthetic":True,
        "uses_actual_f2_character_ids":False,
        "checks":checks,
        "verified_cases":len(checks),
        "initial_snapshot_sha256":baseline,
        "rollback_restored_snapshot_sha256":undo["restored_fingerprint"],
        "production_write_permission":False,
        "production_operations_applied":0,
        "provider_calls":0,
    }


def _write_exclusive(path:Path,obj:dict):
    with path.open("x",encoding="utf-8") as f:
        json.dump(obj,f,ensure_ascii=False,indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def write_preview(out_dir:Path)->dict:
    _check(not out_dir.exists(),"G2_DRY_RUN_OUTPUT_ALREADY_EXISTS")
    result=preview()
    out_dir.mkdir(parents=True,mode=0o700)
    _write_exclusive(out_dir/"g2-mapping-preview.json",result)
    _write_exclusive(out_dir/"synthetic-transaction-report.json",
                     synthetic_transaction_report())
    return result


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--out-dir",required=True,type=Path)
    args=p.parse_args()
    result=write_preview(args.out_dir)
    print(json.dumps({"status":result["g2_mapping_status"],
                      "model_earned":result["model_earned_count"],
                      "g2_executable_operations":0,
                      "missing_binding_count":len(result["missing_authoritative_bindings"]),
                      "world_state_committed":False,"provider_posts":0,
                      "new_cost_usd":"0"}))
