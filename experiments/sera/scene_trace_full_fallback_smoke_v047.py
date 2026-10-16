"""Run v0.47 scene continuity and fallback cases with NO paid model."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.sera.scene_trace_full_fallback_v047 import (
    verify_durable_replay,
)


def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--output-dir",type=Path,required=True)
    args=cli.parse_args()
    root=args.output_dir
    root.mkdir(parents=True,exist_ok=True)
    scenarios={
        "complete_rewritten_scene":("fallback",True),
        "ready_scene_after_model_fallback":("fallback",False),
        "both_receipted_models_invalid":("both_bad",False),
        "unknown_inflight_model_attempt":("unreceipted",False),
    }
    reports={}
    for name,(mode,rewrite) in scenarios.items():
        result=verify_durable_replay(root/name,mode=mode,rewrite=rewrite)
        reports[name]=result
        expected=("SCENE_CANDIDATE_READY_NONCANONICAL"
                  if mode=="fallback" else "FAILED_SAFE_FINAL")
        assert result["initial"]["status"]==expected, name
        assert result["stable_replay_without_new_model_or_writer"]
        assert result["replay"]["total_scripted_provider_calls_current_run"]==0
        assert result["replay"]["scripted_writer_calls_current_run"]==0
        assert result["initial"]["canonical_commit_authorized"] is False
        assert result["initial"]["real_external_model_calls"]==0
        assert result["initial"]["production_db_writes"]==0
        if mode=="unreceipted":
            assert result["initial"]["independent_fallback_sweep_responses"]==0
        if mode=="fallback":
            assert result["initial"]["first_model_bad_sweep_receipts"]>=1
            assert result["initial"]["independent_fallback_sweep_responses"]>=1
    report={
        "schema":"sera.v047-full-path-synthetic-lab-evidence",
        "status":"OFFLINE_AUTOMATIC_RECOVERY_AND_SAFE_STOP_VERIFIED_NONCANONICAL",
        "scenarios":reports,
        "new_real_provider_calls":0,"new_real_provider_spend_usd":"0",
        "source_story":"Ari/box two-sentence synthetic control, not Mara S1",
        "full_mara_independent_semantic_recall_proven":False,
        "production_db_writes":0,"sqlite_lab_writes":0,
        "canonical_commit_authorized":False,
    }
    (root/"proof.json").write_text(json.dumps(report,ensure_ascii=False,
                              sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":report["status"],
        "scenario_results":{k:{
            "status":v["initial"]["status"],
            "synthetic_provider_dispatches":
                v["initial"]["total_scripted_provider_calls_current_run"],
            "fallback_sweep_receipts":
                v["initial"]["independent_fallback_sweep_responses"],
            "scripted_rewrites":
                v["initial"]["scripted_writer_calls_current_run"],
            "replay_dispatches":
                v["replay"]["total_scripted_provider_calls_current_run"],
        } for k,v in reports.items()},
        "real_paid_requests":0,"canonical_commit_authorized":False,
    },ensure_ascii=False))


if __name__=="__main__":
    main()
