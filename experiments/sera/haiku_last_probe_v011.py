"""SERA v0.11.2 final independent task 003, zero duplicate Haiku calls.

Reuse pinned paid task 001 and 002 evidence; inspect only open pocket
watch -> closed case, never set output token ceilings, retry on failure,
mutate story text, or commit World State.
"""
from __future__ import annotations

import argparse
from decimal import Decimal,InvalidOperation
import json
import os
from pathlib import Path

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_haiku_probes_v011 import (
    qualify_source,MODEL,MIN_KEY_REMAINING,write_atomic,one_provider_call,
)
from experiments.sera.haiku_evidence_recovery_v011 import (
    recover_historical_first,recover_historical_second,recover_model_task,
)
from experiments.sera.semantic_risks_v011 import make_task_request

TASK="task_003"
MAX_NEW_CALLS=1
OBSERVED_COST_GUARD_USD=Decimal("0.02")

def require(ok,code):
    if not ok:
        raise CoverageError(code)

def prepare(*,audit:dict,original_one:dict,manifest_one:dict,
            original_two:dict,manifest_two:dict) -> list[dict]:
    qualify_source(audit)
    a=recover_historical_first(
        audit=audit,task_artifact=original_one,manifest=manifest_one)
    b=recover_historical_second(
        audit=audit,task_artifact=original_two,manifest=manifest_two)
    require(a["canonical_commit_authorized"] is False and
            b["canonical_commit_authorized"] is False and
            a["model_calls_during_recovery"]==0 and
            b["model_calls_during_recovery"]==0,
            "HAIKU_FIRST_TWO_NOT_VERIFIED")
    return [a,b]

def run(*,audit:dict,first:dict,first_manifest:dict,
        second:dict,second_manifest:dict,
        output_dir:Path,launch_id:str,key:str) -> dict:
    previous=prepare(
        audit=audit,original_one=first,manifest_one=first_manifest,
        original_two=second,manifest_two=second_manifest)
    require(not output_dir.exists(),"HAIKU_LAST_OUTPUT_EXISTS")
    output_dir.mkdir(parents=True,exist_ok=False)
    write_atomic(output_dir/"reused-task-001.json",previous[0])
    write_atomic(output_dir/"reused-task-002.json",previous[1])
    state={
        "schema":"sera.mara-s1-haiku-last-probe.v0.11.2",
        "launch_id":launch_id,
        "source_prose_sha256":audit["source_prose_sha256"],
        "model":MODEL,"historical_tasks_reused":["task_001","task_002"],
        "pending_tasks":[TASK],"completed_tasks":["task_001","task_002"],
        "max_new_calls":MAX_NEW_CALLS,"new_provider_calls":0,
        "new_provider_reported_cost_usd":0.0,
        "status":"PREFLIGHT_HOLD","error_code":None,
        "output_token_cap_set":False,"canonical_commit_authorized":False,
        "world_db_writes":0,"human_gold_qualified":False,
    }
    manifest=output_dir/"manifest.json"
    write_atomic(manifest,state)
    try:
        require(bool(key),"HAIKU_LAST_KEY_MISSING")
        from src.openrouter_preflight import (
            fetch_key_status,enforce_key_access,
        )
        enforce_key_access(
            fetch_key_status(key),min_remaining=MIN_KEY_REMAINING)
        request=make_task_request(audit=audit,task_id=TASK)
        item={
            "task_id":TASK,"request_sha256":request["request_sha256"],
            "source_prose_sha256":audit["source_prose_sha256"],
            "model_requested":MODEL,"provider_attempted":True,
            "provider_reported_cost":None,"provider_usage":None,
            "finish_reason":None,"raw_content":None,
            "recovered_advisory":None,
            "status":"ATTEMPTING",
            "canonical_commit_authorized":False,
        }
        f=output_dir/"task_003.json"
        write_atomic(f,item)
        state["new_provider_calls"]=1
        state["status"]="IN_PROGRESS"
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
            item["provider_error"]=response["error"]
            item["provider_detail"]=response.get("provider_detail")
            write_atomic(f,item)
            raise CoverageError("HAIKU_LAST_PROVIDER_ERROR:"+response["error"])
        raw=response.get("raw")
        require(isinstance(raw,dict),"HAIKU_LAST_BODY_INVALID")
        item["provider_response_id"]=raw.get("id")
        item["observed_model"]=raw.get("model")
        item["provider_usage"]=raw.get("usage")
        item["provider_reported_cost"]=(
            raw["usage"].get("cost") if
            isinstance(raw.get("usage"),dict) else None
        )
        choices=raw.get("choices")
        require(isinstance(choices,list) and len(choices)==1,
                "HAIKU_LAST_CHOICES_INVALID")
        item["finish_reason"]=choices[0].get("finish_reason")
        item["raw_content"]=(choices[0].get("message") or {}).get("content")
        write_atomic(f,item)
        require(item["provider_reported_cost"] is not None,
                "HAIKU_LAST_PROVIDER_COST_MISSING")
        try:
            cost=Decimal(str(item["provider_reported_cost"]))
        except InvalidOperation:
            raise CoverageError("HAIKU_LAST_COST_INVALID") from None
        require(cost.is_finite() and cost>=0,"HAIKU_LAST_COST_INVALID")
        state["new_provider_reported_cost_usd"]=float(cost)
        write_atomic(manifest,state)
        require(item["finish_reason"]=="stop","HAIKU_LAST_INCOMPLETE")
        result=recover_model_task(
            risk_audit=audit,task_id=TASK,
            raw_provider_content=item["raw_content"])
        item["recovered_advisory"]=result
        item["status"]="SOURCE_BOUND_INDEPENDENT_OPINION_HOLD"
        write_atomic(f,item)
        state["pending_tasks"]=[]
        state["completed_tasks"].append(TASK)
        state["status"]="THREE_INDEPENDENT_OPINIONS_RECORDED_SEMANTIC_HOLD"
    except Exception as exc:
        state["status"]="LAST_PROBE_INCOMPLETE_HOLD"
        state["error_code"]=str(exc)[:300]
    write_atomic(manifest,state)
    return state

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--risks",type=Path,required=True)
    p.add_argument("--first-dir",type=Path,required=True)
    p.add_argument("--second-dir",type=Path,required=True)
    p.add_argument("--output-dir",type=Path)
    p.add_argument("--launch-id",default="dry")
    p.add_argument("--live",action="store_true")
    args=p.parse_args()
    audit=json.loads(args.risks.read_text(encoding="utf-8"))
    first=json.loads((args.first_dir/"task_001.json").read_text(encoding="utf-8"))
    first_m=json.loads((args.first_dir/"manifest.json").read_text(encoding="utf-8"))
    second=json.loads((args.second_dir/"task_002.json").read_text(encoding="utf-8"))
    second_m=json.loads((args.second_dir/"manifest.json").read_text(encoding="utf-8"))
    previous=prepare(
        audit=audit,original_one=first,manifest_one=first_m,
        original_two=second,manifest_two=second_m)
    if not args.live:
        print(json.dumps({
            "mode":"NO_PROVIDER_CALL",
            "source_prose_sha256":audit["source_prose_sha256"],
            "paid_tasks_reused":[x["task_id"] for x in previous],
            "new_target":TASK,
            "output_token_limit":"NOT_SET_BY_APPLICATION",
            "canonical_commit_authorized":False,
        },ensure_ascii=False,indent=2))
        return
    if args.output_dir is None:
        p.error("--live requires --output-dir")
    out=run(
        audit=audit,first=first,first_manifest=first_m,
        second=second,second_manifest=second_m,
        output_dir=args.output_dir,launch_id=args.launch_id,
        key=os.getenv("OPENROUTER_API_KEY",""))
    print(json.dumps({
        "status":out["status"],"completed_tasks":out["completed_tasks"],
        "pending_tasks":out["pending_tasks"],
        "new_provider_calls":out["new_provider_calls"],
        "new_provider_reported_cost_usd":out["new_provider_reported_cost_usd"],
        "error_code":out["error_code"],
        "canonical_commit_authorized":False,
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
