"""Automatic scene identity stage v0.16.

One invocation owns generation, recovery, targeted repair, verification,
and fail-closed disposition. The stage never writes a canonical world.
No output token ceiling is configured.
"""
from __future__ import annotations

import json
from pathlib import Path

from experiments.sera.coverage import CoverageError
from experiments.sera.blind_identity_v015 import make_request
from experiments.sera.identity_auto_repair_v016 import repair

def persist(path,data):
    tmp=path.with_suffix(".pending")
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",
                   encoding="utf-8")
    tmp.replace(path)

def execute(*,prose,world,census,call_model,output_dir,
            primary_model="anthropic/claude-haiku-4.5",
            repair_model="anthropic/claude-haiku-4.5",
            repair_calls_allowed=4):
    """call_model(model=...,prepared={'request':...}) -> OpenRouter envelope."""
    if output_dir.exists():
        raise CoverageError("V016_STAGE_OUTPUT_EXISTS")
    request=make_request(prose=prose,world=world,census=census)
    output_dir.mkdir(parents=True,exist_ok=False)
    ledger=[]
    used={"primary":0,"targeted":0}
    def note(item):
        ledger.append(item)
        persist(output_dir/"ledger.json",ledger)
    def model_call(*,model,messages,ref):
        kind="primary" if ref=="ALL" else "targeted"
        note({"stage":"REQUEST_STARTED","kind":kind,"ref":ref})
        used[kind]+=1
        answer=call_model(model=model,prepared={"request":{
            "messages":messages,"response_format":{"type":"json_object"},
        }})
        if answer.get("error"):
            raise CoverageError("V016_PROVIDER_ERROR:"+str(answer["error"]))
        body=answer.get("raw")
        if not isinstance(body,dict):
            raise CoverageError("V016_PROVIDER_BODY_INVALID")
        choices=body.get("choices")
        if not isinstance(choices,list) or len(choices)!=1:
            raise CoverageError("V016_PROVIDER_CHOICE_INVALID")
        text=(choices[0].get("message") or {}).get("content")
        receipt={"ref":ref,"model":body.get("model"),"id":body.get("id"),
                 "usage":body.get("usage"),
                 "finish_reason":choices[0].get("finish_reason"),
                 "raw_content":text}
        persist(output_dir/("primary.json" if ref=="ALL" else
                            "targeted_"+ref.replace(":","_")+".json"),receipt)
        note({"stage":"RAW_RESPONSE_SAVED","ref":ref})
        if choices[0].get("finish_reason")!="stop" or not isinstance(text,str):
            raise CoverageError("V016_PROVIDER_INCOMPLETE")
        return text
    summary={"schema":"sera.identity-stage.v0.16",
             "status":"STARTED","primary_calls":0,"targeted_calls":0,
             "result":None,"error":None,"canonical_commit_authorized":False,
             "world_db_writes":0}
    persist(output_dir/"result.json",summary)
    try:
        original=model_call(model=primary_model,
                            messages=request["messages"],ref="ALL")
        def targeted(task):
            if used["targeted"]>=repair_calls_allowed:
                raise CoverageError("V016_TARGETED_CALL_LIMIT")
            return model_call(model=repair_model,messages=task["messages"],
                              ref=task["target_ref"])
        summary["result"]=repair(
            prose=prose,world=world,census=census,
            raw_provider_content=original,
            model_repair=targeted if repair_calls_allowed else None,
            max_targeted_calls=repair_calls_allowed,
            checkpoints=note)
        summary["status"]="AUTO_REPAIR_FINISHED_NONCANONICAL_HOLD"
    except Exception as exc:
        summary["status"]="AUTO_REPAIR_FAILED_SAFE_HOLD"
        summary["error"]=str(exc)[:300]
    summary["primary_calls"]=used["primary"]
    summary["targeted_calls"]=used["targeted"]
    persist(output_dir/"result.json",summary)
    return summary
