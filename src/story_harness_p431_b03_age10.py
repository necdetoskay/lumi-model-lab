"""P4.31 — third distinct real story generation; age 10, river festival.

Reuses unchanged P4.17 SpineForge→Writer model/transport for frozen B03;
does not inherit B01/B02 quality acceptance or authorize Canon writes.
"""
from __future__ import annotations
from decimal import Decimal
import json,os
from pathlib import Path
from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p416_input_bridge import compile_case
from src.story_harness_p417_live_pilot import (
    BoundedOncePilot,https_post_once,STAGE_MAX_USD,USD_CAP,GLOBAL_USER_CAP,MODEL
)
from src.story_harness_v1 import HarnessStop

SCHEMA="lumi.story-harness-p431-age10-third-distinct-story.v1"
CASE_ID="B03"
VARIANT="r06"
SOURCE_SHA="b55ba5c57a3abda0a1b4ef18fe98284f4fea7511b1b82281585ac9da77a205c0"
CONSERVATIVE_PRIOR_RESERVED_USD=Decimal("1.381838")


def must(ok,why):
    if not ok:raise HarnessStop(why)


def source_case(repo_root):
    plan=load_plan(repo_root)
    case=next((c for c in plan["cases"] if c["id"]==CASE_ID),None)
    must(case is not None and case.get("split")=="pilot",
         "B03 not a frozen pilot input")
    pack=compile_case(case)
    canon=pack["canonical_state"]
    must(pack["pack_sha256"]==SOURCE_SHA
         and pack["reader_age"]==10
         and pack["word_targets"]=={"min":800,"max":1400}
         and canon["protagonist"]["name"]=="Duru"
         and canon["protagonist"]["location"]=="RIVERBANK"
         and canon["locations"]==["RIVERBANK","VILLAGE"]
         and len(pack["open_obligations"])==2,
         "B03 age, original Canon or source SHA drift")
    must(CONSERVATIVE_PRIOR_RESERVED_USD+USD_CAP<=GLOBAL_USER_CAP
         and sum(STAGE_MAX_USD.values())<=USD_CAP,
         "B03 story cannot fit user 10 USD cumulative budget")
    return plan,pack


def third_story_once(repo_root,claim_root,*,transport):
    plan,pack=source_case(repo_root)
    root=Path(claim_root)
    must(root.is_dir() and not root.is_symlink(),
         "B03 protected run ledger missing")
    pilot=BoundedOncePilot(str(root),case_id=CASE_ID,plan=plan,run_variant=VARIANT)
    must(pilot.pack["pack_sha256"]==SOURCE_SHA,
         "B03 model pack differs from preflight")
    result=pilot.execute(transport=transport)
    frozen=json.loads((pilot.dir/"spine-plan.json").read_bytes())
    manuscript=json.loads((pilot.dir/"story-draft.json").read_bytes())
    must(frozen["source_pack_sha256"]==SOURCE_SHA
         and manuscript["source_pack_sha256"]==SOURCE_SHA
         and frozen["spine_sha256"]==manuscript["spine_sha256"]
         and manuscript["story_sha256"]==result["story_sha256"]
         and 800<=manuscript["word_count"]<=1400
         and manuscript["quality_accepted"] is False
         and manuscript["english_master_authorized"] is False
         and manuscript["q25_authorized"] is False
         and manuscript["story_state_write_authorized"] is False,
         "B03 source, age word target, or model approval was forged")
    return {
        "schema":SCHEMA,"case_id":CASE_ID,"reader_age":10,
        "source_pack_sha256":SOURCE_SHA,
        "original_spine_sha256":result["spine_sha256"],
        "original_story_sha256":result["story_sha256"],
        "original_word_count":result["story_words"],
        "model":MODEL,"model_posts_max":2,
        "actual_generation_cost_usd":result["two_stage_cost_usd"],
        "quality_initial_verdict":"NOT_YET_AUDITED",
        "english_master_authorized":False,
        "q25_authorized":False,
        "production_state_write_authorized":False,
        "auto_retry":False,
    }


def default_status(repo_root="."):
    _,pack=source_case(repo_root)
    return {
        "schema":SCHEMA,"case_id":CASE_ID,
        "reader_age":10,
        "word_targets":pack["word_targets"],
        "source_pack_sha256":SOURCE_SHA,
        "provider_calls":0,"paid_execution_default":False,
        "cost_cap_usd":str(USD_CAP),
        "previous_conservative_budget_usd":str(CONSERVATIVE_PRIOR_RESERVED_USD),
        "total_approved_user_budget_usd":str(GLOBAL_USER_CAP),
        "quality_accepted":False,"production_state_write_authorized":False,
    }


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",default=".")
    p.add_argument("--claim-root")
    p.add_argument("--paid-b03-once",action="store_true")
    args=p.parse_args()
    if not args.paid_b03_once:
        print(json.dumps(default_status(args.repo_root),sort_keys=True))
    else:
        must(os.getenv("LUMI_P431_ENABLE_B03")=="ONE_REAL_AGE10_CANON_GENERATION",
             "B03 paid once-only branch not granted")
        must(args.claim_root,"Missing B03 protected output")
        key=os.getenv("OPENROUTER_API_KEY","")
        must(type(key) is str and key.startswith("sk-or-"),"Inference key unavailable")
        print(json.dumps(third_story_once(args.repo_root,args.claim_root,
             transport=lambda body:https_post_once(key,body)),sort_keys=True))
