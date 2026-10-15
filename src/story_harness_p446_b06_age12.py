"""P4.46: real-source-locked B06 age-12 SpineForge -> Writer one-shot.

Same verified P4.17 bounded pilot engine, same original validated scene
contracts and no auto retries. Newly frozen B06 Canon and topic; no initial
quality, Master, Q25, production Canon or state authority at generation.
"""
from __future__ import annotations
from decimal import Decimal
import json
import os
from pathlib import Path

from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p416_input_bridge import compile_case
from src.story_harness_p417_live_pilot import (
    BoundedOncePilot,https_post_once,OUTPUT_CAPS,MODEL,
    USD_CAP,GLOBAL_USER_CAP,STAGE_MAX_USD
)
from src.story_harness_v1 import HarnessStop

SCHEMA="lumi.story-harness-p446-sixth-age12-story.v1"
CASE_ID="B06"
VARIANT="r06"
SOURCE_SHA="cc68b39084f270df88357dc6fa29acdb7eeb5a645d23de7e592c3c486e04277e"
PRIOR_CONSERVATIVE=Decimal("2.369558")

def must(condition,reason):
    if not condition: raise HarnessStop(reason)

def source_case(repo_root):
    plan=load_plan(repo_root)
    case=next((c for c in plan["cases"] if c["id"]==CASE_ID),None)
    must(case is not None and case["split"]=="pilot",
         "B06 must use original frozen registered pilot case")
    pack=compile_case(case)
    canon=pack["canonical_state"]
    must(pack["pack_sha256"]==SOURCE_SHA
         and pack["reader_age"]==12
         and pack["topic"]=="Ay ışığındaki kütüphane"
         and pack["word_targets"]=={"min":1600,"max":2500}
         and canon["protagonist"]=={
             "name":"Yasmin","location":"LIBRARY","known_locations":["LIBRARY"]}
         and canon["locations"]==["LIBRARY","TOWER"]
         and canon["objects"]==[]
         and canon["open_obligations"]==[
             "Sözleşme kapanmamıştır","Atlasın sahibi bilinmemektedir"]
         and canon["unknown_facts"]==[
             "unobserved_owners","unobserved_locations"]
         and pack["forbidden_state_invention"]==
             "Atlasın sahibi veya konumu icat edilmez",
         "B06 age12 Canon, unknown owner or topic unexpectedly changed")
    must(PRIOR_CONSERVATIVE+USD_CAP<=GLOBAL_USER_CAP
         and sum(STAGE_MAX_USD.values())<=USD_CAP
         and OUTPUT_CAPS["SPINEFORGE"]==5500
         and OUTPUT_CAPS["WRITER"]==6500,
         "Original bounded model budgets not honored for B06")
    return plan,pack

def sixth_story_once(repo_root, claim_root, *, transport):
    plan,pack=source_case(repo_root)
    root=Path(claim_root)
    must(root.is_dir() and not root.is_symlink(),"Protected B06 claim root missing")
    pilot=BoundedOncePilot(str(root),case_id=CASE_ID,plan=plan,run_variant=VARIANT)
    must(pilot.pack["pack_sha256"]==SOURCE_SHA,
         "B06 original source pack changed after claim")
    done=pilot.execute(transport=transport)
    spine=json.loads((pilot.dir/"spine-plan.json").read_bytes())
    draft=json.loads((pilot.dir/"story-draft.json").read_bytes())
    must(spine["source_pack_sha256"]==SOURCE_SHA
         and draft["source_pack_sha256"]==SOURCE_SHA
         and draft["spine_sha256"]==spine["spine_sha256"]
         and draft["story_sha256"]==done["story_sha256"]
         and 1600<=draft["word_count"]<=2500
         and draft["quality_accepted"] is False
         and draft["english_master_authorized"] is False
         and draft["q25_authorized"] is False
         and draft["story_state_write_authorized"] is False,
         "B06 unreviewed Writer cannot self-certify initial quality or Canon")
    return {
        "schema":SCHEMA,"case_id":CASE_ID,"reader_age":12,
        "source_pack_sha256":SOURCE_SHA,
        "spine_sha256":done["spine_sha256"],
        "story_sha256":done["story_sha256"],
        "english_word_count":done["story_words"],
        "model":MODEL,"maximum_model_posts":2,
        "actual_generation_cost_usd":done["two_stage_cost_usd"],
        "initial_quality_verdict":"NOT_YET_AUDITED",
        "english_master_authorized":False,
        "q25_authorized":False,
        "production_state_write_authorized":False,
        "automatic_retries":False,
    }

def status(repo_root="."):
    _,pack=source_case(repo_root)
    return {
        "schema":SCHEMA,"case_id":CASE_ID,"reader_age":12,
        "source_pack_sha256":SOURCE_SHA,
        "word_targets":pack["word_targets"],
        "generation_cost_cap_usd":format(USD_CAP,"f"),
        "prior_conservative_budget_reserved_usd":format(PRIOR_CONSERVATIVE,"f"),
        "user_approved_total_usd":format(GLOBAL_USER_CAP,"f"),
        "provider_calls":0,"paid_execution_enabled":False,
        "quality_initial_accepted":False,
        "production_state_write_authorized":False,
    }

def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",default=".")
    p.add_argument("--claim-root")
    p.add_argument("--paid-once",action="store_true")
    a=p.parse_args()
    if not a.paid_once:
        print(json.dumps(status(a.repo_root),sort_keys=True))
        return
    must(os.getenv("LUMI_P446_B06")=="ONE_ORIGINAL_B06_AGE12_GENERATION",
         "B06 original real provider grant missing")
    must(a.claim_root,"B06 paid source claim root required")
    key=os.getenv("OPENROUTER_API_KEY","")
    must(type(key) is str and key.startswith("sk-or-"),
         "Original OpenRouter inference key not provided")
    result=sixth_story_once(a.repo_root,a.claim_root,
                           transport=lambda body:https_post_once(key,body))
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":
    main()
