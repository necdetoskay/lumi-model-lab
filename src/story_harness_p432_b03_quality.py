"""P4.32 — Genuine B03 10-year-old river story independent initial quality.

Reuses P4.22 source-sealed, 12-family, quote-grounded adversarial Sonnet
auditor. Not a frozen v21.4 production final audit; no B01/B02 pass reuse.
"""
from __future__ import annotations
from decimal import Decimal
import json,os
from pathlib import Path
from src.story_harness_p431_b03_age10 import source_case,SOURCE_SHA
from src.story_harness_p422_independent_audit import (
    load_source,audit_wire,audit_once,STAGE_COST_CAP
)
from src.story_harness_p417_live_pilot import https_post_once,MODEL
from src.story_harness_v1 import HarnessStop

SCHEMA="lumi.story-harness-p432-b03-independent-age10-quality.v1"
SPINE_SHA="9a0b0476c2c5f94bc5e7f3a6d0261cefbee9ce22062c02f8a55fed761c10a9ad"
STORY_SHA="80fa8224c78c494b13bc347ecabdfff75fd5c9e1638ad88ee9ba47c6986643f9"
GEN_COST=Decimal("0.067720")
PRIOR_RESERVED=Decimal("1.449558")
USER_CAP=Decimal("10.00")
EVIDENCE_DIR="evidence/story_harness_p431/"
FILES={
    "spine-plan.json":"b03-r06-original-spine-plan.json",
    "story-draft.json":"b03-r06-original-writer-draft.json",
    "01-spineforge-receipt.json":"b03-r06-original-spineforge-receipt.json",
    "02-writer-receipt.json":"b03-r06-original-writer-receipt.json",
}

def must(ok,why):
    if not ok:raise HarnessStop(why)

def get_original_B03(repo_root,claim_root):
    _,pack=source_case(repo_root)
    must(pack["pack_sha256"]==SOURCE_SHA,"B03 Canon changed")
    source=load_source(repo_root,claim_root,case_id="B03",run_variant="r06")
    must(source["case_id"]=="B03"
         and source["pack"]["reader_age"]==10
         and source["pack"]["word_targets"]=={"min":800,"max":1400}
         and source["story"]["word_count"]==1300
         and source["spine"]["spine_sha256"]==SPINE_SHA
         and source["story"]["story_sha256"]==STORY_SHA
         and Decimal(source["generation_cost_usd"])==GEN_COST,
         "Original B03 provider story or cost differs")
    original=Path(claim_root)/source["original_claim_id"]
    for live_name,saved_name in FILES.items():
        live=original/live_name
        saved=Path(repo_root)/EVIDENCE_DIR/saved_name
        must(live.is_file() and saved.is_file()
             and not live.is_symlink() and not saved.is_symlink()
             and live.read_bytes()==saved.read_bytes(),
             "B03 original source/provider receipts not byte-identical")
    must(PRIOR_RESERVED+STAGE_COST_CAP<=USER_CAP,
         "B03 quality would exceed 10 USD approved user limit")
    return source

def inspect_B03_audit(source):
    must(source.get("case_id")=="B03"
         and source["story"]["story_sha256"]==STORY_SHA
         and source["spine"]["spine_sha256"]==SPINE_SHA,
         "B03 independent audit cannot reuse earlier story acceptance")
    wire=audit_wire(source)
    payload=json.loads(wire["messages"][1]["content"])
    must(payload["case_id"]=="B03" and payload["reader_age"]==10
         and payload["source_pack_sha256"]==SOURCE_SHA
         and "10 years old" in wire["messages"][0]["content"]
         and wire["response_format"]["json_schema"]["name"]==
             "lumi_b03_independent_initial_audit_v1",
         "B03 independent auditor not age-sensitive or source-bound")
    return wire

def audit_B03_once(source,quality_root,*,transport):
    inspect_B03_audit(source)
    verdict=audit_once(source,quality_root,
                       transport=transport,audit_prefix="p432")
    must(verdict["case_id"]=="B03"
         and verdict["story_sha256"]==STORY_SHA
         and verdict["spine_sha256"]==SPINE_SHA
         and verdict["english_master_authorized"] is False
         and verdict["q25_authorized"] is False
         and verdict["state_write_authorized"] is False
         and verdict["full_original_v21_final_audit_completed"] is False,
         "B03 initial quality cannot promote final production acceptance")
    return verdict

def status():
    return {"schema":SCHEMA,"case_id":"B03",
            "reader_age":10,"source_pack_sha256":SOURCE_SHA,
            "spine_sha256":SPINE_SHA,"story_sha256":STORY_SHA,
            "real_generation_cost_usd":str(GEN_COST),
            "max_new_quality_posts":1,
            "max_new_quality_stage_usd":str(STAGE_COST_CAP),
            "prior_budget_reserved_usd":str(PRIOR_RESERVED),
            "user_total_cap_usd":str(USER_CAP),
            "initial_quality_accepted":False,
            "production_state_write_authorized":False,
            "model_calls":0}

def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",default=".")
    p.add_argument("--producer-root")
    p.add_argument("--quality-root")
    p.add_argument("--paid-audit-once",action="store_true")
    args=p.parse_args()
    if not args.paid_audit_once:
        print(json.dumps(status(),sort_keys=True))
        return
    must(os.getenv("LUMI_P432_AGE10_QA")=="B03_ONE_INDEPENDENT_SONNET_QUALITY",
         "B03 paid independent quality call not granted")
    must(args.producer_root and args.quality_root,
         "Original protected B03 producer/auditor paths missing")
    src=get_original_B03(args.repo_root,args.producer_root)
    result=audit_B03_once(src,args.quality_root,transport=lambda body:
                https_post_once(os.getenv("OPENROUTER_API_KEY",""),body))
    print(json.dumps({
        "schema":SCHEMA,"case_id":"B03",
        "story_sha256":result["story_sha256"],
        "initial_quality_verdict":result["quality_initial_verdict"],
        "reader_score":result["reader_score"],
        "blockers":len(result["blocking_findings"]),
        "audit_model_generation":result["auditor_generation_id"],
        "actual_provider_quality_cost_usd":result["auditor_reported_cost_usd"],
        "english_master_authorized":False,
        "q25_authorized":False,
        "production_state_write_authorized":False},sort_keys=True))

if __name__=="__main__":
    main()
