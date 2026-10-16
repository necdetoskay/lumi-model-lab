"""SERA v0.11 — 3 isolated Haiku semantic probe calls, full evidence, no canon.

Reuses actual Mara v0.10 offline semantic risk audit. Blind independent
Haiku only sees exact source sentences and neutral questions, not Gemini's
answers. Up to three actual provider calls; stop on first failure / missing
cost / observed USD spend guard; persist original raw response and HOLD.

No output token ceilings. No Writer regeneration, DB, JEV or story commits.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import argparse
import json
import os
from pathlib import Path

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_typed_live_v05 import one_provider_call
from experiments.sera.mara_s1_v04_audit import EXPECTED_SHA
from experiments.sera.semantic_risks_v011 import (
    SCHEMA, make_task_request, bind_task_response,
)

MODEL = "anthropic/claude-haiku-4.5"
MAX_PROVIDER_ATTEMPTS = 3
USD_OBSERVED_SPEND_STOP = Decimal("0.08")
MIN_KEY_REMAINING = 0.25


def require(flag,code):
    if not flag:
        raise CoverageError(code)


def qualify_source(data: dict) -> dict:
    require(isinstance(data,dict) and data.get("schema")==SCHEMA and
            data.get("source_prose_sha256")==EXPECTED_SHA and
            data.get("candidate_event_count")==25 and
            data.get("targeted_task_count")==MAX_PROVIDER_ATTEMPTS and
            data.get("automatic_state_writes")==0 and
            data.get("canonical_commit_authorized") is False and
            [x["task_id"] for x in data["targeted_tasks"]]==[
                "task_001","task_002","task_003"
            ],"V011_PROBE_SOURCE_NOT_PINNED")
    required_prefixes=(
        "MOVE_KIND_EFFECT_MISMATCH:",
        "DOCUMENT_APPEND_MISREAD_AS_SPEECH:",
        "OPENABLE_BEFORE_CLOSE_NEEDS_TYPED_ASPECT:",
    )
    require(all(any(x["finding_code"].startswith(prefix)
                    for x in data["targeted_tasks"])
                for prefix in required_prefixes),
            "V011_REQUIRED_DIAGNOSTIC_TASK_MISSING")
    return data


def write_atomic(path:Path,obj:dict)->None:
    temp=path.with_suffix(path.suffix+".stage")
    temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",
                    encoding="utf-8")
    temp.replace(path)


def run(*, evidence:dict, output_dir:Path, launch_id:str,
        key:str)->dict:
    qualify_source(evidence)
    require(not output_dir.exists(),"V011_OUTPUT_EXISTS")
    output_dir.mkdir(parents=True,exist_ok=False)
    state={
        "schema":"sera.mara-s1-independent-haiku-probes.v0.11",
        "launch_id":launch_id,
        "source_prose_sha256":EXPECTED_SHA,
        "model_requested":MODEL,
        "reviewed_task_ids":[],
        "pending_task_ids":[x["task_id"] for x in
                            evidence["targeted_tasks"]],
        "max_provider_attempts":MAX_PROVIDER_ATTEMPTS,
        "provider_attempts":0,
        "provider_reported_cost_usd":0.0,
        "status":"PREFLIGHT_HOLD",
        "error_code":None,
        "model_output_token_cap_configured":False,
        "paid_calls_authorize_canonical_truth":False,
        "world_db_writes":0,
        "canonical_commit_authorized":False,
    }
    manifest=output_dir/"manifest.json"
    write_atomic(manifest,state)
    try:
        if not key:
            raise CoverageError("V011_KEY_MISSING")
        from src.openrouter_preflight import (
            fetch_key_status,enforce_key_access,
        )
        enforce_key_access(
            fetch_key_status(key),min_remaining=MIN_KEY_REMAINING,
        )
        observed=Decimal("0")
        for task in evidence["targeted_tasks"]:
            require(state["provider_attempts"]<MAX_PROVIDER_ATTEMPTS,
                    "V011_CALL_COUNT_EXCEEDED")
            if observed>=USD_OBSERVED_SPEND_STOP:
                raise CoverageError("V011_SPEND_GUARD_REACHED")
            request=make_task_request(
                audit=evidence,task_id=task["task_id"]
            )
            item={
                "task_id":task["task_id"],
                "request_sha256":request["request_sha256"],
                "source_prose_sha256":EXPECTED_SHA,
                "model_requested":MODEL,
                "provider_attempted":True,
                "provider_usage":None,
                "provider_reported_cost":None,
                "raw_content":None,
                "raw_model_output":None,
                "bound_advisory_result":None,
                "status":"ATTEMPTING",
                "canonical_commit_authorized":False,
            }
            path=output_dir/(task["task_id"]+".json")
            write_atomic(path,item)
            state["provider_attempts"]+=1
            state["status"]="IN_PROGRESS_MODEL_PROBES"
            write_atomic(manifest,state)
            response=one_provider_call(
                key=key,model=MODEL,
                prepared={"request":{
                    "messages":request["messages"],
                    "response_format":request["response_format"],
                }},
            )
            if response["error"]:
                item["status"]="PROVIDER_ERROR_HOLD"
                item["error_code"]=response["error"]
                item["provider_detail"]=response.get("provider_detail")
                write_atomic(path,item)
                raise CoverageError(
                    f"V011_PROVIDER_ERROR:{task['task_id']}:{response['error']}"
                )
            body=response["raw"]
            item["provider_response_id"]=body.get("id")
            item["observed_model"]=body.get("model")
            item["provider_usage"]=body.get("usage")
            if isinstance(body.get("usage"),dict):
                item["provider_reported_cost"]=body["usage"].get("cost")
            choices=body.get("choices")
            if not isinstance(choices,list) or len(choices)!=1:
                raise CoverageError("V011_PROVIDER_CHOICES_INVALID")
            choice=choices[0]
            item["finish_reason"]=choice.get("finish_reason")
            item["raw_content"]=(choice.get("message") or {}).get("content")
            write_atomic(path,item)
            if item["provider_reported_cost"] is None:
                raise CoverageError("V011_COST_UNREPORTED_STOP")
            try:
                actual=Decimal(str(item["provider_reported_cost"]))
            except InvalidOperation:
                raise CoverageError("V011_COST_INVALID") from None
            require(actual.is_finite() and actual>=0,"V011_COST_INVALID")
            observed+=actual
            state["provider_reported_cost_usd"]=float(observed)
            if item["finish_reason"]!="stop":
                raise CoverageError("V011_INCOMPLETE_PROVIDER_RESPONSE")
            if not isinstance(item["raw_content"],str):
                raise CoverageError("V011_CONTENT_INVALID")
            try:
                raw=json.loads(item["raw_content"])
            except ValueError:
                raise CoverageError("V011_JSON_INVALID") from None
            item["raw_model_output"]=raw
            write_atomic(path,item)
            bounded=bind_task_response(
                audit=evidence,request=request,raw=raw,
            )
            item["bound_advisory_result"]=bounded
            item["status"]="MODEL_SOURCE_BOUND_BUT_NOT_AUTHORITY"
            write_atomic(path,item)
            state["reviewed_task_ids"].append(task["task_id"])
            state["pending_task_ids"].remove(task["task_id"])
            write_atomic(manifest,state)
        state["status"]="ALL_TARGETED_PROBES_RETURNED_SEMANTIC_HOLD"
    except Exception as exc:
        state["status"]="PROBE_ERROR_OR_INCOMPLETE_HOLD"
        state["error_code"]=str(exc)[:300]
    write_atomic(manifest,state)
    return state


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",required=True,type=Path)
    p.add_argument("--output-dir",type=Path)
    p.add_argument("--live",action="store_true")
    p.add_argument("--launch-id",default="dry-run")
    args=p.parse_args()
    evidence=qualify_source(
        json.loads(args.evidence.read_text(encoding="utf-8"))
    )
    if not args.live:
        print(json.dumps({
            "mode":"DRY_RUN_NO_PROVIDER_CALL",
            "source_prose_sha256":EXPECTED_SHA,
            "independent_model":MODEL,
            "tasks":[x["finding_code"] for x in evidence["targeted_tasks"]],
            "max_provider_attempts":MAX_PROVIDER_ATTEMPTS,
            "output_token_limit":"NOT_SET_BY_APPLICATION",
            "canonical_commit_authorized":False,
        },ensure_ascii=False,indent=2))
        return
    if args.output_dir is None:
        p.error("--live requires --output-dir")
    result=run(
        evidence=evidence,output_dir=args.output_dir,
        launch_id=args.launch_id,
        key=os.getenv("OPENROUTER_API_KEY",""),
    )
    print(json.dumps({
        "status":result["status"],
        "provider_attempts":result["provider_attempts"],
        "provider_reported_cost_usd":result["provider_reported_cost_usd"],
        "reviewed_task_ids":result["reviewed_task_ids"],
        "pending_task_ids":result["pending_task_ids"],
        "error_code":result.get("error_code"),
        "canonical_commit_authorized":False,
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
