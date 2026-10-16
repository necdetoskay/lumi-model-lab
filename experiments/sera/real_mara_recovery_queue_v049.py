"""SERA v0.49 — automate grounded Mara S1 repair work orders from real v0.48 receipts.

ARCHIVED REAL MODEL PROVENANCE + OFFLINE RE-REVIEW, NO NEW PROVIDER CALLS.

1. Re-hash all 14 original raw Gemini/Haiku receipt envelopes.
2. Re-bind every one using the actual v0.48 exact-source binder.
3. Derive 5 Haiku quarantines + 21 comparable cross-model disagreements.
4. Prepare blind 26-task v0.11 prompts, without the preceding model answers.
5. Optionally exercise the actual v0.18 source-quote binder with an injected
   SCRIPTED reviewer; never mistake this for real semantic validation.

All receipts, prompts and status are noncanonical. Missing, invalid and
unknown-in-flight scripted replies cannot be resent without an external
authenticated receipt reconciler. Real provider posting is NOT implemented
or authorized here; future billable calls require a fresh user approval.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.real_blind_benchmark_v040 import EXPECTED_SHA, MODELS
from experiments.sera.real_full_scene_blind_v048 import (
    prepare as frozen_full_plan, assess_received, analyze_plan_coverage,
)
from experiments.sera.request_policy import enforce_no_output_token_limit
from experiments.sera.scene_trace_autorepair_v045 import _read, _write, digest
from experiments.sera.semantic_risks_v011 import make_task_request
from experiments.sera.semantic_recovery_v018 import _bind as bind_v018
from experiments.sera.world_state_v02 import canonical

SCHEMA = "sera.v049-real-mara-automatic-shadow-triage"
EXPECTED_MANIFEST_SHA = (
    "91bb4ddc72c6c104ee3322808e08e3a9cdda40a95a460225f4a3717680adad64"
)
REAL_RUN_ID = 38957808652
REAL_ARTIFACT_ID = 12071052906
REEXTRACT_IDS = frozenset({"s006","s014","s018","s021","s024"})
DISAGREEMENTS = frozenset({
    "s001","s002","s003","s004","s005","s007","s008","s009",
    "s011","s012","s013","s015","s016","s017","s019","s020",
    "s022","s025","s026","s027","s028",
})
QUESTION = (
    "Review only the exact source sentence. Which physical action, reported "
    "claim, observation, object change, document change, actor and causal "
    "agent are EXPLICITLY supported? Cite exact source text. Do not infer "
    "a previous state, hidden agent, elapsed/story clock time or relocation. "
    "Return UNCERTAIN when the physical before/after or agent is unproven."
)


def require(ok, code):
    if not ok:
        raise CoverageError(code)


def _read_bytes_json(path, *, expected=None):
    try:
        data=Path(path).read_bytes()
        if expected is not None:
            require(sha256(data).hexdigest()==expected,
                    "V049_IMMUTABLE_ARCHIVE_SHA_MISMATCH")
        return json.loads(data)
    except (OSError,UnicodeError,ValueError) as exc:
        raise CoverageError("V049_RECEIPT_FILE_UNREADABLE") from exc


def verified_real_receipts(receipt_root):
    """Never trust a persisted summary alone: recheck raw and re-bind."""
    root=Path(receipt_root)
    report=_read_bytes_json(root/"result.json",expected=EXPECTED_MANIFEST_SHA)
    source,manifest=frozen_full_plan()
    require(
        report.get("schema")=="sera.v048-full-blind-real-mara" and
        report.get("status")=="FOURTEEN_REAL_RECEIPTS_NONCANONICAL" and
        report.get("source_sha256")==EXPECTED_SHA and
        manifest["source_prose_sha256"]==EXPECTED_SHA and
        report.get("model_ids")==list(MODELS) and
        report.get("attempts_started")==14 and
        report.get("outstanding_request_may_have_billed") is False and
        report.get("canonical_commit_authorized") is False and
        report.get("production_db_writes")==0 and
        report.get("model_output_token_limit_set") is False and
        isinstance(report.get("receipts"),list) and
        len(report["receipts"])==14 and
        report.get("manifest",{}).get("batches")==manifest["batches"],
        "V049_ARCHIVED_REAL_SCOPE_INVALID",
    )
    ids=set()
    receipts=[]
    total=Decimal("0")
    for index,row in enumerate(report["receipts"]):
        batch=source["plan"]["batches"][index//2]
        model=MODELS[index%2]
        filename=f"provider_reply_{index+1:02d}.json"
        require(
            row.get("model")==model and
            row.get("batch_id")==batch["batch_id"] and
            row.get("receipt_file")==filename and
            isinstance(row.get("receipt_sha256"),str) and
            isinstance(row.get("assessment"),dict),
            "V049_REAL_RECEIPT_SLOT_OR_ORDER_MISMATCH",
        )
        raw=_read_bytes_json(root/filename,expected=row["receipt_sha256"])
        require(raw.get("batch_id")==batch["batch_id"] and
                raw.get("model")==model and
                raw.get("request_sha256")==batch["request_sha256"] and
                isinstance(raw.get("provider_envelope"),dict) and
                raw["provider_envelope"].get("error") is None and
                isinstance(raw["provider_envelope"].get("raw"),dict),
                "V049_RAW_RECEIPT_WRONG_MODEL_BATCH")
        envelope=raw["provider_envelope"]["raw"]
        generation=envelope.get("id")
        require(isinstance(generation,str) and bool(generation) and
                generation not in ids,
                "V049_REAL_GENERATION_ID_MISSING_OR_DUPLICATED")
        ids.add(generation)
        rebinding=assess_received(
            source=source,batch=batch,model=model,receipt=raw,
        )
        require(rebinding==row["assessment"],
                "V049_ARCHIVED_MODEL_ASSESSMENT_DRIFT")
        require(rebinding["provider_complete"] is True and
                rebinding["charge_usd"] is not None,
                "V049_PROVIDER_COMPLETION_OR_COST_UNKNOWN")
        total+=Decimal(rebinding["charge_usd"])
        receipts.append({
            "model":model,"batch_id":batch["batch_id"],
            "assessment":rebinding,
        })
    require(str(total)==report["observed_spend_usd"],
            "V049_ARCHIVED_REAL_COST_MISMATCH")
    coverage=analyze_plan_coverage(source,receipts)
    require(coverage==report["coverage"],
            "V049_ARCHIVED_COMPARISON_SUMMARY_DRIFT")
    return source,receipts,coverage,report


def build_work_orders(*,source,receipts,coverage):
    """Derived from validated source-row statuses; never fabricates gold."""
    require(prose_hash(source["prose"])==EXPECTED_SHA and
            len(source["plan"]["source_sentences"])==28 and
            len(receipts)==14 and
            coverage.get("canonical_commit_authorized") is False,
            "V049_WORK_ORDER_SOURCE_SCOPE_INVALID")
    statuses=coverage["model_results"]
    originals=source["plan"]["source_sentences"]
    require(set(statuses)==set(MODELS),
            "V049_REQUIRED_INDEPENDENT_MODEL_MISSING")
    raw_quarantines={model:set() for model in MODELS}
    for item in receipts:
        require(item["model"] in MODELS,"V049_UNKNOWN_RECEIPT_MODEL")
        for row in item["assessment"].get("quarantined_rows",[]):
            raw_quarantines[item["model"]].add(row["sentence_id"])
    require(raw_quarantines[MODELS[0]]==set() and
            raw_quarantines[MODELS[1]]==REEXTRACT_IDS and
            statuses[MODELS[0]]["source_bound_sentence_count"]==28 and
            statuses[MODELS[1]]["source_bound_sentence_count"]==23 and
            statuses[MODELS[1]]["quarantined_sentence_count"]==5 and
            statuses[MODELS[0]]["unsampled_sentence_count"]==0 and
            statuses[MODELS[1]]["unsampled_sentence_count"]==0 and
            coverage["both_models_source_bound_sentence_count"]==23 and
            set(coverage["model_candidate_disagreement_sentence_ids"])==
               DISAGREEMENTS and
            coverage["model_candidate_signature_disagreement_count"]==21,
            "V049_ARCHIVED_SCOPE_COUNTS_CHANGED",
    )
    risks={
        risk["sentence_id"]:[] for model in MODELS
        for risk in statuses[model].get("source_risk_flags",[])
    }
    for model in MODELS:
        for risk in statuses[model].get("source_risk_flags",[]):
            risks.setdefault(risk["sentence_id"],[]).append({
                "model":model,"risk_code":risk["risk_code"],
            })
    tasks=[]
    audit_rows=[]
    for sentence in originals:
        sid=sentence["id"]
        is_missing=sid in REEXTRACT_IDS
        is_different=sid in DISAGREEMENTS
        if not is_missing and not is_different:
            continue
        kind=("AUTO_REEXTRACT_INDEPENDENT_ROW" if is_missing else
              "BLIND_DISAGREEMENT_SOURCE_ADJUDICATION")
        require(not(is_missing and is_different),
                "V049_REVIEW_SCOPE_DOUBLE_COUNT")
        index=len(tasks)+1
        task_id=f"task_{index:03d}"
        exact={
            "sentence_id":sid,"start":sentence["start"],
            "end":sentence["end"],"quote":sentence["quote"],
        }
        require(source["prose"][exact["start"]:exact["end"]]==exact["quote"],
                "V049_SENTENCE_BOUNDARY_MISMATCH")
        audit_rows.append({
            "task_id":task_id,"finding_code":kind,
            "target_sentence_ids":[sid],
            "trigger":"BLIND_SOURCE_ONLY_REVIEW",
            "exact_source_context":[exact],
            "independent_review_question":QUESTION,
            "explanation":"machine-made shadow recovery task",
            "no_prior_model_answer_in_prompt":True,
            "canonical_commit_authorized":False,
        })
        tasks.append({
            "task_id":task_id,"sentence_id":sid,
            "action":kind,"source_sentence":sentence["quote"],
            "source_span":{"start":sentence["start"],"end":sentence["end"]},
            "causal_risk_flags":risks.get(sid,[]),
            "model_truth_known":False,
            "physical_transition_authorized":False,
            "expected_reviewer":"INDEPENDENT_SOURCE_ONLY_MODEL",
        })
    require(len(tasks)==26 and
            sum(t["action"]=="AUTO_REEXTRACT_INDEPENDENT_ROW"
                for t in tasks)==5 and
            sum(t["action"]=="BLIND_DISAGREEMENT_SOURCE_ADJUDICATION"
                for t in tasks)==21 and
            sum(bool(t["causal_risk_flags"]) for t in tasks)==2 and
            {t["sentence_id"] for t in tasks}==
                (REEXTRACT_IDS|DISAGREEMENTS),
            "V049_INCOMPLETE_OR_CONFLATED_WORK_ORDERS")
    audit={
        "schema":"sera.semantic-risk-audit.v0.11",
        "source_prose_sha256":EXPECTED_SHA,
        "targeted_tasks":audit_rows,"targeted_task_count":26,
        "candidate_event_count":0,
        "canonical_commit_authorized":False,
    }
    prepared=[]
    for task in tasks:
        req=make_task_request(audit=audit,task_id=task["task_id"])
        payload={
            "messages":req["messages"],
            "response_format":req["response_format"],
        }
        enforce_no_output_token_limit(payload)
        visible=json.loads(payload["messages"][1]["content"])
        require(set(visible)=={
            "source_prose_sha256","task_id","exact_chronological_sentences",
            "independent_question",
        } and visible["exact_chronological_sentences"]==[
            {"sentence_id":task["sentence_id"],
             "start":task["source_span"]["start"],
             "end":task["source_span"]["end"],
             "quote":task["source_sentence"]},
        ] and
        "risk_code" not in canonical(visible) and
        "model_candidate" not in canonical(visible) and
        "previous_model" not in canonical(visible),
        "V049_BLIND_REQUEST_LEAK_OR_SOURCE_DRIFT")
        prepared.append({**task,"request_sha256":req["request_sha256"],
                         "request":payload})
    return audit,prepared


def save_plan(*,receipt_root,output_root):
    source,receipts,coverage,old=verified_real_receipts(receipt_root)
    audit,tasks=build_work_orders(
        source=source,receipts=receipts,coverage=coverage,
    )
    root=Path(output_root)
    root.mkdir(parents=True,exist_ok=True)
    manifest={
        "schema":SCHEMA,"source_prose_sha256":EXPECTED_SHA,
        "real_run_id":REAL_RUN_ID,"real_artifact_id":REAL_ARTIFACT_ID,
        "original_raw_provider_reply_count":14,
        "real_provider_spend_ledger_usd":old["observed_spend_usd"],
        "real_provider_calls_for_this_revision":0,
        "model_counts":{
            m:{
                "source_bound":coverage["model_results"][m][
                    "source_bound_sentence_count"],
                "quarantined":coverage["model_results"][m][
                    "quarantined_sentence_count"],
            } for m in MODELS
        },
        "total_tasks":26,"quarantined_source_reextract_tasks":5,
        "independent_disagreement_review_tasks":21,
        "prior_real_risk_flags":2,
        "tasks":[{
            "task_id":t["task_id"],"sentence_id":t["sentence_id"],
            "action":t["action"],
            "request_sha256":t["request_sha256"],
            "causal_risk_flags":t["causal_risk_flags"],
        } for t in tasks],
        "truth_not_verified":True,
        "source_complete_repaired":False,
        "world_commit_authorized":False,
        "production_db_writes":0,"sqlite_world_db_writes":0,
        "next_automatic_action":"AWAIT_AUTHORIZED_BLIND_REEXTRACTION",
    }
    policy={
        "schema":"sera.v049-workorders-contract",
        "source_sha256":EXPECTED_SHA,"real_artifact_id":REAL_ARTIFACT_ID,
        "result_sha256":EXPECTED_MANIFEST_SHA,
        "task_requests_digest":digest(manifest["tasks"]),
        "transport":"NO_REAL_PROVIDER_KEY_OFFLINE_ONLY",
    }
    for name,obj in [("contract.json",policy),
                     ("work_orders.json",manifest)]:
        target=root/name
        if target.exists():
            require(_read(target)==obj,"V049_PREPARED_JOURNAL_DRIFT")
        else:
            _write(target,obj)
    for task in tasks:
        dest=root/(task["task_id"]+".request.json")
        if dest.exists():
            require(_read(dest)==task["request"],
                    "V049_BLIND_REQUEST_JOURNAL_DRIFT")
        else:
            _write(dest,task["request"])
    return {"manifest":manifest,"audit":audit,"tasks":tasks}


def execute_scripted(*,prepared,output_root,synthetic_reply):
    """Replayable scripted v0.18 binder; ALWAYS unresolved story hold."""
    require(callable(synthetic_reply),"V049_SCRIPTED_REVIEWER_REQUIRED")
    root=Path(output_root)
    audit=prepared["audit"]
    seen=[]
    dispatched=0
    for task in prepared["tasks"]:
        request=make_task_request(audit=audit,task_id=task["task_id"])
        wire=task["request"]
        expected={
            "task_id":task["task_id"],"source_sha256":EXPECTED_SHA,
            "request_sha256":task["request_sha256"],
            "model":"synthetic/noncanonical-v049-no-provider",
        }
        target=root/task["task_id"]
        started=target.with_suffix(".started.json")
        receipt=target.with_suffix(".reply.json")
        if receipt.exists():
            require(started.exists() and _read(started)==expected,
                    "V049_REPLY_UNTRUSTED_OR_STARTED_MISSING")
            bundle=_read(receipt)
            require(bundle.get("identity")==expected and
                    isinstance(bundle.get("provider_response"),dict),
                    "V049_REPLAY_RECEIPT_NOT_BOUND_TO_SOURCE")
            answer=bundle["provider_response"]
        elif started.exists():
            return _safe_finish("V049_UNKNOWN_IN_FLIGHT_NO_RESEND",
                                seen,dispatched)
        else:
            _write(started,expected)
            dispatched+=1
            try:
                answer=synthetic_reply(
                    task_id=task["task_id"],prepared=deepcopy(wire),
                )
            except Exception:
                return _safe_finish("V049_SCRIPTED_REPLY_MISSING_NO_RESEND",
                                    seen,dispatched)
            require(isinstance(answer,dict),
                    "V049_SCRIPTED_REPLY_ENVELOPE_INVALID")
            _write(receipt,{"identity":expected,
                            "provider_response":answer})
        try:
            bound=bind_v018(audit=audit,request=request,response=answer)
            require(bound["status"]=="HOLD_MODEL_RESPONSE_NOT_AUTHORITY" and
                    bound["canonical_commit_authorized"] is False and
                    bound["source_prose_sha256"]==EXPECTED_SHA,
                    "V049_SOURCE_BOUND_REPLY_NOT_AUTHORITY")
        except (CoverageError,KeyError,TypeError,ValueError):
            return _safe_finish("V049_INVALID_INDEPENDENT_SOURCE_QUOTE",
                                seen,dispatched)
        seen.append({
            "task_id":task["task_id"],
            "sentence_id":task["sentence_id"],
            "status":bound["status"],
            "proposed_model_verdict":bound["verdict_model_proposed"],
            "semantic_truth_verified":False,
            "canonical_commit_authorized":False,
        })
    return {
        "schema":"sera.v049-scripted-automatic-shadow-review",
        "status":"SOURCE_BOUND_MODEL_ADVISORIES_NONCANONICAL",
        "bound_task_count":len(seen),
        "task_advisories":seen,
        "scripted_model_calls_this_run":dispatched,
        "real_model_calls_this_run":0,
        "semantic_truth_proven":False,
        "quarantined_rows_reextracted_by_real_provider":0,
        "world_commit_authorized":False,
        "production_db_writes":0,
        "requires_manual_story_edit":False,
        "next_automatic_action":"AWAIT_AUTHORIZED_INDEPENDENT_REEXTRACTION",
    }


def _safe_finish(code,seen,dispatched):
    return {
        "schema":"sera.v049-scripted-automatic-shadow-review",
        "status":"FAILED_SAFE_FINAL","failure_code":code,
        "bound_task_count":len(seen),"task_advisories":seen,
        "scripted_model_calls_this_run":dispatched,
        "real_model_calls_this_run":0,
        "semantic_truth_proven":False,
        "world_commit_authorized":False,
        "production_db_writes":0,
        "requires_manual_story_edit":False,
        "next_automatic_action":"TERMINAL_SAFE_FAILURE",
    }
