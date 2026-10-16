"""SERA v0.42 / SceneTrace v0.1 — full-source read-only story timeline.

Reuse existing v0.6 source scanner and v0.41.2 SOURCE-BOUND model rows.
Source order is NEVER treated as exact event time. Lexical references are
NOT real entities. Candidates and quoted observations NEVER approve a
transition, actor, holder, physical position, causality, or canonical write.

The sidecar only exposes what the source / preexisting evidence already
contains. This is NOT an independent semantic extractor or a new model.
"""
from __future__ import annotations

from hashlib import sha256
import re

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.sentence_ledger_v06 import scanner
from experiments.sera.world_state_v02 import canonical

SCHEMA = "sera.scene-trace-shadow.v0.42"
OBSERVATION_ONLY = "TEXT_ORDER_NO_EXACT_ACTION_TIME"
SAFE_TYPES = frozenset({"SOURCE_SENTENCE", "ENTITY_REFERENCE_HINT",
                        "ACTION_OR_SPEECH_CUE", "TIME_EXPRESSION_MENTION",
                        "PRONOUN_REFERENCE_UNRESOLVED",
                        "SOURCE_BOUND_MODEL_ENTITY_CANDIDATE",
                        "SOURCE_BOUND_MODEL_EVENT_CANDIDATE"})


def require(ok, code):
    if not ok:
        raise CoverageError(code)


def _source_span(prose, sentence, atom):
    require(type(atom.get("start")) is int and
            type(atom.get("end")) is int and
            sentence["start"] <= atom["start"] < atom["end"] <= sentence["end"] and
            atom.get("quote") == prose[atom["start"]:atom["end"]],
            "SCENETRACE_SOURCE_SPAN_UNVERIFIED")


def _atom(*, scene_id, sentence, ordinal, kind, source, ref=None,
          source_proof="LEXICAL_HINT_ONLY", **extra):
    require(kind in SAFE_TYPES, "SCENETRACE_KIND_UNREGISTERED")
    value = {
        "atom_id": f"{scene_id}:{sentence['id']}:a{ordinal:03d}",
        "kind": kind, "source_start": source["start"],
        "source_end": source["end"], "quote": source["quote"],
        "ref": ref, "evidence_authority": source_proof,
        "epistemic_status": "UNVERIFIED_NOT_CANON",
        "actor_id": None, "observer_id": None,
        "from_location": None, "to_location": None,
        "from_holder": None, "to_holder": None,
        "state_delta": None,
        "world_commit_authorized": False,
    }
    value.update(extra)
    return value


def _risk_codes(sentence_quote):
    """Contextual scrutiny flags only; not an assertion of physical truth."""
    risks=[]
    if re.search(r"\bwatch\s+open\s+in\b",sentence_quote,re.I):
        risks.append("STATIC_WATCH_DESCRIPTION_NOT_EVIDENCE_OF_OPEN_ACTION")
    if re.search(r"\bwatched\b.{0,80}\bmove\b",sentence_quote,re.I|re.S):
        risks.append("OBSERVED_MOTION_DOES_NOT_IDENTIFY_CAUSAL_ACTOR")
    return risks


def build_trace(*, prose, scene_id, registry, candidate_lexicon,
                source_bound_rows=(), quarantined_rows=()):
    require(isinstance(scene_id,str) and bool(scene_id.strip()) and
            isinstance(registry,dict) and isinstance(candidate_lexicon,dict),
            "SCENETRACE_INPUT_INVALID")
    scan = scanner(prose=prose, registry=registry,
                   candidate_lexicon=candidate_lexicon)
    by_id={s["id"]:s for s in scan["sentences"]}
    accepted={}
    quarantine={}
    require(isinstance(source_bound_rows,(list,tuple)) and
            isinstance(quarantined_rows,(list,tuple)),
            "SCENETRACE_MODEL_EVIDENCE_LIST_INVALID")
    for row in source_bound_rows:
        require(isinstance(row,dict) and
                row.get("sentence_id") in by_id and
                row["sentence_id"] not in accepted and
                row.get("source_spans_checked") is True and
                row.get("semantic_truth_verified") is False and
                isinstance(row.get("candidate_mentions"),list) and
                isinstance(row.get("candidate_events"),list) and
                set(row)=={
                    "sentence_id","source_spans_checked",
                    "model_disposition","candidate_mentions",
                    "candidate_events","semantic_truth_verified",
                },
                "SCENETRACE_UNQUALIFIED_SOURCE_BOUND_MODEL_ROW")
        src=by_id[row["sentence_id"]]
        for cat,items in (("candidate_mentions",row["candidate_mentions"]),
                          ("candidate_events",row["candidate_events"])):
            for item in items:
                require(isinstance(item,dict) and
                        isinstance(item.get("quote"),str),
                        "SCENETRACE_MODEL_ATOM_SHAPE_INVALID")
                _source_span(prose,src,item)
                if cat=="candidate_events":
                    require(item.get("epistemic") is not None and
                            item.get("kind") is not None and
                            isinstance(item.get("entity_refs"),list),
                            "SCENETRACE_MODEL_EVENT_UNTYPED")
                else:
                    require(isinstance(item.get("entity_ref"),str) and
                            bool(item["entity_ref"]),
                            "SCENETRACE_MODEL_MENTION_ID_INVALID")
        accepted[row["sentence_id"]]=row
    for row in quarantined_rows:
        require(isinstance(row,dict) and row.get("sentence_id") in by_id and
                row["sentence_id"] not in accepted and
                row["sentence_id"] not in quarantine and
                row.get("source_spans_checked") is False and
                isinstance(row.get("reason"),str) and
                row.get("automated_repair_not_possible_without_reextraction")
                     is True,
                "SCENETRACE_QUARANTINE_PROOF_INVALID")
        quarantine[row["sentence_id"]]=row

    lines=[]
    total_atoms=0
    for order,sentence in enumerate(scan["sentences"],1):
        sid=sentence["id"]
        atoms=[]
        def add(kind, source, ref=None, proof="LEXICAL_HINT_ONLY", **extra):
            _source_span(prose,sentence,source)
            atoms.append(_atom(
                scene_id=scene_id,sentence=sentence,ordinal=len(atoms)+1,
                kind=kind,source=source,ref=ref,source_proof=proof,
                **extra,
            ))
        add("SOURCE_SENTENCE",sentence,proof="EXACT_PROSE_SOURCE")
        for hint in scan["hints"]:
            if hint["sentence_id"]==sid:
                add("ENTITY_REFERENCE_HINT",hint,hint["ref"],
                    tier=hint["tier"],
                    registered=hint["tier"]=="REGISTERED")
        cues=next(x for x in scan["sentence_cues"]
                  if x["sentence_id"]==sid)
        for cue in cues["cues"]:
            add("ACTION_OR_SPEECH_CUE",cue,
                cue["family"],cue_family=cue["family"])
        for expression in cues["time_expressions"]:
            add("TIME_EXPRESSION_MENTION",expression,
                proof="EXACT_PROSE_TIME_MENTION_NOT_ACTION_CLOCK",
                reported_time_only=True)
        for pronoun in cues["pronouns"]:
            add("PRONOUN_REFERENCE_UNRESOLVED",pronoun,
                proof="EXACT_PROSE_UNRESOLVED_REFERENCE")
        if sid in accepted:
            row=accepted[sid]
            for mention in row["candidate_mentions"]:
                add("SOURCE_BOUND_MODEL_ENTITY_CANDIDATE",{
                    "start":mention["start"],"end":mention["end"],
                    "quote":mention["quote"],
                },mention["entity_ref"],proof="MODEL_SOURCE_SPAN_ONLY")
            for event in row["candidate_events"]:
                add("SOURCE_BOUND_MODEL_EVENT_CANDIDATE",{
                    "start":event["start"],"end":event["end"],
                    "quote":event["quote"],
                },proof="MODEL_SOURCE_SPAN_ONLY",
                model_kind=event["kind"],
                model_epistemic=event["epistemic"],
                proposed_entity_refs=event["entity_refs"])
        status=("MODEL_ROW_SOURCE_BOUND_NONCANONICAL" if sid in accepted else
                "MODEL_ROW_QUARANTINED" if sid in quarantine else
                "SOURCE_ONLY_MODEL_NOT_ASSESSED")
        lines.append({
            "scene_id":scene_id,
            "sentence_id":sid,
            "source_start":sentence["start"],
            "source_end":sentence["end"],
            "quote":sentence["quote"],
            "source_sha256":scan["prose_sha256"],
            "narrative_ordinal":order,
            "time_semantics":OBSERVATION_ONLY,
            "exact_story_second":None,
            "story_time_window":None,
            "depends_on_events":[],
            "model_row_status":status,
            "quarantine_reason":(
                quarantine[sid]["reason"] if sid in quarantine else None
            ),
            "risk_hints":_risk_codes(sentence["quote"]),
            "atoms":atoms,
            "source_sentence_accounted_for":True,
            "semantic_completeness_proven":False,
            "state_transition_authorized":False,
        })
        total_atoms+=len(atoms)
    require(len(lines)==len(by_id) and all(
            len(r["atoms"])>=1 for r in lines),
            "SCENETRACE_SOURCE_COVERAGE_INCOMPLETE")
    return {
        "schema":SCHEMA,"scene_id":scene_id,
        "source_sha256":prose_hash(prose),
        "source_sentence_count":len(lines),
        "sentence_order_is_action_time":False,
        "source_bound_model_sentence_count":len(accepted),
        "quarantined_model_sentence_count":len(quarantine),
        "source_only_model_unassessed_sentence_count":
            len(lines)-len(accepted)-len(quarantine),
        "atom_count":total_atoms,
        "rows":lines,
        "semantic_completeness_proven":False,
        "newly_validated_state_changes":0,
        "canonical_commit_authorized":False,
        "production_db_writes":0,
        "sqlite_lab_writes":0,
        "external_model_calls":0,
    }


def comparison(trace, *, baseline_model_rows, baseline_quarantined_rows):
    """Coverage VISIBILITY delta, not independent recall/precision gain."""
    require(trace.get("schema")==SCHEMA and
            type(baseline_model_rows) is int and baseline_model_rows>=0 and
            type(baseline_quarantined_rows) is int and
            baseline_quarantined_rows>=0 and
            baseline_model_rows==trace["source_bound_model_sentence_count"] and
            baseline_quarantined_rows==trace["quarantined_model_sentence_count"],
            "SCENETRACE_BASELINE_MISMATCH")
    return {
        "schema":"sera.scene-trace-comparison.v0.42",
        "baseline_source_bound_model_rows":baseline_model_rows,
        "baseline_quarantined_model_rows":baseline_quarantined_rows,
        "trace_source_sentence_rows":trace["source_sentence_count"],
        "trace_source_bound_model_rows":trace["source_bound_model_sentence_count"],
        "trace_quarantined_model_rows":trace["quarantined_model_sentence_count"],
        "trace_source_only_unassessed_rows":
            trace["source_only_model_unassessed_sentence_count"],
        "incremental_independent_semantic_events_proven":0,
        "evidence_visibility_improved":True,
        "extraction_recall_improvement_proven":False,
        "cost_usd_incremental":"0",
        "recommendation":"KEEP_SHADOW_ONLY_PENDING_INDEPENDENT_RECALL_MEASUREMENT",
        "canonical_commit_authorized":False,
    }
