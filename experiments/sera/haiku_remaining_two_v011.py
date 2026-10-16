"""SERA v0.11.1 — resume ONLY missing Haiku tasks 002/003, not task 001.

Fully source-bound to original risk evidence and first already-paid Haiku
response. Two provider calls maximum, no retry, fallback, output token cap,
story/state mutations or human-gold claims. Each new reply is preserved
before strict JSON fence + typographic apostrophe replay.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_haiku_probes_v011 import (
    qualify_source, MODEL, MIN_KEY_REMAINING,
    write_atomic, one_provider_call,
)
from experiments.sera.haiku_evidence_recovery_v011 import (
    recover_historical_first, recover_model_task,
)
from experiments.sera.semantic_risks_v011 import make_task_request

MAX_NEW_CALLS=2
OBSERVED_SPEND_STOP_USD=Decimal("0.04")
TASKS=("task_002","task_003")

def require(ok,code):
    if not ok:
        raise CoverageError(code)

def preflight(*,audit:dict,original_task:dict,original_manifest:dict)->dict:
    qualify_source(audit)
    recovered=recover_historical_first(
        audit=audit,task_artifact=original_task,manifest=original_manifest
    )
    require(recovered["model_calls_during_recovery"]==0 and
            recovered["canonical_commit_authorized"] is False,
            "V0111_HISTORICAL_FIRST_NOT_RECOVERED")
    return recovered

def run(*,audit:dict,original_task:dict,original_manifest:dict,
        output_dir:Path,launch_id:str,key:str)->dict:
    previous=preflight(
        audit=audit,original_task=original_task,
        original_manifest=original_manifest,
    )
    require(not output_dir.exists(),"V0111_OUTPUT_EXISTS")
    output_dir.mkdir(parents=True,exist_ok=False)
    write_atomic(output_dir/"reused-task-001.json",previous)
    state={
        "schema":"sera.haiku-two-remaining.v0.11.1",
        "launch_id":launch_id,
        "source_prose_sha256":audit["source_prose_sha256"],
        "model":MODEL,
        "reused_original_task":"task_001",
        "reused_previous_provider_response_id":
            previous["historical_provider_response_id"],
        "reused_historical_provider_cost":
            previous["historical_provider_reported_cost"],
        "max_new_provider_calls":MAX_NEW_CALLS,
        "new_provider_calls":0,
        "new_provider_reported_cost_usd":0.0,
        "completed_tasks":["task_001"],
        "pending_tasks":list(TASKS),
        "status":"PREFLIGHT_HOLD",
        "error_code":None,
        "model_output_token_cap_configured":False,
        "semantic_completeness_proven":False,
        "canonical_commit_authorized":False,
        "world_db_writes":0,
    }
    manifest=output_dir/"manifest.json"
    write_atomic(manifest,state)
    try:
        require(bool(key),"V0111_PROVIDER_KEY_MISSING")
        from src.openrouter_preflight import fetch_key_status,enforce_key_access
        enforce_key_access(fetch_key_status(key),min_remaining=MIN_KEY_REMAINING)
        spent=Decimal("0")
        for task_id in TASKS:
            require(state["new_provider_calls"]<MAX_NEW_CALLS,
                    "V0111_NEW_CALL_LIMIT")
            if spent>=OBSERVED_SPEND_STOP_USD:
                raise CoverageError("V0111_OBSERVED_USD_SPEND_STOP")
            request=make_task_request(audit=audit,task_id=task_id)
            path=output_dir/(task_id+".json")
            item={
                "schema":"sera.haiku-second-opinion-proof.v0.11.1",
                "task_id":task_id,
                "source_prose_sha256":audit["source_prose_sha256"],
                "request_sha256":request["request_sha256"],
                "model_requested":MODEL,
                "attempted":True,
                "provider_usage":None,
                "provider_reported_cost":None,
                "finish_reason":None,
                "raw_content":None,
                "recovered_advisory":None,
                "status":"ATTEMPTING",
                "canonical_commit_authorized":False,
            }
            write_atomic(path,item)
            state["new_provider_calls"]+=1
            state["status"]="IN_PROGRESS_SOURCE_ONLY"
            write_atomic(manifest,state)
            response=one_provider_call(
                key=key,model=MODEL,
                prepared={"request":{
                    "messages":request["messages"],
                    "response_format":request["response_format"],
                }},
            )
            if response.get("error"):
                item["status"]="PROVIDER_ERROR_HOLD"
                item["error_code"]=response["error"]
                item["provider_detail"]=response.get("provider_detail")
                write_atomic(path,item)
                raise CoverageError(
                    "V0111_PROVIDER_ERROR:"+task_id+":"+response["error"]
                )
            body=response.get("raw")
            require(isinstance(body,dict),"V0111_PROVIDER_BODY_INVALID")
            item["provider_response_id"]=body.get("id")
            item["observed_model"]=body.get("model")
            item["provider_usage"]=body.get("usage")
            item["provider_reported_cost"]=(
                body["usage"].get("cost") if
                isinstance(body.get("usage"),dict) else None
            )
            choices=body.get("choices")
            require(isinstance(choices,list) and len(choices)==1,
                    "V0111_PROVIDER_CHOICES_INVALID")
            choice=choices[0]
            item["finish_reason"]=choice.get("finish_reason")
            item["raw_content"]=(choice.get("message") or {}).get("content")
            write_atomic(path,item)
            if item["provider_reported_cost"] is None:
                raise CoverageError("V0111_PROVIDER_COST_UNREPORTED")
            try:
                charge=Decimal(str(item["provider_reported_cost"]))
            except InvalidOperation:
                raise CoverageError("V0111_PROVIDER_COST_INVALID") from None
            require(charge.is_finite() and charge>=0,
                    "V0111_PROVIDER_COST_INVALID")
            spent+=charge
            state["new_provider_reported_cost_usd"]=float(spent)
            write_atomic(manifest,state)
            require(item["finish_reason"]=="stop",
                    "V0111_PROVIDER_INCOMPLETE")
            result=recover_model_task(
                risk_audit=audit,task_id=task_id,
                raw_provider_content=item["raw_content"],
            )
            item["recovered_advisory"]=result
            item["status"]="SOURCE_BOUND_ADVISORY_HOLD"
            write_atomic(path,item)
            state["completed_tasks"].append(task_id)
            state["pending_tasks"].remove(task_id)
            write_atomic(manifest,state)
        state["status"]="ALL_3_ADVISORY_TASKS_SOURCE_BOUND_SEMANTIC_HOLD"
    except Exception as exc:
        state["status"]="INCOMPLETE_TARGETED_REVIEW_HOLD"
        state["error_code"]=str(exc)[:300]
    write_atomic(manifest,state)
    return state

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--risks",type=Path,required=True)
    p.add_argument("--historical-dir",type=Path,required=True)
    p.add_argument("--output-dir",type=Path)
    p.add_argument("--launch-id",default="dry")
    p.add_argument("--live",action="store_true")
    args=p.parse_args()
    risks=json.loads(args.risks.read_text(encoding="utf-8"))
    old=json.loads((args.historical_dir/"task_001.json").read_text(encoding="utf-8"))
    manifest=json.loads((args.historical_dir/"manifest.json").read_text(encoding="utf-8"))
    previous=preflight(audit=risks,original_task=old,original_manifest=manifest)
    if not args.live:
        print(json.dumps({
            "mode":"NO_PROVIDER_CALL",
            "source_sha256":risks["source_prose_sha256"],
            "reused_task":previous["task_id"],
            "pending_tasks":list(TASKS),
            "output_token_cap":"NOT_SET_BY_APPLICATION",
            "canonical_commit_authorized":False,
        },ensure_ascii=False,indent=2))
        return
    if args.output_dir is None:
        p.error("--live requires --output-dir")
    result=run(
        audit=risks,original_task=old,original_manifest=manifest,
        output_dir=args.output_dir,launch_id=args.launch_id,
        key=os.getenv("OPENROUTER_API_KEY",""),
    )
    print(json.dumps({
        "status":result["status"],
        "new_provider_calls":result["new_provider_calls"],
        "new_provider_reported_cost_usd":result["new_provider_reported_cost_usd"],
        "completed_tasks":result["completed_tasks"],
        "pending_tasks":result["pending_tasks"],
        "error_code":result["error_code"],
        "canonical_commit_authorized":False,
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
