"""P4.38 — Fourth genuine age-10 B04 SpineForge→Writer controlled pilot.

Reuses the proven original P4.17 bounded Sonnet generator, unchanged model
schemas, prompts, Spine validators and no-retry policy. This source intentionally
has different protagonist, locations, obligations and topic from B03.
No initial-quality ACCEPT, English Master or state authority at generation.
"""
from __future__ import annotations

from decimal import Decimal
import json
import os
from pathlib import Path

from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p416_input_bridge import compile_case
from src.story_harness_p417_live_pilot import (
    BoundedOncePilot, https_post_once, STAGE_MAX_USD, USD_CAP, GLOBAL_USER_CAP,
    MODEL,
)
from src.story_harness_v1 import HarnessStop

SCHEMA="lumi.story-harness-p438-fourth-age10-story.v1"
CASE_ID="B04"
VARIANT="r06"
SOURCE_SHA="f6edbf321afab965b1a0166ff0a4feb267935f6be556996c4168572477fa1c47"
PRIOR_CONSERVATIVE_USD=Decimal("1.539558")

def must(condition,reason):
    if not condition:
        raise HarnessStop(reason)

def source_case(repo_root):
    plan=load_plan(repo_root)
    case=next((c for c in plan["cases"] if c["id"]==CASE_ID),None)
    must(case is not None and case.get("split")=="pilot",
         "B04 is not a frozen pilot input")
    pack=compile_case(case)
    canon=pack["canonical_state"]
    must(pack["pack_sha256"]==SOURCE_SHA
         and pack["topic"]=="Kayıp renklerin peşinde"
         and pack["reader_age"]==10
         and pack["word_targets"]=={"min":800,"max":1400}
         and canon["protagonist"]=={
             "name":"Emir","location":"MARKET","known_locations":["MARKET"]}
         and canon["locations"]==["MARKET","STUDIO"]
         and canon["objects"]==[]
         and canon["open_obligations"]==[
             "Emir'in boyası tükenmiştir","Harita henüz bulunmamıştır"]
         and canon["unknown_facts"]==[
             "unobserved_owners","unobserved_locations"]
         and pack["forbidden_state_invention"]=="Durumda olmayan rehberlik bilgisi eklenmez",
         "B04 exact age/topic/Canon/source SHA drift")
    must(PRIOR_CONSERVATIVE_USD+USD_CAP<=GLOBAL_USER_CAP
         and sum(STAGE_MAX_USD.values())<=USD_CAP,
         "B04 new story cannot fit user's $10 exposure ceiling")
    return plan,pack

def fourth_story_once(repo_root,claim_root,*,transport):
    plan,pack=source_case(repo_root)
    root=Path(claim_root)
    must(root.is_dir() and not root.is_symlink(),
         "B04 protected one-shot claim ledger missing")
    pilot=BoundedOncePilot(str(root),case_id=CASE_ID,plan=plan,run_variant=VARIANT)
    must(pilot.pack["pack_sha256"]==SOURCE_SHA,"B04 generated from wrong source")
    result=pilot.execute(transport=transport)
    spine=json.loads((pilot.dir/"spine-plan.json").read_bytes())
    story=json.loads((pilot.dir/"story-draft.json").read_bytes())
    must(spine["source_pack_sha256"]==SOURCE_SHA
         and story["source_pack_sha256"]==SOURCE_SHA
         and spine["spine_sha256"]==story["spine_sha256"]
         and story["story_sha256"]==result["story_sha256"]
         and 800<=story["word_count"]<=1400
         and story["quality_accepted"] is False
         and story["english_master_authorized"] is False
         and story["q25_authorized"] is False
         and story["story_state_write_authorized"] is False,
         "B04 Writer/Spine/age cannot assert unaudited quality or production authority")
    return {
        "schema":SCHEMA,
        "case_id":CASE_ID,
        "reader_age":10,
        "source_pack_sha256":SOURCE_SHA,
        "original_spine_sha256":result["spine_sha256"],
        "original_story_sha256":result["story_sha256"],
        "original_word_count":result["story_words"],
        "model":MODEL,
        "model_posts_max":2,
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
        "schema":SCHEMA,"case_id":CASE_ID,"reader_age":10,
        "source_pack_sha256":SOURCE_SHA,
        "word_targets":pack["word_targets"],
        "cost_cap_usd":format(USD_CAP,"f"),
        "previous_conservative_budget_usd":format(PRIOR_CONSERVATIVE_USD,"f"),
        "user_total_cap_usd":format(GLOBAL_USER_CAP,"f"),
        "provider_calls":0,"paid_execution_default":False,
        "quality_accepted":False,"production_state_write_authorized":False,
    }

def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",default=".")
    p.add_argument("--claim-root")
    p.add_argument("--paid-b04-once",action="store_true")
    a=p.parse_args()
    if not a.paid_b04_once:
        print(json.dumps(default_status(a.repo_root),sort_keys=True))
        return
    must(os.getenv("LUMI_P438_ENABLE_B04")=="ONE_REAL_AGE10_B04_CANON_GENERATION",
         "B04 one-shot paid execution not explicitly granted")
    must(a.claim_root,"Protected B04 producer claim root missing")
    key=os.getenv("OPENROUTER_API_KEY","")
    must(type(key) is str and key.startswith("sk-or-"),
         "OpenRouter authorized inference key unavailable")
    print(json.dumps(fourth_story_once(
        a.repo_root,a.claim_root,
        transport=lambda body:https_post_once(key,body)),sort_keys=True))

if __name__=="__main__":
    main()
