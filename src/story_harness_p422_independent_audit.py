"""P4.22 independent initial audit of the exact model-generated Spine+Writer pair.

This versioned adapter borrows the original v21 blocking families but does not
modify/impersonate the immutable frozen v21.4 engine. Initial audit ONLY:
no repair, no full story final audit, no English Master/Q25 admission.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path

from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p416_input_bridge import compile_case, sha
from src.story_harness_p417_live_pilot import (
    MODEL, PROVIDER, https_post_once, money
)
from src.story_harness_p410 import canonical_json
from src.story_harness_v1 import HarnessStop

SCHEMA="lumi.story-harness-p422-independent-initial-audit.v1"
FAMILIES={
    "physical","causal","state","spatial","temporal","epistemic",
    "response","closure","canon","age","spine","narrative",
}
OUTPUT_CAP=3200
STAGE_COST_CAP=Decimal("0.040")
DEFAULT_CASE="B01"
ALLOWED_RUN_SUFFIX="-r06"


def must(condition,msg):
    if not condition:
        raise HarnessStop(msg)


def _path(path):
    must(path.is_file() and not path.is_symlink() and path.stat().st_size<200000,
         "Missing or mutable unsupported source artifact")
    return json.loads(path.read_bytes())


def load_source(repo_root, producer_claim_root, *, case_id=DEFAULT_CASE,
                run_variant="r06"):
    plan=load_plan(repo_root)
    must(type(case_id) is str and case_id in {"B01","B02"},
         "Unreviewed case not eligible for audited pilot")
    must(run_variant=="r06", "Unreviewed model run variant")
    case=next((c for c in plan["cases"] if c["id"]==case_id),None)
    must(case is not None and case.get("split")=="pilot",
         "Missing approved pilot case")
    pack=compile_case(case)
    root=Path(producer_claim_root)
    must(root.is_dir() and not root.is_symlink(),"Missing original model claim root")
    name=case_id.lower()+"-"+pack["pack_sha256"][:16]+"-"+run_variant
    options=list(root.glob(case_id.lower()+"-*-"+run_variant))
    must(len(options)==1 and options[0].is_dir() and not options[0].is_symlink(),
         "Original case claim not unique or not present")
    claim=options[0]
    must(claim.name==name,"Another story claim cannot enter independent audit")
    spine=_path(claim/"spine-plan.json")
    story=_path(claim/"story-draft.json")
    first=_path(claim/"01-spineforge-receipt.json")
    second=_path(claim/"02-writer-receipt.json")
    must(spine.get("schema")=="lumi.story-harness-p421-real-spine-artifact.v1"
         and spine.get("source_pack_sha256")==pack["pack_sha256"]
         and type(spine.get("spine")) is dict
         and spine.get("spine_sha256")==sha(spine["spine"]),
         "Provenance or SHA of real Spine artifact changed")
    must(story.get("schema")=="lumi.story-harness-p417-real-provider-pilot.v1"
         and story.get("model_generated") is True
         and story.get("quality_accepted") is False
         and story.get("source_pack_sha256")==pack["pack_sha256"]
         and story.get("spine_sha256")==spine["spine_sha256"]
         and story.get("spine_artifact_path")=="spine-plan.json"
         and type(story.get("story_text")) is str
         and len(story["story_text"].split())==story.get("word_count")
         and hashlib.sha256(story["story_text"].encode()).hexdigest()==story.get("story_sha256"),
         "Real Writer manuscript or source identity changed")
    must(story.get("english_master_authorized") is False
         and story.get("q25_authorized") is False
         and story.get("story_state_write_authorized") is False,
         "Writer draft cannot assert downstream authorization")
    costs=[]
    for expected_stage,receipt in (("SPINEFORGE",first),("WRITER",second)):
        must(receipt.get("stage")==expected_stage
             and receipt.get("outcome")=="SETTLED"
             and receipt.get("retry_authorized") is False
             and type(receipt.get("provider_generation_id")) is str
             and receipt["provider_generation_id"].startswith("gen-")
             and type(receipt.get("provider_usage")) is dict,
             "Unsettled, synthetic or missing original model stage")
        costs.append(money(receipt.get("provider_reported_cost_usd")))
    must(sum(costs)==money(story["total_reported_usd"]),
         "Real stage charges do not match final Writer record")
    must(spine.get("provider_generation_id")==first["provider_generation_id"],
         "Spine artifact not from the accounted SpineForge request")
    return {"pack":pack,"spine":spine,"story":story,
            "case_id":case_id,"run_variant":run_variant,
            "generation_cost_usd":format(sum(costs),"f"),
            "original_claim_id":claim.name}


def audit_wire(source):
    pack,story,spine=source["pack"],source["story"],source["spine"]
    system=(
        "You are a SEPARATE adversarial literary and Canon auditor, not the "
        "author of the story. The target reader is "+
        str(pack["reader_age"])+" years old. Validate "
        "every original approved Spine beat, physical causation, chronology, "
        "known vs unknown ownership, character action and response, ending "
        "obligations, age appropriateness and imaginative literary engagement. "
        "Use blocking families physical, causal, state, spatial, temporal, "
        "epistemic, response, closure, canon, age, spine and narrative. "
        "Mark a serious/critical defect blocking; do NOT invent unsupported "
        "canon facts, missing events or a solved ending. The protagonist must "
        "act with meaningful agency, not merely narrate checklist steps. "
        "For a quoted existing error copy a verbatim excerpt from story_text. "
        "For an omission, identify the unfulfilled approved Spine or Canon "
        "obligation and cite the closest story passage. Return STRICT JSON "
        "with blocking_findings_json as a JSON STRING containing an array "
        "of objects with keys family, quote, reason; use [] if no blockers. "
        "Include advisories_json as a JSON STRING array. The reader score "
        "must be integer 1-5. ACCEPT only if zero blockers, full Spine "
        "fidelity, closure appropriate to the given state and score >=4."
    )
    payload={
        "case_id":source.get("case_id",DEFAULT_CASE),
        "source_pack_sha256":pack["pack_sha256"],
        "approved_spine_sha256":spine["spine_sha256"],
        "story_sha256":story["story_sha256"],
        "reader_age":pack["reader_age"],
        "topic":pack["topic"],
        "canonical_state":pack["canonical_state"],
        "open_obligations":pack["open_obligations"],
        "unknown_facts":pack["unknown_facts"],
        "approved_spine_beats":spine["spine"]["beats"],
        "approved_spine_summary":spine["spine"]["spine_summary"],
        "complete_story_text":story["story_text"],
    }
    schema={"type":"object","additionalProperties":False,
        "properties":{
            "story_sha256":{"type":"string"},
            "spine_sha256":{"type":"string"},
            "verdict":{"type":"string","enum":["ACCEPT","REJECT"]},
            "reader_score":{"type":"integer"},
            "blocking_findings_json":{"type":"string"},
            "advisories_json":{"type":"string"},
            "rationale":{"type":"string"},
        },
        "required":["story_sha256","spine_sha256","verdict",
            "reader_score","blocking_findings_json","advisories_json","rationale"]}
    body={
        "model":MODEL,
        "messages":[{"role":"system","content":system},
                    {"role":"user","content":canonical_json(payload).decode()}],
        "max_tokens":OUTPUT_CAP,
        "stream":False,
        "usage":{"include":True},
        "provider":{"only":[PROVIDER],"allow_fallbacks":False,
                    "require_parameters":True,
                    "max_price":{"prompt":2,"completion":10}},
        "response_format":{"type":"json_schema","json_schema":{
            "name":"lumi_"+source.get("case_id",DEFAULT_CASE).lower()+
                   "_independent_initial_audit_v1",
            "strict":True,"schema":schema}},
    }
    must(len(canonical_json(body))<20000,"Unbounded quality request")
    return body


def verify_auditor_reply(source,response):
    must(type(response) is dict and response.get("model")==MODEL,
         "Wrong independent auditor model")
    usage=response.get("usage")
    must(type(usage) is dict and type(usage.get("prompt_tokens")) is int
         and type(usage.get("completion_tokens")) is int
         and usage["prompt_tokens"]>=0 and
         0<=usage["completion_tokens"]<=OUTPUT_CAP,
         "Quality provider token accounting missing")
    paid=money(usage.get("cost"))
    must(paid<=STAGE_COST_CAP, "Original 0.040 initial-audit cost cap exceeded")
    choices=response.get("choices")
    must(type(choices) is list and len(choices)==1
         and choices[0].get("finish_reason")=="stop",
         "Audit incomplete/truncated")
    content=choices[0].get("message",{}).get("content")
    must(type(content) is str and len(content)<=32000,
         "Audit response is not bounded text")
    try:
        q=json.loads(content)
        must(type(q) is dict and set(q)=={
            "story_sha256","spine_sha256","verdict","reader_score",
            "blocking_findings_json","advisories_json","rationale"},
            "Audit output contract mismatch")
        blockers=json.loads(q["blocking_findings_json"])
        advisories=json.loads(q["advisories_json"])
    except (TypeError,ValueError,KeyError):
        raise HarnessStop("Invalid strict quality JSON content") from None
    must(q["story_sha256"]==source["story"]["story_sha256"]
         and q["spine_sha256"]==source["spine"]["spine_sha256"],
         "Quality auditor was not bound to same immutable story+Spine")
    must(type(blockers) is list and len(blockers)<=24
         and type(advisories) is list and len(advisories)<=30,
         "Invalid audit findings")
    for finding in blockers:
        must(type(finding) is dict and set(finding)=={"family","quote","reason"}
             and finding["family"] in FAMILIES
             and type(finding["quote"]) is str
             and 4<=len(finding["quote"])<=500
             and finding["quote"] in source["story"]["story_text"]
             and type(finding["reason"]) is str
             and 8<=len(finding["reason"])<=1600,
             "Unanchored or invented blocking finding")
    must(type(q["reader_score"]) is int and
         1<=q["reader_score"]<=5 and
         q["verdict"] in ("ACCEPT","REJECT")
         and type(q["rationale"]) is str
         and 8<=len(q["rationale"])<=2500,
         "Invalid literary evaluation")
    if q["verdict"]=="ACCEPT":
        must(not blockers and q["reader_score"]>=4,
             "Model cannot accept unresolved blockers or poor reader quality")
    elif not blockers and q["reader_score"]>=4:
        must(q["verdict"]=="REJECT",
             "Model verdict mismatch")
    gid=response.get("id")
    must(type(gid) is str and gid.startswith("gen-"),
         "Missing authoritative auditor generation ID")
    return {
        "schema":SCHEMA,
        "case_id":source.get("case_id",DEFAULT_CASE),
        "source_pack_sha256":source["pack"]["pack_sha256"],
        "spine_sha256":source["spine"]["spine_sha256"],
        "story_sha256":source["story"]["story_sha256"],
        "original_spine_generation_id":source["spine"]["provider_generation_id"],
        "auditor_generation_id":gid,
        "auditor_model":MODEL,
        "quality_initial_verdict":q["verdict"],
        "blocking_findings":blockers,
        "advisories":advisories,
        "reader_score":q["reader_score"],
        "rationale":q["rationale"],
        "quality_initial_audit_accepted":q["verdict"]=="ACCEPT",
        "full_original_v21_final_audit_completed":False,
        "english_master_authorized":False,
        "q25_authorized":False,
        "state_write_authorized":False,
        "auditor_usage":{"prompt_tokens":usage["prompt_tokens"],
                         "completion_tokens":usage["completion_tokens"]},
        "auditor_reported_cost_usd":format(paid,"f"),
    }


def _write(path,data):
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    if hasattr(os,"O_NOFOLLOW"):flags|=os.O_NOFOLLOW
    fd=os.open(path,flags,0o600)
    with os.fdopen(fd,"wb") as f:
        f.write(canonical_json(data)+b"\n")
        f.flush()
        os.fsync(f.fileno())


def audit_once(source, audit_root, *,transport, audit_prefix="p422"):
    root=Path(audit_root)
    must(root.is_dir() and not root.is_symlink(),
         "No durable independent quality claim root")
    must(audit_prefix in ("p422","p427"),"Unreviewed audit prefix")
    case_id=source.get("case_id",DEFAULT_CASE)
    must(case_id in ("B01","B02"),"Invalid source case for paid audit")
    run=root/(audit_prefix+"-"+case_id.lower()+"-r06-"+
              source["story"]["story_sha256"][:12])
    run.mkdir(mode=0o700,exist_ok=False)
    body=audit_wire(source)
    _write(run/"00-intent.json",{
        "schema":SCHEMA,"case_id":case_id,
                "source_story_sha256":source["story"]["story_sha256"],
        "spine_sha256":source["spine"]["spine_sha256"],
        "exact_request_sha256":hashlib.sha256(canonical_json(body)).hexdigest(),
        "maximum_quality_model_posts":1,
        "stage_maximum_reported_usd":format(STAGE_COST_CAP,"f"),
        "automatic_retry":False,
    })
    try:
        outcome=verify_auditor_reply(source,transport(body))
        _write(run/"01-audit-outcome.json",outcome)
        return outcome
    except Exception:
        if not (run/"01-audit-outcome.json").exists():
            _write(run/"01-audit-outcome.json",{
                "schema":SCHEMA,"source_story_sha256":source["story"]["story_sha256"],
                "quality_initial_verdict":"STOP_UNKNOWN_OR_INVALID",
                "auditor_reported_cost_usd":None,
                "english_master_authorized":False,
                "retry_allowed":False})
        raise HarnessStop("Independent audit consumed, no retry") from None


if __name__=="__main__":
    import argparse
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--repo-root",default=".")
    cli.add_argument("--producer-claims")
    cli.add_argument("--audit-claims")
    cli.add_argument("--paid-audit-once",action="store_true")
    args=cli.parse_args()
    if not args.paid_audit_once:
        print(json.dumps({"schema":SCHEMA,"initial_audit_only":True,
                          "provider_model_calls":0,
                          "stage_cap_usd":"0.040",
                          "english_master_authorized":False,
                          "strict_spine_source_required":True},sort_keys=True))
    else:
        must(os.getenv("LUMI_P422_AUDIT_ENABLE")==
             "ONE_BOUNDED_GENUINE_INITIAL_AUDIT",
             "Quality paid attempt requires explicit one-shot runtime gate")
        must(args.producer_claims and args.audit_claims,
             "Missing independent immutable source and audit paths")
        source=load_source(args.repo_root,args.producer_claims)
        result=audit_once(source,args.audit_claims,
             transport=lambda body:https_post_once(os.getenv("OPENROUTER_API_KEY",""),body))
        print(json.dumps({"source_story_sha256":result["story_sha256"],
            "quality_initial_verdict":result["quality_initial_verdict"],
            "blocking_count":len(result["blocking_findings"]),
            "reader_score":result["reader_score"],
            "auditor_reported_cost_usd":result["auditor_reported_cost_usd"],
            "english_master_authorized":False},sort_keys=True))
