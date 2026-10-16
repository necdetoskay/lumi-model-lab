"""v0.50 actual v0.48 14 paid receipts -> 26 scripted automatic repair stages.

Uses ORIGINAL real source provenance, but NO NEW provider inference. No
manual repair/resume/event approval gate. Scripted model never grants truth.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.sera.automated_row_recovery_v050 import execute
from experiments.sera.real_mara_recovery_queue_v049 import (
    verified_real_receipts,build_work_orders,
)
from experiments.sera.tests.test_automated_row_recovery_v050 import (
    scripted_provider,
)


def smoke(*,receipt_root,output_root):
    source,receipts,coverage,paid=verified_real_receipts(receipt_root)
    audit,tasks=build_work_orders(
        source=source,receipts=receipts,coverage=coverage,
    )
    root=Path(output_root)
    calls=[]
    provider=scripted_provider(calls,invalid_first={"s006","s004"})
    original=execute(
        source=source,audit=audit,tasks=tasks,
        output_root=root/"worker",scripted_provider=provider,
    )
    count=len(calls)
    replay=execute(
        source=source,audit=audit,tasks=tasks,
        output_root=root/"worker",
        scripted_provider=lambda **kw:(_ for _ in ()).throw(
            AssertionError("V050_REPLAY_MUST_NOT_REPOST_PROVIDER")
        ),
    )
    assert replay==original
    assert len(calls)==count
    assert original["status"]==\
           "SOURCE_CANDIDATES_READY_FOR_FULL_REEXTRACTION_NONCANONICAL"
    assert original["candidate_source_rows_reextracted"]==5
    assert original["source_blind_advisories"]==21
    assert original["scripted_fallback_attempts_this_run"]==2
    assert original["tasks_accounted_for"]==26
    assert original["world_db_writes"]==0
    assert original["requires_manual_intervention"] is False
    assert original["real_new_paid_calls"]==0
    proof={
        "schema":"sera.v050-real-provenance-automatic-scripted-repair-proof",
        "status":"SCRIPTED_AUTONOMOUS_REEXTRACTION_AND_INDEPENDENT_REVIEW_NONCANONICAL",
        "real_source_run_id":38957808652,
        "immutable_real_provider_receipts_verified":14,
        "previous_paid_cost_usd":paid["observed_spend_usd"],
        "new_paid_calls":0,"new_paid_usd":"0",
        "reextracted_source_rows_scripted_only":5,
        "source_blind_independent_advisories_scripted_only":21,
        "fallbacks_after_fully_received_invalid_source":2,
        "scripted_provider_attempts":count,
        "replay_provider_attempts":0,
        "same_results_after_restart":True,
        "automatic_replan_for_unresolved_supported":True,
        "genuine_full_28_sentence_semantic_correctness_proven":False,
        "canonical_commit_authorized":False,
        "world_db_writes":0,
        "requires_manual_intervention":False,
        "next_action":"AUTO_FULL_SCENE_REEXTRACTION_AND_REVALIDATION_REQUIRED",
    }
    root.mkdir(parents=True,exist_ok=True)
    (root/"proof.json").write_text(json.dumps(
        proof,ensure_ascii=False,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )
    print(json.dumps(proof,ensure_ascii=False,sort_keys=True))
    return proof


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--receipt-root",type=Path,required=True)
    p.add_argument("--output-root",type=Path,required=True)
    args=p.parse_args()
    smoke(receipt_root=args.receipt_root,output_root=args.output_root)


if __name__=="__main__":
    main()
