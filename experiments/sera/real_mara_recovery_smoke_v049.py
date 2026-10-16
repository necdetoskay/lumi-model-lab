"""v0.49 run against 14 ORIGINAL real receipts, no billing."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.sera.real_mara_recovery_queue_v049 import (
    save_plan,execute_scripted,
)


def offline_scripted_reviewer(*,task_id,prepared):
    """Reproduce source quote ONLY. NOT a model's independent semantics."""
    prompt=json.loads(prepared["messages"][1]["content"])
    assert prompt["task_id"]==task_id
    sentence=prompt["exact_chronological_sentences"][0]["quote"]
    return {"choices":[{
        "finish_reason":"stop",
        "message":{"content":json.dumps({
            "verdict":"UNCERTAIN",
            "operation_kind":"UNMAPPED",
            "effect":"UNKNOWN",
            "evidence_quote":sentence,
            "reason":"Source-only scripted test double; not semantic gold",
        })},
    }]}


def run(*,receipt_root,output_root):
    root=Path(output_root)
    plan=save_plan(receipt_root=receipt_root,output_root=root)
    first=execute_scripted(
        prepared=plan,output_root=root/"scripted",
        synthetic_reply=offline_scripted_reviewer,
    )
    replay=execute_scripted(
        prepared=plan,output_root=root/"scripted",
        synthetic_reply=lambda **kw:(_ for _ in ()).throw(
            AssertionError("V049_ARCHIVED_RECEIPT_MUST_NOT_RECALL_PROVIDER")
        ),
    )
    assert first["status"]=="SOURCE_BOUND_MODEL_ADVISORIES_NONCANONICAL"
    assert first["bound_task_count"]==26
    assert first["scripted_model_calls_this_run"]==26
    assert replay["bound_task_count"]==26
    assert replay["scripted_model_calls_this_run"]==0
    assert first["task_advisories"]==replay["task_advisories"]
    assert plan["manifest"]["quarantined_source_reextract_tasks"]==5
    assert plan["manifest"]["independent_disagreement_review_tasks"]==21
    result={
        "schema":"sera.v049-real-mara-offline-challenge-smoke",
        "status":"REAL_SOURCE_TASKS_READY_SCRIPTED_REVIEW_ONLY",
        "real_model_provenance_run":plan["manifest"]["real_run_id"],
        "archived_real_model_responses_verified":14,
        "quarantined_haiku_rows":5,
        "cross_model_candidate_disagreement_tasks":21,
        "source_blind_independent_review_requests":26,
        "scripted_review_bound_responses":first["bound_task_count"],
        "scripted_review_requests_replayed":replay["bound_task_count"],
        "extra_model_calls_on_replay":replay["scripted_model_calls_this_run"],
        "new_paid_provider_calls":0,
        "additional_real_model_semantic_fixes":0,
        "true_mara_physical_qualification":False,
        "world_commit_authorized":False,
        "production_db_writes":0,
        "sqlite_world_db_writes":0,
    }
    (root/"proof.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )
    return result


def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--receipt-root",required=True,type=Path)
    cli.add_argument("--output-root",required=True,type=Path)
    args=cli.parse_args()
    report=run(receipt_root=args.receipt_root,output_root=args.output_root)
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()
