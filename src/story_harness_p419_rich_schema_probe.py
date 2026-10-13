"""P4.19 one-shot provider shape probe for the EXACT P4.17 nested Spine schema.

Uses the real B01 pack ONLY to assemble a schema, then sends a small public
synthetic prompt instead of user Canon/story. Does NOT produce or accept story.
One request, no retries, durable atomic local claim, strict redacted reporting.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path

from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p416_input_bridge import compile_case, build_spine_request
from src.story_harness_p417_live_pilot import wire
from src.story_harness_p418_compat_probe import (
    http_post_once, _write_once, _money, ENDPOINT
)
from src.story_harness_p410 import canonical_json
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-p419-rich-schema-differential.v1"
DIR = "p419-rich-spine-schema-v01"
PUBLIC_SYSTEM = "You are testing a public synthetic JSON response format. Nothing here is a real story or user canonical state."
PUBLIC_USER = (
    "Return one JSON object with source_pack_sha256 set to the given value. "
    "Provide four simple numbered beats at the HOME and MEADOW locations; "
    "make each goal, choice and consequence a sentence, and include a "
    "brief spine summary. The JSON response is a disposable synthetic probe."
)


def full_rich_wire(repo_root):
    plan=load_plan(repo_root)
    case=next(x for x in plan["cases"] if x["id"]=="B01")
    pack=compile_case(case)
    body=wire("SPINEFORGE",build_spine_request(pack))
    # Preserve EXACT response_format schema and routing, but NEVER use
    # actual state/topic prompts for this diagnostic.
    body["messages"]=[
        {"role":"system","content":PUBLIC_SYSTEM},
        {"role":"user","content":PUBLIC_USER+"\nsource_pack_sha256="+pack["pack_sha256"]},
    ]
    body["max_tokens"]=512
    assert body["response_format"]["type"]=="json_schema"
    assert len(canonical_json(body))<10000
    return body


def run_once(*, repo_root, root, api_key, post=http_post_once):
    where=Path(root)
    if not where.is_dir() or where.is_symlink():
        raise HarnessStop("Protected persistent P419 ledger missing")
    claim=where/DIR
    claim.mkdir(mode=0o700,exist_ok=False)
    body=full_rich_wire(repo_root)
    _write_once(claim,"00-claim.json",{
        "schema":SCHEMA,"one_provider_post":True,
        "live_story_dispatched":False,
        "model_usage_budget_usd":"0.03",
        "previous_uncertain_story_exposure_usd":"1.05",
        "previous_known_microprobe_charge_usd":"0.000714",
        "automatic_retry":False,
    })
    _write_once(claim,"01-intent.json",{
        "schema":SCHEMA,
        "exact_rich_wire_sha256":hashlib.sha256(canonical_json(body)).hexdigest(),
        "source_prompt_is_public_synthetic":True,
        "request_output_cap_tokens":512,
        "retry_allowed":False,
    })
    try:
        r=post(api_key,body)
        if type(r) is not dict or type(r.get("http_status")) is not int:
            raise HarnessStop("Unknown P419 transport response")
        result={
            "schema":SCHEMA,
            "probe_type":"EXACT_P417_SPINE_SCHEMA_PUBLIC_PROMPT",
            "http_status":r["http_status"],
            "successful_http":r["http_status"]==200,
            "safe_provider_error":r.get("error") if r["http_status"]!=200 else None,
            "known_cost_usd":None,
            "usage_input_tokens":None,
            "usage_output_tokens":None,
            "model_identity_matches":None,
            "real_story_generated":False,
            "quality_accepted":False,
            "retry_allowed":False,
        }
        if r["http_status"]==200:
            response=r.get("body")
            if type(response) is not dict:
                raise HarnessStop("Invalid successful provider envelope")
            result["model_identity_matches"]=response.get("model")==body["model"]
            usage=response.get("usage")
            if type(usage) is not dict:
                raise HarnessStop("Provider usage missing")
            result["usage_input_tokens"]=usage.get("prompt_tokens")
            result["usage_output_tokens"]=usage.get("completion_tokens")
            cost=_money(usage.get("cost"))
            if cost>Decimal("0.03"):
                raise HarnessStop("Microprobe charge exceeds ceiling")
            result["known_cost_usd"]=format(cost,"f")
        else:
            e=result["safe_provider_error"]
            if not(type(e) is dict and e.get("category") in (
                "PROVIDER_REJECTED","SENSITIVE_ERROR_REDACTED")):
                raise HarnessStop("Unsafe provider error envelope")
        _write_once(claim,"01-provider-receipt.json",result)
        return result
    except Exception:
        if not(claim/"01-provider-receipt.json").exists():
            _write_once(claim,"01-provider-receipt.json",{
                "schema":SCHEMA,"outcome":"CONSUMED_UNKNOWN","known_cost_usd":None,
                "retry_allowed":False,"real_story_generated":False,
            })
        raise HarnessStop("P419 consumed, no retry") from None


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--repo-root",default=".")
    parser.add_argument("--run-root")
    parser.add_argument("--paid-one-shot",action="store_true")
    args=parser.parse_args()
    if not args.paid_one_shot:
        print(json.dumps({"schema":SCHEMA,
                          "provider_post_calls":0,
                          "status":"PAID_DISABLED_DEFAULT",
                          "max_billed_exposure_usd":"0.03"},sort_keys=True))
    else:
        if os.environ.get("LUMI_P419_ENABLE")!="AGGREGATE_10_USD_APPROVED":
            raise HarnessStop("No exact signed-run execution flag")
        result=run_once(repo_root=args.repo_root,root=args.run_root,
                        api_key=os.getenv("OPENROUTER_API_KEY",""))
        print(json.dumps(result,sort_keys=True))
