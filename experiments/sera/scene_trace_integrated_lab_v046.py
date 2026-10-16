"""SERA v0.46 — compose real SceneTrace risk receipts with actual v0.18/v0.22 seams.

All independent replies here are SCRIPTED OFFLINE TEST DOUBLES. They are
never provider truth, and no provider API key is requested. Mara S1's original
v0.40/41 real responses establish the two risk cards, but NOT scene coverage.

Pipeline: original receipts -> v0.44 source-bound risks -> v0.45 durable
automatic repair -> v0.11/v0.18 source-only semantic request+real binder ->
v0.22 actual full-scene preparer. v0.22 deliberately receives a malformed
scripted full-scene answer and MUST terminate without a world write. This
tests real control handoff under incomplete independent extraction, NOT
successful whole-story repair. No model output token ceiling, no human gate.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.fresh_scene_evidence_worker_v022 import create_preparer
from experiments.sera.mara_s1_typed_live_v05 import REGISTRY, entry_state
from experiments.sera.real_blind_benchmark_v040 import EXPECTED_SHA, LEXICON, prepare
from experiments.sera.request_policy import enforce_no_output_token_limit
from experiments.sera.scene_trace_autorepair_v045 import (
    execute as repair, _write, _read, digest,
)
from experiments.sera.scene_trace_evidence_challenge_v044 import compare_receipts
from experiments.sera.semantic_recovery_v018 import _bind as source_bind
from experiments.sera.semantic_risks_v011 import make_task_request
from experiments.sera.world_state_v02 import canonical

SCHEMA = "sera.scene-trace-v018-v022-shadow-orchestration.v0.46"
MODEL_SEMANTIC = "synthetic/independent-semantic-v046"
MODEL_EXTRACTION = "synthetic/fail-incomplete-sweep-v046"
MODEL_TYPED = "synthetic/not-reached-typed-v046"


def check(ok,code):
    if not ok:
        raise CoverageError(code)


def _audit_from_real_challenges(*, risk_proof, prose):
    """Build v0.11 audit, not a fabricated v0.10 full-scene extraction."""
    check(risk_proof.get("original_source_sha256")==prose_hash(prose) and
          risk_proof.get("model_response_challenge_count")==2 and
          risk_proof.get("canonical_commit_authorized") is False and
          risk_proof.get("additional_paid_model_requests")==0 and
          len(risk_proof["challenges"])==2,
          "V046_REAL_RISK_SCOPE_INVALID")
    tasks=[]
    for i,c in enumerate(risk_proof["challenges"],1):
        part=c["source_evidence_span"]
        check(type(part["start"]) is int and
              type(part["end"]) is int and
              prose[part["start"]:part["end"]]==part["quote"],
              "V046_UNVERIFIED_RISK_SOURCE_SPAN")
        # The question is deliberately generic, not the previous proposal
        # or its expected answer; the prior model may not teach the judge.
        sentence=c["source_sentence"]
        start=prose.find(sentence)
        check(start>=0 and prose.find(sentence,start+1)<0,
              "V046_SOURCE_SENTENCE_AMBIGUOUS")
        tasks.append({
            "task_id":f"task_{i:03d}",
            "finding_code":"EXTERNAL_SOURCE_BOUND_SCENETRACE_RISK",
            "target_sentence_ids":[c["sentence_id"]],
            "trigger":"INDEPENDENT_SOURCE_REVIEW",
            "exact_source_context":[{
                "sentence_id":c["sentence_id"],"start":start,
                "end":start+len(sentence),"quote":sentence,
            }],
            "independent_review_question":(
                "Which physical transition, speaker, observer or causal "
                "actor is explicitly established by this sentence? "
                "Do not infer hidden actions. Answer UNCERTAIN when needed."
            ),
            "explanation":"source-only autonomous shadow review",
            "no_prior_model_answer_in_prompt":True,
            "canonical_commit_authorized":False,
        })
    return {
        "schema":"sera.semantic-risk-audit.v0.11",
        "source_prose_sha256":prose_hash(prose),
        "targeted_tasks":tasks,
        "targeted_task_count":len(tasks),
        "candidate_event_count":0,
        "canonical_commit_authorized":False,
    }


def _source_bound_semantics(*, risk_proof, prose, output_root, synthetic_reply):
    """Use genuine v0.11 task request and v0.18 exact-source binder.

    Persistent results use the *completed* replay receipt, not a new model
    call. STARTED without a receipt is a safe terminal failure, not resend.
    """
    audit=_audit_from_real_challenges(risk_proof=risk_proof,prose=prose)
    root=Path(output_root)
    contract={
        "schema":"sera.scene-trace-v018-bridge-contract.v0.46",
        "source_sha256":prose_hash(prose),
        "risk_sha256":digest(risk_proof),
        "model":MODEL_SEMANTIC,
        "transport":"OFFLINE_SCRIPTED_NO_PROVIDER",
    }
    if (root/"contract.json").exists():
        check(_read(root/"contract.json")==contract,
              "V046_SEMANTIC_BRIDGE_CONTRACT_DRIFT")
    else:
        _write(root/"contract.json",contract)
    accepted=[]
    dispatches=0
    for task in audit["targeted_tasks"]:
        request=make_task_request(audit=audit,task_id=task["task_id"])
        payload={
            "messages":request["messages"],
            "response_format":request["response_format"],
        }
        enforce_no_output_token_limit(payload)
        number=task["task_id"]
        root_id=root/number
        started=root_id.with_suffix(".started.json")
        reply_path=root_id.with_suffix(".reply.json")
        identity={
            "task_id":number,"source_sha256":prose_hash(prose),
            "request_sha256":request["request_sha256"],"model":MODEL_SEMANTIC,
        }
        if reply_path.exists():
            check(started.exists() and _read(started)==identity,
                  "V046_COMPLETED_REPLY_MISSING_OR_INVALID_STARTED")
            receipt=_read(reply_path)
            check(isinstance(receipt,dict) and
                  receipt.get("identity")==identity,
                  "V046_ARCHIVED_SEMANTIC_RECEIPT_MISMATCH")
            response=receipt["provider_response"]
        elif started.exists():
            return {
                "status":"FAILED_SAFE_FINAL",
                "reason_code":"V046_STARTED_WITHOUT_RECEIPT_NO_RESEND",
                "bound_advisories":accepted,
                "scripted_dispatches_current_run":dispatches,
                "canonical_commit_authorized":False,
            }
        else:
            _write(started,identity)
            try:
                response=synthetic_reply(
                    prepared=deepcopy(payload),task_id=number,
                )
            except Exception:
                return {
                    "status":"FAILED_SAFE_FINAL",
                    "reason_code":"V046_UNKNOWN_SCRIPTED_RESPONSE_NO_RESEND",
                    "bound_advisories":accepted,
                    "scripted_dispatches_current_run":dispatches+1,
                    "canonical_commit_authorized":False,
                }
            dispatches+=1
            _write(reply_path,{
                "identity":identity,"provider_response":response,
            })
        try:
            bound=source_bind(
                audit=audit,request=request,response=response,
            )
            check(bound["status"]=="HOLD_MODEL_RESPONSE_NOT_AUTHORITY" and
                  bound["canonical_commit_authorized"] is False and
                  bound["source_prose_sha256"]==prose_hash(prose),
                  "V046_SEMANTIC_ADVISORY_CANNOT_AUTHORIZE")
        except (CoverageError,ValueError,TypeError,KeyError):
            return {
                "status":"FAILED_SAFE_FINAL",
                "reason_code":"V046_SEMANTIC_SOURCE_BIND_FAILED",
                "bound_advisories":accepted,
                "scripted_dispatches_current_run":dispatches,
                "canonical_commit_authorized":False,
            }
        accepted.append(bound)
    return {
        "status":"TWO_SOURCE_BOUND_ADVISORIES_NONCANONICAL",
        "reason_code":None,
        "bound_advisories":accepted,
        "scripted_dispatches_current_run":dispatches,
        "canonical_commit_authorized":False,
    }


def orchestrate(*, bench_dir, pencil_dir, work_root,
                synthetic_repair_reply, synthetic_semantic_reply,
                synthetic_full_extraction_reply):
    """All callbacks are explicitly OFFLINE doubles, never OpenRouter."""
    root=Path(work_root)
    risk=compare_receipts(bench_dir=bench_dir,pencil_dir=pencil_dir)
    prose=prepare()["prose"]
    check(risk["original_source_sha256"]==EXPECTED_SHA,
          "V046_REAL_PROSE_NOT_FROZEN")
    first=repair(
        proof=risk,prose=prose,output_dir=root/"repair",
        synthetic_source_reply=synthetic_repair_reply,
    )
    # If the earlier stage failed, subsequent stages MUST never run.
    if first["status"]!="SOURCE_BOUND_REPAIR_ADVISORIES_ONLY":
        return _final(risk,first,None,None,
                      "V046_SCENETRACE_REPAIR_NOT_SOURCE_BOUND")
    semantic=_source_bound_semantics(
        risk_proof=risk,prose=prose,
        output_root=root/"semantic",
        synthetic_reply=synthetic_semantic_reply,
    )
    if semantic["status"]!="TWO_SOURCE_BOUND_ADVISORIES_NONCANONICAL":
        return _final(risk,first,semantic,None,
                      "V046_TARGETED_INDEPENDENT_REVIEW_FAILED")
    # Only now invoke *actual* v0.22 full-scene worker. It has NOT been given
    # any fabricated/full-semantics labels from v0.44/45. The model double
    # deliberately returns an incomplete source sweep: v0.22 must fail.
    world=entry_state()
    registry={k:v for k,v in REGISTRY.items()
              if k in world["entities"]}
    lexicon=json.loads(LEXICON.read_text(encoding="utf-8"))["candidates"]
    worker=create_preparer(
        evidence_root=root/"full-evidence",
        work_root=root/"full-worker",
        scene_key="v046-real-mara-shadow",
        registry=registry,candidate_lexicon=lexicon,
        typed_registry={"openables":[],"documents":[]},
        api_key="OFFLINE_TEST_DOUBLE_NEVER_SENT_TO_PROVIDER",
        extraction_model=MODEL_EXTRACTION,
        semantic_model=MODEL_SEMANTIC,
        typed_model=MODEL_TYPED,
        provider_call=synthetic_full_extraction_reply,
        max_model_requests=4,observed_spend_guard_usd="0.01",
    )
    full=worker(prose=prose,world=world)
    check(full["canonical_commit_authorized"] is False and
          full["world_db_writes"]==0 and
          full["prose_sha256"]==prose_hash(prose),
          "V046_FRESH_WORKER_WORLD_AUTHORITY_INVALID")
    # Even an EVIDENCE_READY_NONCANONICAL from a scripted provider could
    # never authorize a physical world mutation in this coordinator.
    return _final(risk,first,semantic,full,
                  "V046_FULL_REAL_SOURCE_INDEPENDENT_SEMANTICS_UNPROVEN")


def _final(risk,repair_stage,semantic,full,reason):
    return {
        "schema":SCHEMA,"status":"FAILED_SAFE_FINAL",
        "reason_code":reason,
        "real_model_source_runs":risk["archived_real_runs"],
        "original_prose_sha256":risk["original_source_sha256"],
        "real_source_risk_count":risk["model_response_challenge_count"],
        "repair_stage_status":repair_stage["status"],
        "targeted_semantic_stage_status":(
            semantic["status"] if semantic is not None else "NOT_STARTED"),
        "full_fresh_v022_stage_status":(
            full["status"] if full is not None else "NOT_STARTED"),
        "full_fresh_v022_failure_code":(
            full.get("failure_code") if full is not None else None),
        "source_recall_improvement_proven":False,
        "independent_semantic_qualification":False,
        "provider_model_was_real_during_new_stages":False,
        "canonical_commit_authorized":False,
        "production_db_writes":0,
        "sqlite_lab_writes":0,
        "paid_provider_calls_new":0,
        "requires_manual_intervention":False,
        "next_automatic_action":"TERMINAL_SAFE_FAILURE",
    }
