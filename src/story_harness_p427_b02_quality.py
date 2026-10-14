"""P4.27 real B02 original Writer + Spine → independent initial Sonnet audit.

Reuses source/quotation/age/12-blocker-family validators from P4.22 with
B02-specific SHA proof and a new one-shot claim. It never inherits B01 ACCEPT,
never runs original frozen v21.4, never authorizes English Master or state writes.
"""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path

from src.story_harness_p410 import canonical_json
from src.story_harness_p416_input_bridge import compile_case
from src.story_harness_p426_second_case import get_case
from src.story_harness_p422_independent_audit import (
    load_source, audit_wire, audit_once, verify_auditor_reply,
    STAGE_COST_CAP, FAMILIES,
)
from src.story_harness_p417_live_pilot import https_post_once, MODEL
from src.story_harness_v1 import HarnessStop

SCHEMA="lumi.story-harness-p427-b02-independent-initial-audit.v1"
SOURCE_SHA="95397810d5a20c9c7f4a4185f914bf73bf84179ddc5a495c62db84c1fcdac2b8"
SPINE_SHA="9223dc5662f8a200b23ce3011bd36f8f84c3278ca9e2665feb3ea124a3cef25b"
STORY_SHA="7712f1561881ba50544857bc1d384eba163691c6a1e1bf65b295d90f86e5955d"
ORIGINAL_STAGE_COST=Decimal("0.04503")
PRIOR_BUDGET_RESERVED=Decimal("1.339402")  # B01 ledger + actual B02 generation
TOTAL_USER_BUDGET=Decimal("10.00")
QUALITY_CAP=STAGE_COST_CAP
EVIDENCE_DIR="evidence/story_harness_p426/"
COPY_FILES={
    "spine-plan.json":"b02-r06-original-spine-plan.json",
    "story-draft.json":"b02-r06-original-writer-draft.json",
    "01-spineforge-receipt.json":"b02-r06-original-spineforge-receipt.json",
    "02-writer-receipt.json":"b02-r06-original-writer-receipt.json",
}


def must(ok,reason):
    if not ok:
        raise HarnessStop(reason)


def get_b02_original(repo_root,claim_root):
    plan,case,pack=get_case(repo_root)
    must(pack["pack_sha256"]==SOURCE_SHA,"Original B02 canonical pack drifted")
    source=load_source(repo_root,claim_root,case_id="B02",run_variant="r06")
    must(source["case_id"]=="B02"
         and source["spine"]["spine_sha256"]==SPINE_SHA
         and source["story"]["story_sha256"]==STORY_SHA
         and source["story"]["word_count"]==561
         and Decimal(source["generation_cost_usd"])==ORIGINAL_STAGE_COST,
         "Real B02 model-generated artifact drift")
    directory=Path(claim_root)/source["original_claim_id"]
    repo=Path(repo_root)
    for original,reference in COPY_FILES.items():
        live=(directory/original)
        frozen=(repo/EVIDENCE_DIR/reference)
        must(frozen.is_file() and not frozen.is_symlink()
             and live.is_file() and not live.is_symlink()
             and live.read_bytes()==frozen.read_bytes(),
             "B02 durable provider model receipt not byte-identical to frozen GitHub evidence")
    must(PRIOR_BUDGET_RESERVED+QUALITY_CAP<=TOTAL_USER_BUDGET,
         "Total B02 independent quality allocation exceeds approved 10 USD")
    return source


def inspect_b02_initial(source):
    must(source.get("case_id")=="B02"
         and source["story"]["story_sha256"]==STORY_SHA
         and source["spine"]["spine_sha256"]==SPINE_SHA,
         "B01 or other state/story cannot enter B02 independent quality")
    request=audit_wire(source)
    must(request["model"]==MODEL
         and "four years old" not in request["messages"][0]["content"]
         and '4 years old' in request["messages"][0]["content"]
         and json.loads(request["messages"][1]["content"])["case_id"]=="B02"
         and request["response_format"]["json_schema"]["name"]==
             "lumi_b02_independent_initial_audit_v1",
         "B02 age, case or source not independently scoped")
    return request


def audit_b02_once(source,audit_root,*,transport):
    inspect_b02_initial(source)
    verdict=audit_once(source,audit_root,transport=transport,
                       audit_prefix="p427")
    must(verdict["case_id"]=="B02"
         and verdict["story_sha256"]==STORY_SHA
         and verdict["spine_sha256"]==SPINE_SHA
         and verdict["english_master_authorized"] is False
         and verdict["q25_authorized"] is False
         and verdict["full_original_v21_final_audit_completed"] is False
         and verdict["state_write_authorized"] is False,
         "Independent pilot quality tried to promote B02 to production")
    return verdict


def default_status():
    return {"schema":SCHEMA,"case_id":"B02",
            "source_pack_sha256":SOURCE_SHA,
            "spine_sha256":SPINE_SHA,
            "story_sha256":STORY_SHA,
            "source_generation_cost_usd":"0.04503",
            "maximum_new_quality_posts":1,
            "maximum_new_quality_usd":format(QUALITY_CAP,"f"),
            "previous_budget_reserved_usd":format(PRIOR_BUDGET_RESERVED,"f"),
            "total_user_budget_usd":format(TOTAL_USER_BUDGET,"f"),
            "quality_accepted":False,
            "english_master_authorized":False,
            "q25_authorized":False,
            "production_state_write_authorized":False,
            "provider_calls":0}


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root",default=".")
    parser.add_argument("--b02-producer-claims")
    parser.add_argument("--b02-quality-claims")
    parser.add_argument("--paid-once",action="store_true")
    args=parser.parse_args()
    if not args.paid_once:
        print(json.dumps(default_status(),sort_keys=True))
        return
    must(os.getenv("LUMI_P427_QA_B02")=="B02_INDEPENDENT_QA_SINGLE_CALL",
         "Paid B02 independent audit not approved for this one-shot")
    must(args.b02_producer_claims and args.b02_quality_claims,
         "B02 original producer and audit roots required")
    source=get_b02_original(args.repo_root,args.b02_producer_claims)
    result=audit_b02_once(source,args.b02_quality_claims,
                          transport=lambda wire:https_post_once(
                              os.getenv("OPENROUTER_API_KEY",""),wire))
    print(json.dumps({
        "schema":SCHEMA,
        "case_id":"B02",
        "initial_quality_verdict":result["quality_initial_verdict"],
        "reader_score":result["reader_score"],
        "blocking_findings":len(result["blocking_findings"]),
        "story_sha256":result["story_sha256"],
        "spine_sha256":result["spine_sha256"],
        "auditor_generation_id":result["auditor_generation_id"],
        "provider_reported_cost_usd":result["auditor_reported_cost_usd"],
        "english_master_authorized":False,
        "q25_authorized":False,
        "production_state_write_authorized":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
