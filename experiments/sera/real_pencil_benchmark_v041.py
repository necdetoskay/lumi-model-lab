"""SERA v0.41: Second real one-use blind pilot — uncertain pencil motion.

Uses SAME frozen Mara S1 story, but DIFFERENT four-sentence batch containing
"Vane watched the pencil move". Only two independently requested providers.
Full code SHA grant gate belongs to the one-use self-hosted CI workflow.
No output token ceiling, canon commit, SQLite write, manual repair or
automatic network retry. Reuse v0.40 provider/archive/cost helpers.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import argparse
import json
import os
from pathlib import Path

from experiments.sera.coverage import CoverageError
from experiments.sera.haiku_evidence_recovery_v011 import parse_json_model_reply
from experiments.sera.mara_s1_typed_live_v05 import one_provider_call
from experiments.sera.real_blind_benchmark_v040 import (
    EXPECTED_SHA, MODELS, SPEND_STOP_USD, _cost, _save,
    _result_from_response, prepare as original_plan,
)
from experiments.sera.request_policy import verify_current_sera_clients

SOURCE_TARGET = "pencil"
SCHEMA = "sera.real-pencil-blind-benchmark.v0.41"
GRANT = (Path(__file__).resolve().parent / "launch" /
         "sera-v041-real-pencil-one-shot.json")


def ensure(ok,code):
    if not ok:
        raise CoverageError(code)


def prepare():
    original=original_plan()
    candidates=[s for s in original["plan"]["source_sentences"]
                if SOURCE_TARGET in s["quote"].casefold()]
    ensure(len(candidates)==1, "V041_PENCIL_SOURCE_SENTENCE_NOT_UNIQUE")
    batches=[b for b in original["plan"]["batches"]
             if candidates[0]["id"] in b["sentence_ids"]]
    ensure(len(batches)==1 and
           batches[0]["request_sha256"]!=
               original["batch"]["request_sha256"],
           "V041_NEW_BLIND_BATCH_REQUIRED")
    return {**original,"batch":batches[0],
            "target_sentence_id":candidates[0]["id"]}


def verify_grant(source,grant):
    ensure(isinstance(grant,dict) and set(grant)=={
        "schema","authorized","scope","source_prose_sha256",
        "model_ids","max_provider_attempts","observed_spend_stop_usd",
        "no_reruns","no_output_token_limit","no_canonical_commit",
        "approved_code_sha",
    } and grant["schema"]=="sera.real-pencil-oneuse-grant.v0.41" and
           grant["authorized"] is True and
           grant["scope"]=="FROZEN_MARA_S1_PENCIL_BATCH_ONLY" and
           grant["source_prose_sha256"]==EXPECTED_SHA and
           grant["model_ids"]==list(MODELS) and
           type(grant["max_provider_attempts"]) is int and
           grant["max_provider_attempts"]==2 and
           grant["observed_spend_stop_usd"]==str(SPEND_STOP_USD) and
           grant["no_reruns"] is True and
           grant["no_output_token_limit"] is True and
           grant["no_canonical_commit"] is True and
           isinstance(grant["approved_code_sha"],str) and
           len(grant["approved_code_sha"])==40,
           "V041_PAID_GRANT_UNVERIFIED")
    ensure(source["plan"]["source_prose_sha256"]==EXPECTED_SHA and
           source["plan"]["prior_writer_report_included"] is False and
           source["plan"]["prior_analyst_events_included"] is False,
           "V041_BLIND_SOURCE_NOT_TRUSTED")
    verify_current_sera_clients()


def interpret(*,source,model,returned):
    """Unmodified provider raw archived separately BEFORE safe envelope parse."""
    adjusted=deepcopy(returned)
    envelope_kind=None
    if (adjusted.get("error") is None and
        isinstance(adjusted.get("raw"),dict)):
        choices=adjusted["raw"].get("choices")
        if (isinstance(choices,list) and len(choices)==1 and
            isinstance(choices[0],dict) and
            isinstance(choices[0].get("message"),dict) and
            isinstance(choices[0]["message"].get("content"),str) and
            choices[0].get("finish_reason")=="stop"):
            text=choices[0]["message"]["content"]
            try:
                parsed,envelope_kind=parse_json_model_reply(text)
                adjusted["raw"]["choices"][0]["message"]["content"]=json.dumps(
                    parsed,ensure_ascii=False,
                )
            except (CoverageError,TypeError,ValueError):
                envelope_kind="UNREPAIRABLE_OR_UNRECEIPTED"
    record=_result_from_response(
        source=source,model=model,returned=adjusted,
    )
    # Preserve the original model evidence, not silently normalized text.
    record["raw_response"]=returned.get("raw")
    record["json_envelope"]=envelope_kind
    mentions=[
        (row["sentence_id"],mention)
        for row in (record.get("bound_batch") or {}).get("rows",[])
        for mention in row.get("mentions",[])
    ]
    pencil=[
        mention for sid,mention in mentions
        if sid==source["target_sentence_id"] and
        mention["entity_ref"] in ("new:pencil","candidate:pencil") and
        "pencil" in mention["quote"].casefold()
    ]
    record["target_pencil_mentioned"]=bool(pencil)
    record["source_motion_ambiguous"] = True
    record["event_subject_and_cause_verified"] = False
    record["physical_pencil_move_committable"] = False
    record["production_db_writes"] = 0
    record["canonical_commit_authorized"] = False
    return record


def live(*,output,launch_id,key,grant):
    ensure(not output.exists(),"V041_REPLAY_OR_OUTPUT_ALREADY_EXISTS")
    source=prepare()
    verify_grant(source,grant)
    ensure(isinstance(key,str) and bool(key),"V041_PROVIDER_KEY_MISSING")
    from src.openrouter_preflight import fetch_key_status,enforce_key_access
    enforce_key_access(fetch_key_status(key),min_remaining=0.10)
    proof={
        "schema":SCHEMA,"status":"PREFLIGHT_COMPLETE",
        "launch_id":launch_id,
        "source_prose_sha256":EXPECTED_SHA,
        "target_sentence_id":source["target_sentence_id"],
        "target_term":"pencil",
        "batch_id":source["batch"]["batch_id"],
        "request_sha256":source["batch"]["request_sha256"],
        "batch_sentence_ids":source["batch"]["sentence_ids"],
        "model_ids":list(MODELS),
        "provider_attempts":0,
        "results":[],
        "observed_spend_usd":"0",
        "model_output_token_limit_set":False,
        "independent_semantic_qualification":False,
        "canonical_commit_authorized":False,
        "production_db_writes":0,
    }
    _save(output,proof)
    spent=Decimal("0")
    for model in MODELS:
        if spent>=SPEND_STOP_USD:
            proof["status"]="OBSERVED_SPEND_STOP_HOLD"
            break
        proof["provider_attempts"]+=1
        proof["in_flight_model"]=model
        proof["status"]="IN_FLIGHT_UNKNOWN_CHARGE_NO_AUTORETRY"
        _save(output,proof)
        try:
            response=one_provider_call(
                key=key,model=model,prepared={
                    "request":{
                        "messages":source["batch"]["messages"],
                        "response_format":source["batch"]["response_format"],
                    }
                },
            )
        except Exception as exc:
            proof["status"]="UNKNOWN_PROVIDER_RECEIPT_HOLD"
            proof["transport_error_type"]=type(exc).__name__
            _save(output,proof)
            break
        # Exact raw response first. Parsing only touches a COPY.
        _save(output.parent/f"provider_reply_{proof['provider_attempts']}.json",{
            "model":model,"request_sha256":source["batch"]["request_sha256"],
            "provider_envelope":response,
        })
        row=interpret(source=source,model=model,returned=response)
        proof["results"].append(row)
        proof.pop("in_flight_model",None)
        charge=_cost((response.get("raw") or {}).get("usage"))
        if charge is None:
            proof["status"]="PROVIDER_COST_UNKNOWN_NO_FURTHER_CALL_HOLD"
            _save(output,proof)
            break
        spent+=charge
        proof["observed_spend_usd"]=str(spent)
        proof["status"]="PARTIAL_REAL_SOURCE_EVIDENCE_HOLD"
        _save(output,proof)
    if len(proof["results"])==len(MODELS):
        proof["status"]="TWO_REAL_PENCIL_MODELS_DIAGNOSTIC_HOLD"
    elif proof["status"]=="PARTIAL_REAL_SOURCE_EVIDENCE_HOLD":
        proof["status"]="PARTIAL_REAL_PENCIL_EVIDENCE_HOLD"
    _save(output,proof)
    return proof


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--live",action="store_true")
    parser.add_argument("--output",type=Path)
    parser.add_argument("--launch-id",default="dry-run")
    args=parser.parse_args()
    source=prepare()
    if not args.live:
        print(json.dumps({
            "status":"DRY_RUN_NO_MODEL_CALL",
            "source_sha256":EXPECTED_SHA,
            "batch_id":source["batch"]["batch_id"],
            "target_sentence_id":source["target_sentence_id"],
            "target_quote":next(x["quote"] for x in
                source["plan"]["source_sentences"]
                if x["id"]==source["target_sentence_id"]),
            "requested_models":MODELS,
            "provider_calls":0,
            "canonical_commit_authorized":False,
        },ensure_ascii=False,indent=2))
        return
    if args.output is None:
        parser.error("--live requires --output")
    grant=json.loads(GRANT.read_text(encoding="utf-8"))
    result=live(
        output=args.output,launch_id=args.launch_id,
        key=os.getenv("OPENROUTER_API_KEY",""),grant=grant,
    )
    print(json.dumps({
        "status":result["status"],
        "provider_attempts":result["provider_attempts"],
        "models":[{
            "requested_model":z["requested_model"],
            "status":z["status"],
            "pencil_source_mention":z["target_pencil_mentioned"],
            "source_bound":z["source_bound"],
            "event_count":z["candidate_event_count"],
            "cost_usd":z.get("provider_cost_usd"),
            "json_envelope":z.get("json_envelope"),
        } for z in result["results"]],
        "observed_spend_usd":result["observed_spend_usd"],
        "canonical_commit_authorized":False,
    },ensure_ascii=False))


if __name__ == "__main__":
    main()
