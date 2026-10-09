"""Q5T: apply the qualified SFR-v1 semantic guard to the Sol SC01 candidate."""
from __future__ import annotations
import hashlib, json, time
from pathlib import Path
from typing import Any, Callable

from src.generate import OpenRouterCallError
from src.model_registry import normalize_openrouter_request, require_qualification_runtime_profile, runtime_profile_identity
from src.spineforge_relay_v1_guard import (
    SEMANTIC_GUARD_RESPONSE_SCHEMA, build_semantic_guard_input,
    deterministic_scene_findings, normalize_semantic_guard,
)
from src.spineforge_relay_v1_q5_sol import build_inputs as build_sol_inputs
from src.spineforge_v19_transport import call_strict_json_once
from src.spineforge_v21_model_adapter import provider_usage
from src.spineforge_v6_json_schema import build_json_schema_response_format

MODEL="anthropic/claude-sonnet-5.5"
REQUEST_CLASS="spineforge_relay_v1_scene_guard"
AUTH_SCOPE="SFR_V1_Q5T_SOL_SC01_GUARD_ONE_CALL"
SCHEMA_NAME="spineforge_relay_scene_guard_v1"
PROMPT=Path("prompts/spineforge_relay_v1_scene_guard.md")
SOURCE_RESULT=Path("evidence/spineforge-relay/SFR-V1-Q5S-PAID-20261007/result.json")
DEFAULT_OUTPUT=Path("evidence/spineforge-relay/SFR-V1-Q5T-PREFLIGHT-20261007")
MAX_TOKENS=2500
MAX_COST_USD=0.05
GuardCall=Callable[..., tuple[dict[str,Any],dict[str,Any],dict[str,Any],list[dict[str,Any]]]]

def _sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()

def build_inputs():
    src=json.loads(SOURCE_RESULT.read_text(encoding="utf-8"))
    prose=str((src.get("candidate") or {}).get("prose") or "")
    if not prose: raise RuntimeError("Q5T source prose missing")
    _wi,state,_plan,_route,contract=build_sol_inputs()
    det=deterministic_scene_findings(prose=prose,contract=contract)
    payload=build_semantic_guard_input(state=state,contract=contract,prose=prose,deterministic_findings=det)
    return payload,state,contract,prose,det

def request_payload(inp):
    req=normalize_openrouter_request(
        MODEL,{"model":MODEL,"messages":[
            {"role":"system","content":PROMPT.read_text(encoding="utf-8").strip()},
            {"role":"user","content":json.dumps(inp,ensure_ascii=False,separators=(",",":"))},
        ],"temperature":0.0,"max_tokens":MAX_TOKENS},
        request_class=REQUEST_CLASS,structured_output=False,
    )
    req["response_format"]=build_json_schema_response_format(name=SCHEMA_NAME,schema=SEMANTIC_GUARD_RESPONSE_SCHEMA)
    provider=dict(req.get("provider") or {}); provider["require_parameters"]=True; req["provider"]=provider
    return req

def prepare(out:Path=DEFAULT_OUTPUT):
    profile=require_qualification_runtime_profile(MODEL)
    inp,state,contract,prose,det=build_inputs()
    req=request_payload(inp)
    pricing=(profile.get("metadata") or {}).get("pricing_usd_per_million_tokens") or {}
    ib=len(json.dumps(req,ensure_ascii=False).encode("utf-8"))
    planned=round(ib*float(pricing.get("input",0))/1_000_000+MAX_TOKENS*float(pricing.get("output",0))/1_000_000,6)
    out.mkdir(parents=True,exist_ok=True)
    (out/"guard-input.json").write_text(json.dumps(inp,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    report={
      "schema":"spineforge-relay.q5t-preflight.v1","status":"OFFLINE_PREPARED_PAID_NOT_AUTHORIZED",
      "model":MODEL,"request_class":REQUEST_CLASS,"model_runtime_profile":runtime_profile_identity(MODEL),
      "source_result_sha256":_sha(SOURCE_RESULT),"candidate_prose_sha256":hashlib.sha256(prose.encode()).hexdigest(),
      "story_state_revision":state.revision,"scene_id":contract.scene_id,
      "deterministic_blocking_count":len([x for x in det if x.severity=="BLOCKING"]),
      "request":req,"request_sha256":hashlib.sha256(json.dumps(req,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
      "planned_uncached_cost_usd":planned,"proposed_max_cost_usd":MAX_COST_USD,
      "max_guard_calls":1,"automatic_retry":False,"rewrite_authorized":False,
      "state_application_authorized":False,"paid_execution_authorized":False,
      "files":[{"path":str(p),"sha256":_sha(p)} for p in [
        Path(__file__).relative_to(Path.cwd()),Path("src/spineforge_relay_v1_guard.py"),
        Path("src/spineforge_relay_v1_q5_sol.py"),PROMPT,SOURCE_RESULT,Path("configs/model_runtime_profiles.yaml")]],
    }
    report["artifact_sha256"]=hashlib.sha256(json.dumps(report,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    (out/"preflight.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return report

def verify(p=DEFAULT_OUTPUT/"preflight.json",i=DEFAULT_OUTPUT/"guard-input.json"):
    report=json.loads(Path(p).read_text(encoding="utf-8")); saved=report.pop("artifact_sha256")
    if hashlib.sha256(json.dumps(report,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()!=saved:
        raise RuntimeError("Q5T preflight integrity drift")
    report["artifact_sha256"]=saved
    for row in report["files"]:
        if _sha(Path(row["path"]))!=row["sha256"]: raise RuntimeError("Q5T dependency drift: "+row["path"])
    fresh,*_=build_inputs()
    if json.loads(Path(i).read_text(encoding="utf-8"))!=fresh: raise RuntimeError("Q5T guard input drift")
    if report["request"]!=request_payload(fresh): raise RuntimeError("Q5T request drift")
    return report

def execute_once(*,api_key:str,run_id:str,authorization:dict[str,Any],
                 preflight_path=DEFAULT_OUTPUT/"preflight.json",guard_input_path=DEFAULT_OUTPUT/"guard-input.json",
                 output_root=Path("evidence/spineforge-relay/q5t-runs"),call_fn:GuardCall|None=None):
    pf=verify(preflight_path,guard_input_path)
    if not (authorization.get("paid_execution_authorized") is True and authorization.get("scope")==AUTH_SCOPE
      and authorization.get("preflight_sha256")==pf["artifact_sha256"] and authorization.get("max_cost_usd")==MAX_COST_USD
      and authorization.get("max_guard_calls")==1 and authorization.get("automatic_retry") is False
      and authorization.get("rewrite_authorized") is False and authorization.get("state_application_authorized") is False
      and authorization.get("explicit_user_message")):
        raise RuntimeError("Separate explicit SFR-v1 Q5T guard authorization required")
    output_root.mkdir(parents=True,exist_ok=True)
    claim=output_root/("authorization-"+hashlib.sha256(json.dumps(authorization,sort_keys=True,separators=(",",":")).encode()).hexdigest()+".claimed")
    claim.open("x").close(); out=output_root/run_id; out.mkdir(exist_ok=False)
    inp=json.loads(Path(guard_input_path).read_text(encoding="utf-8")); prose=inp["candidate_prose"]; req=pf["request"]
    ev={"status":"STARTED","api_calls":0,"automatic_retry_executed":False,"rewrite_authorized":False,"state_application_authorized":False,"usage":None}
    started=time.perf_counter()
    try:
        raw,body,actual,_=(call_fn or call_strict_json_once)(
          api_key=api_key,model=MODEL,system_prompt=req["messages"][0]["content"],user_prompt=req["messages"][1]["content"],
          temperature=0.0,max_tokens=MAX_TOKENS,seed=None,request_class=REQUEST_CLASS,schema_name=SCHEMA_NAME,schema=SEMANTIC_GUARD_RESPONSE_SCHEMA)
        ev["api_calls"]=1; ev["usage"]=provider_usage(body,"SFR_V1_Q5T_SOL_GUARD",time.perf_counter()-started)
        if actual!=req: raise RuntimeError("Q5T dispatched request differs from frozen preflight")
        if ev["usage"]["cost_usd"] is None or float(ev["usage"]["cost_usd"])>MAX_COST_USD: raise RuntimeError("Q5T cost missing or above ceiling")
        report=normalize_semantic_guard(raw=raw,prose=prose)
        blocking=[f.model_dump(mode="json") for f in report.findings if f.severity=="BLOCKING"]
        result={"decision":report.decision,"blocking_findings":blocking,"summary":report.summary}
        (out/"guard-report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        ev["status"]="GUARD_ACCEPT" if report.decision=="PASS" else "GUARD_REWRITE_REQUIRED"
        ev["decision"]=report.decision; ev["blocking_count"]=len(blocking)
    except Exception as exc:
        if isinstance(exc,OpenRouterCallError): ev["api_calls"]=1
        ev["status"]="STOPPED_NO_RETRY"; ev["failure_type"]=type(exc).__name__; ev["failure_message"]=str(exc)
    (out/"guard-call.json").write_text(json.dumps(ev,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return ev
