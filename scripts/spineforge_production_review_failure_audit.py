"""Offline audit of an admitted plan followed by invalid legacy review grounding."""
import json
import hashlib
from decimal import Decimal
from pathlib import Path
from src.spineforge_relay_v1_contracts import canonical_sha256
from src.spineforge_relay_v1_compile import _value_at
from src.spineforge_seeded_design import verify_frozen_seed,SeededStoryDesignV2,validate_seeded_design
from src.spineforge_story_design import StoryRequestV1
from src.spineforge_production_compact_v3 import CompactStoryPlanV3,compile_compact_v3
from src.spineforge_production_pipeline import validate_review
from src.model_registry import normalize_openrouter_request

def verify_review_failure(root,authority):
    root=Path(root)
    def read(name): return json.loads((root/name).read_text(encoding="utf8"))
    def require(value,reason):
        if not value: raise RuntimeError("Saved review failure mismatch: "+reason)
    pf,result=read("preflight.json"),read("result.json")
    for row in pf["sources"]:
        require(hashlib.sha256((root/"frozen-sources"/row["path"]).read_bytes()).hexdigest()==row["sha256"],"frozen source")
    for row,name in zip(pf["inputs"],["request-input.json","seed-input.json","frozen-seed.json","run-config.json"]):
        require(hashlib.sha256((root/name).read_bytes()).hexdigest()==row["sha256"],"frozen input")
    request=StoryRequestV1.model_validate_json((root/"request-input.json").read_bytes())
    seed=verify_frozen_seed(root/"seed-input.json",root/"frozen-seed.json")
    require(canonical_sha256(request)==pf["request_sha256"] and canonical_sha256(seed)==pf["seed_sha256"],"identity")
    require(result["status"]=="REJECT_NON_CONVERGENT" and result["phase"]=="planning" and result["reason"]=="FAILED_CLOSED_NO_RETRY" and result["failure_type"]=="ValueError","decision")
    require(result["provider_calls"]==2 and result["usage_complete"] is True and result["automatic_retry"] is False and len(result["ledger"])==2,"bounded dispatch")
    cost=Decimal("0");tokens=0;latency=0;texts=[]
    for count,(stage,ledger) in enumerate(zip(["planner","plan_guard"],result["ledger"]),1):
        prefix="plan-1-"+stage
        require(ledger==read(prefix+"-ledger.json") and ledger["stage"]==stage and ledger["attempt"]==1 and ledger["status"]=="COMPLETE","ledger")
        kwargs=read(f"transport-captures/dispatch-{count}-input.json");require("api_key" not in kwargs,"credential")
        expected=normalize_openrouter_request(kwargs["model"],dict(model=kwargs["model"],messages=[dict(role="system",content=kwargs["system_prompt"]),dict(role="user",content=kwargs["user_prompt"])],temperature=kwargs["temperature"],max_tokens=kwargs["max_tokens"]),request_class=kwargs["request_class"],structured_output=False)
        expected["response_format"]=kwargs["response_format"];expected["provider"]={**expected.get("provider",{}),"require_parameters":True}
        require(expected==read(prefix+"-request.json")==read(f"transport-captures/dispatch-{count}-request.json") and canonical_sha256(expected)==ledger["request_sha256"],"request")
        body=read(prefix+"-response.json");require(body==read(f"transport-captures/dispatch-{count}-response.json") and body["choices"][0]["finish_reason"]=="stop","response")
        text=read(prefix+"-text.json")["text"];require(text==body["choices"][0]["message"]["content"],"text");texts.append(text)
        usage=body["usage"]
        require(all(type(usage[k]) is int and usage[k]>=0 for k in ["prompt_tokens","completion_tokens","total_tokens"]),"integer usage")
        require(usage["total_tokens"]==usage["prompt_tokens"]+usage["completion_tokens"] and (ledger["input_tokens"],ledger["output_tokens"],ledger["total_tokens"])==(usage["prompt_tokens"],usage["completion_tokens"],usage["total_tokens"]),"usage")
        charge=Decimal(str(usage["cost"]));require(charge.is_finite() and charge>=0 and charge==Decimal(str(ledger["cost_usd"])) and ledger["latency_seconds"]>0,"charge")
        cost+=charge;tokens+=usage["total_tokens"];latency+=ledger["latency_seconds"]
    compact=CompactStoryPlanV3.model_validate_json(texts[0]);design=SeededStoryDesignV2.model_validate(read("plan-1-expanded-design.json"))
    require(compact.model_dump(mode="json")==read("plan-1-compact.json") and compile_compact_v3(request,seed,compact)==design,"expanded proposal")
    require(design.fixture==read("plan-1-fixture.json") and validate_seeded_design(request,seed,design,root/"plan-1-fixture.json")==read("plan-1-structural.json"),"structural pass")
    review=json.loads(texts[1])
    try: validate_review(review,request,seed,design)
    except ValueError as exc: require(str(exc)=="Ungrounded semantic plan finding","legacy rejection")
    else: raise RuntimeError("Saved review failure mismatch: invalid review accepted")
    missing=sum(not _value_at(design.model_dump(mode="json"),f["design_pointer"])[0] for f in review["findings"])
    require(missing==len(review["findings"]) and review["decision"]=="REWRITE","invalid pointers")
    require(not (root/"story").exists() and not (root/"accepted-design.json").exists() and not list(root.glob("plan-2-*")),"no repair/downstream")
    for name,digest in read("manifest.json")["files"].items(): require(hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,"inventory")
    closed=json.loads(Path(authority).read_text(encoding="utf8"));scope=closed["grant"]["scopes"][0];reservation=closed["reservations"][scope["id"]]
    require(closed["status"]=="CLOSED" and reservation["status"]=="SETTLED" and scope["preflight_sha256"]==canonical_sha256(pf)==reservation["preflight_sha256"],"closed scope")
    require(reservation["actual_calls"]==2 and Decimal(reservation["actual_cost_usd"])==cost==Decimal(str(result["known_cost_usd"])),"settlement")
    return dict(status="OFFLINE_REVIEW_FAILURE_AUDIT_PASS",provider_calls=2,cost_usd=str(cost),total_tokens=tokens,latency_seconds=round(latency,3),
        plan_structural_status="PASS",review_raw_decision="REWRITE",invalid_source_pointers=missing,review_admitted=False,
        plan_rewrite_dispatches=0,story_generated=False,state_advanced=False,no_retry=True,authority_status="CLOSED",reservation_status="SETTLED",seed_sha256=canonical_sha256(seed))
