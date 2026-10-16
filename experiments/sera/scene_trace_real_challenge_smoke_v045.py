"""SERA v0.45 real paid evidence + OFFLINE automatic independent retry smoke.

All risk cards come from authentic earlier paid Mara receipts. No new paid
model execution. The callback is explicitly scripted and must not be
mistaken for independent real-model competence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.sera.real_blind_benchmark_v040 import prepare
from experiments.sera.scene_trace_evidence_challenge_v044 import compare_receipts
from experiments.sera.scene_trace_autorepair_v045 import execute


def synthetic_source_only_double(*, request, task_id, attempt, failure_codes):
    """Fault injection on first result, correction from the same source."""
    source=json.loads(request["messages"][1]["content"])["target_sentence"]
    assert "prior_model" not in str(request)
    assert "rule_code" not in str(request)
    assert "CHANGE_STATE" not in str(request)
    assert "target_sentence" in str(request)
    if "pocket watch open in his palm" in source:
        kind="STATIC_STATE_DESCRIPTION"
    elif "watched the pencil move" in source:
        kind="OBSERVED_MOTION_CAUSE_UNKNOWN"
    else:
        raise AssertionError("V045_UNEXPECTED_REAL_MODEL_SOURCE")
    if attempt==1 and "pencil" in source:
        # Prove automatic second extraction can repair a BAD quote using
        # original source, not a model-invented transition or human edit.
        return {
            "source_quote":"Vane teleported to the pencil.",
            "interpretation":"PHYSICAL_ACTION_WITH_EXPLICIT_ACTOR",
            "actor_id":"vane",
            "transition_proven":True,
            "reason":"intentionally false synthetic first reply",
        }
    if attempt>1 and "pencil" in source:
        assert failure_codes
    return {
        "source_quote":source,
        "interpretation":kind,
        "actor_id":None,
        "transition_proven":False,
        "reason":"offline synthetic independent-source candidate only",
    }


def smoke(*,bench_dir,pencil_dir,output_root):
    proof=compare_receipts(bench_dir=bench_dir,pencil_dir=pencil_dir)
    frozen=prepare()["prose"]
    result=execute(
        proof=proof,prose=frozen,
        output_dir=Path(output_root)/"durable-worker",
        synthetic_source_reply=synthetic_source_only_double,
    )
    assert result["status"]=="SOURCE_BOUND_REPAIR_ADVISORIES_ONLY"
    assert result["task_count"]==2
    assert len(result["source_bound_advisories"])==2
    assert len(result["attempts"])==3
    assert result["paid_provider_calls"]==0
    assert result["canonical_commit_authorized"] is False
    assert result["production_db_writes"]==0
    return {
        "schema":"sera.scenetrace-v045-real-receipts-synthetic-repair.v0.45",
        "status":"REAL_CHALLENGES_SYNTHETIC_REPAIR_VERIFIED_NONCANONICAL",
        "input_real_model_runs":proof["archived_real_runs"],
        "risk_cards":[{"model":x["model"],"source":x["sentence_id"],
                       "missing_evidence":x["missing_evidence"]}
                      for x in proof["challenges"]],
        "synthetic_worker_result":result,
        "paid_model_calls_new":0,
        "new_provider_cost_usd":"0",
        "independent_real_semantics_proven":False,
        "canonical_commit_authorized":False,
        "production_db_writes":0,
        "sqlite_lab_writes":0,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--bench-receipt-dir",type=Path,required=True)
    p.add_argument("--pencil-receipt-dir",type=Path,required=True)
    p.add_argument("--output-root",type=Path,required=True)
    args=p.parse_args()
    proof=smoke(
        bench_dir=args.bench_receipt_dir,
        pencil_dir=args.pencil_receipt_dir,
        output_root=args.output_root,
    )
    output=args.output_root/"summary.json"
    output.write_text(json.dumps(proof,ensure_ascii=False,indent=2,
                                 sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":proof["status"],
        "source_risks":len(proof["risk_cards"]),
        "attempts":proof["synthetic_worker_result"]["attempts"],
        "new_paid_calls":0,
        "real_semantic_qualification":False,
        "canonical_commit_authorized":False,
    },ensure_ascii=False))


if __name__=="__main__":
    main()
