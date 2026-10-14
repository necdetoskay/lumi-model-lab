"""P4.42: real original B04 Q25 -> immutable READ-ONLY Final StoryState draft.

Zero paid calls, never updates production or Canon. All evidence is
source-bound to the protected original B04 Spine, Writer, independent
ACCEPT, English Master and Q25. Open obligations remain OPEN.
"""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from src.story_harness_p410 import canonical_json
from src.story_harness_p416_input_bridge import sha
from src.story_harness_p424_q25_evidence import verify_candidate, COST_CAP
from src.story_harness_p441_b04_q25 import (
    load_b04_bundle, SCHEMA as Q25_SCHEMA, RUN_NAME as Q25_RUN_NAME,
    MODEL, SOURCE_SHA, SPINE_SHA, STORY_SHA,
)
from src.story_harness_v1 import HarnessStop
from src.story_harness_p423_master import write_exclusive

SCHEMA = "lumi.story-harness-p442-b04-read-only-final-state-draft.v1"
Q25_REFERENCE = "evidence/story_harness_p441/b04-r06-original-q25-evidence.json"
Q25_RECEIPT_SHA = "d81c8c56dbaa89f510e51e53471954c76b8636cf0f14a095096830de217acc90"
Q25_ID = "gen-1791967013-OBmyunMTruhDSL9mkOYD"
MASTER_REFERENCE = "evidence/story_harness_p440/b04-r06-original-pilot-master-manifest.json"
MASTER_RECEIPT_SHA = "7db3779815c8c42287ea4d67e163be580c16180d83c4f8ea571ae56e2b3209ec"
OUTPUT_DIR = "p442-b04-r06-" + STORY_SHA[:12]

def must(ok, reason):
    if not ok: raise HarnessStop(reason)

def original_b04_q25(repo_root, q25_root):
    root = Path(q25_root)
    claim = root / Q25_RUN_NAME
    must(root.is_dir() and claim.is_dir()
         and not root.is_symlink() and not claim.is_symlink(),
         "Protected original B04 Q25 claim missing")
    original = claim / "01-q25-evidence.json"
    saved = Path(repo_root) / Q25_REFERENCE
    must(original.is_file() and saved.is_file()
         and not original.is_symlink() and not saved.is_symlink()
         and original.stat().st_size < 65000,
         "Original B04 Q25 receipt missing or unsafe")
    raw = original.read_bytes()
    must(raw == saved.read_bytes()
         and hashlib.sha256(raw).hexdigest() == Q25_RECEIPT_SHA,
         "Original B04 Q25 differs from actual Sonnet artifact")
    return json.loads(raw)

def verify_original_master_receipt(repo_root, master_root, bundle):
    original = (Path(master_root) /
                ("b04-"+STORY_SHA[:16]) / "master-manifest.json")
    saved = Path(repo_root) / MASTER_REFERENCE
    must(original.is_file() and saved.is_file()
         and not original.is_symlink() and not saved.is_symlink()
         and original.read_bytes() == saved.read_bytes()
         and hashlib.sha256(original.read_bytes()).hexdigest() == MASTER_RECEIPT_SHA
         and json.loads(original.read_bytes()) == bundle["master"],
         "Original B04 Master manifest not byte-identical to frozen evidence")

def qualify_b04_q25(bundle, receipt):
    source = bundle["source"]
    must(source["case_id"] == "B04"
         and source["pack"]["pack_sha256"] == SOURCE_SHA
         and source["spine"]["spine_sha256"] == SPINE_SHA
         and source["story"]["story_sha256"] == STORY_SHA
         and bundle["master"]["accepted_story_sha256"] == STORY_SHA,
         "B04 original state pipeline source mismatch")
    must(type(receipt) is dict and receipt.get("schema") == Q25_SCHEMA
         and receipt.get("case_id") == "B04"
         and receipt.get("model") == MODEL
         and receipt.get("generation_id") == Q25_ID
         and receipt.get("source_pack_sha256") == SOURCE_SHA
         and receipt.get("spine_sha256") == SPINE_SHA
         and receipt.get("story_sha256") == STORY_SHA
         and receipt.get("provenance_verified") is True
         and receipt.get("quote_matching_verified") is True
         and receipt.get("prior_english_master_unchanged") is True
         and receipt.get("semantic_state_fully_certified") is False
         and receipt.get("final_story_state_committed") is False
         and receipt.get("production_state_write_authorized") is False,
         "B04 Q25 not genuine, source-bound read-only evidence")
    charge = Decimal(str(receipt.get("provider_reported_cost_usd")))
    usage = receipt.get("provider_usage")
    must(charge.is_finite() and charge == Decimal("0.0452")
         and charge <= COST_CAP
         and type(usage) is dict
         and usage.get("prompt_tokens") == 5255
         and usage.get("completion_tokens") == 3469,
         "B04 actual provider cost/token receipt mismatch")
    evidence = receipt.get("evidence_proposal")
    must(type(evidence) is dict, "Missing B04 genuine Q25 observation")
    validated = verify_candidate(bundle, {
        "source_pack_sha256":SOURCE_SHA,
        "spine_sha256":SPINE_SHA,
        "story_sha256":STORY_SHA,
        "evidence_json":json.dumps(evidence,ensure_ascii=False),
        "explanation":"Independent deterministic replay of exact B04 source-grounded Q25 observations.",
    })
    must(validated["final_location"]["location_id"] == "STUDIO"
         and [v["location_id"] for v in validated["discovered_locations"]] == ["STUDIO"]
         and [(x["object_name"],x["last_seen_relation"],x["ownership"])
              for x in validated["object_observations"]] == [
                 ("satchel","AT_STUDIO","UNKNOWN"),
                 ("pot","AT_STUDIO","UNKNOWN"),
                 ("brush","HELD_BY_PROTAGONIST","UNKNOWN"),
                 ("pencil","WITH_PROTAGONIST","UNKNOWN"),
              ],
         "B04 observed studio location or objects cannot be reinterpreted")
    must([(x["obligation"],x["status"]) for x in validated["open_obligation_outcomes"]]
         == [(x,"OPEN") for x in source["pack"]["open_obligations"]],
         "B04 paint and missing map are still open, never close by inference")
    return validated,format(charge,"f")

def project_b04_final_state(bundle, receipt):
    q25, cost = qualify_b04_q25(bundle, receipt)
    start = deepcopy(bundle["source"]["pack"]["canonical_state"])
    known = list(start["protagonist"]["known_locations"])
    for found in q25["discovered_locations"]:
        if found["location_id"] not in known:
            known.append(found["location_id"])
    must(known == ["MARKET","STUDIO"]
         and start["protagonist"]["location"] == "MARKET"
         and q25["final_location"]["location_id"] == "STUDIO",
         "B04 original location/Cannon discovery mismatch")
    draft = {
        "schema":SCHEMA,
        "case_id":"B04",
        "artifact_classification":"READ_ONLY_FINAL_STORY_STATE_DRAFT_NOT_CANON",
        "source_pack_sha256":SOURCE_SHA,
        "original_spine_sha256":SPINE_SHA,
        "english_master_sha256":STORY_SHA,
        "original_master_manifest_sha256":MASTER_RECEIPT_SHA,
        "original_q25_receipt_sha256":Q25_RECEIPT_SHA,
        "canonical_start_snapshot_sha256":sha(start),
        "original_protagonist_name":start["protagonist"]["name"],
        "original_q25_generation_id":receipt["generation_id"],
        "original_q25_reported_cost_usd":cost,
        "last_protagonist_location_proposal":deepcopy(q25["final_location"]),
        "new_discoveries_with_evidence":deepcopy(q25["discovered_locations"]),
        "known_locations_proposal":known,
        "objects_not_admitted_to_canon":deepcopy(q25["object_observations"]),
        "original_canonical_objects_unchanged":deepcopy(start["objects"]),
        "original_open_obligations_unchanged":deepcopy(start["open_obligations"]),
        "open_obligation_outcomes_unapproved":deepcopy(q25["open_obligation_outcomes"]),
        "unknown_facts_retained":deepcopy(q25["unknown_facts_retained"]),
        "world_time_initial_snapshot":start["world_time"],
        "world_time_final":None,
        "world_time_status":"UNKNOWN_DELTA_NOT_COMMITTED",
        "independent_final_state_semantic_certification":False,
        "original_full_frozen_v21_4_final_quality_verified":False,
        "canon_commit_authorized":False,
        "production_change":False,
        "model_posts_for_projection":0,
        "manual_story_prose_edits":0,
    }
    must(draft["unknown_facts_retained"] == start["unknown_facts"]
         and draft["original_open_obligations_unchanged"] == start["open_obligations"]
         and [x["status"] for x in draft["open_obligation_outcomes_unapproved"]] == ["OPEN","OPEN"]
         and all(x["ownership"] == "UNKNOWN" for x in draft["objects_not_admitted_to_canon"])
         and draft["world_time_final"] is None,
         "B04 cannot invent owner/time/closed obligations on read-only projection")
    return draft

def freeze_or_verify(bundle, receipt, final_root):
    root=Path(final_root)
    must(root.is_dir() and not root.is_symlink(),
         "Missing protected B04 read-only state root")
    result=project_b04_final_state(bundle,receipt)
    folder=root/OUTPUT_DIR
    raw=canonical_json(result)+b"\n"
    if folder.exists():
        saved=folder/"final-state-draft.json"
        must(folder.is_dir() and not folder.is_symlink()
             and saved.is_file() and not saved.is_symlink()
             and saved.read_bytes()==raw,
             "Original B04 Final StoryState already sealed and differs")
        return result,False
    folder.mkdir(mode=0o700,exist_ok=False)
    write_exclusive(folder/"final-state-draft.json",raw)
    return result,True

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
    args=p.parse_args()
    if not args.freeze_or_verify:
        print(json.dumps({"case_id":"B04","model_calls":0,
                          "final_story_state_committed":False,
                          "production_state_write_authorized":False},sort_keys=True))
        return
    must(all((args.producer_root,args.quality_root,args.master_root,args.q25_root,args.state_root)),
         "Original B04 source, quality, Master, Q25 and State roots required")
    bundle=load_b04_bundle(args.repo_root,args.producer_root,args.quality_root,args.master_root)
    verify_original_master_receipt(args.repo_root,args.master_root,bundle)
    receipt=original_b04_q25(args.repo_root,args.q25_root)
    result,new=freeze_or_verify(bundle,receipt,args.state_root)
    print(json.dumps({"case_id":"B04","source_story_sha256":STORY_SHA,
                      "final_location_proposal":result["last_protagonist_location_proposal"]["location_id"],
                      "discovered_locations":len(result["new_discoveries_with_evidence"]),
                      "observed_objects":len(result["objects_not_admitted_to_canon"]),
                      "open_obligation_statuses":[x["status"] for x in result["open_obligation_outcomes_unapproved"]],
                      "created_this_run":new,"model_calls":0,
                      "production_state_write_authorized":False},sort_keys=True))
if __name__=="__main__":
    main()
