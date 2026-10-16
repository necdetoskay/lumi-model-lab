"""SERA v0.44: machine-only source challenge cards for real model proposals.

No external requests, G2 world writes, nor assertion of complete semantics.
This is a *shadow decision explanation* on genuinely archived, already-paid
models. It cannot self-promote candidates or call re-extraction. Any unsafe
proposal gets a machine-readable next-stage instruction, never a human gate.

The detector is a NARROW source-phrase policy, not an independent LLM judge.
There is NO release/semantic recall improvement claim without separate proof.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import argparse
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError
from experiments.sera.real_blind_benchmark_v040 import MODELS, EXPECTED_SHA
from experiments.sera.scene_trace_dual_real_v043 import (
    dual_real_evaluation, source_risks,
)

SCHEMA = "sera.scene-trace-evidence-challenge.v0.44"
POLICY_VERSION = "source-narrow-risk-two-contrasts.v0.1"
CONTRASTS = (Path(__file__).resolve().parent / "fixtures" /
             "scene_trace_policy_contrasts_v044.json")
BLOCKING = {
    "STATIC_WATCH_PREDICATE_MISREAD_AS_TRANSITION_RISK": {
        "challenge": "BLOCK_STATIC_PREDICATE_AS_TRANSITION",
        "missing_evidence": [
            "EXPLICIT_OPENING_ACTION",
            "PREVIOUS_CLOSED_STATE_AND_CHANGED_STATE",
        ],
        "machine_next_action": "TARGETED_INDEPENDENT_STATE_TRANSITION_REEXTRACTION",
    },
    "PENCIL_MOTION_OBSERVED_BUT_CAUSAL_ACTOR_UNKNOWN": {
        "challenge": "BLOCK_UNATTRIBUTED_CAUSAL_AGENT",
        "missing_evidence": [
            "ACTOR_WHO_CAUSED_PENCIL_MOTION",
            "BEFORE_AFTER_OBJECT_LOCATION_AND_TIMING",
        ],
        "machine_next_action": "TARGETED_INDEPENDENT_CAUSAL_AGENT_REEXTRACTION",
    },
}
KIND = {
    "STATIC_WATCH_PREDICATE_MISREAD_AS_TRANSITION_RISK": "CHANGE_STATE",
    "PENCIL_MOTION_OBSERVED_BUT_CAUSAL_ACTOR_UNKNOWN": "MOVE",
}


def require(ok,code):
    if not ok:
        raise CoverageError(code)


def narrow_policy(*, prose_sentence, model_kind):
    """Return a source-supported *challenge*, not semantic correctness.

    Empty warning means no rule recognized that form; it never means the
    event is true, the author has proved causality, or a commit is allowed.
    """
    require(isinstance(prose_sentence,str) and
            isinstance(model_kind,str) and bool(model_kind),
            "SCENETRACE_V044_POLICY_INPUT_INVALID")
    risks=source_risks(
        source_sentence=prose_sentence,
        model_event={"kind":model_kind},
    )
    require(len(risks)<=1 and
            all(code in BLOCKING for code in risks),
            "SCENETRACE_V044_RISK_POLICY_UNRECOGNIZED")
    return (BLOCKING[risks[0]]["challenge"] if risks else
            "NO_POLICY_BLOCK_SEMANTIC_UNVERIFIED")


def evaluate_predeclared_contrasts():
    fixture=json.loads(CONTRASTS.read_text(encoding="utf-8"))
    require(fixture.get("schema")==
            "sera.source-proof-contrast-cases.v0.44" and
            isinstance(fixture.get("cases"),list) and
            len(fixture["cases"])>=8,
            "SCENETRACE_V044_CONTRAST_FIXTURE_INVALID")
    actual=[]
    ids=set()
    for c in fixture["cases"]:
        require(set(c)=={"id","source","kind","expected"} and
                c["id"] not in ids,
                "SCENETRACE_V044_CONTRAST_CASE_INVALID")
        ids.add(c["id"])
        got=narrow_policy(
            prose_sentence=c["source"],
            model_kind=c["kind"],
        )
        actual.append({"id":c["id"],"expected":c["expected"],
                       "observed":got,"passed":got==c["expected"]})
    return {
        "fixture_schema":fixture["schema"],
        "fixture_sha256":sha256(CONTRASTS.read_bytes()).hexdigest(),
        "cases":actual,
        "pass_count":sum(1 for c in actual if c["passed"]),
        "case_count":len(actual),
        "full_story_semantic_gold":False,
        "nonmatching_policy_means_semantic_pass":False,
    }


def _check_source_projection(report, *, exact_prose):
    require(isinstance(report,dict) and
            report.get("schema")==
                "sera.scenetrace-dual-receipt-comparison.v0.43" and
            report.get("original_prose_sha256")==EXPECTED_SHA and
            report.get("source_sentence_count")==28 and
            report.get("real_paid_runs")==[38936451931,38938438488] and
            report.get("additional_paid_requests")==0 and
            report.get("canonical_commit_authorized") is False and
            report.get("production_db_writes")==0 and
            len(report.get("source_timeline",[]))==28 and
            len(report.get("source_bound_semantic_risk_flags",[]))==2 and
            report.get("source_bound_event_candidate_disagreements")==6,
            "SCENETRACE_V044_REAL_ARCHIVE_SCOPE_UNQUALIFIED")
    from experiments.sera.sentence_ledger_v06 import sentences
    actual=sentences(exact_prose)
    for index,(a,b) in enumerate(zip(actual,report["source_timeline"])):
        require(a["id"]==b["sentence_id"] and
                b["narrative_ordinal"]==index+1 and
                a["quote"]==b["quote"] and
                b["source_sha256"]==EXPECTED_SHA and
                b["world_state_write_authorized"] is False and
                b["exact_story_second"] is None and
                len(b["model_candidates"])==2 and
                [m["model"] for m in b["model_candidates"]]==list(MODELS),
                "SCENETRACE_V044_SOURCE_PROJECTION_MISMATCH")
    return actual


def build_challenges(*, archived_comparison, frozen_prose):
    """Trace source-bound risks as potential mutation blocks, never PASS."""
    source=_check_source_projection(
        archived_comparison,exact_prose=frozen_prose,
    )
    check_source={x["id"]:x for x in source}
    by_id={x["sentence_id"]:x for x in
           archived_comparison["source_timeline"]}
    records=[]
    seen=set()
    for risk in archived_comparison["source_bound_semantic_risk_flags"]:
        sid=risk["source_sentence_id"]
        model=risk["model"]
        code=risk["risk_code"]
        require(sid in check_source and model in MODELS and
                code in BLOCKING and code in KIND and
                risk["world_state_write_authorized"] is False and
                risk["semantic_truth_verified"] is False,
                "SCENETRACE_V044_RISK_PROVENANCE_INVALID")
        src=check_source[sid]
        start,end=risk["source_start"],risk["source_end"]
        require(type(start) is int and type(end) is int and
                src["start"]<=start<end<=src["end"] and
                frozen_prose[start:end]==risk["source_quote"],
                "SCENETRACE_V044_RISK_QUOTE_NOT_SOURCE_BOUND")
        row=by_id[sid]
        entry=next(x for x in row["model_candidates"]
                   if x["model"]==model)
        require(entry["status"]=="SOURCE_BOUND" and
                KIND[code] in entry["candidate_event_kinds"] and
                narrow_policy(prose_sentence=src["quote"],
                              model_kind=KIND[code])==
                     BLOCKING[code]["challenge"],
                "SCENETRACE_V044_RISK_EVENT_NOT_VERIFIED")
        identity=(sid,model,code,start,end)
        require(identity not in seen,
                "SCENETRACE_V044_DUPLICATE_SAFETY_CHALLENGE")
        seen.add(identity)
        policy=BLOCKING[code]
        records.append({
            "challenge_id":f"{sid}:{model}:{code}",
            "sentence_id":sid,
            "narrative_ordinal":row["narrative_ordinal"],
            "model":model,
            "proposed_event_kind":KIND[code],
            "source_evidence_span":{"start":start,"end":end,
                                    "quote":risk["source_quote"]},
            "source_sentence":src["quote"],
            "rule_code":code,
            "status":"PHYSICAL_MUTATION_PROPOSAL_BLOCKED_IN_SHADOW",
            "reason":"REQUIRED_PHYSICAL_TRANSITION_EVIDENCE_MISSING",
            "missing_evidence":list(policy["missing_evidence"]),
            "machine_next_action":policy["machine_next_action"],
            "exact_story_second":None,
            "actor_id":None,
            "world_state_transition_authorized":False,
            "independent_semantic_truth_proven":False,
            "repair_was_executed":False,
        })
    require(len(records)==2,"SCENETRACE_V044_EXPECTED_REAL_RISKS_MISSING")
    sampled=sum(1 for row in archived_comparison["source_timeline"]
                if any(m["status"]!="NOT_EXTRACTED" for m in
                       row["model_candidates"]))
    unassessed=28-sampled
    require(sampled==8 and unassessed==20,
            "SCENETRACE_V044_SAMPLED_SENTENCE_ACCOUNTING_WRONG")
    contrasts=evaluate_predeclared_contrasts()
    require(contrasts["case_count"]==contrasts["pass_count"],
            "SCENETRACE_V044_POLICY_CONTRAST_FAILED")
    return {
        "schema":SCHEMA,
        "status":"REAL_SOURCE_EVIDENCE_CHALLENGED_SHADOW_ONLY",
        "original_source_sha256":EXPECTED_SHA,
        "archived_real_runs":[38936451931,38938438488],
        "model_response_challenge_count":len(records),
        "mutation_proposals_blocked_in_shadow":len(records),
        "mutation_proposals_previously_committed":0,
        "new_real_model_errors_proven":0,
        "independent_semantic_event_recall_proven":False,
        "source_sentences_total":28,
        "source_sentences_sampled_by_any_real_model":sampled,
        "source_sentences_not_sampled":unassessed,
        "real_model_event_disagreements":
            archived_comparison["source_bound_event_candidate_disagreements"],
        "contrast_policy":contrasts,
        "challenges":records,
        "machine_action_recommendations_only":True,
        "repair_automatic_execution_qualified":False,
        "ongoing_story_pipeline_changed":False,
        "zero_manual_runtime_gates":True,
        "canonical_commit_authorized":False,
        "additional_paid_model_requests":0,
        "additional_provider_cost_usd":"0",
        "production_db_writes":0,
        "sqlite_lab_writes":0,
        "recommendation":"SHADOW_ONLY_UNTIL_INDEPENDENT_REAL_SEMANTIC_MEASUREMENT",
    }


def compare_receipts(*, bench_dir, pencil_dir):
    from experiments.sera.real_blind_benchmark_v040 import prepare
    evidence=dual_real_evaluation(
        bench_receipt_dir=bench_dir,
        pencil_receipt_dir=pencil_dir,
    )
    exact=prepare()["prose"]
    return build_challenges(
        archived_comparison=evidence,frozen_prose=exact,
    )


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--bench-receipt-dir",type=Path,required=True)
    parser.add_argument("--pencil-receipt-dir",type=Path,required=True)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    proof=compare_receipts(
        bench_dir=args.bench_receipt_dir,
        pencil_dir=args.pencil_receipt_dir,
    )
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(
            json.dumps(proof,ensure_ascii=False,sort_keys=True,indent=2)+"\n",
            encoding="utf-8",
        )
    print(json.dumps({
        "status":proof["status"],
        "real_candidate_risks":proof["model_response_challenge_count"],
        "sampled_source_sentences":
            proof["source_sentences_sampled_by_any_real_model"],
        "unassessed_source_sentences":proof["source_sentences_not_sampled"],
        "risk_examples":[{
            "model":row["model"],"source":row["sentence_id"],
            "kind":row["proposed_event_kind"],
            "next_machine_action":row["machine_next_action"],
        } for row in proof["challenges"]],
        "contrast_cases":proof["contrast_policy"]["pass_count"],
        "paid_calls":proof["additional_paid_model_requests"],
        "semantic_recall_proven":False,
    },ensure_ascii=False))


if __name__=="__main__":
    main()
