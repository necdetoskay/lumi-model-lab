"""SERA v0.40 — 2 independent REAL-model blind diagnostics, one frozen batch.

A one-use, code-pinned GitHub grant separately authorizes this exact paid
diagnostic. No Writer, repair call, canonical mutation or production DB query.
Existing OpenRouter adapter is the ONLY model transport. No output token caps.
Network timeouts and uncertain receipts are NEVER automatically retried.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import os
from pathlib import Path

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.mara_s1_v04_audit import EXPECTED_SHA, PATH
from experiments.sera.mara_s1_typed_live_v05 import (
    entry_state, one_provider_call, REGISTRY,
)
from experiments.sera.request_policy import verify_current_sera_clients
from experiments.sera.sentence_sweep_v010 import (
    bind_batch, create_plan, summarize_partial,
)
from experiments.sera.world_state_v02 import canonical

SCHEMA = "sera.real-blind-benchmark.v0.40"
MODELS = ("google/gemini-3.7-flash", "anthropic/claude-haiku-4.5")
SPEND_STOP_USD = Decimal("0.05")
SOURCE_TARGET = "bench"
LEXICON = Path(__file__).resolve().parent / "fixtures" / "object_candidate_lexicon_v0.1.json"
GRANT = Path(__file__).resolve().parent / "launch" / "sera-v040-real-blind-one-shot.json"


def require(ok,code):
    if not ok:
        raise CoverageError(code)


def prepare():
    fixture=json.loads(PATH.read_text(encoding="utf-8"))
    text=fixture["prose"]
    require(prose_hash(text)==EXPECTED_SHA and
            fixture.get("source_prose_sha256")==EXPECTED_SHA and
            fixture.get("production_commit_authorized") is False,
            "V040_FROZEN_MARA_SOURCE_UNVERIFIED")
    world=entry_state()
    aliases={key:value for key,value in REGISTRY.items()
             if key in world["entities"]}
    lexicon=json.loads(LEXICON.read_text(encoding="utf-8"))["candidates"]
    require("candidate:bench" in lexicon,
            "V040_BENCH_CANDIDATE_MISSING")
    plan=create_plan(
        prose=text,scene_key=fixture["scene_id"],
        entry_revision=world["revision"],registry=aliases,
        candidate_lexicon=lexicon,
    )
    targets=[s["id"] for s in plan["source_sentences"]
             if SOURCE_TARGET in s["quote"].casefold()]
    require(len(targets)==1, "V040_UNIQUE_SOURCE_BENCH_SENTENCE_REQUIRED")
    selected=[b for b in plan["batches"]
              if targets[0] in b["sentence_ids"]]
    require(len(selected)==1 and
            plan["source_prose_sha256"]==EXPECTED_SHA and
            plan["prior_writer_report_included"] is False and
            plan["prior_analyst_events_included"] is False and
            plan["canonical_commit_authorized"] is False,
            "V040_BLIND_EXTRACTOR_SCOPE_MISMATCH")
    return {
        "prose":text,"plan":plan,"batch":selected[0],
        "target_sentence_id":targets[0],
    }


def _save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    stage=path.with_suffix(".pending")
    with stage.open("w",encoding="utf-8") as fd:
        fd.write(json.dumps(value,ensure_ascii=False,
                            indent=2,allow_nan=False)+"\n")
        fd.flush()
        os.fsync(fd.fileno())
    stage.replace(path)


def _cost(usage):
    if not isinstance(usage,dict):
        return None
    try:
        amount=Decimal(str(usage.get("cost")))
    except (TypeError,ValueError,InvalidOperation):
        return None
    return amount if amount.is_finite() and amount>=0 else None


def verified_grant(source,grant):
    require(isinstance(grant,dict) and set(grant)=={
        "schema","authorized","scope","source_prose_sha256",
        "model_ids","max_provider_attempts","observed_spend_stop_usd",
        "no_reruns","no_output_token_limit","no_canonical_commit",
        "approved_code_sha",
    } and grant["schema"]=="sera.real-blind-oneuse-grant.v0.40" and
            grant["authorized"] is True and
            grant["scope"]=="FROZEN_MARA_S1_BENCH_BATCH_ONLY" and
            grant["source_prose_sha256"]==EXPECTED_SHA and
            grant["model_ids"]==list(MODELS) and
            type(grant["max_provider_attempts"]) is int and
            grant["max_provider_attempts"]==2 and
            grant["observed_spend_stop_usd"]==str(SPEND_STOP_USD) and
            grant["no_reruns"] is True and
            grant["no_output_token_limit"] is True and
            grant["no_canonical_commit"] is True and
            isinstance(grant["approved_code_sha"],str) and
            len(grant["approved_code_sha"])==40 and
            source["batch"]["request_sha256"],
            "V040_EXACT_ONE_USE_GRANT_INVALID")
    verify_current_sera_clients()


def _result_from_response(*,source,model,returned):
    """Preserve raw provider envelope BEFORE any parse/binder assessment."""
    record={
        "requested_model":model,"status":"PROVIDER_ERROR_HOLD",
        "error":returned.get("error"),
        "raw_response":returned.get("raw"),
        "provider_request_id":None,"observed_model":None,
        "provider_cost_usd":None,"source_bound":False,
        "target_bench_mentioned":False,"findings":[],
        "candidate_event_count":0,"candidate_mention_count":0,
    }
    if returned.get("error"):
        record["provider_detail"]=str(returned.get("provider_detail") or "")[:400]
        return record
    raw=returned.get("raw")
    if not isinstance(raw,dict):
        record["status"]="PROVIDER_ENVELOPE_UNAVAILABLE_HOLD"
        return record
    record["provider_request_id"]=raw.get("id")
    record["observed_model"]=raw.get("model")
    usage=raw.get("usage")
    charge=_cost(usage)
    if charge is not None:
        record["provider_cost_usd"]=str(charge)
    record["provider_usage"]=usage
    choices=raw.get("choices")
    if not isinstance(choices,list) or len(choices)!=1:
        record["status"]="PROVIDER_CHOICES_INVALID_HOLD"
        return record
    msg=choices[0].get("message")
    content=msg.get("content") if isinstance(msg,dict) else None
    record["finish_reason"]=choices[0].get("finish_reason")
    if record["finish_reason"]!="stop" or not isinstance(content,str):
        record["status"]="PROVIDER_INCOMPLETE_HOLD"
        return record
    try:
        answer=json.loads(content)
        bound=bind_batch(
            plan=source["plan"],batch_id=source["batch"]["batch_id"],
            raw=answer,prose=source["prose"],
        )
        partial=summarize_partial(
            plan=source["plan"],bound_batches=[bound],
        )
    except (ValueError,CoverageError,TypeError,KeyError) as exc:
        record["status"]="MODEL_RESPONSE_SOURCE_BIND_HOLD"
        record["error"]=str(exc)[:200]
        return record
    events=[e for row in bound["rows"] for e in row["events"]]
    mentions=[m for row in bound["rows"] for m in row["mentions"]]
    bench_mentions=[m for m in mentions
                    if m["entity_ref"] in ("candidate:bench","new:bench")
                    and SOURCE_TARGET in m["quote"].lower()]
    record.update({
        "status":"SOURCE_BOUND_CANDIDATES_SEMANTIC_HOLD",
        "source_bound":True,
        "candidate_mention_count":len(mentions),
        "candidate_event_count":len(events),
        "target_bench_mentioned":bool(bench_mentions),
        "bound_batch":bound,
        "partial_source_coverage":partial,
        "findings":partial.get("findings",[]),
    })
    return record


def live(*,output,launch_id,key,grant):
    require(not output.exists(),"V040_REPEATED_LAUNCH_EVIDENCE_EXISTS")
    source=prepare()
    verified_grant(source,grant)
    from src.openrouter_preflight import fetch_key_status,enforce_key_access
    require(isinstance(key,str) and bool(key),"V040_OPENROUTER_KEY_ABSENT")
    enforce_key_access(fetch_key_status(key),min_remaining=0.10)
    proof={
        "schema":SCHEMA,"status":"PREFLIGHT_COMPLETE",
        "launch_id":launch_id,
        "source_prose_sha256":EXPECTED_SHA,
        "target_sentence_id":source["target_sentence_id"],
        "target_term":SOURCE_TARGET,
        "batch_id":source["batch"]["batch_id"],
        "batch_sentence_ids":source["batch"]["sentence_ids"],
        "request_sha256":source["batch"]["request_sha256"],
        "model_ids":list(MODELS),
        "results":[],"provider_attempts":0,
        "observed_spend_usd":"0","semantic_recall_proven":False,
        "canonical_commit_authorized":False,"production_db_writes":0,
        "model_output_token_limit_set":False,
    }
    _save(output,proof)
    spent=Decimal("0")
    for model in MODELS:
        if spent>=SPEND_STOP_USD:
            proof["status"]="OBSERVED_SPEND_STOP_HOLD"
            break
        # Persist attempt before a paid POST; no automatic rerun or retry
        # after a lost/unknown provider acknowledgement.
        proof["provider_attempts"]+=1
        proof["status"]="IN_FLIGHT_UNKNOWN_CHARGE_NO_AUTORETRY"
        proof["in_flight_model"]=model
        _save(output,proof)
        try:
            response=one_provider_call(
                key=key,model=model,
                prepared={"request":{
                    "messages":source["batch"]["messages"],
                    "response_format":source["batch"]["response_format"],
                }},
            )
        except Exception as exc:
            proof["status"]="PROVIDER_ATTEMPT_UNKNOWN_HOLD"
            proof["transport_error_type"]=type(exc).__name__
            _save(output,proof)
            break
        # Archive raw response first; a subsequent crash can be analyzed
        # without repeating a possibly billed call.
        rawfile=output.parent/(f"provider_reply_{proof['provider_attempts']}.json")
        _save(rawfile,{
            "model":model,"request_sha256":source["batch"]["request_sha256"],
            "provider_envelope":response,
        })
        rec=_result_from_response(source=source,model=model,returned=response)
        proof["results"].append(rec)
        proof.pop("in_flight_model",None)
        charge=rec.get("provider_cost_usd")
        if charge is None:
            proof["status"]="PROVIDER_CHARGE_UNCONFIRMED_HOLD"
            _save(output,proof)
            break
        spent+=Decimal(charge)
        proof["observed_spend_usd"]=str(spent)
        proof["status"]="PARTIAL_EVIDENCE_NONCANONICAL"
        _save(output,proof)
    if len(proof["results"])==len(MODELS):
        proof["status"]="TWO_REAL_MODEL_RESPONSES_DIAGNOSTIC_HOLD"
    elif proof["status"]=="PARTIAL_EVIDENCE_NONCANONICAL":
        proof["status"]="PARTIAL_DIAGNOSTIC_HOLD"
    _save(output,proof)
    return proof


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--live",action="store_true")
    p.add_argument("--output",type=Path)
    p.add_argument("--launch-id",default="dry-run")
    a=p.parse_args()
    source=prepare()
    if not a.live:
        print(json.dumps({
            "status":"DRY_RUN_NO_PROVIDER_CALL",
            "source_prose_sha256":EXPECTED_SHA,
            "batch_id":source["batch"]["batch_id"],
            "target_sentence_id":source["target_sentence_id"],
            "target_quote":next(x["quote"] for x in
                source["plan"]["source_sentences"]
                if x["id"]==source["target_sentence_id"]),
            "models":MODELS,"max_provider_attempts":2,
            "observed_spend_stop_usd":str(SPEND_STOP_USD),
            "canonical_commit_authorized":False,
        },ensure_ascii=False,indent=2))
        return
    if a.output is None:
        p.error("--live requires --output")
    grant=json.loads(GRANT.read_text(encoding="utf-8"))
    result=live(
        output=a.output,launch_id=a.launch_id,
        key=os.getenv("OPENROUTER_API_KEY",""),grant=grant,
    )
    # No raw text in action logs; preserve only in the private artifact.
    print(json.dumps({
        "status":result["status"],
        "attempts":result["provider_attempts"],
        "models":[{"requested":x["requested_model"],
                   "status":x["status"],
                   "source_bound":x["source_bound"],
                   "bench_mentioned":x["target_bench_mentioned"],
                   "cost_usd":x["provider_cost_usd"]}
                  for x in result["results"]],
        "observed_spend_usd":result["observed_spend_usd"],
        "canonical_commit_authorized":False,
    },ensure_ascii=False))


if __name__=="__main__":
    main()
