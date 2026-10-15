"""P4.53: authentic B06 Sonnet Q25 v02 -> immutable READ-ONLY Final StoryState draft.

Zero provider calls, no Canon mutations, no quality verdict promotion.
B06 Q25 v01 terminal STOP remains immutable and permanently consumed.
"""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from pathlib import Path
import hashlib
import json

from src.story_harness_p410 import canonical_json
from src.story_harness_p416_input_bridge import sha
from src.story_harness_p424_q25_evidence import verify_candidate, COST_CAP
from src.story_harness_p452_b06_q25 import (
    load_b06_bundle, SCHEMA as Q25_SCHEMA, RUN_NAME as Q25_RUN_NAME,
    MODEL, SOURCE_SHA, SPINE_SHA, STORY_SHA, verify_original_v01_stop,
)
from src.story_harness_p423_master import write_exclusive
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-p453-b06-read-only-final-state-draft.v1"
Q25_REFERENCE = "evidence/story_harness_p452/b06-r06-original-q25-evidence.json"
Q25_RECEIPT_SHA = "daafcbe39e0aa8b86510ad5bf5b861e4859e6b15cd6343b04a1f842a86343aaf"
Q25_INTENT_REFERENCE = "evidence/story_harness_p452/b06-r06-original-q25-intent.json"
Q25_INTENT_SHA = "e07c59bca2cdc353c6ee1c705f66f9c67084194c56149b2022a08acf52b19dd7"
Q25_ID = "gen-1791994391-Nq4NFlp6dwA6ZLmm01MP"
MASTER_REFERENCE = "evidence/story_harness_p450/b06-r06-original-pilot-master-manifest.json"
MASTER_RECEIPT_SHA = "877c2fee70f5fc2469c01c2a007db420fbe46f3ed8343732d3b615d9c6af3d61"
OUTPUT_DIR = "p453-b06-r06-" + STORY_SHA[:12]

def must(ok, reason):
    if not ok:
        raise HarnessStop(reason)

def _original(path, saved, expected_digest, *, bound=64000):
    must(path.is_file() and saved.is_file()
         and not path.is_symlink() and not saved.is_symlink()
         and 0 < path.stat().st_size <= bound,
         "Required immutable original B06 evidence is missing")
    raw = path.read_bytes()
    must(raw == saved.read_bytes()
         and hashlib.sha256(raw).hexdigest() == expected_digest,
         "B06 original provider/master receipt differs from frozen bytes")
    return raw

def original_b06_q25(repo_root, q25_root):
    verify_original_v01_stop(repo_root)
    root=Path(q25_root)
    claim=root/Q25_RUN_NAME
    must(root.is_dir() and claim.is_dir()
         and not root.is_symlink() and not claim.is_symlink(),
         "B06 v02 original provider Q25 root missing")
    saved=Path(repo_root)
    _original(claim/"00-intent.json",saved/Q25_INTENT_REFERENCE,Q25_INTENT_SHA)
    raw=_original(claim/"01-q25-evidence.json",saved/Q25_REFERENCE,Q25_RECEIPT_SHA)
    return json.loads(raw)

def verify_original_master_receipt(repo_root, master_root, bundle):
    original=Path(master_root)/("b06-"+STORY_SHA[:16])/"master-manifest.json"
    raw=_original(original,Path(repo_root)/MASTER_REFERENCE,MASTER_RECEIPT_SHA)
    must(json.loads(raw)==bundle["master"]
         and bundle["master"]["independent_initial_audit_verdict"]=="ACCEPT"
         and bundle["master"]["q25_read_only_extraction_allowed"] is True
         and bundle["master"]["manual_text_edits"] == 0,
         "Original B06 approved English Master manifest differs")

def qualify_b06_q25(bundle, receipt):
    source=bundle["source"]
    must(source["case_id"]=="B06"
         and source["pack"]["pack_sha256"]==SOURCE_SHA
         and source["spine"]["spine_sha256"]==SPINE_SHA
         and source["story"]["story_sha256"]==STORY_SHA
         and bundle["master"]["accepted_story_sha256"]==STORY_SHA,
         "B06 original source/Q25 identity mismatch")
    must(type(receipt) is dict
         and hashlib.sha256(canonical_json(receipt)+b"\n").hexdigest()==Q25_RECEIPT_SHA
         and receipt.get("schema")==Q25_SCHEMA
         and receipt.get("case_id")=="B06"
         and receipt.get("model")==MODEL
         and receipt.get("generation_id")==Q25_ID
         and receipt.get("source_pack_sha256")==SOURCE_SHA
         and receipt.get("spine_sha256")==SPINE_SHA
         and receipt.get("story_sha256")==STORY_SHA
         and receipt.get("provenance_verified") is True
         and receipt.get("quote_matching_verified") is True
         and receipt.get("prior_english_master_unchanged") is True
         and receipt.get("semantic_state_fully_certified") is False
         and receipt.get("final_story_state_committed") is False
         and receipt.get("production_state_write_authorized") is False,
         "B06 Q25 v02 not genuine original read-only evidence")
    try:
        charge=Decimal(str(receipt["provider_reported_cost_usd"]))
    except (KeyError,TypeError,ValueError,InvalidOperation):
        raise HarnessStop("B06 original Q25 provider cost invalid") from None
    usage=receipt.get("provider_usage")
    must(charge.is_finite() and charge==Decimal("0.029742")
         and charge<=COST_CAP
         and type(usage) is dict
         and usage.get("prompt_tokens")==7256
         and usage.get("completion_tokens")==1523,
         "B06 original Q25 reported tokens/cost mismatch")
    evidence=receipt.get("evidence_proposal")
    must(type(evidence) is dict, "Missing real B06 Q25 evidence proposal")
    checked=verify_candidate(bundle,{
        "source_pack_sha256":SOURCE_SHA,
        "spine_sha256":SPINE_SHA,
        "story_sha256":STORY_SHA,
        "evidence_json":json.dumps(evidence,ensure_ascii=False),
        "explanation":"Bounded offline recheck of exact original B06 quoted provider evidence.",
    })
    must(checked["final_location"]["location_id"]=="LIBRARY"
         and [p["location_id"] for p in checked["discovered_locations"]]==["TOWER"]
         and checked["object_observations"]==[]
         and checked["world_time_delta"] is None
         and checked["unknown_facts_retained"]==source["pack"]["unknown_facts"]
         and [(p["obligation"],p["status"]) for p in checked["open_obligation_outcomes"]]
             ==[(s,"OPEN") for s in source["pack"]["open_obligations"]],
         "B06 Q25 cannot fabricate Atlas, world time, location or closed obligations")
    return checked,format(charge,"f")

def project_b06_final_state(bundle, receipt):
    evidence,cost=qualify_b06_q25(bundle,receipt)
    start=deepcopy(bundle["source"]["pack"]["canonical_state"])
    must(start["protagonist"]=={
        "name":"Yasmin","location":"LIBRARY","known_locations":["LIBRARY"]}
         and start["locations"]==["LIBRARY","TOWER"]
         and start["objects"]==[]
         and start["open_obligations"]==[
             "Sözleşme kapanmamıştır","Atlasın sahibi bilinmemektedir"],
         "B06 original Canon mutated before read-only state proposal")
    known=list(start["protagonist"]["known_locations"])
    for found in evidence["discovered_locations"]:
        if found["location_id"] not in known:
            known.append(found["location_id"])
    must(known==["LIBRARY","TOWER"]
         and evidence["final_location"]["location_id"]=="LIBRARY",
         "B06 first-hand discovery and return to LIBRARY not proven")
    draft={
        "schema":SCHEMA,"case_id":"B06",
        "artifact_classification":"READ_ONLY_FINAL_STORY_STATE_DRAFT_NOT_CANON",
        "source_pack_sha256":SOURCE_SHA,
        "original_spine_sha256":SPINE_SHA,
        "english_master_sha256":STORY_SHA,
        "original_master_manifest_sha256":MASTER_RECEIPT_SHA,
        "original_q25_receipt_sha256":Q25_RECEIPT_SHA,
        "original_v01_terminal_q25_stop_preserved":True,
        "canonical_start_snapshot_sha256":sha(start),
        "original_protagonist_name":start["protagonist"]["name"],
        "original_q25_generation_id":receipt["generation_id"],
        "original_q25_reported_cost_usd":cost,
        "last_protagonist_location_proposal":deepcopy(evidence["final_location"]),
        "new_discoveries_with_evidence":deepcopy(evidence["discovered_locations"]),
        "known_locations_proposal":known,
        "objects_not_admitted_to_canon":deepcopy(evidence["object_observations"]),
        "original_canonical_objects_unchanged":deepcopy(start["objects"]),
        "original_open_obligations_unchanged":deepcopy(start["open_obligations"]),
        "open_obligation_outcomes_unapproved":deepcopy(evidence["open_obligation_outcomes"]),
        "unknown_facts_retained":deepcopy(evidence["unknown_facts_retained"]),
        "world_time_initial_snapshot":start["world_time"],
        "world_time_final":None,"world_time_status":"UNKNOWN_DELTA_NOT_COMMITTED",
        "independent_final_state_semantic_certification":False,
        "original_full_frozen_v21_4_final_quality_verified":False,
        "canon_commit_authorized":False,"production_change":False,
        "final_story_state_committed":False,
        "model_posts_for_projection":0,"manual_story_prose_edits":0,
    }
    must(draft["unknown_facts_retained"]==start["unknown_facts"]
         and draft["original_open_obligations_unchanged"]==start["open_obligations"]
         and [p["status"] for p in draft["open_obligation_outcomes_unapproved"]]==["OPEN","OPEN"]
         and draft["original_canonical_objects_unchanged"]==[]
         and draft["world_time_final"] is None
         and draft["canon_commit_authorized"] is False,
         "B06 read-only projection cannot invent Canon facts")
    return draft

def freeze_or_verify(bundle, receipt, final_root):
    root=Path(final_root)
    must(root.is_dir() and not root.is_symlink(),
         "Missing protected B06 read-only state directory")
    state=project_b06_final_state(bundle,receipt)
    folder=root/OUTPUT_DIR
    raw=canonical_json(state)+b"\n"
    if folder.exists():
        path=folder/"final-state-draft.json"
        must(folder.is_dir() and not folder.is_symlink()
             and path.is_file() and not path.is_symlink()
             and path.read_bytes()==raw,
             "Previously frozen B06 state differs; no overwrite")
        return state,False
    folder.mkdir(mode=0o700,exist_ok=False)
    write_exclusive(folder/"final-state-draft.json",raw)
    return state,True

def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",default=".")
    p.add_argument("--producer-root")
    p.add_argument("--quality-root")
    p.add_argument("--master-root")
    p.add_argument("--q25-root")
    p.add_argument("--state-root")
    p.add_argument("--freeze-or-verify",action="store_true")
    a=p.parse_args()
    if not a.freeze_or_verify:
        print(json.dumps({"case_id":"B06","model_calls":0,
            "final_story_state_committed":False,
            "production_state_write_authorized":False}))
        return
    must(all((a.producer_root,a.quality_root,a.master_root,a.q25_root,a.state_root)),
         "Original B06 Spine/Writer, QA, Master, Q25 and State roots required")
    b=load_b06_bundle(a.repo_root,a.producer_root,a.quality_root,a.master_root)
    verify_original_master_receipt(a.repo_root,a.master_root,b)
    r=original_b06_q25(a.repo_root,a.q25_root)
    result,new=freeze_or_verify(b,r,a.state_root)
    print(json.dumps({
        "case_id":"B06","source_story_sha256":STORY_SHA,
        "final_location_proposal":result["last_protagonist_location_proposal"]["location_id"],
        "discovered_locations":len(result["new_discoveries_with_evidence"]),
        "objects_admitted_to_canon":0,
        "open_obligation_statuses":[p["status"] for p in result["open_obligation_outcomes_unapproved"]],
        "created_this_run":new,"model_calls":0,
        "production_state_write_authorized":False},sort_keys=True))
if __name__=="__main__":
    main()
