"""SERA v0.10 — finish six remaining Mara sentence groups, reuse paid batch 3.

Dry run by default. --live is one explicit isolated opt-in. The original
paid batch 003 is reused without another provider call and with original
request provenance preserved. On first provider/contract failure STOP, keep
immutable response and a resume queue. Never commit world or EventGraph.
No configured model-output token ceilings.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import argparse
import json
import os
from pathlib import Path

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_sweep_pilot_v010 import (
    prepare, one_provider_call, MODEL,
)
from experiments.sera.mara_s1_v010_forensics import (
    read_evidence, replay, PILOT_BATCH, PILOT_REQUEST_SHA,
)
from experiments.sera.sentence_sweep_v010 import (
    bind_batch, aggregate, summarize_partial,
)

OBSERVED_SPEND_STOP_USD = Decimal("0.12")
# Monetary stop is NOT an output-token limit.
MIN_KEY_REMAINING_USD = 0.25
MAX_NEW_PROVIDER_ATTEMPTS = 6  # exactly the number of missing source groups


def require(ok, code):
    if not ok:
        raise CoverageError(code)


def make_resume_plan(*, pilot_evidence: dict) -> dict:
    preflight = prepare()
    plan = preflight["plan"]
    forensic = replay(evidence=pilot_evidence)
    history = bind_batch(
        plan=plan, batch_id=PILOT_BATCH,
        raw=pilot_evidence["raw_extraction"], prose=preflight["prose"],
    )
    pending = summarize_partial(plan=plan,bound_batches=[history])
    require(pending["pending_batch_ids"] and
            len(pending["pending_batch_ids"]) == MAX_NEW_PROVIDER_ATTEMPTS,
            "SWEEP_SIX_REMAINING_BATCHES_NOT_PINNED")
    return {
        "preflight": preflight,
        "historic_bound": history,
        "historic_forensics": forensic,
        "remaining": pending["pending_batch_ids"],
    }


def _persist(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(path.suffix+".stage")
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",
                   encoding="utf-8")
    tmp.replace(path)


def run(*, output_dir: Path, launch_id: str, key: str,
        pilot_evidence: dict) -> dict:
    if output_dir.exists():
        raise CoverageError("SWEEP_OUTPUT_DIRECTORY_EXISTS")
    start = make_resume_plan(pilot_evidence=pilot_evidence)
    source = start["preflight"]
    plan = source["plan"]
    bound = [start["historic_bound"]]
    remaining = start["remaining"]
    output_dir.mkdir(parents=True,exist_ok=False)
    out = {
        "schema": "sera.mara-full-scene-sweep.v0.10",
        "launch_id": launch_id, "scene_key": plan["scene_key"],
        "source_prose_sha256": plan["source_prose_sha256"],
        "model": MODEL,
        "source_sentence_count": plan["sentence_count"],
        "source_batch_count": len(plan["batches"]),
        "reused_original_pilot_batch": PILOT_BATCH,
        "reused_original_request_sha256": PILOT_REQUEST_SHA,
        "historical_provider_cost_usd":
            pilot_evidence.get("provider_reported_cost"),
        "pending_batch_ids": remaining[:],
        "completed_batch_ids": [PILOT_BATCH],
        "new_provider_attempts": 0,
        "max_new_provider_attempts": MAX_NEW_PROVIDER_ATTEMPTS,
        "new_provider_cost_usd": 0.0,
        "reported_usage_complete": True,
        "provider_diagnostics": [],
        "status": "PREFLIGHT_HOLD",
        "error_code": None,
        "model_output_token_cap_configured": False,
        "semantic_completeness_proven": False,
        "canonical_commit_authorized": False,
        "world_db_writes": 0,
    }
    manifest=output_dir/"manifest.json"
    _persist(manifest,out)
    try:
        if not key:
            raise CoverageError("SWEEP_KEY_MISSING")
        from src.openrouter_preflight import (
            fetch_key_status, enforce_key_access,
        )
        enforce_key_access(
            fetch_key_status(key), min_remaining=MIN_KEY_REMAINING_USD,
        )
        cost = Decimal("0")
        for b in plan["batches"]:
            if b["batch_id"] == PILOT_BATCH:
                continue
            if cost >= OBSERVED_SPEND_STOP_USD:
                raise CoverageError("SWEEP_OBSERVED_DOLLAR_SPEND_STOP")
            require(out["new_provider_attempts"] <
                    MAX_NEW_PROVIDER_ATTEMPTS,
                    "SWEEP_CALL_COUNT_BREACH")
            # Request exactly one immutable source group; no model-specific
            # reasoning flags, fallback or artificial output-token ceiling.
            diag = {
                "batch_id": b["batch_id"],
                "request_sha256": b["request_sha256"],
                "source_prose_sha256": plan["source_prose_sha256"],
                "response_format": b["response_format"],
                "provider_attempted": True,
                "status": "ATTEMPTING",
                "provider_usage": None,
                "provider_reported_cost": None,
                "raw_content": None,
                "raw_extraction": None,
                "bound_batch": None,
                "canonical_commit_authorized": False,
            }
            batch_file=output_dir/(b["batch_id"]+".json")
            _persist(batch_file,diag)
            out["new_provider_attempts"]+=1
            out["status"]="IN_PROGRESS_NO_CANONICAL_WRITES"
            _persist(manifest,out)
            response=one_provider_call(
                key=key,
                prepared={"request":{
                    "messages":b["messages"],
                    "response_format":b["response_format"],
                }},
            )
            if response["error"]:
                diag["status"]="PROVIDER_ERROR_HOLD"
                diag["error_code"]=response["error"]
                diag["provider_detail"]=response.get("provider_detail")
                _persist(batch_file,diag)
                raise CoverageError(
                    f"SWEEP_PROVIDER_ERROR:{b['batch_id']}:{response['error']}"
                )
            raw=response["raw"]
            diag["response_id"]=raw.get("id")
            diag["observed_model"]=raw.get("model")
            diag["provider_usage"]=raw.get("usage")
            choices=raw.get("choices")
            if not isinstance(choices,list) or len(choices)!=1:
                diag["status"]="PROVIDER_CHOICES_HOLD"
                _persist(batch_file,diag)
                raise CoverageError("SWEEP_PROVIDER_CHOICES_INVALID")
            choice=choices[0]
            diag["finish_reason"]=choice.get("finish_reason")
            diag["raw_content"]=(choice.get("message") or {}).get("content")
            diag["provider_reported_cost"]=(
                raw["usage"].get("cost")
                if isinstance(raw.get("usage"),dict) else None
            )
            _persist(batch_file,diag)
            # Without reported cost, do not continue a multi-call run.
            if diag["provider_reported_cost"] is None:
                diag["status"]="COST_UNREPORTED_HOLD"
                out["reported_usage_complete"]=False
                _persist(batch_file,diag)
                raise CoverageError("SWEEP_PROVIDER_COST_UNKNOWN_STOP")
            try:
                charge=Decimal(str(diag["provider_reported_cost"]))
            except InvalidOperation:
                raise CoverageError("SWEEP_PROVIDER_COST_INVALID") from None
            require(charge.is_finite() and charge>=0,
                    "SWEEP_PROVIDER_COST_INVALID")
            cost+=charge
            out["new_provider_cost_usd"]=float(cost)
            if diag["finish_reason"]!="stop":
                diag["status"]="PROVIDER_INCOMPLETE_HOLD"
                _persist(batch_file,diag)
                raise CoverageError("SWEEP_PROVIDER_FINISH_NOT_STOP")
            if not isinstance(diag["raw_content"],str):
                raise CoverageError("SWEEP_PROVIDER_CONTENT_INVALID")
            try:
                parsed=json.loads(diag["raw_content"])
            except ValueError:
                raise CoverageError("SWEEP_PROVIDER_JSON_INVALID") from None
            diag["raw_extraction"]=parsed
            _persist(batch_file,diag)
            result=bind_batch(
                plan=plan,batch_id=b["batch_id"],raw=parsed,
                prose=source["prose"],
            )
            diag["bound_batch"]=result
            diag["status"]="SOURCE_BOUND_NONCANONICAL_CANDIDATES"
            _persist(batch_file,diag)
            bound.append(result)
            out["completed_batch_ids"].append(b["batch_id"])
            out["pending_batch_ids"].remove(b["batch_id"])
            out["provider_diagnostics"].append({
                "batch_id":b["batch_id"],
                "reported_cost":diag["provider_reported_cost"],
                "event_candidates":sum(len(x["events"]) for x in result["rows"]),
                "candidate_mentions":sum(len(x["mentions"]) for x in result["rows"]),
            })
            _persist(manifest,out)
        final=aggregate(
            plan=plan,bound_batches=bound,prose=source["prose"],
        )
        _persist(output_dir/"full_scene_assurance.json",final)
        out["status"]="ALL_28_SENTENCES_EXTRACTED_SEMANTIC_HOLD"
        out["candidate_events"]=len(final["candidate_events"])
        out["targeted_probe_count"]=len(final["targeted_probes"])
        out["finding_count"]=len(final["findings"])
        out["all_sentences_accounted_for"]=final["sentences_accounted_for"]
    except Exception as exc:
        out["status"]="INCOMPLETE_SOURCE_DIAGNOSTIC_HOLD"
        out["error_code"]=str(exc)[:300]
        out["recovery_queue"]=summarize_partial(
            plan=plan,bound_batches=bound,
        )
    _persist(manifest,out)
    return out


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--pilot-evidence",required=True,type=Path)
    parser.add_argument("--output-dir",type=Path)
    parser.add_argument("--live",action="store_true")
    parser.add_argument("--launch-id",default="dry-run")
    args=parser.parse_args()
    old=read_evidence(args.pilot_evidence)
    staged=make_resume_plan(pilot_evidence=old)
    if not args.live:
        print(json.dumps({
            "mode":"DRY_RUN_NO_PROVIDER_CALL",
            "source_sha256":staged["preflight"]["plan"]["source_prose_sha256"],
            "original_paid_request_sha256":PILOT_REQUEST_SHA,
            "reused_existing_batch":PILOT_BATCH,
            "remaining_batch_ids":staged["remaining"],
            "remaining_sentences":24,
            "new_model_output_token_limit":"NOT_SET_BY_APPLICATION",
            "world_db_writes":0,
        },ensure_ascii=False,indent=2))
        return
    if args.output_dir is None:
        parser.error("--live requires --output-dir")
    report=run(
        output_dir=args.output_dir, launch_id=args.launch_id,
        key=os.getenv("OPENROUTER_API_KEY",""),
        pilot_evidence=old,
    )
    print(json.dumps({
        "status":report["status"],
        "new_provider_attempts":report["new_provider_attempts"],
        "new_provider_cost_usd":report["new_provider_cost_usd"],
        "completed_batch_ids":report["completed_batch_ids"],
        "pending_batch_ids":report["pending_batch_ids"],
        "error_code":report.get("error_code"),
        "candidate_events":report.get("candidate_events"),
        "targeted_probe_count":report.get("targeted_probe_count"),
        "world_db_writes":0,
        "canonical_commit_authorized":False,
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
