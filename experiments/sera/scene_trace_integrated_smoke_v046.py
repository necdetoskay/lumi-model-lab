"""SERA v0.46: actual paid Mara risk provenance -> scripted full SERA safety path.

Exercises the *real* v0.18 source quote binder and v0.22 fresh evidence
worker using a deliberately insufficient FULL-SCENE scripted answer. The
correct result is terminal FAILED_SAFE_FINAL, not an invented pass.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.sera.request_policy import enforce_no_output_token_limit
from experiments.sera.scene_trace_integrated_lab_v046 import orchestrate
from experiments.sera.scene_trace_real_challenge_smoke_v045 import (
    synthetic_source_only_double,
)

COUNTER = {"semantic":0,"full":0}


def synthetic_v018_semantic(*,prepared,task_id):
    """v0.11/v0.18 judge double receives ONLY original source text."""
    enforce_no_output_token_limit(prepared)
    source=json.loads(prepared["messages"][1]["content"])
    assert "exact_chronological_sentences" in source
    assert source["source_prose_sha256"]
    assert "risk_code" not in str(source)
    assert "prior_model" not in str(source)
    quote=source["exact_chronological_sentences"][0]["quote"]
    COUNTER["semantic"]+=1
    return {
        "choices":[{"finish_reason":"stop","message":{"content":json.dumps({
            "verdict":"STATE_OBSERVATION",
            "operation_kind":"OBSERVE",
            "effect":"NONE",
            "evidence_quote":quote,
            "reason":"scripted quote-binding test; not independent model truth",
        })}}],
    }


def intentionally_incomplete_full_sweep(*,key,model,prepared):
    """Read-only model double; real v0.22 must reject fake full coverage."""
    enforce_no_output_token_limit(prepared["request"])
    assert key=="OFFLINE_TEST_DOUBLE_NEVER_SENT_TO_PROVIDER"
    COUNTER["full"]+=1
    return {
        "error":None,
        "raw":{
            "id":f"synthetic-v046-incomplete-{COUNTER['full']}",
            "model":model,
            "usage":{"cost":"0"},
            "choices":[{"finish_reason":"stop",
                        "message":{"content":json.dumps({"rows":[]})}}],
        },
    }


def smoke(*,bench_dir,pencil_dir,root):
    result=orchestrate(
        bench_dir=bench_dir,pencil_dir=pencil_dir,
        work_root=root,
        synthetic_repair_reply=synthetic_source_only_double,
        synthetic_semantic_reply=synthetic_v018_semantic,
        synthetic_full_extraction_reply=intentionally_incomplete_full_sweep,
    )
    return {
        "schema":"sera.v046-real-risk-full-evidence-failsafe-smoke",
        "result":result,
        "synthetic_semantic_calls_this_execution":COUNTER["semantic"],
        "synthetic_full_sweep_calls_this_execution":COUNTER["full"],
        "new_paid_provider_calls":0,
        "world_db_writes":0,
    }


def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--bench-receipt-dir",type=Path,required=True)
    cli.add_argument("--pencil-receipt-dir",type=Path,required=True)
    cli.add_argument("--output-root",type=Path,required=True)
    args=cli.parse_args()
    args.output_root.mkdir(parents=True,exist_ok=True)
    first=smoke(
        bench_dir=args.bench_receipt_dir,
        pencil_dir=args.pencil_receipt_dir,root=args.output_root,
    )
    # Replay to prove v0.45/v0.18/v0.22 receipt reuse across all stages.
    prior_semantic=COUNTER["semantic"]
    prior_full=COUNTER["full"]
    again=smoke(
        bench_dir=args.bench_receipt_dir,
        pencil_dir=args.pencil_receipt_dir,root=args.output_root,
    )
    assert again["result"]==first["result"]
    assert COUNTER["semantic"]==prior_semantic
    assert COUNTER["full"]==prior_full
    output={
        **first,
        "repeat_read_only_result_identical":True,
        "repeat_semantic_scripted_calls":0,
        "repeat_full_sweep_scripted_calls":0,
    }
    (args.output_root/"v046-proof.json").write_text(
        json.dumps(output,ensure_ascii=False,sort_keys=True,
                   indent=2)+"\n",encoding="utf-8",
    )
    print(json.dumps({
        "status":output["result"]["status"],
        "reason":output["result"]["reason_code"],
        "repair":output["result"]["repair_stage_status"],
        "v018":output["result"]["targeted_semantic_stage_status"],
        "v022":output["result"]["full_fresh_v022_stage_status"],
        "v022_failure":output["result"]["full_fresh_v022_failure_code"],
        "initial_semantic_scripted_calls":
            output["synthetic_semantic_calls_this_execution"],
        "initial_full_sweep_scripted_calls":
            output["synthetic_full_sweep_calls_this_execution"],
        "repeat_calls":0,
        "new_paid_calls":0,
        "canonical_commit_authorized":False,
    },ensure_ascii=False))


if __name__=="__main__":
    main()
