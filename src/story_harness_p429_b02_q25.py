"""P4.29 B02-only real Q25 quote evidence from source-matched Pilot Master.

Reuse the successful P4.24 read-only Q25 extraction method, with B02-specific
Canon locations, original Master, unique claim, one real Sonnet POST and
bounded $0.050 exposure. No automatic repairs, state commits or inference
based on B01's unrelated state.
"""
from __future__ import annotations
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re

from src.story_harness_p410 import canonical_json
from src.story_harness_p424_q25_evidence import (
    extraction_wire, verify_model_response, SAFE_FAILURE_CODE, COST_CAP,
    MODEL, money,
)
from src.story_harness_p427_b02_quality import (
    get_b02_original, SOURCE_SHA,SPINE_SHA,STORY_SHA,
)
from src.story_harness_p428_b02_master import load_b02_quality,MASTER_DIR
from src.story_harness_p423_master import qualify_master
from src.story_harness_p417_live_pilot import https_post_once
from src.story_harness_v1 import HarnessStop

SCHEMA="lumi.story-harness-p429-b02-evidence-proposal.v1"
RUN_NAME="p429-b02-r06-q25-evidence-v01"
MASTER_MANIFEST="evidence/story_harness_p428/b02-r06-pilot-master-manifest.json"
MASTER_PROSE="evidence/story_harness_p428/b02-r06-pilot-english-master.txt"
PREVIOUS_RESERVED_USD=Decimal("1.360092")
USER_CAP_USD=Decimal("10.00")


def must(ok, reason):
    if not ok:
        raise HarnessStop(reason)


def load_b02_bundle(repo_root,producer_root,quality_root,master_root):
    source=get_b02_original(repo_root,producer_root)
    audit=load_b02_quality(repo_root,quality_root)
    accepted=qualify_master(source,audit)
    master=Path(master_root)/MASTER_DIR
    must(master.is_dir() and not master.is_symlink(),
         "B02 source-sealed pilot English Master missing")
    mf=master/"master-manifest.json"
    prose=master/"ENGLISH_MASTER.txt"
    repo=Path(repo_root)
    for src,dest in ((mf,repo/MASTER_MANIFEST),(prose,repo/MASTER_PROSE)):
        must(src.is_file() and dest.is_file()
             and not src.is_symlink() and not dest.is_symlink()
             and src.read_bytes()==dest.read_bytes(),
             "B02 exact original English Master bytes differ from GitHub evidence")
    manifest=json.loads(mf.read_bytes())
    raw=prose.read_bytes()
    must(manifest.get("schema")=="lumi.story-harness-p423-pilot-english-master.v1"
         and manifest.get("case_id")=="B02"
         and manifest.get("source_pack_sha256")==SOURCE_SHA
         and manifest.get("approved_spine_sha256")==SPINE_SHA
         and manifest.get("source_story_sha256")==STORY_SHA
         and manifest.get("accepted_story_sha256")==STORY_SHA
         and manifest.get("independent_auditor_generation_id")==accepted["auditor_generation_id"]
         and manifest.get("independent_initial_audit_verdict")=="ACCEPT"
         and manifest.get("reader_score")==5
         and manifest.get("english_master_word_count")==561
         and manifest.get("manual_text_edits")==0
         and manifest.get("q25_read_only_extraction_allowed") is True
         and manifest.get("production_state_write_authorized") is False
         and manifest.get("full_original_frozen_v21_4_production_quality_accepted") is False,
         "B02 Master not genuinely same-source pilot accepted")
    must(hashlib.sha256(raw).hexdigest()==STORY_SHA
         and raw.decode("utf-8")==source["story"]["story_text"],
         "B02 Master prose not exact independent-approved model text")
    must(PREVIOUS_RESERVED_USD+COST_CAP<=USER_CAP_USD,
         "B02 Q25 may exceed cumulative user authorization")
    return {"source":source,"audit":audit,"master":manifest,
            "english_master_text":raw.decode("utf-8")}


def b02_q25_wire(bundle):
    must(bundle["source"].get("case_id")=="B02",
         "B01 cannot enter B02 Q25")
    wire=extraction_wire(bundle)
    must(wire["response_format"]["json_schema"]["name"]==
         "lumi_b02_q25_evidence_proposal_v1",
         "B02 not independently scoped in provider format")
    system=wire["messages"][0]["content"]
    must("AT_GARDEN" in system and "AT_COMMONS" in system
         and "AT_HOME" not in system and "AT_MEADOW" not in system,
         "B02 Q25 provider must not use B01 spatial relation vocabulary")
    must(json.loads(wire["messages"][1]["content"])["case_id"]=="B02",
         "B02 source missing from model prompt")
    return wire


def _write(path,body):
    flags=os.O_CREAT|os.O_EXCL|os.O_WRONLY
    if hasattr(os,"O_NOFOLLOW"): flags|=os.O_NOFOLLOW
    fd=os.open(path,flags,0o600)
    with os.fdopen(fd,"wb") as f:
        f.write(canonical_json(body)+b"\n")
        f.flush()
        os.fsync(f.fileno())


def one_b02_q25(bundle,claim_root,*,transport):
    root=Path(claim_root)
    must(root.is_dir() and not root.is_symlink(),
         "No protected Q25 ledger for B02")
    folder=root/RUN_NAME
    folder.mkdir(mode=0o700,exist_ok=False)
    body=b02_q25_wire(bundle)
    _write(folder/"00-intent.json",{
        "schema":SCHEMA,"case_id":"B02",
        "story_sha256":STORY_SHA,"spine_sha256":SPINE_SHA,
        "request_sha256":hashlib.sha256(canonical_json(body)).hexdigest(),
        "maximum_model_posts":1,
        "stage_cost_cap_usd":format(COST_CAP,"f"),
        "prior_budget_reserved_usd":format(PREVIOUS_RESERVED_USD,"f"),
        "automatic_retry":False,"production_state_write_authorized":False,
    })
    response=None
    try:
        response=transport(body)
        result=verify_model_response(bundle,response)
        must(result["case_id"]=="B02"
             and result["story_sha256"]==STORY_SHA
             and result["spine_sha256"]==SPINE_SHA
             and result["production_state_write_authorized"] is False
             and result["semantic_state_fully_certified"] is False,
             "B02 Q25 may not self-authorize final state or cross-story facts")
        result["schema"]=SCHEMA
        _write(folder/"01-b02-q25-evidence.json",result)
        return result
    except Exception as exc:
        usage=response.get("usage") if type(response) is dict else None
        cost=None
        if type(usage) is dict:
            try: cost=money(usage.get("cost"))
            except HarnessStop: pass
        gid=response.get("id") if type(response) is dict else None
        if not (type(gid) is str and re.fullmatch(r"gen-[A-Za-z0-9_-]{6,120}",gid)):
            gid=None
        reason=(SAFE_FAILURE_CODE.get(str(exc),"UNKNOWN_SAFE_Q25_VALIDATION")
                if isinstance(exc,HarnessStop) else "PROVIDER_OR_UNEXPECTED_ERROR")
        if not (folder/"01-b02-q25-evidence.json").exists():
            _write(folder/"01-b02-q25-evidence.json",{
                "schema":SCHEMA,"case_id":"B02","status":"STOP_UNKNOWN_OR_INVALID",
                "safe_failure_code":reason,"provider_generation_id":gid,
                "provider_reported_cost_usd":format(cost,"f") if cost is not None else None,
                "source_story_sha256":STORY_SHA,
                "model_post_attempt_consumed":True,
                "automatic_retry":False,"production_state_write_authorized":False,
            })
        raise HarnessStop("B02 Q25 consumed, no retry; reason="+reason) from None


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",default=".")
    p.add_argument("--producer-root")
    p.add_argument("--quality-root")
    p.add_argument("--master-root")
    p.add_argument("--q25-root")
    p.add_argument("--paid-once",action="store_true")
    args=p.parse_args()
    if not args.paid_once:
        print(json.dumps({"schema":SCHEMA,"case_id":"B02",
                          "model_posts":0,"quality_reused_from_B01":False,
                          "new_stage_cap_usd":"0.050",
                          "production_state_write_authorized":False},sort_keys=True))
        return
    must(os.getenv("LUMI_P429_Q25_B02")=="ONE_REVIEWED_B02_MASTER_Q25",
         "No B02-specific paid Q25 grant")
    must(args.producer_root and args.quality_root and args.master_root and args.q25_root,
         "B02 authenticated source roots missing")
    key=os.getenv("OPENROUTER_API_KEY","")
    must(type(key) is str and key.startswith("sk-or-"),"No authorized inference key")
    bundle=load_b02_bundle(args.repo_root,args.producer_root,args.quality_root,args.master_root)
    r=one_b02_q25(bundle,args.q25_root,transport=lambda body:https_post_once(key,body))
    print(json.dumps({"schema":SCHEMA,"case_id":"B02",
         "story_sha256":r["story_sha256"],
         "proposed_final_location":r["evidence_proposal"]["final_location"]["location_id"],
         "object_mentions":len(r["evidence_proposal"]["object_observations"]),
         "provider_reported_cost_usd":r["provider_reported_cost_usd"],
         "state_committed":False,"production_state_write_authorized":False},sort_keys=True))


if __name__=="__main__":
    main()
