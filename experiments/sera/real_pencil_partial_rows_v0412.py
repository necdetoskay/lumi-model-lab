"""v0.41.2: independent real-model sentence-row isolation, zero new paid calls.

This is SOURCE BINDING PER ROW, never a full-scene sweep or world permission.
It preserves valid model candidate rows while quarantining fabricated or
misquoted rows; it NEVER rewrites a quote, guesses an actor, creates an entity,
or fabricates row-event claims to pass completeness.
"""
from __future__ import annotations

from hashlib import sha256
import argparse
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError
from experiments.sera.haiku_evidence_recovery_v011 import parse_json_model_reply
from experiments.sera.real_pencil_benchmark_v041 import prepare
from experiments.sera.real_pencil_receipt_replay_v0411 import (
    EVIDENCE_RUN, EVIDENCE_ARTIFACT, load_archived,
    normalize_only_safe_advisory_fields,
)
from experiments.sera.sentence_sweep_v010 import bind_batch

SCHEMA = "sera.real-pencil-partial-row-quarantine.v0.41.2"


def isolate_rows(*,plan,parsed,prose):
    """Prove each source span individually; every other row is a PLACEHOLDER.

    Placeholders are used ONLY while running v0.10's real binder; they are
    never persisted as evidence, emitted into the candidate list or passed
    to an aggregate/completeness validator.
    """
    accepted=[]
    quarantine=[]
    expected=plan["batch"]["sentence_ids"]
    source_rows=parsed["rows"]
    if len(source_rows)!=len(expected) or any(
        not isinstance(row,dict) or row.get("sentence_id")!=expected[i]
        for i,row in enumerate(source_rows)
    ):
        raise CoverageError("V0412_SOURCE_ROWS_ID_OR_COUNT_INVALID")
    for index,row in enumerate(source_rows):
        masked=[{
            "sentence_id":sid,
            "disposition":"AMBIGUOUS",
            "reason":"V0412_MASKED_NOT_MODEL_EVIDENCE",
            "mentions":[],"events":[],
        } for sid in expected]
        masked[index]=row
        try:
            bound=bind_batch(
                plan=plan["plan"],batch_id=plan["batch"]["batch_id"],
                raw={"rows":masked},prose=prose,
            )
            valid_row=bound["rows"][index]
            accepted.append({
                "sentence_id":valid_row["sentence_id"],
                "source_spans_checked":True,
                "model_disposition":valid_row["disposition"],
                "candidate_mentions":[{
                    "entity_ref":m["entity_ref"],
                    "quote":m["quote"],
                    "start":m["start"],"end":m["end"],
                    "role":m["role"],
                } for m in valid_row["mentions"]],
                "candidate_events":[{
                    "kind":e["kind"],"epistemic":e["epistemic"],
                    "effect":e["effect"],"quote":e["quote"],
                    "start":e["start"],"end":e["end"],
                    "entity_refs":e["entity_refs"],
                } for e in valid_row["events"]],
                "semantic_truth_verified":False,
            })
        except (CoverageError,ValueError,KeyError,TypeError) as exc:
            quarantine.append({
                "sentence_id":expected[index],
                "reason":str(exc)[:160],
                "source_spans_checked":False,
                "automated_repair_not_possible_without_reextraction":True,
            })
    return accepted,quarantine


def replay(directory):
    archived=load_archived(directory)
    source=prepare()
    proof=archived["result.json"]
    assert proof["request_sha256"]==source["batch"]["request_sha256"]
    receipt=archived["provider_reply_2.json"]
    assert receipt["model"]=="anthropic/claude-haiku-4.5"
    raw=receipt["provider_envelope"]["raw"]
    content=raw["choices"][0]["message"]["content"]
    parsed,envelope=parse_json_model_reply(content)
    normalized,repairs=normalize_only_safe_advisory_fields(parsed)
    accepted,quarantined=isolate_rows(
        plan=source,parsed=normalized,prose=source["prose"],
    )
    pencil=next((row for row in accepted
                 if row["sentence_id"]==source["target_sentence_id"]),None)
    return {
        "schema":SCHEMA,
        "status":"PARTIAL_REAL_HAIKU_SOURCE_ROWS_QUARANTINED_HOLD",
        "source_run_id":EVIDENCE_RUN,
        "source_artifact_id":EVIDENCE_ARTIFACT,
        "original_source_sha256":proof["source_prose_sha256"],
        "original_model_content_sha256":sha256(
            content.encode("utf-8")
        ).hexdigest(),
        "model":"anthropic/claude-haiku-4.5",
        "json_envelope":envelope,
        "nonsemantic_metadata_repairs":repairs,
        "accepted_source_bound_candidate_rows":accepted,
        "quarantined_rows":quarantined,
        "target_pencil_row_source_bound":pencil is not None and any(
            m["entity_ref"] in ("new:pencil","candidate:pencil")
            for m in pencil["candidate_mentions"]
        ),
        "whole_provider_response_bound":False,
        "source_complete":False,
        "epistemic_actor_causality_verified":False,
        "independent_semantic_qualification":False,
        "canonical_commit_authorized":False,
        "production_db_writes":0,
        "sqlite_lab_writes":0,
        "new_provider_calls":0,
    }


def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--receipt-dir",type=Path,required=True)
    cli.add_argument("--output",type=Path)
    args=cli.parse_args()
    result=replay(args.receipt_dir)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(
            json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",
            encoding="utf-8",
        )
    print(json.dumps({
        "status":result["status"],
        "accepted_candidate_sentences":[x["sentence_id"] for x in
            result["accepted_source_bound_candidate_rows"]],
        "quarantined_sentences":result["quarantined_rows"],
        "pencil_candidate_source_bound":
            result["target_pencil_row_source_bound"],
        "new_provider_calls":0,
        "canonical_commit_authorized":False,
    },ensure_ascii=False))


if __name__=="__main__":
    main()
