"""SERA v0.47 — v0.22 real fallback + v0.20 full recheck, offline success path.

Unlike v0.46, test a REPAIRABLE fully-receipted incomplete sweep: first
scripted extraction returns {rows: []}, then the distinct fallback model
returns an exact v0.10 source-bound candidate. v0.22 independently produces
a complete source/world evidence bundle. v0.21 check and v0.20 autonomous
scene rewrite+recheck are real SERA modules, not mocked success decisions.

Uses existing 2-sentence v0.22 synthetic Ari/box fixture, NOT Mara S1's
unreviewed 20 sentences. NO paid provider inference or semantic gold claim.
Never treats synthetic provider usage.cost as actual USD billed.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

from experiments.sera.artifact_scene_checker_v021 import create_checker
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.fresh_scene_evidence_worker_v022 import create_preparer
from experiments.sera.scene_trace_shadow_v042 import build_trace
from experiments.sera.tests.test_fresh_scene_evidence_worker_v022 import (
    SOURCE_1, SOURCE_2, EXTRACT, SEMANTIC, TYPED, entry, fake_model,
)
from experiments.sera.unattended_scene_rewrite_v020 import execute as scene_loop

SCHEMA = "sera.scenetrace-v047-full-scene-fallback-v020-v022-lab"
FALLBACK = "synthetic/v047-independent-extractor-fallback"


def _check(cond,code):
    if not cond:
        raise CoverageError(code)


def initial_failure_then_fallback(calls, *, mode="fallback"):
    """Transport double with authentic v0.22 request/envelope semantics.

    "fallback": the first, fully receipted model reply is structurally bad.
    "both_bad": both providers return invalid rows; do NOT claim readiness.
    "unreceipted": first dispatch has unknown charge/no receipt; no retry.
    """
    _check(mode in ("fallback","both_bad","unreceipted"),
           "V047_INVALID_LAB_MODE")
    existing=fake_model([])
    def provider(*,key,model,prepared):
        request=prepared["request"]
        wire=json.dumps(request,ensure_ascii=False)
        _check(all(p not in wire for p in (
            "max_tokens","max_output_tokens","max_completion_tokens",
            "max_generation_tokens","max_new_tokens")),
            "V047_OUTPUT_TOKEN_LIMIT_FORBIDDEN")
        _check(key=="SYNTHETIC_NEVER_USED_NETWORK",
               "V047_PROVIDER_KEY_MUST_BE_SYNTHETIC")
        source_input=json.loads(request["messages"][1]["content"])
        stage=("SWEEP" if "target_sentences" in source_input else
               "TYPED" if "original_prose" in source_input else "SEMANTIC")
        calls.append({"model":model,"stage":stage,
                      "request_sha256":prose_hash(wire)})
        if stage=="SWEEP" and model==EXTRACT and mode=="unreceipted":
            raise ConnectionError("synthetic uncertain request outcome")
        if stage=="SWEEP" and (model==EXTRACT or mode=="both_bad"):
            return {"error":None,"raw":{
                "id":f"v047-fully-receipted-bad-{len(calls)}",
                "model":model,"usage":{"cost":"0.001"},
                "choices":[{"finish_reason":"stop",
                            "message":{"content":'{"rows":[]}'}}],
            }}
        out=existing(key=key,model=model,prepared=prepared)
        return out
    return provider


def _trace(prose):
    scene_id=("ari-box-original" if prose==SOURCE_1 else
              "ari-box-revised")
    return build_trace(
        prose=prose,scene_id=scene_id,
        registry={"ari":["Ari"],"box":["box"]},
        candidate_lexicon={},
    )


def one_synthetic_trial(root, *, mode="fallback", rewrite=True):
    root=Path(root)
    root.mkdir(parents=True,exist_ok=True)
    calls=[]
    provider=initial_failure_then_fallback(calls,mode=mode)
    worker=create_preparer(
        evidence_root=root/"evidence",work_root=root/"worker",
        scene_key=f"v047-{mode}-{'rewrite' if rewrite else 'ready'}",
        registry={"ari":["Ari"],"box":["box"]},
        candidate_lexicon={},
        typed_registry={"openables":["box"],"documents":[]},
        api_key="SYNTHETIC_NEVER_USED_NETWORK",
        extraction_model=EXTRACT,
        semantic_model=SEMANTIC,typed_model=TYPED,
        fallback_model=FALLBACK,
        provider_call=provider,
        max_model_requests=16,
        observed_spend_guard_usd="0.30",
    )
    writer_calls=[]
    def synthetic_writer(*,source,defects):
        writer_calls.append({"source_sha256":prose_hash(source),
                             "defect_count":len(defects)})
        _check(source==SOURCE_1,
               "V047_SCRIPTED_REWRITE_SOURCE_NOT_EXPECTED")
        return {"prose":SOURCE_2,
                "receipt":{
                    "source_prose_sha256":prose_hash(source),
                    "response_id":"synthetic-v047-rewrite",
                    "model":"synthetic/v047-writer",
                    "finish_reason":"stop",
                    "cost_usd":"0",
                }}
    source=SOURCE_1 if rewrite else SOURCE_2
    world=entry()
    out=scene_loop(
        prose=source,world=world,
        check_scene=create_checker(evidence_root=root/"evidence"),
        rewrite_scene=synthetic_writer,
        prepare_evidence=worker,
        evidence_policy_id=f"v047-{mode}-reuse-actual-v022-validator",
        output_dir=root/"controller",
        max_rewrites=2 if rewrite else 0,
    )
    ready=out.get("status")=="SCENE_CANDIDATE_READY_NONCANONICAL"
    if ready:
        _check((root/"evidence"/(prose_hash(SOURCE_2)+".json")).exists(),
               "V047_REVISED_SOURCE_EVIDENCE_MISSING")
    # Distinct source checkpoints should exist for a rewrite.
    traces=[_trace(SOURCE_1),_trace(SOURCE_2)] if rewrite else [_trace(SOURCE_2)]
    for trace in traces:
        _check(trace["canonical_commit_authorized"] is False and
               trace["source_sentence_count"]==2 and
               trace["external_model_calls"]==0 and
               trace["newly_validated_state_changes"]==0,
               "V047_UNAUTHORIZED_SCENE_TRACE_AUTHORITY")
    counts=dict(Counter((c["model"],c["stage"]) for c in calls))
    primary_bad=counts.get((EXTRACT,"SWEEP"),0)
    fallback_good=counts.get((FALLBACK,"SWEEP"),0)
    return {
        "schema":SCHEMA,"mode":mode,"rewrite_enabled":rewrite,
        "status":out["status"],
        "controller_result":out,
        "first_model_bad_sweep_receipts":primary_bad,
        "independent_fallback_sweep_responses":fallback_good,
        "total_scripted_provider_calls_current_run":len(calls),
        "scripted_writer_calls_current_run":len(writer_calls),
        "synthetic_writer_events":writer_calls,
        "source_before_sha256":prose_hash(source),
        "source_after_sha256":prose_hash(SOURCE_2) if ready else None,
        "trace_sentence_counts":[x["source_sentence_count"] for x in traces],
        "trace_atoms_by_scene":[x["atom_count"] for x in traces],
        "real_model_causal_validation":False,
        "synthetic_success_is_not_mara_g2_approval":True,
        "real_external_model_calls":0,
        "actual_spend_usd":"0",
        "canonical_commit_authorized":False,
        "production_db_writes":0,
        "sqlite_lab_writes":0,
    }


def verify_durable_replay(root, *, mode="fallback", rewrite=True):
    root=Path(root)
    first=one_synthetic_trial(root,mode=mode,rewrite=rewrite)
    next_result=one_synthetic_trial(root,mode=mode,rewrite=rewrite)
    _check(first["controller_result"]==next_result["controller_result"] and
           next_result["total_scripted_provider_calls_current_run"]==0 and
           next_result["scripted_writer_calls_current_run"]==0,
           "V047_COMPLETED_RECEIPT_REPLAY_DISPATCHED_AGAIN")
    return {"initial":first,"replay":next_result,
            "stable_replay_without_new_model_or_writer":True}
