"""Offline evidence recovery for the first already-paid Haiku probe.

Only a complete fenced JSON object and unique typographic apostrophe
equivalence can be repaired, with full raw/source provenance.
No new model calls, entity creation or state approval.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_haiku_probes_v011 import qualify_source, MODEL
from experiments.sera.semantic_risks_v011 import make_task_request, bind_task_response

LAUNCH="sera-v011-haiku-38863339302"
TASK="task_001"
REQUEST_SHA="e0fd233de02cd8a7a7d24c7bfae1b1d91b1b676504255a4272eb8049096b8489"
RESPONSE_ID="gen-1792133339-aMZqjZ7FiMSO96EzJeOI"
FENCE=re.compile(r"\A[ \t]*\x60{3}(?:json)?[ \t]*\r?\n(.*?)\r?\n\x60{3}[ \t\r\n]*\Z",re.S|re.I)

def require(condition,code):
    if not condition:
        raise CoverageError(code)

def parse_json_model_reply(text:str) -> tuple[dict,str]:
    """No prefixed/suffixed chatter; exact single object required."""
    require(isinstance(text,str) and text.strip(),"PROBE_CONTENT_REQUIRED")
    try:
        obj=json.loads(text)
        envelope="RAW_JSON"
    except json.JSONDecodeError:
        match=FENCE.fullmatch(text)
        require(match is not None,"PROBE_UNSAFE_NONJSON_ENVELOPE")
        try:
            obj=json.loads(match.group(1))
        except ValueError:
            raise CoverageError("PROBE_FENCED_JSON_MALFORMED") from None
        envelope="FULL_JSON_CODE_FENCE"
    require(isinstance(obj,dict),"PROBE_JSON_OBJECT_REQUIRED")
    return obj,envelope

def fold(s:str) -> str:
    # Length preserving: do NOT perform fuzzy-match or silent truth repair.
    return (s.replace("’","'").replace("‘","'")
            .replace("“",'"').replace("”",'"'))

def source_quote_repair(*,task:dict,proposed_quote:str) -> tuple[str,str]:
    require(isinstance(proposed_quote,str) and proposed_quote.strip(),
            "PROBE_EVIDENCE_REQUIRED")
    exact=[]
    equivalent=[]
    for sentence in task["exact_source_context"]:
        source=sentence["quote"]
        start=0
        while True:
            pos=source.find(proposed_quote,start)
            if pos<0:break
            exact.append(source[pos:pos+len(proposed_quote)])
            start=pos+1
        folded=fold(source)
        start=0
        while True:
            pos=folded.find(fold(proposed_quote),start)
            if pos<0:break
            candidate=source[pos:pos+len(proposed_quote)]
            if candidate!=proposed_quote and fold(candidate)==fold(proposed_quote):
                equivalent.append(candidate)
            start=pos+1
    if exact:
        return proposed_quote,"EXACT"
    require(len(equivalent)==1,"PROBE_TYPOGRAPHIC_MATCH_NOT_UNIQUE")
    method=("TYPOGRAPHIC_DOUBLE_QUOTES_EQUIVALENCE_UNVERIFIED"
            if any(c in equivalent[0] for c in ("“","”"))
            else "TYPOGRAPHIC_APOSTROPHE_EQUIVALENCE_UNVERIFIED")
    return equivalent[0],method

def recover_model_task(*,risk_audit:dict,task_id:str,
                       raw_provider_content:str) -> dict:
    qualify_source(risk_audit)
    task=next((t for t in risk_audit["targeted_tasks"]
               if t["task_id"]==task_id),None)
    require(task is not None,"PROBE_TASK_UNKNOWN")
    raw,envelope=parse_json_model_reply(raw_provider_content)
    require("evidence_quote" in raw,"PROBE_EVIDENCE_QUOTE_MISSING")
    exact_quote,method=source_quote_repair(
        task=task,proposed_quote=raw["evidence_quote"])
    repaired=deepcopy(raw)
    repaired["evidence_quote"]=exact_quote
    request=make_task_request(audit=risk_audit,task_id=task_id)
    bound=bind_task_response(audit=risk_audit,request=request,raw=repaired)
    return {
        "schema":"sera.haiku-advisory-recovery.v0.11.1",
        "task_id":task_id,
        "source_prose_sha256":risk_audit["source_prose_sha256"],
        "request_sha256_in_current_binder":request["request_sha256"],
        "raw_provider_content_sha256":sha256(
            raw_provider_content.encode("utf-8")).hexdigest(),
        "provider_content_envelope":envelope,
        "original_model_evidence_quote":raw["evidence_quote"],
        "exact_source_evidence_quote":exact_quote,
        "quote_binding_method":method,
        "unmodified_proposed_semantics":{
            key:raw[key] for key in ("verdict","operation_kind","effect","reason")
        },
        "bound_advisory":bound,
        "model_calls_during_recovery":0,
        "human_adjudicated":False,
        "canonical_commit_authorized":False,
        "world_db_writes":0,
        "status":"RECOVERED_ADVISORY_SOURCE_BOUND_SEMANTIC_HOLD",
    }

def recover_historical_first(*,audit:dict,task_artifact:dict,
                             manifest:dict) -> dict:
    qualify_source(audit)
    require(isinstance(manifest,dict) and
            manifest.get("schema")=="sera.mara-s1-independent-haiku-probes.v0.11" and
            manifest.get("launch_id")==LAUNCH and
            manifest.get("provider_attempts")==1 and
            manifest.get("reviewed_task_ids")==[] and
            manifest.get("pending_task_ids")==[
                "task_001","task_002","task_003"] and
            manifest.get("canonical_commit_authorized") is False,
            "PROBE_HISTORICAL_MANIFEST_MISMATCH")
    require(isinstance(task_artifact,dict) and
            task_artifact.get("task_id")==TASK and
            task_artifact.get("request_sha256")==REQUEST_SHA and
            task_artifact.get("provider_response_id")==RESPONSE_ID and
            task_artifact.get("model_requested")==MODEL and
            task_artifact.get("observed_model")==MODEL and
            task_artifact.get("finish_reason")=="stop" and
            task_artifact.get("provider_reported_cost")==0.001252 and
            task_artifact.get("canonical_commit_authorized") is False,
            "PROBE_HISTORICAL_RESPONSE_NOT_PINNED")
    request=make_task_request(audit=audit,task_id=TASK)
    require(request["request_sha256"]==REQUEST_SHA,
            "PROBE_HISTORICAL_REQUEST_BINDING_MISMATCH")
    recovered=recover_model_task(
        risk_audit=audit,task_id=TASK,
        raw_provider_content=task_artifact.get("raw_content"))
    recovered["historical_launch_id"]=LAUNCH
    recovered["historical_model_requested"]=MODEL
    recovered["historical_provider_response_id"]=RESPONSE_ID
    recovered["historical_provider_reported_cost"]=0.001252
    return recovered
