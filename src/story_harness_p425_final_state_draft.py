"""P4.25 — deterministic, evidence-bound B01 read-only Final StoryState DRAFT.

Consumes the exact original P4.24 model response, P4.23 pilot English Master,
P4.22 independent initial quality and P4.21 Writer/Spine artifacts.
Never promotes model facts to LUMI production Canon or asserts a final
semantic state certification. No provider call; no text edits.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re

from src.story_harness_p416_input_bridge import sha
from src.story_harness_p424_q25_evidence import (
    load_pilot_source, verify_candidate, SCHEMA as Q25_SCHEMA,
    COST_CAP as Q25_COST_CAP, MODEL, R02_RUN_NAME,
)
from src.story_harness_p417_live_pilot import money
from src.story_harness_p410 import canonical_json
from src.story_harness_v1 import HarnessStop

SCHEMA="lumi.story-harness-p425-read-only-final-story-state-draft.v1"
SOURCE_STORY_SHA="cbbf3ba8cb3a9ec5d19ed51238bc3b9a0259237cdb7896b75dcdd0584adca912"
SOURCE_SPINE_SHA="daafc25a6701a8369be994000e71669722c1cb56364bce3559f5fb8ca944f7a9"
SOURCE_PACK_SHA="91854710f46db13ee2599d567ca2fcbbcd945af50515a779ddee58211ee050dc"
# Exact original JSON receipt, independently persisted in protected runner
# and frozen as an audit document in the Draft PR.
EXPECTED_Q25_RECEIPT_SHA="58f265f5684acf3552b7cf9b9de7cbfca592ef8cc2f3d5d5caa03f6dca324568"
REFERENCE="evidence/story_harness_p424/b01-r06-q25-r02-real-evidence.json"
DRAFT_DIR="p425-b01-r06-"+SOURCE_STORY_SHA[:12]


def must(check, why):
    if not check:
        raise HarnessStop(why)


def load_original_q25(repo_root, q25_root):
    repo=Path(repo_root)
    root=Path(q25_root)
    must(root.is_dir() and not root.is_symlink(),
         "Missing protected original Q25 ledger root")
    file=root/R02_RUN_NAME/"01-q25-proposal.json"
    proof=repo/REFERENCE
    must(file.is_file() and not file.is_symlink()
         and proof.is_file() and not proof.is_symlink(),
         "Original Q25 response and frozen GitHub evidence both required")
    real=file.read_bytes()
    copy=proof.read_bytes()
    must(real==copy and hashlib.sha256(real).hexdigest()==EXPECTED_Q25_RECEIPT_SHA,
         "Q25 receipt bytes drift or wrong recorded model output")
    must(len(real)<50000,"Q25 original receipt size unbounded")
    return json.loads(real)


def qualify_q25(bundle, q25):
    src=bundle["source"]
    pack=src["pack"]
    story=src["story"]
    spine=src["spine"]
    must(type(q25) is dict and q25.get("schema")==Q25_SCHEMA
         and q25.get("case_id")=="B01"
         and q25.get("model")==MODEL
         and q25.get("source_pack_sha256")==pack["pack_sha256"]==SOURCE_PACK_SHA
         and q25.get("spine_sha256")==spine["spine_sha256"]==SOURCE_SPINE_SHA
         and q25.get("story_sha256")==story["story_sha256"]==SOURCE_STORY_SHA
         and type(q25.get("generation_id")) is str
         and re.fullmatch(r"gen-[A-Za-z0-9_-]{6,120}",q25["generation_id"])
         and q25.get("provenance_verified") is True
         and q25.get("quote_matching_verified") is True
         and q25.get("prior_english_master_unchanged") is True
         and q25.get("semantic_state_fully_certified") is False
         and q25.get("final_story_state_committed") is False
         and q25.get("production_state_write_authorized") is False,
         "Q25 outcome not the actual source-aligned evidence-only pilot")
    usage=q25.get("provider_usage")
    must(type(usage) is dict and
         type(usage.get("prompt_tokens")) is int and
         type(usage.get("completion_tokens")) is int and
         usage["prompt_tokens"]>=0 and usage["completion_tokens"]>=0,
         "Q25 model receipt must preserve real token counts")
    cost=money(q25.get("provider_reported_cost_usd"))
    must(cost<=Q25_COST_CAP, "Original Q25 cost exceeded stage authorization")
    observations=q25.get("evidence_proposal")
    must(type(observations) is dict,"Missing actual model state observations")
    # Completely reexecute quote, source and canon checks. The stored
    # q25 quote_matching_verified flag does not certify itself.
    envelope={
        "source_pack_sha256":pack["pack_sha256"],
        "story_sha256":story["story_sha256"],
        "spine_sha256":spine["spine_sha256"],
        "evidence_json":json.dumps(observations,sort_keys=True,
                      separators=(",",":"),ensure_ascii=False),
        "explanation":"A replay of immutable quote-bound original Q25 evidence.",
    }
    grounded=verify_candidate(bundle,envelope)
    return grounded,cost


def project_proposed_state(bundle, q25):
    observation,cost=qualify_q25(bundle,q25)
    pack=bundle["source"]["pack"]
    canon=deepcopy(pack["canonical_state"])
    initially_known=list(canon["protagonist"]["known_locations"])
    discovered=[x["location_id"] for x in observation["discovered_locations"]]
    known_ordered=initially_known+[x for x in discovered if x not in initially_known]
    # Do NOT claim that original canonical object IDs/ownership are known.
    # Retain candidates separately from preexisting Canon object collection.
    final_location=observation["final_location"]
    result={
        "schema":SCHEMA,
        "case_id":"B01",
        "artifact_classification":"READ_ONLY_FINAL_STORY_STATE_DRAFT_NOT_CANON",
        "source_pack_sha256":pack["pack_sha256"],
        "source_spine_sha256":bundle["source"]["spine"]["spine_sha256"],
        "english_master_sha256":bundle["source"]["story"]["story_sha256"],
        "original_q25_generation_id":q25["generation_id"],
        "original_q25_model":q25["model"],
        "original_q25_reported_cost_usd":format(cost,"f"),
        "canonical_start_snapshot_sha256":sha(canon),
        "original_protagonist_name":canon["protagonist"]["name"],
        "final_protagonist_location_proposal":deepcopy(final_location),
        "known_locations_proposal":known_ordered,
        "newly_discovered_location_evidence":deepcopy(observation["discovered_locations"]),
        "observed_objects_not_admitted_to_canon":deepcopy(observation["object_observations"]),
        "original_canonical_objects_unchanged":deepcopy(canon["objects"]),
        "open_canonical_obligations_unchanged":deepcopy(canon["open_obligations"]),
        "obligation_closure_evidence_not_yet_approved":deepcopy(observation["open_obligation_outcomes"]),
        "unknown_facts_retained":deepcopy(observation["unknown_facts_retained"]),
        "world_time_initial_snapshot":canon["world_time"],
        "world_time_final":None,
        "world_time_status":"UNMEASURED_DELTA_NOT_COMMITTED",
        "independent_state_semantic_validator_passed":False,
        "original_v21_4_full_final_quality_audit_passed":False,
        "state_commit_authorized":False,
        "production_change":False,
        "model_calls_for_projection":0,
        "manual_prose_edits":0,
    }
    must(result["unknown_facts_retained"]==canon["unknown_facts"],
         "Unknown facts removed by projection")
    must(all(o["ownership"]=="UNKNOWN"
             for o in result["observed_objects_not_admitted_to_canon"]),
         "Q25 projected unknown object owner as a fact")
    must(result["world_time_final"] is None and
         result["open_canonical_obligations_unchanged"]==canon["open_obligations"],
         "Q25 projection silently changed unproven time or open commitments")
    return result


def write_once(path,payload):
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    if hasattr(os,"O_NOFOLLOW"): flags|=os.O_NOFOLLOW
    handle=os.open(path,flags,0o600)
    with os.fdopen(handle,"wb") as file:
        file.write(canonical_json(payload)+b"\n")
        file.flush()
        os.fsync(file.fileno())


def freeze_state_draft(bundle,q25,master_root):
    root=Path(master_root)
    must(root.is_dir() and not root.is_symlink(),
         "Read-only final state proposal root absent")
    proposal=project_proposed_state(bundle,q25)
    folder=root/DRAFT_DIR
    folder.mkdir(mode=0o700,exist_ok=False)
    write_once(folder/"final-state-draft.json",proposal)
    return proposal


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root",default=".")
    parser.add_argument("--producer-claims")
    parser.add_argument("--quality-claims")
    parser.add_argument("--master-root")
    parser.add_argument("--q25-claims")
    parser.add_argument("--final-state-root")
    parser.add_argument("--freeze-once",action="store_true")
    args=parser.parse_args()
    if not args.freeze_once:
        print(json.dumps({"schema":SCHEMA,"read_only":True,
                          "provider_calls":0,"state_commit_authorized":False,
                          "original_q25_source_checked":False},sort_keys=True))
        return
    must(args.producer_claims and args.quality_claims and args.master_root
         and args.q25_claims and args.final_state_root,
         "Required immutable source and final state claim roots missing")
    bundle=load_pilot_source(args.repo_root,args.producer_claims,
                             args.quality_claims,args.master_root)
    q25=load_original_q25(args.repo_root,args.q25_claims)
    state=freeze_state_draft(bundle,q25,args.final_state_root)
    print(json.dumps({
        "schema":SCHEMA,
        "source_story_sha256":state["english_master_sha256"],
        "proposed_final_location":state["final_protagonist_location_proposal"]["location_id"],
        "newly_discovered_locations":len(state["newly_discovered_location_evidence"]),
        "observed_objects_with_unknown_owner":len(state["observed_objects_not_admitted_to_canon"]),
        "state_commit_authorized":False,
        "model_calls_for_projection":0,
    },sort_keys=True))


if __name__=="__main__":
    main()
