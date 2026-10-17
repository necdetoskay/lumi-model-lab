"""SERA v0.52 source-bound story chronology, NONCANONICAL.

Tracks every exact sentence and optional independent *model candidate*
events, with source-span provenance and immutable deterministic digest.
Narrative order is NOT a proven event timestamp, clock text does NOT
assert real action time, and model proposals never mutate the world.
No network, writer gold, manual repairs or production data writes.
"""
from __future__ import annotations

from hashlib import sha256

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.sentence_ledger_v06 import scanner
from experiments.sera.sentence_sweep_v010 import REPORT_SCHEMA
from experiments.sera.world_state_v02 import canonical

SCHEMA="sera.v052-source-chronology-noncanonical"


def _need(ok,code):
    if not ok:
        raise CoverageError(code)


def build_source_chronology(*,prose,scene_key,world_sha256,
                            registry,candidate_lexicon,model_report=None):
    """Read-only, source-only chronological ordinal and evidence inventory."""
    _need(isinstance(scene_key,str) and bool(scene_key.strip()) and
          isinstance(world_sha256,str) and len(world_sha256)==64 and
          all(x in "0123456789abcdef" for x in world_sha256),
          "V052_CHRONOLOGY_SCOPE_INVALID")
    scan=scanner(prose=prose,registry=registry,
                 candidate_lexicon=candidate_lexicon)
    source=scan["sentences"]
    ids=[s["id"] for s in source]
    _need(len(ids)==len(set(ids)),
          "V052_CHRONOLOGY_DUPLICATE_SOURCE_SENTENCE")
    rows_by_id={}
    candidate_events=[]
    source_sha=prose_hash(prose)
    if model_report is not None:
        _need(isinstance(model_report,dict) and
              model_report.get("schema")==REPORT_SCHEMA and
              model_report.get("source_prose_sha256")==source_sha and
              model_report.get("scene_key")==scene_key and
              model_report.get("sentences_accounted_for")==len(source) and
              model_report.get("canonical_commit_authorized") is False and
              model_report.get("world_state_writes")==0 and
              model_report.get("semantic_recall_proven") is False,
              "V052_CHRONOLOGY_MODEL_REPORT_NOT_SOURCE_BOUND")
        ledger=model_report.get("model_ledger")
        _need(isinstance(ledger,dict) and
              ledger.get("prose_sha256")==source_sha and
              isinstance(ledger.get("rows"),list) and
              [r.get("sentence_id") for r in ledger["rows"]
               if isinstance(r,dict)]==ids and
              isinstance(model_report.get("candidate_events"),list),
              "V052_CHRONOLOGY_MODEL_LEDGER_INCOMPLETE")
        rows_by_id={r["sentence_id"]:r for r in ledger["rows"]}
        seen=set()
        sid_to_source={s["id"]:s for s in source}
        declared={(r["sentence_id"],event_id)
                  for r in ledger["rows"]
                  for event_id in r["event_ids"]}
        for event in model_report["candidate_events"]:
            _need(isinstance(event,dict) and
                  all(key in event for key in (
                      "event_id","sentence_id","start","end","quote",
                      "kind","effect","epistemic")) and
                  (event["sentence_id"],event["event_id"]) in declared and
                  (event["sentence_id"],event["event_id"]) not in seen,
                  "V052_CHRONOLOGY_MODEL_EVENT_UNLINKED")
            sid=event["sentence_id"]
            src=sid_to_source[sid]
            a,b=event["start"],event["end"]
            _need(type(a) is int and type(b) is int and
                  src["start"]<=a<b<=src["end"] and
                  prose[a:b]==event["quote"],
                  "V052_CHRONOLOGY_MODEL_EVENT_SPAN_INVALID")
            seen.add((sid,event["event_id"]))
            candidate_events.append({
                "event_id":event["event_id"],
                "source_sentence_id":sid,
                "source_start":a,"source_end":b,
                "exact_evidence_quote":event["quote"],
                "model_event_kind":event["kind"],
                "model_epistemic":event["epistemic"],
                "model_effect":event["effect"],
                "source_ordinal":ids.index(sid)+1,
                "event_action_minute":None,
                "time_provenance":"NOT_PROVEN",
                "event_truth":"MODEL_CANDIDATE_UNVERIFIED",
                "canonical_commit_authorized":False,
            })
        _need(seen==declared,
              "V052_CHRONOLOGY_MODEL_EVENT_COVERAGE_MISMATCH")
    rows=[]
    hint_by_sid={sid:[] for sid in ids}
    for hint in scan["hints"]:
        hint_by_sid[hint["sentence_id"]].append({
            "ref":hint["ref"],"tier":hint["tier"],
            "start":hint["start"],"end":hint["end"],
            "physical_presence":"UNDETERMINED"})
    cues={c["sentence_id"]:c for c in scan["sentence_cues"]}
    for ordinal,src in enumerate(source,start=1):
        sid=src["id"]
        item=cues[sid]
        rows.append({
            "source_ordinal":ordinal,
            "sentence_id":sid,
            "source_start":src["start"],"source_end":src["end"],
            "exact_source_quote":src["quote"],
            "action_minute":None,
            "action_time_status":"NOT_PROVEN",
            "quoted_clock_expressions":[{
                "quote":t["quote"],"start":t["start"],"end":t["end"],
                "is_action_time":False,
            } for t in item["time_expressions"]],
            "lexical_action_cues":[{
                "family":c["family"],"quote":c["quote"],
                "start":c["start"],"end":c["end"]
            } for c in item["cues"]],
            "entity_hints":hint_by_sid[sid],
            "model_disposition":(
                rows_by_id[sid]["disposition"]
                if sid in rows_by_id else "NOT_EXTRACTED"),
            "model_event_ids":(
                list(rows_by_id[sid]["event_ids"])
                if sid in rows_by_id else []),
            "physical_world_authority":"NONE",
        })
    candidate_events.sort(key=lambda e:(
        e["source_start"],e["source_end"],e["event_id"]))
    report={
        "schema":SCHEMA,
        "scene_key":scene_key,
        "source_prose_sha256":source_sha,
        "entry_world_sha256":world_sha256,
        "source_sentence_count":len(rows),
        "sentences_accounted_for":len(rows),
        "candidate_event_count":len(candidate_events),
        "model_report_available":model_report is not None,
        "time_order_semantics":"SOURCE_ORDINAL_ONLY",
        "wall_clock_action_time_proven":False,
        "source_sentences":rows,
        "model_candidate_events":candidate_events,
        "unresolved_semantics":(
            list(model_report["findings"])
            if model_report is not None else ["MODEL_EXTRACTION_NOT_AVAILABLE"]),
        "source_graph_status":"HOLD_NONCANONICAL",
        "canonical_commit_authorized":False,
        "world_db_writes":0,
    }
    # A digest can be compared across restarts without changing model input.
    return dict(report,chronology_sha256=sha256(
        canonical(report).encode("utf-8")).hexdigest())
