"""SERA v0.43 — compare four REAL model replies in one 28-sentence trace.

Source is the frozen Mara S1 prose. Receipts are the SHA-256 pinned real
OpenRouter v0.40/v0.41 archives. Both paid models are independently bound
to EXACT source sentences; damaged Haiku rows are quarantined, never
silently repaired into invented events. This is an evidence comparison,
NOT semantic gold, automatic scene qualification, or authorizing reducer.

Zero new LLM requests; no output token ceiling, world or SQLite writes.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import argparse
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError
from experiments.sera.haiku_evidence_recovery_v011 import parse_json_model_reply
from experiments.sera.real_blind_benchmark_v040 import (
    EXPECTED_SHA, MODELS, prepare as prepare_bench,
)
from experiments.sera.real_blind_receipt_replay_v0401 import (
    file_proof as verified_bench_receipts,
)
from experiments.sera.real_pencil_benchmark_v041 import prepare as prepare_pencil
from experiments.sera.real_pencil_receipt_replay_v0411 import (
    load_archived as verified_pencil_receipts,
    normalize_only_safe_advisory_fields,
)
from experiments.sera.real_pencil_partial_rows_v0412 import isolate_rows
from experiments.sera.scene_trace_shadow_v042 import build_trace
from experiments.sera.mara_s1_typed_live_v05 import REGISTRY, entry_state
from experiments.sera.real_blind_benchmark_v040 import LEXICON

SCHEMA = "sera.scenetrace-dual-receipt-comparison.v0.43"
BATCHES = ("bench", "pencil")


def check(ok, code):
    if not ok:
        raise CoverageError(code)


def source_risks(*, source_sentence, model_event):
    """Advisory flags for two *observed* historical failure patterns.

    Warning means 'requires independent adjudication', NOT that an action
    was certainly false. Never rewrite/override the model event.
    """
    check(isinstance(source_sentence, str) and
          isinstance(model_event, dict) and
          isinstance(model_event.get("kind"), str),
          "SCENETRACE_V043_RISK_INPUT_INVALID")
    warnings=[]
    lower=source_sentence.casefold()
    if ("pocket watch open in his palm" in lower and
        model_event["kind"]=="CHANGE_STATE"):
        warnings.append("STATIC_WATCH_PREDICATE_MISREAD_AS_TRANSITION_RISK")
    if ("watched the pencil move" in lower and
        model_event["kind"]=="MOVE"):
        warnings.append("PENCIL_MOTION_OBSERVED_BUT_CAUSAL_ACTOR_UNKNOWN")
    return warnings


def _direct_model_batch(source, envelope, model):
    check(isinstance(envelope, dict) and
          envelope.get("error") is None and
          isinstance(envelope.get("raw"), dict),
          "SCENETRACE_V043_PROVIDER_RESPONSE_NOT_VERIFIED")
    raw=envelope["raw"]
    check(raw.get("model")==model and
          isinstance(raw.get("choices"),list) and
          len(raw["choices"])==1 and
          raw["choices"][0].get("finish_reason")=="stop",
          "SCENETRACE_V043_PROVIDER_MODEL_MISMATCH")
    body=raw["choices"][0]["message"]["content"]
    parsed,format_label=parse_json_model_reply(body)
    parsed,repairs=normalize_only_safe_advisory_fields(parsed)
    return parsed,format_label,repairs


def _raw_rows_from_source(*, source, receipt, model,
                          permit_partial_quarantine):
    check(receipt.get("model")==model and
          receipt.get("request_sha256")==source["batch"]["request_sha256"],
          "SCENETRACE_V043_WRONG_MODEL_OR_SOURCE_BATCH")
    parsed,format_label,repairs=_direct_model_batch(
        source,receipt["provider_envelope"],model,
    )
    # Real SERA exact-source binder is reused. Partial salvage is explicitly
    # limited to the two original Haiku pencil rows already isolated in v0.41.2.
    if permit_partial_quarantine:
        accepted,quarantined=isolate_rows(
            plan=source,parsed=parsed,prose=source["prose"],
        )
        return accepted,quarantined,format_label,repairs
    from experiments.sera.sentence_sweep_v010 import bind_batch
    bound=bind_batch(
        plan=source["plan"],batch_id=source["batch"]["batch_id"],
        raw=parsed,prose=source["prose"],
    )
    accepted=[{
        "sentence_id":row["sentence_id"],
        "source_spans_checked":True,
        "model_disposition":row["disposition"],
        "candidate_mentions":[{
            "entity_ref":m["entity_ref"],"quote":m["quote"],
            "start":m["start"],"end":m["end"],"role":m["role"],
        } for m in row["mentions"]],
        "candidate_events":[{
            "kind":e["kind"],"epistemic":e["epistemic"],
            "effect":e["effect"],"quote":e["quote"],
            "start":e["start"],"end":e["end"],
            "entity_refs":e["entity_refs"],
        } for e in row["events"]],
        "semantic_truth_verified":False,
    } for row in bound["rows"]]
    return accepted,[],format_label,repairs


def dual_real_evaluation(*, bench_receipt_dir, pencil_receipt_dir):
    bench_archive=verified_bench_receipts(bench_receipt_dir)
    pencil_archive=verified_pencil_receipts(pencil_receipt_dir)
    sources={"bench":prepare_bench(),"pencil":prepare_pencil()}
    check(sources["bench"]["prose"]==sources["pencil"]["prose"] and
          sources["bench"]["plan"]["source_prose_sha256"]==EXPECTED_SHA and
          sources["pencil"]["plan"]["source_prose_sha256"]==EXPECTED_SHA,
          "SCENETRACE_V043_FROZEN_SOURCE_MISMATCH")

    reports={"bench":bench_archive,"pencil":pencil_archive}
    records={}
    by_model={model:{} for model in MODELS}
    bind_meta=[]
    quarantined_by_model={m:[] for m in MODELS}
    for name in BATCHES:
        source=sources[name]
        archive=reports[name]
        check(archive["result.json"]["request_sha256"]==
              source["batch"]["request_sha256"] and
              archive["result.json"]["source_prose_sha256"]==EXPECTED_SHA,
              "SCENETRACE_V043_ARCHIVE_REQUEST_MISMATCH")
        for i,model in enumerate(MODELS,1):
            raw_receipt=archive[f"provider_reply_{i}.json"]
            permit=(name=="pencil" and model==MODELS[1])
            accepted,quarantined,format_label,repairs=_raw_rows_from_source(
                source=source,receipt=raw_receipt,model=model,
                permit_partial_quarantine=permit,
            )
            for row in accepted:
                sid=row["sentence_id"]
                check(sid not in by_model[model],
                      "SCENETRACE_V043_DUPLICATE_MODEL_SOURCE_ROW")
                by_model[model][sid]=row
            quarantined_by_model[model]+=quarantined
            bind_meta.append({
                "model":model,"source_batch":name,
                "source_bound_row_count":len(accepted),
                "quarantined_row_count":len(quarantined),
                "parsed_model_format":format_label,
                "nonsemantic_metadata_repairs":len(repairs),
                "new_provider_calls":0,
            })

    registry={k:v for k,v in REGISTRY.items()
              if k in entry_state()["entities"]}
    lexicon=json.loads(LEXICON.read_text(encoding="utf-8"))["candidates"]
    # Only one model's evidence per trace; no source-bound status is
    # treated as a consensus or authorization by collecting both.
    traces={}
    for model in MODELS:
        traces[model]=build_trace(
            prose=sources["bench"]["prose"],
            scene_id=sources["bench"]["plan"]["scene_key"],
            registry=registry,candidate_lexicon=lexicon,
            source_bound_rows=list(by_model[model].values()),
            quarantined_rows=quarantined_by_model[model],
        )
    plan=sources["bench"]["plan"]
    model_comparisons=[]
    risks=[]
    disagreement_count=0
    kind_disagreement_count=0
    field_disagreement_count=0
    unique_scoped=set()
    for sentence in plan["source_sentences"]:
        sid=sentence["id"]
        statuses=[]
        signatures=[]
        for model in MODELS:
            candidate=by_model[model].get(sid)
            quarantined=any(r["sentence_id"]==sid
                            for r in quarantined_by_model[model])
            state=("SOURCE_BOUND" if candidate else
                   "QUARANTINED" if quarantined else "NOT_EXTRACTED")
            statuses.append({
                "model":model,
                "status":state,
                "candidate_event_kinds":(
                    [e["kind"] for e in candidate["candidate_events"]]
                    if candidate else []),
                "candidate_entity_refs":(
                    [m["entity_ref"] for m in candidate["candidate_mentions"]]
                    if candidate else []),
            })
            if candidate:
                signatures.append(sorted([
                    (e["kind"],e["epistemic"],e["effect"],
                     tuple(sorted(e["entity_refs"])))
                    for e in candidate["candidate_events"]
                ]))
                for event in candidate["candidate_events"]:
                    for code in source_risks(
                        source_sentence=sentence["quote"],model_event=event,
                    ):
                        key=(model,sid,code,event["start"],event["end"])
                        if key in unique_scoped:
                            continue
                        unique_scoped.add(key)
                        risks.append({
                            "source_sentence_id":sid,
                            "model":model,
                            "risk_code":code,
                            "source_quote":event["quote"],
                            "source_start":event["start"],
                            "source_end":event["end"],
                            "semantic_truth_verified":False,
                            "world_state_write_authorized":False,
                        })
        both=len(signatures)==2
        disputed=both and signatures[0]!=signatures[1]
        disagreement_class=(
            "EVENT_KIND_SET_MISMATCH" if disputed and
            statuses[0]["candidate_event_kinds"]!=
                statuses[1]["candidate_event_kinds"] else
            "EVENT_ARGUMENT_OR_EPISTEMIC_MISMATCH" if disputed else None
        )
        if disputed:
            disagreement_count+=1
            if disagreement_class=="EVENT_KIND_SET_MISMATCH":
                kind_disagreement_count+=1
            else:
                field_disagreement_count+=1
        model_comparisons.append({
            "sentence_id":sid,"narrative_ordinal":len(model_comparisons)+1,
            "quote":sentence["quote"],
            "source_sha256":EXPECTED_SHA,
            "model_candidates":statuses,
            "both_models_source_bound":both,
            "event_candidate_signature_disagreement":disputed,
            "disagreement_class":disagreement_class,
            "independent_semantic_event_verified":False,
            "exact_story_second":None,
            "world_state_write_authorized":False,
        })
    check(all(t["canonical_commit_authorized"] is False
              for t in traces.values()),
          "SCENETRACE_V043_FORBIDDEN_WORLD_AUTHORITY")
    bound_counts={model:len(by_model[model]) for model in MODELS}
    quarantine_counts={model:len(quarantined_by_model[model])
                       for model in MODELS}
    return {
        "schema":SCHEMA,
        "status":"REAL_PAID_MODEL_RECEIPTS_CROSS_CHECKED_SHADOW_ONLY",
        "original_prose_sha256":EXPECTED_SHA,
        "real_paid_runs":[38936451931,38938438488],
        "source_sentence_count":len(model_comparisons),
        "source_sentence_rows_sampled_by_both_models":len([
            row for row in model_comparisons if
            all(m["status"]!="NOT_EXTRACTED" for m in
                row["model_candidates"])
        ]),
        "source_bound_model_rows":bound_counts,
        "quarantined_model_rows":quarantine_counts,
        "source_bound_event_candidate_disagreements":disagreement_count,
        "event_kind_disagreement_count":kind_disagreement_count,
        "event_argument_or_epistemic_disagreement_count":
            field_disagreement_count,
        "source_bound_semantic_risk_flags":risks,
        "model_batch_evidence":bind_meta,
        "source_timeline":model_comparisons,
        "semantic_gold_labels_independently_established":False,
        "semantic_recall_improvement_proven":False,
        "model_error_rate_reduction_proven":False,
        "additional_paid_requests":0,
        "additional_cost_usd":"0",
        "production_db_writes":0,
        "sqlite_lab_writes":0,
        "canonical_commit_authorized":False,
        "recommendation":"SHADOW_ONLY_MEASURE_BEFORE_INTEGRATION",
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--bench-receipt-dir",type=Path,required=True)
    parser.add_argument("--pencil-receipt-dir",type=Path,required=True)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    proof=dual_real_evaluation(
        bench_receipt_dir=args.bench_receipt_dir,
        pencil_receipt_dir=args.pencil_receipt_dir,
    )
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(
            json.dumps(proof,ensure_ascii=False,sort_keys=True,indent=2)+"\n",
            encoding="utf-8",
        )
    print(json.dumps({
        "status":proof["status"],
        "source_sentences":proof["source_sentence_count"],
        "bound_model_rows":proof["source_bound_model_rows"],
        "quarantined_model_rows":proof["quarantined_model_rows"],
        "event_signature_disagreements":
            proof["source_bound_event_candidate_disagreements"],
        "event_kind_disagreements":proof["event_kind_disagreement_count"],
        "event_argument_or_epistemic_disagreements":
            proof["event_argument_or_epistemic_disagreement_count"],
        "risk_flags":[(r["model"],r["source_sentence_id"],r["risk_code"])
                      for r in proof["source_bound_semantic_risk_flags"]],
        "extra_model_calls":proof["additional_paid_requests"],
        "semantic_recall_improvement_proven":False,
    },ensure_ascii=False))


if __name__=="__main__":
    main()
