"""SERA v0.13 — full 25-event source-bound Mara qualification blocker census.

This analyzes the original completed independent Gemini model sweep,
Haiku-backed *proposed* repairs and a NEW versioned facet simulation.
It DOES NOT approve a world fact, infer clock minutes, or mutate SQLite.
A proposal passing source binding is not a semantic pass. Every original
event remains HOLD until independently qualified and authorized.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy

from experiments.sera.coverage import CoverageError,prose_hash
from experiments.sera.world_state_v02 import canonical,validate as validate_v02

SCHEMA="sera.mara-s1-event-qualification-census.v0.13"
EXPECTED_SHA="80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03"
EPHEMERAL_PREFIXES=("new:","candidate:")
CLAIMS=("REPORTED_CLAIM","HYPOTHESIS","NEGATED","UNCERTAIN")
CHANGE_KINDS={"CLOSE","OPEN","WRITE","TRANSFER","MOVE","CHANGE_STATE",
              "KNOWLEDGE_UPDATE","LEARN_FACT","UNMAPPED"}
CHANGES={"OBJECT","DOCUMENT","CHARACTER_KNOWLEDGE","WORLD","UNKNOWN"}

def need(flag,code):
    if not flag:
        raise CoverageError(code)

def _event_source(prose,event):
    need(isinstance(event,dict) and
         isinstance(event.get("event_id"),str) and event["event_id"] and
         type(event.get("start")) is int and
         type(event.get("end")) is int and
         0<=event["start"]<event["end"]<=len(prose) and
         prose[event["start"]:event["end"]]==event.get("quote") and
         isinstance(event.get("sentence_id"),str) and
         isinstance(event.get("kind"),str) and
         isinstance(event.get("epistemic"),str) and
         isinstance(event.get("effect"),str) and
         isinstance(event.get("entity_refs"),list),
         "V013_CENSUS_EVENT_NOT_SOURCE_BOUND")

def run(*,prose:str,world:dict,full_report:dict,
        repairs:dict,versioned_simulation:dict)->dict:
    validate_v02(world)
    need(prose_hash(prose)==EXPECTED_SHA,
         "V013_CENSUS_FROZEN_SOURCE_MISMATCH")
    need(isinstance(full_report,dict) and
         full_report.get("schema")=="sera.blind-sweep-bound.v0.10" and
         full_report.get("source_prose_sha256")==EXPECTED_SHA and
         full_report.get("sentences_accounted_for")==28 and
         full_report.get("status")=="HOLD_MODEL_SEMANTICS_UNVERIFIED" and
         full_report.get("canonical_commit_authorized") is False and
         full_report.get("world_state_writes")==0 and
         len(full_report.get("candidate_events",[]))==25,
         "V013_CENSUS_FULL_SWEEP_UNQUALIFIED")
    need(isinstance(repairs,dict) and
         repairs.get("schema")=="sera.mara-s1-provisional-corrections.v0.12" and
         repairs.get("source_prose_sha256")==EXPECTED_SHA and
         repairs.get("status")=="PROPOSED_REPAIR_ONLY_CANNOT_COMMIT" and
         repairs.get("canonical_commit_authorized") is False and
         repairs.get("world_state_writes")==0 and
         len(repairs.get("replacements",[]))==2,
         "V013_CENSUS_REPAIR_PROVENANCE_INVALID")
    need(isinstance(versioned_simulation,dict) and
         versioned_simulation.get("schema")==
           "sera.mara-s1-v013-versioned-facets-qualification" and
         versioned_simulation.get("source_prose_sha256")==EXPECTED_SHA and
         versioned_simulation.get("simulated_reducer_events")==3 and
         versioned_simulation.get("state_schema")==
           "sera.world-state.v0.13-experimental" and
         versioned_simulation.get("history_verifies_deterministically") is True and
         versioned_simulation.get("world_v02_snapshot_unchanged") is True and
         versioned_simulation.get("production_database_writes")==0 and
         versioned_simulation.get("real_canonical_authorization") is False and
         versioned_simulation.get("gold_reference_qualified") is False,
         "V013_CENSUS_VERSIONED_TEST_PROOF_INVALID")
    replace_map={}
    for repair in repairs["replacements"]:
        key=repair.get("existing_event_id")
        need(key not in replace_map and
             repair.get("canonical_commit_authorized") is False and
             repair.get("status")=="PROPOSED_AWAITING_TYPED_REDUCER_AND_JUDGE",
             "V013_CENSUS_REPAIR_NOT_SAFE")
        replace_map[key]=repair
    need(set(replace_map)=={
        "batch_004:s014:e1","batch_006:s021:e1"},
        "V013_CENSUS_UNEXPECTED_REPAIR_TARGET")
    known=world["entities"]
    seen=set()
    rows=[]
    all_unregistered=set()
    all_bodyparts=set()
    kinds=Counter()
    epistemics=Counter()
    blockers=Counter()
    for e in full_report["candidate_events"]:
        _event_source(prose,e)
        ident=e["event_id"]
        need(ident not in seen,"V013_CENSUS_DUPLICATE_EVENT")
        seen.add(ident)
        refs=e["entity_refs"]
        need(all(isinstance(x,str) and x for x in refs),
             "V013_CENSUS_EMPTY_ENTITY_REF")
        missing=sorted(set(x for x in refs if x not in known))
        all_unregistered.update(missing)
        body_parts=sorted(x for x in missing if any(
            part in x.lower().split("_")
            for part in ("thumb","finger","hand","arm","eye","head")
        ))
        all_bodyparts.update(body_parts)
        errs=["NO_AUTHENTICATED_EXTERNAL_ADJUDICATION",
              "MODEL_SEMANTIC_COMPLETENESS_NOT_BENCHMARKED"]
        if e["kind"] in CHANGE_KINDS or e["effect"] in CHANGES:
            errs.append("CANONICAL_TYPED_EVENT_MAPPING_NOT_QUALIFIED")
            errs.append("ACTION_CLOCK_OR_TIMELINE_NOT_AUTHORIZED")
        if missing:
            errs.append("UNREGISTERED_OR_PROVISIONAL_ENTITY_REFERENCE")
        if body_parts:
            errs.append("BODY_PART_IS_NOT_INDEPENDENT_WORLD_ITEM")
        if e["epistemic"] in CLAIMS:
            errs.append("REPORTED_OR_UNCERTAIN_CLAIM_NOT_OBJECTIVE_STATE")
        if e["kind"]=="UNMAPPED":
            errs.append("UNKNOWN_ACTION_TAXONOMY")
        if ident in replace_map:
            repair=replace_map[ident]
            before=repair["original_model_action"]
            need(e["kind"]==before["kind"] and
                 e["effect"]==before["effect"] and
                 e["entity_refs"]==before["entity_refs"] and
                 repair["source_evidence"]=={
                   "start":e["start"],"end":e["end"],"quote":e["quote"]},
                 "V013_CENSUS_REPAIR_TARGET_NO_LONGER_MATCHES")
            errs.append("PROPOSED_RECLASSIFICATION_NOT_CANONICAL")
        if e["kind"]=="CLAIM_MENTION" and e["epistemic"]=="REPORTED_CLAIM":
            category="REPORTED_CLAIM_ONLY"
        elif ident in replace_map:
            category="REPAIR_PROPOSED_NEEDS_AUTHORITY"
        elif missing:
            category="UNRESOLVED_ENTITY_IDENTITY"
        elif e["kind"] in CHANGE_KINDS or e["effect"] in CHANGES:
            category="TYPED_STATE_EFFECT_UNQUALIFIED"
        else:
            category="OBSERVATION_OR_TEXTURE_UNQUALIFIED"
        kinds[e["kind"]]+=1
        epistemics[e["epistemic"]]+=1
        for err in set(errs):
            blockers[err]+=1
        rows.append({
            "source_event_id":ident,
            "sentence_id":e["sentence_id"],
            "source_evidence":{"start":e["start"],"end":e["end"],
                               "quote":e["quote"]},
            "model_event_kind":e["kind"],
            "model_epistemic":e["epistemic"],
            "model_effect":e["effect"],
            "registry_unresolved_refs":missing,
            "body_part_provisional_refs":body_parts,
            "repair_proposal":deepcopy(
                replace_map[ident]["proposed_replacement"]
                if ident in replace_map else None),
            "qualification_category":category,
            "blockers":sorted(set(errs)),
            "status":"HOLD_NOT_CANONICAL",
            "canonical_commit_authorized":False,
        })
    need(len(rows)==25,"V013_CENSUS_EVENT_COUNT_CHANGED")
    lexical_hints=full_report.get("targeted_probes",[])
    candidates=set()
    for item in lexical_hints:
        if item.get("kind")=="ENTITY":
            candidates.add(item["candidate_ref_or_kind"])
    all_unregistered.update(candidates)
    return {
        "schema":SCHEMA,"scene_key":full_report["scene_key"],
        "source_prose_sha256":EXPECTED_SHA,
        "source_sentence_count":28,
        "source_model_event_count":len(rows),
        "source_event_types":dict(sorted(kinds.items())),
        "source_event_epistemics":dict(sorted(epistemics.items())),
        "candidate_repair_count":len(replace_map),
        "versioned_facet_events_simulated":3,
        "unregistered_or_provisional_refs":sorted(all_unregistered),
        "body_part_candidate_refs":sorted(all_bodyparts),
        "blocker_frequency":dict(sorted(blockers.items())),
        "rows":rows,
        "events_qualified_for_canonical_commit":0,
        "production_database_writes":0,
        "real_model_calls_in_census":0,
        "status":"ALL_25_EVENTS_AUDITED_SEMANTIC_AND_AUTHORITY_HOLD",
        "canonical_commit_authorized":False,
    }
