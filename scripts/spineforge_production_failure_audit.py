"""Offline audit of a first-planner failure without provider usage. No inference."""
import hashlib
import json
import re
from pathlib import Path
from src.spineforge_relay_v1_contracts import canonical_sha256
from src.model_registry import normalize_openrouter_request
from src.spineforge_seeded_design import verify_frozen_seed


def verify_failure(root,authority,baseline_commit):
    root=Path(root)
    if not re.fullmatch(r"[0-9a-f]{40}",baseline_commit):raise ValueError("Exact source commit required")
    def read(name):return json.loads((root/name).read_text(encoding="utf8"))
    def require(value,reason):
        if not value:raise RuntimeError("Saved failure evidence mismatch: "+reason)
    pf=read("preflight.json");result=read("result.json")
    for source in pf["sources"]:
        blob=(root/"frozen-sources"/source["path"]).read_bytes()
        require(hashlib.sha256(blob).hexdigest()==source["sha256"],"frozen source archive")
    for original,name in zip(pf["inputs"],["request-input.json","seed-input.json","frozen-seed.json","run-config.json"]):
        require(hashlib.sha256((root/name).read_bytes()).hexdigest()==original["sha256"],"frozen input")
    seed=verify_frozen_seed(root/"seed-input.json",root/"frozen-seed.json")
    require(canonical_sha256(seed)==pf["seed_sha256"],"seed identity")
    require(result["status"]=="REJECT_NON_CONVERGENT" and result["reason"]=="FAILED_CLOSED_NO_RETRY" and result["phase"]=="planning","failure decision")
    require(result["provider_calls"]==1 and result["usage_complete"] is False and result["automatic_retry"] is False,"dispatch/usage/retry")
    ledger=read("plan-1-planner-ledger.json")
    require(result["ledger"]==[ledger] and ledger["status"]=="FAILED_NO_RETRY" and ledger["cost_usd"] is None,"failed ledger")
    kwargs=read("transport-captures/dispatch-1-input.json")
    require("api_key" not in kwargs,"credential omitted")
    request=normalize_openrouter_request(kwargs["model"],dict(model=kwargs["model"],messages=[dict(role="system",content=kwargs["system_prompt"]),dict(role="user",content=kwargs["user_prompt"])],temperature=kwargs["temperature"],max_tokens=kwargs["max_tokens"]),request_class=kwargs["request_class"],structured_output=False)
    request["response_format"]=kwargs["response_format"];request["provider"]={**request.get("provider",{}),"require_parameters":True}
    require(request==read("plan-1-planner-request.json") and canonical_sha256(request)==ledger["request_sha256"],"attempted request")
    require(not list(root.rglob("*-response.json")) and not (root/"story").exists() and not (root/"accepted-design.json").exists(),"no response or downstream story")
    failure=read("transport-captures/dispatch-1-failure.json")
    require(failure["failure_type"]=="OpenRouterCallError" and failure["automatic_retry"] is False,"transport failure")
    require(not list(root.glob("plan-2-*")),"no retry/rewrite")
    for name,digest in read("manifest.json")["files"].items():require(hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,"raw inventory")
    closed=json.loads(Path(authority).read_text())
    require(closed["status"]=="CLOSED","closed authority")
    scope=closed["grant"]["scopes"][0]
    require(scope["preflight_sha256"]==canonical_sha256(pf) and closed["reservations"][scope["id"]]["status"]=="UNCERTAIN","unknown usage retained")
    return dict(status="OFFLINE_FAILURE_AUDIT_PASS",baseline_commit=baseline_commit,source_verification="Archived bytes match approved preflight SHA-256; no Git history required",seed_sha256=canonical_sha256(seed),
        attempted_provider_dispatches=1,complete_provider_responses=0,actual_cost_usd=None,usage_complete=False,
        authority_status="CLOSED",reservation_status="UNCERTAIN",held_scope_cost_usd=closed["grant"]["max_cost_usd"],
        no_retry=True,plan_generated=False,story_generated=False,original_http_cause_known=False,
        recorded_json_instruction_present=any("json" in m["content"].lower() for m in request["messages"]),
        files={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file() and p.name!="failure-audit.json"})
