"""P4.30 — real B02 Q25 evidence → immutable, read-only Final StoryState draft.

Replays the EXACT Q25/Writer/Spine/quality/Master artifacts and re-checks all
verbatim quotes and Canon identities. An OPEN original obligation stays OPEN.
No production state writes; no new model calls, no fake semantic certification.
"""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal
import hashlib,json,os
from pathlib import Path
import re

from src.story_harness_p416_input_bridge import sha
from src.story_harness_p410 import canonical_json
from src.story_harness_p424_q25_evidence import verify_candidate,COST_CAP
from src.story_harness_p429_b02_q25 import (
    load_b02_bundle,SCHEMA as Q25_SCHEMA,
    RUN_NAME as Q25_RUN_NAME,MODEL,SPINE_SHA,STORY_SHA,SOURCE_SHA,
)
from src.story_harness_v1 import HarnessStop

SCHEMA="lumi.story-harness-p430-b02-read-only-final-state-draft.v1"
Q25_REFERENCE="evidence/story_harness_p429/b02-r06-original-q25-evidence.json"
Q25_RECEIPT_SHA="27df345c2433b7828b6c8439f5eae44420cebf31cc03fbdf08a3fc067187f27f"
DIR="p430-b02-r06-"+STORY_SHA[:12]

def must(condition,reason):
    if not condition:raise HarnessStop(reason)

def load_original_q25(repo_root,q25_claims):
    f=Path(q25_claims)/Q25_RUN_NAME/"01-b02-q25-evidence.json"
    saved=Path(repo_root)/Q25_REFERENCE
    must(f.is_file() and saved.is_file()
         and not f.is_symlink() and not saved.is_symlink(),
         "Missing original and frozen B02 Q25 evidence")
    raw=f.read_bytes()
    must(len(raw)<65000 and raw==saved.read_bytes()
         and hashlib.sha256(raw).hexdigest()==Q25_RECEIPT_SHA,
         "Original Q25 evidence bytes tampered")
    return json.loads(raw)

def qualify_source_and_evidence(bundle,result):
    source=bundle["source"]
    must(source.get("case_id")=="B02"
         and source["pack"]["pack_sha256"]==SOURCE_SHA
         and source["spine"]["spine_sha256"]==SPINE_SHA
         and source["story"]["story_sha256"]==STORY_SHA,
         "B02 final state source not exact approved story and Spine")
    must(type(result) is dict and result.get("schema")==Q25_SCHEMA
         and result.get("case_id")=="B02"
         and result.get("model")==MODEL
         and result.get("source_pack_sha256")==SOURCE_SHA
         and result.get("spine_sha256")==SPINE_SHA
         and result.get("story_sha256")==STORY_SHA
         and type(result.get("generation_id")) is str
         and re.fullmatch(r"gen-[A-Za-z0-9_-]{6,120}",result["generation_id"])
         and result.get("provenance_verified") is True
         and result.get("quote_matching_verified") is True
         and result.get("prior_english_master_unchanged") is True
         and result.get("semantic_state_fully_certified") is False
         and result.get("final_story_state_committed") is False
         and result.get("production_state_write_authorized") is False,
         "B02 Q25 not properly evidence-only or source-bound")
    cost=Decimal(str(result.get("provider_reported_cost_usd")))
    must(cost.is_finite() and 0<=cost<=COST_CAP,
         "B02 Q25 original reported cost invalid")
    obs=result.get("evidence_proposal")
    must(type(obs) is dict,"Missing original actual model observations")
    verified=verify_candidate(bundle,{
        "source_pack_sha256":SOURCE_SHA,
        "spine_sha256":SPINE_SHA,
        "story_sha256":STORY_SHA,
        "evidence_json":json.dumps(obs,ensure_ascii=False),
        "explanation":"Independent replay of real source-anchored B02 Q25 observations.",
    })
    return verified,format(cost,"f")

def project_b02_final_state(bundle,result):
    evidence,cost=qualify_source_and_evidence(bundle,result)
    source=bundle["source"]
    canon=deepcopy(source["pack"]["canonical_state"])
    orig_known=canon["protagonist"]["known_locations"]
    new_places=[x["location_id"] for x in evidence["discovered_locations"]]
    known=list(orig_known)+[p for p in new_places if p not in orig_known]
    proposal={
        "schema":SCHEMA,"case_id":"B02",
        "artifact_classification":"READ_ONLY_FINAL_STORY_STATE_DRAFT_NOT_CANON",
        "source_pack_sha256":SOURCE_SHA,
        "original_spine_sha256":SPINE_SHA,
        "english_master_sha256":STORY_SHA,
        "canonical_start_snapshot_sha256":sha(canon),
        "original_protagonist_name":canon["protagonist"]["name"],
        "original_q25_generation_id":result["generation_id"],
        "original_q25_reported_cost_usd":cost,
        "last_protagonist_location_proposal":deepcopy(evidence["final_location"]),
        "new_discoveries_with_evidence":deepcopy(evidence["discovered_locations"]),
        "known_locations_proposal":known,
        "objects_not_admitted_to_canon":deepcopy(evidence["object_observations"]),
        "original_canonical_objects_unchanged":deepcopy(canon["objects"]),
        "original_open_obligations_unchanged":deepcopy(canon["open_obligations"]),
        "open_obligation_outcomes_unapproved":deepcopy(evidence["open_obligation_outcomes"]),
        "unknown_facts_retained":deepcopy(evidence["unknown_facts_retained"]),
        "world_time_initial_snapshot":canon["world_time"],
        "world_time_final":None,
        "world_time_status":"UNKNOWN_DELTA_NOT_COMMITTED",
        "independent_final_state_semantic_certification":False,
        "original_full_frozen_v21_4_final_quality_verified":False,
        "canon_commit_authorized":False,
        "production_change":False,
        "model_posts_for_projection":0,
        "manual_story_prose_edits":0,
    }
    must(known==["GARDEN","COMMONS"]
         and proposal["last_protagonist_location_proposal"]["location_id"]=="GARDEN",
         "B02 geographic facts not supported by actual Q25")
    must([x["status"] for x in evidence["open_obligation_outcomes"]]==
         ["SATISFIED","OPEN"],
         "Unproven original B02 obligation must remain OPEN")
    must(proposal["original_open_obligations_unchanged"]==canon["open_obligations"],
         "Could not remove original Canon obligation in a read-only projection")
    must(proposal["world_time_final"] is None
         and proposal["unknown_facts_retained"]==canon["unknown_facts"]
         and all(x["ownership"]=="UNKNOWN"
                 for x in proposal["objects_not_admitted_to_canon"]),
         "Q25 observation illegally invented ownership, time or unknown facts")
    return proposal

def write_once(path,payload):
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    if hasattr(os,"O_NOFOLLOW"): flags|=os.O_NOFOLLOW
    fd=os.open(path,flags,0o600)
    with os.fdopen(fd,"wb") as file:
        file.write(canonical_json(payload)+b"\n")
        file.flush()
        os.fsync(file.fileno())

def freeze_b02_state(bundle,q25,root):
    path=Path(root)
    must(path.is_dir() and not path.is_symlink(),
         "Missing protected B02 final state draft location")
    proposal=project_b02_final_state(bundle,q25)
    folder=path/DIR
    folder.mkdir(mode=0o700,exist_ok=False)
    write_once(folder/"final-state-draft.json",proposal)
    return proposal

def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",default=".")
    p.add_argument("--producer-root")
    p.add_argument("--quality-root")
    p.add_argument("--master-root")
    p.add_argument("--q25-root")
    p.add_argument("--final-root")
    p.add_argument("--freeze-once",action="store_true")
    args=p.parse_args()
    if not args.freeze_once:
        print(json.dumps({"schema":SCHEMA,"case_id":"B02","provider_calls":0,
                          "final_story_state_committed":False,
                          "production_state_write_authorized":False},sort_keys=True))
        return
    must(all((args.producer_root,args.quality_root,args.master_root,
              args.q25_root,args.final_root)),"Missing source chain")
    bundle=load_b02_bundle(args.repo_root,args.producer_root,
                           args.quality_root,args.master_root)
    q25=load_original_q25(args.repo_root,args.q25_root)
    final=freeze_b02_state(bundle,q25,args.final_root)
    print(json.dumps({
        "case_id":"B02",
        "schema":SCHEMA,
        "source_story_sha256":final["english_master_sha256"],
        "final_location_proposal":final["last_protagonist_location_proposal"]["location_id"],
        "discovered_locations":len(final["new_discoveries_with_evidence"]),
        "open_obligation_outcomes":[x["status"] for x in final["open_obligation_outcomes_unapproved"]],
        "world_time_final":None,
        "provider_calls":0,"production_state_write_authorized":False,
    },sort_keys=True))

if __name__=="__main__":
    main()
