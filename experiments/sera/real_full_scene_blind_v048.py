"""SERA v0.48 — complete 28-sentence / 2-real-provider blind pilot (LOCKED).

This file prepares the exact paid experiment, but NEVER authorizes it.
Real calls are impossible without an explicit, later, one-use launch GRANT
pinned to the *entire prior code commit*. The grant file intentionally
does NOT exist in the preparation commit. CI only runs paid mode after
the user-authorized grant-only commit with the exact tag.

No output token ceilings, no model truth/Gold, no retries of unknown
charges, no production DB, no G2 release, no automatic paid repair.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
from hashlib import sha256
import json
import os
import time
from pathlib import Path

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.haiku_evidence_recovery_v011 import parse_json_model_reply
from experiments.sera.mara_s1_typed_live_v05 import one_provider_call
from experiments.sera.real_blind_benchmark_v040 import (
    EXPECTED_SHA, MODELS, _save, _cost, prepare as frozen_source,
)
from experiments.sera.real_pencil_receipt_replay_v0411 import (
    normalize_only_safe_advisory_fields,
)
from experiments.sera.real_pencil_partial_rows_v0412 import isolate_rows
from experiments.sera.request_policy import (
    enforce_no_output_token_limit, verify_current_sera_clients,
)
from experiments.sera.scene_trace_dual_real_v043 import source_risks

SCHEMA = "sera.v048-full-blind-real-mara"
GRANT_SCHEMA = "sera.v048-fullscene-one-use-paid-grant"
GRANT = Path(__file__).parent/"launch"/"sera-v048-fullscene-paid-once-after-preflight-failure.json"
MAX_ATTEMPTS = 14
MAX_SPEND_USD = Decimal("0.25")
MIN_PREFLIGHT_REMAINING_USD = 0.35


def require(ok,code):
    if not ok:
        raise CoverageError(code)


def prepare():
    source=frozen_source()
    plan=source["plan"]
    batches=plan["batches"]
    require(prose_hash(source["prose"])==EXPECTED_SHA and
            len(plan["source_sentences"])==28 and
            len(batches)==7 and
            [len(b["sentence_ids"]) for b in batches]==[4]*7 and
            len(set(s for batch in batches for s in batch["sentence_ids"]))==28 and
            all(b["response_format"]=={"type":"json_object"}
                for b in batches) and
            plan["canonical_commit_authorized"] is False and
            plan["prior_writer_report_included"] is False and
            plan["prior_analyst_events_included"] is False,
            "V048_FULL_FROZEN_BLIND_PLAN_INVALID")
    manifest={
        "schema":"sera.v048-prelaunch-manifest",
        "source_prose_sha256":EXPECTED_SHA,
        "source_sentence_count":28,
        "batches":[{
            "batch_id":b["batch_id"],
            "sentence_ids":b["sentence_ids"],
            "request_sha256":b["request_sha256"],
        } for b in batches],
        "model_ids":list(MODELS),
        "planned_provider_attempts":MAX_ATTEMPTS,
        "observed_spend_stop_usd":str(MAX_SPEND_USD),
        "grant_present":GRANT.is_file(),
        "real_provider_calls_during_preparation":0,
        "independent_semantic_truth_proven":False,
        "canonical_commit_authorized":False,
        "production_db_writes":0,
    }
    return source,manifest


def require_grant(manifest,grant):
    """Validates grant content, not Git commit parent; CI verifies BOTH."""
    require(isinstance(grant,dict) and set(grant)=={
        "schema","authorized","scope","source_prose_sha256",
        "batch_request_sha256","model_ids","max_provider_attempts",
        "observed_spend_stop_usd","approved_code_sha",
        "no_reruns","no_output_token_limit","no_canonical_commit",
        "no_automatic_paid_retries",
    } and grant["schema"]==GRANT_SCHEMA and
            grant["authorized"] is True and
            grant["scope"]=="FROZEN_MARA_S1_28_SENTENCES_TWO_MODELS" and
            grant["source_prose_sha256"]==EXPECTED_SHA and
            grant["batch_request_sha256"]==
                [b["request_sha256"] for b in manifest["batches"]] and
            grant["model_ids"]==list(MODELS) and
            type(grant["max_provider_attempts"]) is int and
            grant["max_provider_attempts"]==MAX_ATTEMPTS and
            grant["observed_spend_stop_usd"]==str(MAX_SPEND_USD) and
            isinstance(grant["approved_code_sha"],str) and
            len(grant["approved_code_sha"])==40 and
            all(grant[x] is True for x in (
                "no_reruns","no_output_token_limit","no_canonical_commit",
                "no_automatic_paid_retries",
            )),
            "V048_EXACT_PAID_GRANT_REQUIRED")
    verify_current_sera_clients()
    return True


def request_payload(batch):
    result={
        "messages":batch["messages"],
        "response_format":batch["response_format"],
    }
    return enforce_no_output_token_limit(result)


def assess_received(*,source,batch,model,receipt):
    """Offline binder. All verified rows are CANDIDATES, not semantic fact."""
    model_id=receipt.get("model")
    envelope=receipt.get("provider_envelope")
    require(model_id==model and
            receipt.get("request_sha256")==batch["request_sha256"] and
            isinstance(envelope,dict),
            "V048_PROVIDER_RECEIPT_SOURCE_OR_MODEL_MISMATCH")
    raw=envelope.get("raw")
    if not isinstance(raw,dict):
        return {"provider_complete":False,"charge_usd":None,
                "source_bound_rows":[],"quarantined_rows":[],
                "problem":"V048_PROVIDER_RAW_RESPONSE_MISSING"}
    price=_cost(raw.get("usage"))
    check={
        "provider_complete":False,
        "charge_usd":str(price) if price is not None else None,
        "source_bound_rows":[],
        "quarantined_rows":[],
        "problem":None,
    }
    choices=raw.get("choices")
    if (envelope.get("error") is not None or raw.get("model")!=model or
        not isinstance(choices,list) or len(choices)!=1 or
        not isinstance(choices[0],dict) or
        choices[0].get("finish_reason")!="stop"):
        check["problem"]="V048_PROVIDER_MODEL_OR_FINISH_UNQUALIFIED"
        return check
    content=choices[0].get("message",{}).get("content")
    if not isinstance(content,str) or not content.strip():
        check["problem"]="V048_PROVIDER_TEXT_UNAVAILABLE"
        return check
    check["provider_complete"]=True
    check["raw_text_sha256"]=sha256(content.encode("utf-8")).hexdigest()
    try:
        parsed,format_kind=parse_json_model_reply(content)
        parsed,nonsemantic=normalize_only_safe_advisory_fields(parsed)
        accepted,quarantined=isolate_rows(
            plan={"plan":source["plan"],"batch":batch},
            parsed=parsed,prose=source["prose"],
        )
        check["format"]=format_kind
        check["nonsemantic_metadata_repairs"]=nonsemantic
        check["source_bound_rows"]=accepted
        check["quarantined_rows"]=quarantined
    except (CoverageError,TypeError,ValueError,KeyError,IndexError) as exc:
        # Structural failure quarantines ALL expected source rows.
        # No fabricated placeholders are passed to aggregation.
        check["problem"]=str(exc)[:160]
        check["quarantined_rows"]=[{
            "sentence_id":sid,
            "reason":"FULL_BATCH_UNQUALIFIED:"+check["problem"],
            "source_spans_checked":False,
            "automated_repair_not_possible_without_reextraction":True,
        } for sid in batch["sentence_ids"]]
    require(len(check["source_bound_rows"])+len(check["quarantined_rows"])==
            len(batch["sentence_ids"]),
            "V048_RECEIPT_SENTENCE_ACCOUNTING_UNSAFE")
    source_by_id={s["id"]:s for s in source["plan"]["source_sentences"]}
    risks=[]
    for row in check["source_bound_rows"]:
        for event in row["candidate_events"]:
            for kind in source_risks(
                source_sentence=source_by_id[row["sentence_id"]]["quote"],
                model_event=event,
            ):
                risks.append({
                    "sentence_id":row["sentence_id"],"model":model,
                    "risk_code":kind,
                    "evidence_quote":event["quote"],
                    "source_span":[event["start"],event["end"]],
                    "semantic_truth_verified":False,
                })
    check["risk_flags"]=risks
    return check


def analyze_plan_coverage(source,receipts):
    """Count actual source-bound model rows; missing is NOT a success."""
    source_ids=[s["id"] for s in source["plan"]["source_sentences"]]
    by_model={}
    for model in MODELS:
        events=[]
        known={}
        risk=[]
        for item in receipts:
            if item["model"]!=model:
                continue
            outcome=item["assessment"]
            for row in outcome.get("source_bound_rows",[]):
                require(row["sentence_id"] not in known,
                        "V048_DUPLICATE_BOUND_SOURCE_ROW")
                known[row["sentence_id"]]="SOURCE_BOUND_NONCANONICAL"
                events+=row["candidate_events"]
            for row in outcome.get("quarantined_rows",[]):
                require(row["sentence_id"] not in known,
                        "V048_DUPLICATE_QUARANTINED_SOURCE_ROW")
                known[row["sentence_id"]]="QUARANTINED"
            risk+=outcome.get("risk_flags",[])
        require(set(known).issubset(source_ids),
                "V048_NON_SOURCE_SENTENCE_IN_RECEIPTS")
        by_model[model]={
            "sentence_statuses":{sid:known.get(sid,"NOT_SAMPLED")
                                 for sid in source_ids},
            "source_bound_sentence_count":sum(
                value=="SOURCE_BOUND_NONCANONICAL" for value in known.values()
            ),
            "quarantined_sentence_count":sum(
                value=="QUARANTINED" for value in known.values()
            ),
            "unsampled_sentence_count":28-len(known),
            "candidate_event_count":len(events),
            "source_risk_flags":risk,
            "independent_semantic_correctness_proven":False,
        }
    # Compare model candidate signatures only when BOTH are source-bound.
    # Agreement and disagreement are diagnostic, NEVER semantic truth.
    event_signatures={}
    for item in receipts:
        for row in item["assessment"].get("source_bound_rows",[]):
            key=(item["model"],row["sentence_id"])
            require(key not in event_signatures,
                    "V048_DUPLICATE_COMPARISON_SOURCE_ROW")
            event_signatures[key]=sorted([
                (e["kind"],e["epistemic"],e["effect"],
                 tuple(sorted(e["entity_refs"])))
                for e in row["candidate_events"]
            ])
    comparable=[
        sid for sid in source_ids
        if all((model,sid) in event_signatures for model in MODELS)
    ]
    discrepancies=[
        sid for sid in comparable
        if event_signatures[(MODELS[0],sid)]!=
           event_signatures[(MODELS[1],sid)]
    ]
    return {
        "model_results":by_model,
        "both_models_source_bound_sentence_count":len(comparable),
        "model_candidate_signature_disagreement_count":len(discrepancies),
        "model_candidate_disagreement_sentence_ids":discrepancies,
        "agreement_does_not_prove_physical_truth":True,
        "source_complete_candidate_binding_all_models":all(
            v["source_bound_sentence_count"]==28 for v in by_model.values()
        ),
        "semantic_recall_precision_proven":False,
        "story_ready_for_g2_commit":False,
        "recommendation":"SHADOW_ONLY_UNTIL_INDEPENDENT_EVENT_TRUTH_GATE",
        "canonical_commit_authorized":False,
    }


def live(*,output,launch_id,key,grant):
    """14 explicitly authorized one-shot attempts at most. NEVER retry."""
    source,manifest=prepare()
    require_grant(manifest,grant)
    require(not output.exists(),"V048_ONE_SHOT_OUTPUT_ALREADY_EXISTS")
    require(isinstance(launch_id,str) and
            launch_id.startswith("sera-v048-full-once-") and
            isinstance(key,str) and bool(key),
            "V048_LIVE_CONTEXT_OR_PROVIDER_SECRET_MISSING")
    from src.openrouter_preflight import fetch_key_status,enforce_key_access
    enforce_key_access(fetch_key_status(key),
                       min_remaining=MIN_PREFLIGHT_REMAINING_USD)
    summary={
        "schema":SCHEMA,"status":"PREFLIGHT_COMPLETE",
        "launch_id":launch_id,
        "manifest":manifest,
        "source_sha256":EXPECTED_SHA,
        "model_ids":list(MODELS),
        "attempts_started":0,
        "receipts":[],
        "observed_spend_usd":"0",
        "outstanding_request_may_have_billed":False,
        "canonical_commit_authorized":False,
        "production_db_writes":0,
        "model_output_token_limit_set":False,
    }
    _save(output,summary)
    spend=Decimal("0")
    attempt_index=0
    for batch in source["plan"]["batches"]:
        for model_index,model in enumerate(MODELS,1):
            if spend>=MAX_SPEND_USD:
                summary["status"]="OBSERVED_SPEND_STOP_HOLD"
                break
            require(attempt_index<MAX_ATTEMPTS,
                    "V048_UNAUTHORIZED_EXTRA_PROVIDER_ATTEMPT")
            request=request_payload(batch)
            attempt_index+=1
            summary["attempts_started"]=attempt_index
            summary["status"]="UNKNOWN_IN_FLIGHT_NO_RESEND"
            summary["outstanding_request_may_have_billed"]=True
            summary["inflight_batch_id"]=batch["batch_id"]
            summary["inflight_model"]=model
            _save(output,summary)
            started_monotonic=time.perf_counter()
            try:
                reply=one_provider_call(key=key,model=model,
                                         prepared={"request":request})
            except Exception as exc:
                summary["status"]="UNKNOWN_PROVIDER_RESULT_NO_RESEND"
                summary["provider_failure_class"]=type(exc).__name__
                summary["unknown_attempt_elapsed_seconds"]=round(
                    time.perf_counter()-started_monotonic,3,
                )
                _save(output,summary)
                break
            elapsed_seconds=round(time.perf_counter()-started_monotonic,3)
            receipt={
                "model":model,"batch_id":batch["batch_id"],
                "client_roundtrip_seconds":elapsed_seconds,
                "request_sha256":batch["request_sha256"],
                "provider_envelope":reply,
            }
            receipt_path=output.parent/(
                f"provider_reply_{attempt_index:02d}.json"
            )
            _save(receipt_path,receipt)  # raw, before ANY binding operation
            summary["outstanding_request_may_have_billed"]=False
            summary.pop("inflight_batch_id",None)
            summary.pop("inflight_model",None)
            try:
                evaluation=assess_received(
                    source=source,batch=batch,model=model,receipt=receipt,
                )
            except (CoverageError,ValueError,TypeError,KeyError) as exc:
                evaluation={
                    "provider_complete":False,"charge_usd":None,
                    "source_bound_rows":[],"quarantined_rows":[],
                    "problem":"V048_ASSESSMENT_EXCEPTION:"+type(exc).__name__,
                }
            summary["receipts"].append({
                "model":model,"batch_id":batch["batch_id"],
                "receipt_file":receipt_path.name,
                "receipt_sha256":sha256(receipt_path.read_bytes()).hexdigest(),
                "client_roundtrip_seconds":elapsed_seconds,
                "assessment":evaluation,
            })
            _save(output,summary)
            price=evaluation.get("charge_usd")
            if price is None:
                summary["status"]="PROVIDER_COST_UNKNOWN_NO_MORE_CALLS"
                _save(output,summary)
                break
            spend+=Decimal(price)
            summary["observed_spend_usd"]=str(spend)
            summary["status"]="RECEIPT_SAVED_NONCANONICAL"
            _save(output,summary)
        if summary["status"] not in (
            "RECEIPT_SAVED_NONCANONICAL","PREFLIGHT_COMPLETE",
        ):
            break
    summary["coverage"]=analyze_plan_coverage(source,summary["receipts"])
    if summary["status"]=="RECEIPT_SAVED_NONCANONICAL":
        summary["status"]=(
            "FOURTEEN_REAL_RECEIPTS_NONCANONICAL"
            if attempt_index==MAX_ATTEMPTS else
            "PARTIAL_REAL_RECEIPTS_HOLD"
        )
    _save(output,summary)
    return summary


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--live",action="store_true")
    p.add_argument("--output",type=Path)
    p.add_argument("--launch-id",default="preparation-only")
    args=p.parse_args()
    source,manifest=prepare()
    if not args.live:
        print(json.dumps(manifest,ensure_ascii=False,sort_keys=True))
        return
    require(args.output is not None and GRANT.is_file(),
            "V048_ONE_USE_USER_AUTHORIZED_GRANT_NOT_PRESENT")
    grant=json.loads(GRANT.read_text(encoding="utf-8"))
    result=live(
        output=args.output,launch_id=args.launch_id,
        key=os.getenv("OPENROUTER_API_KEY",""),grant=grant,
    )
    print(json.dumps({
        "status":result["status"],
        "attempts_started":result["attempts_started"],
        "saved_receipts":len(result["receipts"]),
        "observed_spend_usd":result["observed_spend_usd"],
        "noncanonical":True,
        "canonical_commit_authorized":False,
    },ensure_ascii=False))


if __name__=="__main__":
    main()
