"""Generic frozen-request/seed -> design -> reviewed plan -> story runner.

No scenario names or narratives are executable branches. Shared admission owns
all provider dispatch, including calls after dynamically produced plans.
"""
from __future__ import annotations
import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any,Literal
from pydantic import Field,model_validator
from src.spineforge_relay_v1_contracts import StrictModel,canonical_sha256
from src.spineforge_relay_v1_compile import _value_at
from src.spineforge_seeded_design import verify_frozen_seed,seeded_planner_input,SeededStoryDesignV2,validate_seeded_design
from src.spineforge_story_design import StoryRequestV1
from src.spineforge_production_compact_v3 import compact_planner_input_v3, CompactStoryPlanV3, compile_compact_v3
from src.spineforge_production_plan_review_v2 import build_review_input,bind_review
from src.spineforge_production_config import RunConfigV1
from src.model_registry import require_qualification_runtime_profile,normalize_openrouter_request
from src.spineforge_relay_v1_q5t import save
from src import spineforge_production_compact_range_story as engine
from scripts.spineforge_production_compact_range_replay import verify_story


class PlanFindingV1(StrictModel):
    design_pointer: str=Field(pattern=r"^/.+")
    source_value: Any
    reason: str=Field(min_length=1)
    repair_instruction: str=Field(min_length=1)


class PlanReviewV1(StrictModel):
    request_sha256: str
    seed_sha256: str
    design_sha256: str
    decision: Literal["PASS","REWRITE"]
    findings: list[PlanFindingV1]
    summary: str=Field(min_length=1)

    @model_validator(mode="after")
    def check(self):
        if (self.decision=="PASS") != (not self.findings):raise ValueError("Review decision/findings disagree")
        return self


def prepare(request_path,seed_path,freeze_path,config_path):
    request=StoryRequestV1.model_validate_json(Path(request_path).read_bytes())
    seed=verify_frozen_seed(Path(seed_path),Path(freeze_path))
    config=RunConfigV1.model_validate_json(Path(config_path).read_bytes())
    for model in config.models():require_qualification_runtime_profile(model)
    paths=set(Path("src").glob("spineforge_relay_v1*.py"))
    paths.update(Path("src").glob("spineforge_production*.py"))
    paths.update(Path("prompts").glob("spineforge_relay_v1*.md"))
    paths.update(Path("prompts").glob("spineforge_production*.md"))
    paths.update(Path("prompts").glob("spineforge_joint*.md"))
    paths.update(Path(p) for p in ["src/spineforge_seeded_design.py","src/spineforge_story_design.py",
        "src/spineforge_joint_spatial.py","src/spineforge_source_spans.py","src/spineforge_v19_transport.py",
        "src/model_registry.py","src/generate.py","src/spineforge_span_story_runner.py","src/spineforge_span_paid_entry.py",
        "scripts/spineforge_production_replay.py","scripts/spineforge_production_range_replay.py","scripts/spineforge_production_compact_range_replay.py","configs/model_runtime_profiles.yaml","requirements.txt",
        "prompts/spineforge_seeded_design.md","prompts/spineforge_story_design.md","prompts/spineforge_span_guard.md"])
    return dict(schema="spineforge.production-preflight.v1",request_sha256=canonical_sha256(request),
        seed_sha256=canonical_sha256(seed),config=config.model_dump(mode="json"),max_calls=4+4*request.scene_count,
        max_total_cost_usd=config.max_total_cost_usd,allowed_models=config.models(),automatic_retry=False,
        source_encoding="UTF-8 CRLF normalized to LF",sources=[dict(path=p.as_posix(),sha256=hashlib.sha256(p.read_bytes().replace(b"\r\n",b"\n")).hexdigest()) for p in sorted(paths)],
        inputs=[dict(path=Path(p).as_posix(),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest()) for p in (request_path,seed_path,freeze_path,config_path)],
        registry_branch="sfr-paid-reservations",production_write=False)


def request_for(stage,payload,config):
    model=config.planner if stage=="planner" else config.plan_guard
    prompt=payload["instructions"] if stage=="planner" else Path("prompts/spineforge_production_plan_guard_v2.md" if payload.get("schema")=="spineforge.plan-review-input.v2" else "prompts/spineforge_production_plan_guard.md").read_text(encoding="utf8")
    prompt += "\nReturn exactly one valid JSON object. Do not include Markdown fences or prose outside the JSON object."
    kwargs=dict(model=model,system_prompt=prompt,user_prompt=json.dumps(payload,ensure_ascii=False,separators=(",",":")),
        temperature=.3 if stage=="planner" else 0.,max_tokens=config.planner_max_tokens if stage=="planner" else config.plan_guard_max_tokens,
        seed=None,request_class="spineforge_relay_v1_production_"+stage,response_format={"type":"json_object"},require_parameters=True)
    if stage=="plan_guard" and payload.get("schema")=="spineforge.plan-review-input.v2":
        kwargs["response_format"]={"type":"json_schema","json_schema":{"name":"bound_plan_review","strict":True,"schema":payload["output_schema"]}}
    expected=normalize_openrouter_request(model,dict(model=model,messages=[dict(role="system",content=prompt),dict(role="user",content=kwargs["user_prompt"])],
        temperature=kwargs["temperature"],max_tokens=kwargs["max_tokens"]),request_class=kwargs["request_class"],structured_output=False)
    expected["response_format"]=kwargs["response_format"];expected["provider"]={**expected.get("provider",{}),"require_parameters":True}
    return kwargs,expected


def validate_review(raw,request,seed,design):
    review=PlanReviewV1.model_validate(raw)
    if (review.request_sha256,review.seed_sha256,review.design_sha256)!=(canonical_sha256(request),canonical_sha256(seed),canonical_sha256(design)):
        raise ValueError("Stale semantic plan review")
    for finding in review.findings:
        exists,value=_value_at(design.model_dump(mode="json"),finding.design_pointer)
        if not exists or value!=finding.source_value:raise ValueError("Ungrounded semantic plan finding")
    return review


def execute(*,request_path,seed_path,freeze_path,config_path,preflight,output,api_key,call_fn):
    if preflight!=prepare(request_path,seed_path,freeze_path,config_path):raise ValueError("Frozen pipeline preflight drift")
    if not api_key:raise ValueError("Missing credential")
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    save(output/"preflight.json",preflight)
    for name,path in [("request-input.json",request_path),("seed-input.json",seed_path),("frozen-seed.json",freeze_path),("run-config.json",config_path)]:
        (output/name).write_bytes(Path(path).read_bytes())
    request=StoryRequestV1.model_validate_json(Path(request_path).read_bytes())
    seed=verify_frozen_seed(Path(seed_path),Path(freeze_path))
    config=RunConfigV1.model_validate_json(Path(config_path).read_bytes())
    ledger=[];result=dict(status="REJECT_NON_CONVERGENT",phase="planning",automatic_retry=False,ledger=ledger)
    def call(stage,attempt,payload):
        kwargs,expected=request_for(stage,payload,config)
        rates=require_qualification_runtime_profile(kwargs["model"])["metadata"]["pricing_usd_per_million_tokens"]
        planned=(len(json.dumps({k:v for k,v in kwargs.items()},ensure_ascii=False).encode())*rates["input"]+kwargs["max_tokens"]*rates["output"])/1e6
        if planned>config.max_call_cost_usd or sum(r.get("cost_usd",0) or 0 for r in ledger)+planned>config.max_total_cost_usd:
            raise RuntimeError("Pipeline conservative spend ceiling")
        prefix=output/f"plan-{attempt}-{stage}"
        row=dict(stage=stage,attempt=attempt,model=kwargs["model"],request_sha256=canonical_sha256(expected),status="STARTED",cost_usd=None,planned_cost_usd=planned)
        ledger.append(row);save(str(prefix)+"-request.json",expected);started=time.perf_counter()
        try:
            text,body,actual=call_fn(api_key=api_key,**kwargs)
            save(str(prefix)+"-response.json",{k:body[k] for k in ("id","model","choices","usage") if k in body});save(str(prefix)+"-text.json",dict(text=text))
            if actual!=expected:raise ValueError("Dispatched pipeline request drift")
            usage=body.get("usage",{})
            for key in ("prompt_tokens","completion_tokens","total_tokens"):
                if isinstance(usage.get(key),bool) or not isinstance(usage.get(key),int) or usage[key]<0:raise ValueError("Invalid usage")
            if usage["total_tokens"]!=usage["prompt_tokens"]+usage["completion_tokens"]:raise ValueError("Inconsistent usage")
            cost=usage.get("cost")
            if isinstance(cost,bool) or not isinstance(cost,(float,int)) or not math.isfinite(cost) or cost<0:raise ValueError("Invalid cost")
            row.update(cost_usd=cost,input_tokens=usage["prompt_tokens"],output_tokens=usage["completion_tokens"],total_tokens=usage["total_tokens"])
            if cost>config.max_call_cost_usd or sum(r.get("cost_usd",0) or 0 for r in ledger)>config.max_total_cost_usd:raise ValueError("Provider spend ceiling")
            if body.get("choices",[{}])[0].get("finish_reason")!="stop":raise ValueError("Incomplete response")
            row["status"]="COMPLETE";return text
        except Exception as exc:
            row.update(status="FAILED_NO_RETRY",failure_type=type(exc).__name__);raise
        finally:
            row["latency_seconds"]=round(time.perf_counter()-started,3);save(str(prefix)+"-ledger.json",row)
    try:
        feedback=None;accepted=None
        for attempt in (1,2):
            payload=compact_planner_input_v3(request,seed);payload["rewrite"]=feedback
            payload["instructions"] += "\nScene/route IDs must match [A-Za-z0-9][A-Za-z0-9_-]{0,63}; never use paths or spaces."
            text=call("planner",attempt,payload)
            try:
                compact=CompactStoryPlanV3.model_validate_json(text)
                save(output/f"plan-{attempt}-compact.json",compact.model_dump(mode="json"))
                design=compile_compact_v3(request,seed,compact)
                save(output/f"plan-{attempt}-expanded-design.json",design.model_dump(mode="json"))
                fixture_path=output/f"plan-{attempt}-fixture.json";save(fixture_path,design.fixture)
                engine.load_fixture(fixture_path)
                proof=validate_seeded_design(request,seed,design,fixture_path)
                save(output/f"plan-{attempt}-structural.json",proof)
            except (ValueError,RuntimeError,KeyError,TypeError) as exc:
                feedback=dict(kind="STRUCTURAL",reason=str(exc),candidate=text)
                save(output/f"plan-{attempt}-structural.json",dict(status="REJECTED_DESIGN",failure_type=type(exc).__name__,message=str(exc)))
                continue
            rows=engine.build_chain(fixture_path)[4]
            review_payload=build_review_input(request,seed,compact,design,rows)
            save(output/f"plan-{attempt}-review-input.json",review_payload)
            review=bind_review(json.loads(call("plan_guard",attempt,review_payload)),review_payload,request,seed,compact,design,rows)
            save(output/f"plan-{attempt}-review.json",review.model_dump(mode="json"))
            if review.decision=="PASS":accepted=(design,fixture_path);break
            feedback=dict(kind="SEMANTIC",review=review.model_dump(mode="json"),candidate=text)
        if accepted is None:result["reason"]="PLAN_REJECT_NON_CONVERGENT"
        else:
            design,fixture_path=accepted;result["phase"]="story"
            save(output/"accepted-design.json",design.model_dump(mode="json"))
            remaining=config.max_total_cost_usd-sum(r["cost_usd"] for r in ledger)
            story_config=RunConfigV1.model_validate({**config.model_dump(mode="json"),"max_total_cost_usd":remaining})
            story_preflight=engine.prepare(fixture_path,story_config)
            story=engine.execute_story(fixture_path=fixture_path,api_key=api_key,config=story_config,preflight=story_preflight,output=output/"story",call_fn=call_fn)
            result.update(status=story["status"],story_result=story,phase="verification" if story["status"]=="ACCEPT" else "story")
            ledger.extend(story["ledger"])
            if story["status"]=="ACCEPT":
                proof=verify_story(output/"story",fixture_path);save(output/"offline-replay.json",proof)
                final=json.loads((output/"story"/(design.fixture["route"][-1]+"-accepted.json")).read_text())["state_after"]
                before=seed.initial_state(design.fixture["route"][0]);changes=[]
                def diff(a,b,path):
                    if isinstance(a,dict) and isinstance(b,dict):
                        for k in sorted(set(a)|set(b)):
                            token=k.replace("~","~0").replace("/","~1")
                            if k not in a or k not in b:changes.append(dict(path=path+"/"+token,before_present=k in a,after_present=k in b,before=a.get(k),after=b.get(k)))
                            else:diff(a[k],b[k],path+"/"+token)
                    elif a!=b:changes.append(dict(path=path,before_present=True,after_present=True,before=a,after=b))
                verify_frozen_seed(Path(seed_path),Path(freeze_path));diff(before,{k:final[k] for k in before},"")
                save(output/"state-comparison.json",dict(seed_sha256=canonical_sha256(seed),final_state_sha256=proof["final_state_sha256"],changes=changes,offline_replay="PASS"))
                texts=[json.loads((output/"story"/f"{s}-{json.loads((output/'story'/f'{s}-accepted.json').read_text())["artifact"]["attempt"]}-writer-text.json").read_text())["text"] for s in design.fixture["route"]]
                (output/"assembled-story.md").write_bytes(("\n\n".join(texts)+"\n").encode())
                result["editorial_status"]="REQUIRES_SEPARATE_REVIEW"
                result["phase"]="complete"
    except Exception as exc:result.update(status="REJECT_NON_CONVERGENT",reason="FAILED_CLOSED_NO_RETRY",failure_type=type(exc).__name__)
    result["known_cost_usd"]=round(sum(r.get("cost_usd",0) or 0 for r in ledger),8)
    result["usage_complete"]=all(r.get("cost_usd") is not None for r in ledger)
    result["provider_calls"]=len(ledger)
    save(output/"result.json",result)
    save(output/"manifest.json",dict(files={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob("*")) if p.is_file()},production_write=False))
    return result
