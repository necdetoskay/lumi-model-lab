"""SERA v0.15 — one opt-in, blind model-assisted identity run for Mara S1.

The prompt uses ONLY archived source mentions and initial World State,
never v0.14 analyst-rule conclusions. Any model output is NONCANONICAL.
Single provider call, no retry/fallback, no writer/JEV, no token ceiling.
Persist raw provider content and usage BEFORE attempting deterministic bind.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from decimal import Decimal, InvalidOperation

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_v04_audit import PATH, EXPECTED_SHA
from experiments.sera.mara_s1_typed_live_v05 import entry_state, one_provider_call
from experiments.sera.blind_identity_v015 import make_request, bind
from experiments.sera.world_state_v02 import canonical
from experiments.sera.coverage import prose_hash

MODEL="anthropic/claude-haiku-4.5"
MIN_REMAINING_KEY_USD=0.25
CALL_COUNT_MAX=1
# Observed cost is recorded. This is NOT an output-token ceiling.
# With one call there is no second request that could exceed a stop threshold.

def source_prose():
    item=json.loads(PATH.read_text(encoding="utf-8"))
    prose=item["prose"]
    if item.get("source_prose_sha256")!=EXPECTED_SHA or (
        prose_hash(prose)!=EXPECTED_SHA
    ):
        raise CoverageError("V015_FROZEN_MARA_SOURCE_INVALID")
    return prose

def prepare(mentions:dict):
    prose=source_prose()
    world=entry_state()
    request=make_request(prose=prose,world=world,census=mentions)
    if len(request["requested_refs"])!=16:
        raise CoverageError("V015_MARA_EXPECTED_16_CANDIDATES")
    return prose,world,request

def atomic(path:Path,payload:dict):
    file=path.with_suffix(path.suffix+".stage")
    file.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",
                    encoding="utf-8")
    file.replace(path)

def run(*,mentions:dict,output:Path,launch_id:str,key:str)->dict:
    if output.exists():
        raise CoverageError("V015_EVIDENCE_OUTPUT_ALREADY_EXISTS")
    prose,world,request=prepare(mentions)
    output.parent.mkdir(parents=True,exist_ok=True)
    state={
        "schema":"sera.mara-s1-blind-identity-paid-pilot.v0.15",
        "launch_id":launch_id,"source_prose_sha256":EXPECTED_SHA,
        "model_requested":MODEL,
        "request_sha256":request["request_sha256"],
        "source_mentions_sha256":request["census_sha256"],
        "world_sha256":request["world_sha256"],
        "requested_refs":request["requested_refs"],
        "provider_attempts":0,
        "provider_response_id":None,
        "observed_model":None,
        "finish_reason":None,
        "provider_usage":None,
        "provider_reported_cost":None,
        "raw_provider_content":None,
        "bound_advisory":None,
        "error_code":None,
        "status":"PREFLIGHT_HOLD",
        "output_token_limit_configured":False,
        "canonical_commit_authorized":False,
        "world_db_writes":0,
        "new_entities_created":0,
        "new_relationship_links":0,
    }
    atomic(output,state)
    try:
        if not key:
            raise CoverageError("V015_OPENROUTER_KEY_MISSING")
        from src.openrouter_preflight import (
            fetch_key_status,enforce_key_access,
        )
        enforce_key_access(
            fetch_key_status(key),min_remaining=MIN_REMAINING_KEY_USD)
        state["provider_attempts"]=1
        state["status"]="PROVIDER_REQUEST_STARTED"
        atomic(output,state)
        result=one_provider_call(
            key=key,model=MODEL,prepared={"request":{
                "messages":request["messages"],
                "response_format":request["response_format"],
            }},
        )
        if result.get("error"):
            state["status"]="PROVIDER_ERROR_HOLD"
            state["error_code"]=result["error"]
            state["provider_detail"]=result.get("provider_detail")
            atomic(output,state)
            return state
        raw=result.get("raw")
        if not isinstance(raw,dict):
            raise CoverageError("V015_PROVIDER_BODY_NOT_OBJECT")
        state["provider_response_id"]=raw.get("id")
        state["observed_model"]=raw.get("model")
        usage=raw.get("usage")
        state["provider_usage"]=usage
        if isinstance(usage,dict):
            state["provider_reported_cost"]=usage.get("cost")
        choices=raw.get("choices")
        if not isinstance(choices,list) or len(choices)!=1:
            raise CoverageError("V015_PROVIDER_CHOICES_INVALID")
        choice=choices[0]
        state["finish_reason"]=choice.get("finish_reason")
        state["raw_provider_content"]=(choice.get("message") or {}).get("content")
        state["status"]="RAW_MODEL_RESPONSE_ARCHIVED_HOLD"
        atomic(output,state)
        if state["provider_reported_cost"] is None:
            raise CoverageError("V015_PROVIDER_COST_MISSING")
        try:
            spent=Decimal(str(state["provider_reported_cost"]))
        except InvalidOperation:
            raise CoverageError("V015_PROVIDER_COST_INVALID") from None
        if not spent.is_finite() or spent<0:
            raise CoverageError("V015_PROVIDER_COST_INVALID")
        if state["finish_reason"]!="stop":
            raise CoverageError("V015_PROVIDER_FINISH_NOT_STOP")
        if state["observed_model"]!=MODEL:
            raise CoverageError("V015_UNEXPECTED_PROVIDER_MODEL")
        bound=bind(
            prose=prose,world=world,census=mentions,request=request,
            raw_response=state["raw_provider_content"],
        )
        state["bound_advisory"]=bound
        state["status"]="ALL_IDENTITY_MODEL_OPINIONS_BOUND_NONCANONICAL_HOLD"
    except Exception as exc:
        state["error_code"]=str(exc)[:300]
        state["status"]="IDENTITY_PROVIDER_OR_CONTRACT_HOLD"
    atomic(output,state)
    return state

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mentions",required=True,type=Path)
    p.add_argument("--output",type=Path)
    p.add_argument("--live",action="store_true")
    p.add_argument("--launch-id",default="preflight-only")
    args=p.parse_args()
    source=json.loads(args.mentions.read_text(encoding="utf-8"))
    prose,world,req=prepare(source)
    if not args.live:
        print(json.dumps({
            "mode":"NO_PROVIDER_CALL",
            "model":MODEL,
            "source_sha256":EXPECTED_SHA,
            "request_sha256":req["request_sha256"],
            "requested_refs":req["requested_refs"],
            "model_output_token_limit":"NOT_SET_BY_APPLICATION",
            "canonical_commit_authorized":False,
        },ensure_ascii=False,indent=2))
        return
    if args.output is None:
        p.error("--live requires --output")
    result=run(
        mentions=source,output=args.output,launch_id=args.launch_id,
        key=os.getenv("OPENROUTER_API_KEY",""),
    )
    print(json.dumps({
        "status":result["status"],
        "provider_attempts":result["provider_attempts"],
        "provider_reported_cost":result["provider_reported_cost"],
        "model_observed":result["observed_model"],
        "finish_reason":result["finish_reason"],
        "error_code":result["error_code"],
        "noncanonical_classified": (
            result["bound_advisory"]["proposed_count"]
            if result["bound_advisory"] else None),
        "noncanonical_abstained": (
            result["bound_advisory"]["abstained_count"]
            if result["bound_advisory"] else None),
        "world_db_writes":0,
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
