"""P4.26 second DISTINCT real Canon/topic pilot via the EXISTING P4.17 pipeline.

No new generation method: B02 runs the already approved source-bound BoundedOncePilot
with the same flat JSON Sonnet transport, mutable-free Spine before Writer, once.
B01's prior quality or Q25 verdict is never inherited by B02.
"""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path

from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p416_input_bridge import compile_case
from src.story_harness_p417_live_pilot import (
    BoundedOncePilot, https_post_once, USD_CAP, GLOBAL_USER_CAP,
    STAGE_MAX_USD, OUTPUT_CAPS, MODEL,
)
from src.story_harness_v1 import HarnessStop

SCHEMA="lumi.story-harness-p426-b02-second-variable-story-pilot.v1"
CASE="B02"
VARIANT="r06"
PRIOR_CONSERVATIVE_RESERVED_USD=Decimal("1.294372")
MAX_NEW_USD=USD_CAP


def must(ok,why):
    if not ok:
        raise HarnessStop(why)


def get_case(repo_root):
    p=load_plan(repo_root)
    row=next((x for x in p["cases"] if x["id"]==CASE),None)
    must(row is not None and row.get("split")=="pilot",
         "Second distinct benchmark case not an approved pilot")
    pack=compile_case(row)
    must(pack["reader_age"]==4 and
         pack["canonical_state"]["protagonist"]["location"]=="GARDEN"
         and "COMMONS" in pack["canonical_state"]["locations"]
         and len(pack["open_obligations"])==2,
         "B02 Canon or reader-age fixture changed unexpectedly")
    must(PRIOR_CONSERVATIVE_RESERVED_USD+MAX_NEW_USD<=GLOBAL_USER_CAP,
         "B02 exceeds original user total 10 USD spending authorization")
    must(STAGE_MAX_USD["SPINEFORGE"]+STAGE_MAX_USD["WRITER"]<=MAX_NEW_USD,
         "Declared per-stage cap exceeds one-story bound")
    return p,row,pack


def execute_second_story(repo_root, claim_root, *,transport):
    plan,row,pack=get_case(repo_root)
    root=Path(claim_root)
    must(root.is_dir() and not root.is_symlink(),
         "Dedicated protected immutable story claim directory absent")
    engine=BoundedOncePilot(root,case_id=CASE,plan=plan,
                            run_variant=VARIANT)
    must(engine.pack["pack_sha256"]==pack["pack_sha256"],
         "B02 source swapped during engine compilation")
    result=engine.execute(transport=transport)
    spine=engine.dir/"spine-plan.json"
    writer=engine.dir/"story-draft.json"
    must(spine.is_file() and writer.is_file(),
         "B02 writer cannot continue without frozen original Spine and prose")
    out=json.loads(writer.read_bytes())
    frozen=json.loads(spine.read_bytes())
    must(out["source_pack_sha256"]==pack["pack_sha256"]
         and frozen["source_pack_sha256"]==pack["pack_sha256"]
         and frozen["spine_sha256"]==out["spine_sha256"]
         and out["story_sha256"]==result["story_sha256"]
         and out["word_count"]==result["story_words"]
         and out["quality_accepted"] is False
         and out["english_master_authorized"] is False
         and out["q25_authorized"] is False
         and out["story_state_write_authorized"] is False,
         "B02 mixed state artifacts or smuggled former B01 quality approval")
    return {
        "schema":SCHEMA,
        "case_id":CASE,"reader_age":pack["reader_age"],
        "source_pack_sha256":pack["pack_sha256"],
        "spine_sha256":result["spine_sha256"],
        "writer_sha256":result["story_sha256"],
        "word_count":result["story_words"],
        "model":MODEL,
        "real_provider_transport_called":result["real_generation_transport_invoked"],
        "provider_reported_spine_writer_cost_usd":result["two_stage_cost_usd"],
        "independent_quality_accepted":False,
        "english_master_authorized":False,
        "q25_evidence_accepted":False,
        "final_story_state_certified":False,
        "production_state_write_authorized":False,
        "manual_story_edits":0,
        "automatic_model_retries":False,
    }


def status(repo_root="."):
    _,row,pack=get_case(repo_root)
    return {
        "schema":SCHEMA,
        "case_id":CASE,
        "reader_age":pack["reader_age"],
        "source_pack_sha256":pack["pack_sha256"],
        "first_case_reuse_prohibited":True,
        "provider_calls":0,
        "model":MODEL,
        "stage_spend_usd_max":{k:str(v) for k,v in STAGE_MAX_USD.items()},
        "one_story_exposure_cap_usd":str(MAX_NEW_USD),
        "conservative_prior_spend_reserved_usd":str(PRIOR_CONSERVATIVE_RESERVED_USD),
        "total_user_budget_usd":str(GLOBAL_USER_CAP),
        "default_paid_dispatch_enabled":False,
        "quality_accepted":False,
    }


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",default=".")
    p.add_argument("--claim-root")
    p.add_argument("--paid-b02-once",action="store_true")
    args=p.parse_args()
    if not args.paid_b02_once:
        print(json.dumps(status(args.repo_root),sort_keys=True))
        return
    must(os.getenv("LUMI_P426_RUN_B02")=="ONE_DISTINCT_STATE_TOPIC_REAL_STORY",
         "B02 paid execution not explicitly armed")
    must(args.claim_root, "Missing persistent immutable B02 claim root")
    api_key=os.getenv("OPENROUTER_API_KEY","")
    must(type(api_key) is str and api_key.startswith("sk-or-"),
         "Existing OpenRouter inference key missing")
    result=execute_second_story(args.repo_root,args.claim_root,
        transport=lambda body:https_post_once(api_key,body))
    # Never log actual prose or provider bearer in Actions stdout.
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
