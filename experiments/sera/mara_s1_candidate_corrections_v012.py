"""SERA v0.12 — source-grounded, independent-model supported corrections.

Consume immutable real 28-sentence Gemini candidate evidence and three
independent Haiku source-advisory answers. Produce only correction
PROPOSALS and requirements for typed v0.2 extension. Never forge a human
gold reference, evidence quote, absolute action time, WorldStore approval,
or a canonical WorldState / EventGraph mutation.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.mara_s1_v04_audit import EXPECTED_SHA, PATH
from experiments.sera.mara_s1_typed_live_v05 import entry_state
from experiments.sera.world_state_v02 import canonical, validate as validate_world

SCHEMA="sera.mara-s1-provisional-corrections.v0.12"
EVIDENCE_IDS={
    "task_001":"e0fd233de02cd8a7a7d24c7bfae1b1d91b1b676504255a4272eb8049096b8489",
    "task_002":"75b76a72fd0959497831d2fec0c5c11bb556c99524451e6f022be41c188a2637",
    "task_003":"d781715f3ab9a1cf0bf267d23df9aa9a1da66f130631332c010bd3d32c64107f",
}
TARGET_IDS={
    "task_001":"batch_004:s014:e1",
    "task_002":"batch_006:s021:e1",
    "task_003":"batch_003:s011:e1",
}
EXPECTED_OPINIONS={
    "task_001":("STATE_OBSERVATION","OBSERVE","CHARACTER_KNOWLEDGE"),
    "task_002":("DOCUMENT_WRITE","WRITE","DOCUMENT"),
    "task_003":("STATE_OBSERVATION","OBSERVE","WORLD"),
}

def require(flag,code):
    if not flag:
        raise CoverageError(code)

def _source(prose:str):
    require(prose_hash(prose)==EXPECTED_SHA,"V012_SOURCE_NOT_FROZEN")

def evidence_bundle_from_last_artifact(*,last_artifact:dict)->dict:
    """Read only original raw archive membership and retained prior answers."""
    require(isinstance(last_artifact,dict) and set(last_artifact)=={
        "manifest.json","reused-task-001.json",
        "reused-task-002.json","task_003.json",
    },"V012_LAST_ARTIFACT_FILES_UNEXPECTED")
    manifest=last_artifact["manifest.json"]
    require(manifest.get("schema")=="sera.mara-s1-haiku-last-probe.v0.11.2" and
            manifest.get("status")=="THREE_INDEPENDENT_OPINIONS_RECORDED_SEMANTIC_HOLD" and
            manifest.get("completed_tasks")==[
                "task_001","task_002","task_003"
            ] and manifest.get("pending_tasks")==[] and
            manifest.get("new_provider_calls")==1 and
            manifest.get("output_token_cap_set") is False and
            manifest.get("canonical_commit_authorized") is False and
            manifest.get("world_db_writes")==0,
            "V012_LAST_MANIFEST_NOT_COMPLETE")
    one=last_artifact["reused-task-001.json"]
    two=last_artifact["reused-task-002.json"]
    three=last_artifact["task_003.json"]
    require(three.get("task_id")=="task_003" and
            three.get("status")=="SOURCE_BOUND_INDEPENDENT_OPINION_HOLD" and
            three.get("canonical_commit_authorized") is False,
            "V012_LAST_TASK_NOT_BOUND")
    return {
        "task_001":one,
        "task_002":two,
        "task_003":three["recovered_advisory"],
    }

def validate_model_bundle(*,bundle:dict,prose:str)->dict:
    _source(prose)
    require(isinstance(bundle,dict) and set(bundle)==set(EVIDENCE_IDS),
            "V012_ADVICE_TASK_COVERAGE_INVALID")
    for task_id,model in bundle.items():
        require(isinstance(model,dict) and
                model.get("task_id")==task_id and
                model.get("source_prose_sha256")==EXPECTED_SHA and
                model.get("request_sha256_in_current_binder")==
                    EVIDENCE_IDS[task_id] and
                model.get("canonical_commit_authorized") is False and
                model.get("human_adjudicated") is False and
                model.get("model_calls_during_recovery")==0 and
                model.get("status")==
                    "RECOVERED_ADVISORY_SOURCE_BOUND_SEMANTIC_HOLD",
                "V012_ADVICE_PROVENANCE_INVALID:"+task_id)
        bound=model.get("bound_advisory")
        require(isinstance(bound,dict) and
                bound.get("source_prose_sha256")==EXPECTED_SHA and
                bound.get("canonical_commit_authorized") is False and
                bound.get("status")=="HOLD_MODEL_RESPONSE_NOT_AUTHORITY" and
                (bound.get("verdict_model_proposed"),
                 bound.get("kind_model_proposed"),
                 bound.get("effect_model_proposed"))==
                    EXPECTED_OPINIONS[task_id],
                "V012_ADVICE_SEMANTIC_MISMATCH:"+task_id)
        evidence=bound.get("possible_source_evidence")
        require(isinstance(evidence,list) and evidence and all(
            type(e.get("start")) is int and
            type(e.get("end")) is int and
            0<=e["start"]<e["end"]<=len(prose) and
            prose[e["start"]:e["end"]]==e.get("quote")
            for e in evidence
        ),"V012_ADVICE_EVIDENCE_NOT_EXACT:"+task_id)
    return bundle

def propose(*,prose:str,full_report:dict,bundle:dict)->dict:
    _source(prose)
    validate_model_bundle(bundle=bundle,prose=prose)
    require(isinstance(full_report,dict) and
            full_report.get("schema")=="sera.blind-sweep-bound.v0.10" and
            full_report.get("source_prose_sha256")==EXPECTED_SHA and
            full_report.get("sentences_accounted_for")==28 and
            len(full_report.get("candidate_events",[]))==25 and
            full_report.get("status")=="HOLD_MODEL_SEMANTICS_UNVERIFIED" and
            full_report.get("canonical_commit_authorized") is False and
            full_report.get("world_state_writes")==0,
            "V012_FULL_MODEL_REPORT_NOT_PINNED")
    world=entry_state()
    validate_world(world)
    evs=full_report["candidate_events"]
    ids={}
    for event in evs:
        eid=event.get("event_id")
        require(isinstance(eid,str) and eid not in ids,
                "V012_DUPLICATE_EVENT_ID")
        require(type(event.get("start")) is int and
                type(event.get("end")) is int and
                0<=event["start"]<event["end"]<=len(prose) and
                prose[event["start"]:event["end"]]==event.get("quote"),
                "V012_EVENT_EVIDENCE_TAMPERED")
        ids[eid]=event
    original_actions=[
        ("task_001","MOVE","CHARACTER_KNOWLEDGE","OBSERVED_ACTION","s014"),
        ("task_002","COMMUNICATE","NONE","OBSERVED_ACTION","s021"),
        ("task_003","CLOSE","OBJECT","OBSERVED_ACTION","s011"),
    ]
    for task,kind,effect,epistemic,sid in original_actions:
        event=ids.get(TARGET_IDS[task])
        require(event is not None and
                event.get("kind")==kind and event.get("effect")==effect and
                event.get("epistemic")==epistemic and
                event.get("sentence_id")==sid,
                "V012_TARGET_ORIGINAL_EVENT_CHANGED:"+task)

    correction_specs=[
        ("task_001","OBSERVE","CHARACTER_KNOWLEDGE",
         ["mara","new:strike_record"],
         "Do not move Mara's physical location; inspecting a record is attention."),
        ("task_002","WRITE","DOCUMENT",
         ["mara","mara_notebook"],
         "A written line is appended to notebook; not uttered speech."),
    ]
    corrections=[]
    for task,kind,effect,refs,reason in correction_specs:
        before=ids[TARGET_IDS[task]]
        proof=bundle[task]
        require(all(x in world["entities"] or x.startswith("new:")
                    for x in refs),"V012_UNKNOWN_REQUIRED_ENTITY")
        corrections.append({
            "correction_id":"proposal_"+task,
            "existing_event_id":before["event_id"],
            "sentence_id":before["sentence_id"],
            "source_evidence":{
                "start":before["start"],"end":before["end"],
                "quote":before["quote"],
            },
            "original_model_action":{
                "kind":before["kind"],"effect":before["effect"],
                "entity_refs":before["entity_refs"],
            },
            "proposed_replacement":{
                "kind":kind,"effect":effect,
                "entity_refs":refs,
                "action_time_minute":None,
                "reason":reason,
            },
            "independent_evidence_task":task,
            "source_model_opinion_sha256":sha256(canonical(
                proof["unmodified_proposed_semantics"]
            ).encode("utf-8")).hexdigest(),
            "independent_model_is_not_world_authority":True,
            "status":"PROPOSED_AWAITING_TYPED_REDUCER_AND_JUDGE",
            "canonical_commit_authorized":False,
        })
    open_source=prose.index("pocket watch open in his palm")
    close_source=ids[TARGET_IDS["task_003"]]
    facets=[
        {
            "facet":"openable.case_position",
            "owner_object_id":"vane_watch",
            "old":"UNKNOWN","new":"OPEN",
            "evidence":{
                "start":open_source,"end":open_source+len("pocket watch open in his palm"),
                "quote":"pocket watch open in his palm",
            },
            "observation_not_scene_action":True,
            "source_sentence_id":"s004",
            "action_time_minute":None,
            "status":"PROPOSED_SOURCE_OBSERVATION_NOT_CANONICAL",
        },
        {
            "facet":"openable.case_position",
            "owner_object_id":"vane_watch",
            "old":"OPEN","new":"CLOSED",
            "evidence":{
                "start":close_source["start"],"end":close_source["end"],
                "quote":close_source["quote"],
            },
            "source_sentence_id":"s011",
            "action_time_minute":None,
            "status":"PROPOSED_TRANSITION_NOT_CANONICAL",
        },
    ]
    notebook_sentence="Discrepancy documented; explanation unknown."
    quoted=prose.find(notebook_sentence)
    require(quoted>=0,"V012_NOTEBOOK_APPEND_TEXT_NOT_IN_SOURCE")
    facets.append({
        "facet":"document.written_entries",
        "owner_object_id":"mara_notebook",
        "operation":"APPEND_VERBATIM",
        "quoted_entry":notebook_sentence,
        "evidence":{
            "start":quoted,"end":quoted+len(notebook_sentence),
            "quote":notebook_sentence,
        },
        "source_sentence_id":"s021",
        "action_time_minute":None,
        "status":"PROPOSED_APPEND_NOT_CANONICAL",
    })
    blockers=[
        "OPENABLE_ASPECT_REDUCER_NOT_IN_WORLD_STATE_V02",
        "DOCUMENT_ENTRIES_REDUCER_NOT_IN_WORLD_STATE_V02",
        "PROVISIONAL_NEW_OBJECT_IDENTITIES_NOT_APPROVED",
        "INDIVIDUAL_EVENT_ACTION_TIMES_NOT_GROUNDED",
        "INDEPENDENT_MODEL_IS_NOT_ADJUDICATED_GOLD",
        "WHOLE_SCENE_SEMANTIC_COMPLETENESS_NOT_PROVEN",
        "CANONICAL_COMMIT_AUTHORITY_ABSENT",
    ]
    return {
        "schema":SCHEMA,
        "scene_key":full_report["scene_key"],
        "source_prose_sha256":EXPECTED_SHA,
        "original_model_event_count":25,
        "source_sentence_count":28,
        "replacements":corrections,
        "shadow_facet_proposals":facets,
        "required_new_reducer_contracts":[
            "OPENABLE_CASE_STATE_OBSERVE_AND_CAS",
            "DOCUMENT_WRITTEN_ENTRIES_APPEND_EXACT_SOURCE",
        ],
        "blockers":blockers,
        "status":"PROPOSED_REPAIR_ONLY_CANNOT_COMMIT",
        "human_gold_qualified":False,
        "world_state_writes":0,
        "canonical_commit_authorized":False,
    }
