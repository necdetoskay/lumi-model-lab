"""SERA v0.42 — genuine paid-receipt anchored SceneTrace shadow smoke.

Reads the frozen actual Mara source and v0.41.2's source-bound/quarantined
Haiku rows derived afresh from the SHA-pinned v0.41 *paid* evidence. Produces
a full-source timeline, NOT a new independent model judgement. Zero network
model calls, SQLite writes, application output token ceilings or G2 release.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.mara_s1_typed_live_v05 import REGISTRY, entry_state
from experiments.sera.real_blind_benchmark_v040 import (
    EXPECTED_SHA, LEXICON,
)
from experiments.sera.real_pencil_benchmark_v041 import prepare
from experiments.sera.real_pencil_partial_rows_v0412 import replay as replay_real
from experiments.sera.scene_trace_shadow_v042 import build_trace,comparison

SCHEMA = "sera.scene-trace-real-mara-shadow-smoke.v0.42"


def actual_mara_trace(receipt_dir):
    original = prepare()
    assert prose_hash(original["prose"])==EXPECTED_SHA
    history = replay_real(receipt_dir)  # validates original paid files SHA
    if (history["source_run_id"]!=38938438488 or
        history["original_source_sha256"]!=EXPECTED_SHA or
        history["whole_provider_response_bound"] is not False or
        history["canonical_commit_authorized"] is not False or
        history["new_provider_calls"]!=0):
        raise CoverageError("SCENETRACE_ARCHIVED_PAID_REPLAY_NOT_TRUSTED")
    aliases={k:v for k,v in REGISTRY.items()
             if k in entry_state()["entities"]}
    lexicon=json.loads(LEXICON.read_text(encoding="utf-8"))["candidates"]
    trace=build_trace(
        prose=original["prose"],
        scene_id=original["plan"]["scene_key"],
        registry=aliases,candidate_lexicon=lexicon,
        source_bound_rows=history["accepted_source_bound_candidate_rows"],
        quarantined_rows=history["quarantined_rows"],
    )
    observed=comparison(
        trace,
        baseline_model_rows=len(history["accepted_source_bound_candidate_rows"]),
        baseline_quarantined_rows=len(history["quarantined_rows"]),
    )
    lookup={r["sentence_id"]:r for r in trace["rows"]}
    bench=next(r for r in trace["rows"] if
               "stood beside the bench" in r["quote"])
    pencil=next(r for r in trace["rows"] if
                "watched the pencil move" in r["quote"])
    watch=next(r for r in trace["rows"] if
               "pocket watch open in his palm" in r["quote"])
    assert bench["source_sentence_accounted_for"]
    assert any(a["ref"]=="candidate:bench" for a in bench["atoms"])
    assert pencil["model_row_status"]=="MODEL_ROW_SOURCE_BOUND_NONCANONICAL"
    assert pencil["narrative_ordinal"]>bench["narrative_ordinal"]
    assert "OBSERVED_MOTION_DOES_NOT_IDENTIFY_CAUSAL_ACTOR" in pencil["risk_hints"]
    assert pencil["exact_story_second"] is None
    assert watch["state_transition_authorized"] is False
    assert "STATIC_WATCH_DESCRIPTION_NOT_EVIDENCE_OF_OPEN_ACTION" in watch["risk_hints"]
    assert trace["source_sentence_count"]==28
    assert trace["source_bound_model_sentence_count"]==2
    assert trace["quarantined_model_sentence_count"]==2
    assert trace["external_model_calls"]==0
    assert observed["extraction_recall_improvement_proven"] is False
    return {
        "schema":SCHEMA,
        "status":"REAL_MARA_SOURCE_TRACE_DIAGNOSTIC_ONLY",
        "real_model_source_run":38938438488,
        "real_model_source_artifact":12061129188,
        "source_sha256":EXPECTED_SHA,
        "trace":trace,
        "baseline_comparison":observed,
        "three_focus_sentences":[{
            "topic":name,
            "sentence_id":row["sentence_id"],
            "narrative_ordinal":row["narrative_ordinal"],
            "model_row_status":row["model_row_status"],
            "risk_hints":row["risk_hints"],
            "candidate_entity_refs":sorted({
                a["ref"] for a in row["atoms"]
                if a["kind"] in ("ENTITY_REFERENCE_HINT",
                                 "SOURCE_BOUND_MODEL_ENTITY_CANDIDATE")
            }),
            "exact_story_second":row["exact_story_second"],
            "state_transition_authorized":False,
        } for name,row in (("bench",bench),("watch_already_open",watch),
                           ("pencil_observed_move",pencil))],
        "new_provider_calls":0,
        "canonical_commit_authorized":False,
        "project_lumi_db_writes":0,
        "simulated_world_writes":0,
    }


def write_markdown(proof):
    data=proof["trace"]
    lines=[
        "# SceneTrace v0.42 — Mara S1 source-order timeline",
        "",
        "Real provider data re-used, zero additional LLM calls. The line numbers",
        "are narrative order, **not measured clock time**. Each source row is",
        "advisory until independent semantic qualification.",
        "",
        "| Order | Source sentence | Model evidence | Candidate atoms | Risks |",
        "|---:|---|---|---:|---|",
    ]
    for r in data["rows"]:
        source=r["quote"].replace("|",r"\|").replace("\n"," ")
        status=r["model_row_status"].replace("MODEL_ROW_","")
        risks="; ".join(r["risk_hints"]) or "—"
        lines.append(f"| {r['narrative_ordinal']} | {source} | {status} | "
                     f"{len(r['atoms'])} | {risks} |")
    lines+=["",
            "**No full recall guarantee. No real event second, physical mover,",
            "speaker certainty, approved world mutation or G2 canonical change.**",
            ""]
    return "\n".join(lines)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--receipt-dir",type=Path,required=True)
    parser.add_argument("--json-output",type=Path)
    parser.add_argument("--markdown-output",type=Path)
    args=parser.parse_args()
    proof=actual_mara_trace(args.receipt_dir)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True,exist_ok=True)
        args.json_output.write_text(
            json.dumps(proof,ensure_ascii=False,indent=2,sort_keys=True)+"\n",
            encoding="utf-8",
        )
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True,exist_ok=True)
        args.markdown_output.write_text(write_markdown(proof),
                                        encoding="utf-8")
    print(json.dumps({
        "status":proof["status"],
        "real_model_source_run":proof["real_model_source_run"],
        "sentences":proof["trace"]["source_sentence_count"],
        "atoms":proof["trace"]["atom_count"],
        "model_rows_source_bound":
            proof["trace"]["source_bound_model_sentence_count"],
        "model_rows_quarantined":
            proof["trace"]["quarantined_model_sentence_count"],
        "source_only_unassessed":
            proof["trace"]["source_only_model_unassessed_sentence_count"],
        "comparison":proof["baseline_comparison"],
        "new_provider_calls":0,
        "canonical_commit_authorized":False,
    },ensure_ascii=False))


if __name__=="__main__":
    main()
