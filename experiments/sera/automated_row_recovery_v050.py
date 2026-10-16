"""SERA v0.50: unattended per-sentence repair & independent review, SHADOW LAB.

The pipeline needs NO per-story human fixing, retry/resume commands, or
manual event decisions. The provider adapter is injected and defaults to
NO PROVIDER: this increment exercises OFFLINE scripted transport ONLY.
Future real-provider adoption requires separate spending authorization.

Repair sequence:
- derive defects from pinned, already-paid v0.48 raw receipts via v0.49;
- for five quarantined rows, ask for the single ORIGINAL source sentence,
  independently rebind with v0.41.2's genuine v0.10 exact-quote binder;
- for 21 disagreements, ask a previous-answer-blind v0.11 question and
  validate with genuine v0.18 binder;
- automatic second distinct model when the first COMPLETED/RECEIPTED
  response fails binding; never resend an unknown-in-flight request;
- checkpoint all replies, resume uncompleted jobs with no repeat of
  receipted responses, and terminal FAILED_SAFE_FINAL on unresolved risk;
- NEVER promote script/model opinions to semantic truth or G2 commits.

A physically plausible model-generated answer is NOT established truth;
full scene must be re-extracted/replanned by existing v0.22/v0.20 gates.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.haiku_evidence_recovery_v011 import parse_json_model_reply
from experiments.sera.openrouter_scene_writer_v021 import (
    _durable_provider_response, _provider_body,
)
from experiments.sera.real_blind_benchmark_v040 import EXPECTED_SHA
from experiments.sera.real_mara_recovery_queue_v049 import (
    verified_real_receipts, build_work_orders,
)
from experiments.sera.real_pencil_partial_rows_v0412 import isolate_rows
from experiments.sera.request_policy import enforce_no_output_token_limit
from experiments.sera.scene_trace_autorepair_v045 import _read, _write, digest
from experiments.sera.semantic_recovery_v018 import _bind as semantic_bind
from experiments.sera.semantic_risks_v011 import make_task_request
from experiments.sera.sentence_sweep_v010 import SYSTEM as EXTRACTOR_SYSTEM
from experiments.sera.world_state_v02 import canonical

SCHEMA = "sera.v050-unattended-source-bound-repair-controller"
MODELS = ("synthetic/v050-independent-primary",
          "synthetic/v050-independent-fallback")
STATUS_SOURCE = "SOURCE_BOUND_REEXTRACTION_NONCANONICAL"
STATUS_REVIEW = "SOURCE_BOUND_SEMANTIC_ADVISORY_NONCANONICAL"
TRANSPORT_POLICY = "OFFLINE_SCRIPTED_ZERO_REAL_BILLING"


def require(ok, code):
    if not ok:
        raise CoverageError(code)


def request_for(*,source,task,audit):
    """Blind specific 1-row re-extraction or independent v0.11 review."""
    require(prose_hash(source["prose"])==EXPECTED_SHA and
            task["source_span"]["start"]>=0 and
            source["prose"][task["source_span"]["start"]:
                            task["source_span"]["end"]]==task["source_sentence"],
            "V050_INVALID_OR_CHANGED_SOURCE_SPAN")
    if task["action"]=="AUTO_REEXTRACT_INDEPENDENT_ROW":
        original=next(
            s for s in source["plan"]["source_sentences"]
            if s["id"]==task["sentence_id"]
        )
        ctx={
            "source_prose_sha256":EXPECTED_SHA,
            "task_id":task["task_id"],
            "target_sentences":[deepcopy(original)],
            "instruction":"Extract this one source sentence ONLY. "
                          "Report every explicitly witnessed source action, "
                          "observation or knowledge change; use exact contiguous "
                          "source quote and occurrence. Do not invent actors, "
                          "hidden changes, or times. Reply JSON with one rows item.",
        }
        packet={"messages":[
            {"role":"system","content":EXTRACTOR_SYSTEM},
            {"role":"user","content":canonical(ctx)},
        ],"response_format":{"type":"json_object"}}
    elif task["action"]=="BLIND_DISAGREEMENT_SOURCE_ADJUDICATION":
        req=make_task_request(audit=audit,task_id=task["task_id"])
        packet={"messages":req["messages"],
                "response_format":req["response_format"]}
    else:
        raise CoverageError("V050_UNRECOGNIZED_AUTOMATIC_WORK_ACTION")
    enforce_no_output_token_limit(packet)
    text=packet["messages"][1]["content"]
    require(not any(secret in text for secret in (
        "previous_model_answer","candidate_events","model_opinion",
        "risk_code","correct_answer","quarantined_rows",
    )),"V050_PREVIOUS_MODEL_INFORMATION_LEAKED")
    return packet


def _single_source_rebind(*,source,task,provider_body):
    """v0.41.2 real binder; synthetic masked rows NEVER retained as proof."""
    choice=provider_body["choices"][0]
    require(choice.get("finish_reason")=="stop" and
            isinstance(choice.get("message",{}).get("content"),str),
            "V050_INCOMPLETE_PROVIDER_ANSWER")
    raw,_=parse_json_model_reply(choice["message"]["content"])
    require(isinstance(raw,dict) and set(raw)=={"rows"} and
            isinstance(raw["rows"],list) and len(raw["rows"])==1 and
            raw["rows"][0].get("sentence_id")==task["sentence_id"],
            "V050_SINGLE_ROW_RESPONSE_SCOPE_INVALID")
    row=raw["rows"][0]
    parent=next(
        batch for batch in source["plan"]["batches"]
        if task["sentence_id"] in batch["sentence_ids"]
    )
    padded={
        "rows":[row if sid==task["sentence_id"] else {
            "sentence_id":sid,"disposition":"AMBIGUOUS",
            "reason":"V050_BLIND_SINGLE_ROW_MASKED_NOT_EVIDENCE",
            "mentions":[],"events":[],
        } for sid in parent["sentence_ids"]]
    }
    accepted,quarantined=isolate_rows(
        plan={"plan":source["plan"],"batch":parent},
        parsed=padded,prose=source["prose"],
    )
    require(not quarantined and len(accepted)==len(parent["sentence_ids"]),
            "V050_SOURCE_ROW_BINDING_REJECTED")
    exact=[x for x in accepted if x["sentence_id"]==task["sentence_id"]]
    require(len(exact)==1 and exact[0]["source_spans_checked"] is True,
            "V050_SOURCE_ROW_NOT_INDEPENDENTLY_BOUND")
    row=exact[0]
    return {
        "sentence_id":task["sentence_id"],
        "source_sha256":EXPECTED_SHA,
        "source_bound_candidate_row":row,
        "masking_rows_never_counted":len(parent["sentence_ids"])-1,
        "semantic_truth_verified":False,
        "canonical_commit_authorized":False,
    }


def _bind_answer(*,source,task,audit,raw):
    require(raw.get("error") is None and isinstance(raw.get("raw"),dict),
            "V050_UNQUALIFIED_PROVIDER_ENVELOPE")
    body=raw["raw"]
    if task["action"]=="AUTO_REEXTRACT_INDEPENDENT_ROW":
        return STATUS_SOURCE, _single_source_rebind(
            source=source,task=task,provider_body=body,
        )
    req=make_task_request(audit=audit,task_id=task["task_id"])
    result=semantic_bind(audit=audit,request=req,response=body)
    require(result["status"]=="HOLD_MODEL_RESPONSE_NOT_AUTHORITY" and
            result["canonical_commit_authorized"] is False,
            "V050_SEMANTIC_REPLY_CANNOT_AUTHORIZE_WORLD")
    return STATUS_REVIEW, {
        "sentence_id":task["sentence_id"],
        "source_sha256":EXPECTED_SHA,
        "verdict_model_proposed":result["verdict_model_proposed"],
        "possible_source_evidence":result["possible_source_evidence"],
        "semantic_truth_verified":False,
        "canonical_commit_authorized":False,
    }


def _receipt_id(task,model,request):
    return digest({
        "task_id":task["task_id"],"sentence_id":task["sentence_id"],
        "source_sha256":EXPECTED_SHA,"model":model,"request":request,
    })


def execute(*,source,audit,tasks,output_root,scripted_provider,
            model_profiles=MODELS):
    """No network, no cost. Complete model receipt -> auto-fallback.

    An orphaned STARTED with no reply needs an authenticated provider GET;
    never blindly repost and never require a human story-fixing checkpoint.
    """
    require(callable(scripted_provider) and
            isinstance(model_profiles,tuple) and len(model_profiles)==2 and
            all(isinstance(x,str) and x for x in model_profiles) and
            model_profiles[0]!=model_profiles[1],
            "V050_INDEPENDENT_MODELS_REQUIRED")
    require(len(tasks)==26 and
            audit["targeted_task_count"]==26 and
            audit["source_prose_sha256"]==EXPECTED_SHA and
            len(set(x["task_id"] for x in tasks))==26,
            "V050_TASK_SET_MUST_BE_COMPLETE_AND_UNIQUE")
    root=Path(output_root)
    contract={
        "schema":SCHEMA,"source_sha256":EXPECTED_SHA,
        "task_digest":digest([{
            "task_id":t["task_id"],
            "action":t["action"],"sentence_id":t["sentence_id"],
            "source_span":t["source_span"],
        } for t in tasks]),
        "audit_sha256":digest(audit),
        "models":list(model_profiles),
        "transport":TRANSPORT_POLICY,
    }
    if (root/"contract.json").exists():
        require(_read(root/"contract.json")==contract,
                "V050_SOURCE_TASK_OR_MODEL_PROFILE_DRIFT")
    else:
        _write(root/"contract.json",contract)
    final_path=root/"final.json"
    if final_path.exists():
        prior=_read(final_path)
        require(isinstance(prior,dict) and prior.get("schema")==SCHEMA and
                prior.get("source_sha256")==EXPECTED_SHA and
                prior.get("world_db_writes")==0,
                "V050_ARCHIVED_FINAL_INVALID")
        return prior
    outcomes=[]
    attempted=0
    fallback=0
    for task in tasks:
        request=request_for(source=source,task=task,audit=audit)
        chosen=None
        bound=None
        status=None
        errors=[]
        for i,model in enumerate(model_profiles):
            signature=_receipt_id(task,model,request)
            # v0.21's original provider journal: authentic completed
            # response reuse, atomic writes, started-but-unreceipted HOLD.
            try:
                response=_durable_provider_response(
                    root=root/"receipts"/task["task_id"]/model.replace("/","_"),
                    model=model,request=request,
                    api_key="OFFLINE_TEST_DOUBLE_NOT_AN_OPENROUTER_KEY",
                    provider_call=scripted_provider,
                )
                attempted+=1
                if i==1:
                    fallback+=1
                body,choice,cost=_provider_body(response,model)
                status,bound=_bind_answer(
                    source=source,task=task,audit=audit,raw=response,
                )
                chosen=model
                break
            except CoverageError as exc:
                error=str(exc)
                errors.append(error[:200])
                # Only a **fully received and bound** envelope may cause
                # automatic different-model fallback. Unknown charge =>
                # terminal no resend (no second POST, even to backup).
                provider_root=root/"receipts"/task["task_id"]/model.replace("/","_")
                received=list(provider_root.glob("*.response.json"))
                if not received:
                    result=_result("FAILED_SAFE_FINAL",outcomes,attempted,
                        fallback,"V050_UNKNOWN_PROVIDER_OUTCOME_NO_RESEND")
                    _write(final_path,result)
                    return result
                # Complete but invalid reply: fallback to distinct profile.
                if i==1:
                    break
            except Exception:
                result=_result("FAILED_SAFE_FINAL",outcomes,attempted,
                    fallback,"V050_UNKNOWN_PROVIDER_EXCEPTION_NO_RESEND")
                _write(final_path,result)
                return result
        if bound is None:
            outcomes.append({
                "task_id":task["task_id"],
                "sentence_id":task["sentence_id"],
                "action":task["action"],
                "status":"AUTO_REPLAN_REQUIRED_NONCANONICAL",
                "errors":errors,"semantic_truth_verified":False,
                "canonical_commit_authorized":False,
            })
        else:
            outcomes.append({
                "task_id":task["task_id"],
                "sentence_id":task["sentence_id"],
                "action":task["action"],
                "status":status,"model":chosen,
                "candidate":bound,
                "semantic_truth_verified":False,
                "canonical_commit_authorized":False,
            })
    any_failed=any(x["status"]=="AUTO_REPLAN_REQUIRED_NONCANONICAL"
                   for x in outcomes)
    result=_result(
        ("REPLAN_REQUIRED_NONCANONICAL" if any_failed else
         "SOURCE_CANDIDATES_READY_FOR_FULL_REEXTRACTION_NONCANONICAL"),
        outcomes,attempted,fallback,None,
    )
    _write(final_path,result)
    return result


def _result(status,outcomes,attempted,fallback,failure):
    recovered=[x for x in outcomes if x["status"]==STATUS_SOURCE]
    reviewed=[x for x in outcomes if x["status"]==STATUS_REVIEW]
    return {
        "schema":SCHEMA,"status":status,
        "failure_code":failure,"source_sha256":EXPECTED_SHA,
        "task_results":deepcopy(outcomes),
        "candidate_source_rows_reextracted":len(recovered),
        "source_blind_advisories":len(reviewed),
        "tasks_accounted_for":len(outcomes),
        "scripted_provider_calls_this_run":attempted,
        "scripted_fallback_attempts_this_run":fallback,
        "real_new_paid_calls":0,
        "repair_model_was_real":False,
        "full_scene_semantic_qualification_proven":False,
        "world_commit_authorized":False,
        "world_db_writes":0,
        "requires_manual_intervention":False,
        "next_automatic_action":(
            "AUTO_REPLAN_REWRITE_OR_FULL_SCENE_REEXTRACTION"
            if status=="REPLAN_REQUIRED_NONCANONICAL" else
            "AUTOMATIC_FULL_SCENE_REEXTRACTION_AND_VALIDATION"
            if status=="SOURCE_CANDIDATES_READY_FOR_FULL_REEXTRACTION_NONCANONICAL"
            else "TERMINAL_SAFE_FAILURE"
        ),
    }
