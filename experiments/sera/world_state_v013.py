"""SERA v0.13 experimental versioned World State facet contracts.

This is a NEW schema / isolated deterministic reducer; it does not change
the existing v0.2 WorldStore, its SQLite schema, migrations or production
API. Events are source-bound, typed, CAS-guarded and proof-chained.

OFFLINE_APPROVAL_FIXTURE is a *test* permission only; it is NOT a trusted
production signature or model-authority grant. Never use a self-generated
approval map as evidence that a real human or trusted service approved
a scene. Models cannot call any production write through this module.

No action-time clock is inferred; narrative source ordering is not time.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.world_state_v02 import (
    canonical, fingerprint, validate as validate_v02,
)

SCHEMA="sera.world-state.v0.13-experimental"
EVENT_KEYS=frozenset({
    "event_id","type","actor_id","object_id","sentence_id","evidence","payload"
})
PROOF_KEYS=frozenset({"start","end","quote"})
TYPES={
    "OBSERVE_OPENABLE":frozenset({"expected","observed"}),
    "SET_OPENABLE":frozenset({"expected","next"}),
    "APPEND_DOCUMENT_ENTRY":frozenset({"expected_append_count","text"}),
}
OPENABLE_VALUES=frozenset({"UNKNOWN","OPEN","CLOSED"})
GENESIS="0"*64
MODE="OFFLINE_APPROVAL_FIXTURE"
STATE_KEYS=frozenset({
    "schema","base_world","base_world_sha256","source_prose_sha256",
    "aspects","revision","last_source_offset","events","head_hash",
    "commit_mode","production_commit_authorized",
})

def need(test,code):
    if not test:
        raise CoverageError(code)

def digest(obj)->str:
    return sha256(canonical(obj).encode("utf-8")).hexdigest()

def base_sha(world:dict)->str:
    validate_v02(world)
    return digest(world)

def _entity(world, ident, kind):
    entity=world["entities"].get(ident)
    need(isinstance(ident,str) and bool(ident) and
         isinstance(entity,dict) and entity["kind"]==kind and
         entity["lifecycle"]=="ACTIVE",
         "V013_REGISTERED_ENTITY_REQUIRED:"+str(ident))
    return entity

def create(*,base_world:dict,prose:str,
           openables:list[str],documents:list[str])->dict:
    """Explicit schema lift: old v0.2 base stays byte-identical."""
    validate_v02(base_world)
    need(isinstance(prose,str) and prose.strip() and
         isinstance(openables,list) and isinstance(documents,list) and
         len(openables)>0 and len(documents)>0 and
         all(isinstance(x,str) and bool(x) for x in openables+documents) and
         len(set(openables+documents))==len(openables+documents),
         "V013_OBJECT_ROLE_REGISTRY_INVALID")
    aspects={}
    for ref in openables:
        _entity(base_world,ref,"OBJECT")
        aspects[ref]={"type":"OPENABLE","position":"UNKNOWN",
                      "baseline_observed":False}
    for ref in documents:
        _entity(base_world,ref,"OBJECT")
        aspects[ref]={"type":"DOCUMENT","preexisting_content":"UNKNOWN",
                      "observed_appends":[]}
    state={
        "schema":SCHEMA,"base_world":deepcopy(base_world),
        "base_world_sha256":base_sha(base_world),
        "source_prose_sha256":prose_hash(prose),
        "aspects":aspects,"revision":0,"last_source_offset":-1,
        "events":[],"head_hash":GENESIS,
        "commit_mode":MODE,"production_commit_authorized":False,
    }
    validate(state,prose=prose)
    return state

def _proof(proof:dict,prose:str):
    need(isinstance(proof,dict) and set(proof)==PROOF_KEYS and
         type(proof["start"]) is int and
         type(proof["end"]) is int and
         0<=proof["start"]<proof["end"]<=len(prose) and
         isinstance(proof["quote"],str) and proof["quote"].strip() and
         prose[proof["start"]:proof["end"]]==proof["quote"],
         "V013_EVENT_SOURCE_SPAN_INVALID")

def validate_event(*,event:dict,state:dict,prose:str):
    need(isinstance(event,dict) and set(event)==EVENT_KEYS,
         "V013_EVENT_FIELDS_INVALID")
    need(isinstance(event["event_id"],str) and
         event["event_id"].strip() and
         event["type"] in TYPES and
         isinstance(event["sentence_id"],str) and
         event["sentence_id"].strip(),
         "V013_EVENT_ID_OR_TYPE_INVALID")
    need(isinstance(event["payload"],dict) and
         set(event["payload"])==TYPES[event["type"]],
         "V013_EVENT_PAYLOAD_INVALID")
    _proof(event["evidence"],prose)
    need(event["event_id"] not in [x["event"]["event_id"]
                                   for x in state["events"]],
         "V013_EVENT_ID_REPLAY")
    need(event["evidence"]["start"]>state["last_source_offset"],
         "V013_EVENT_NARRATIVE_ORDER_OR_DUPLICATE")
    actor=_entity(state["base_world"],event["actor_id"],"CHARACTER")
    obj=_entity(state["base_world"],event["object_id"],"OBJECT")
    need(actor["location"]==obj["location"],"V013_ACTOR_OBJECT_NOT_COLOCATED")
    aspect=state["aspects"].get(event["object_id"])
    expected_role=("DOCUMENT" if event["type"]=="APPEND_DOCUMENT_ENTRY"
                   else "OPENABLE")
    need(isinstance(aspect,dict) and aspect.get("type")==expected_role,
         "V013_FACET_ROLE_MISMATCH")
    # Sentence id is validated against the actual scanner, not just a
    # free-form provider label.
    from experiments.sera.sentence_ledger_v06 import sentences
    source=next((s for s in sentences(prose)
                 if s["id"]==event["sentence_id"]),None)
    need(source is not None and
         source["start"]<=event["evidence"]["start"] and
         event["evidence"]["end"]<=source["end"],
         "V013_EVIDENCE_OUTSIDE_NUMBERED_SENTENCE")
    p=event["payload"]
    if event["type"]=="OBSERVE_OPENABLE":
        need(aspect["position"]=="UNKNOWN" and
             aspect["baseline_observed"] is False and
             p["expected"]=="UNKNOWN" and p["observed"] in ("OPEN","CLOSED"),
             "V013_OPENABLE_OBSERVATION_INVALID")
    elif event["type"]=="SET_OPENABLE":
        need(aspect["baseline_observed"] is True and
             aspect["position"] in ("OPEN","CLOSED") and
             p["expected"]==aspect["position"] and
             p["next"] in ("OPEN","CLOSED") and
             p["next"]!=p["expected"],
             "V013_OPENABLE_COMPARE_AND_SWAP_INVALID")
    elif event["type"]=="APPEND_DOCUMENT_ENTRY":
        need(type(p["expected_append_count"]) is int and
             p["expected_append_count"]==len(aspect["observed_appends"]) and
             isinstance(p["text"],str) and p["text"].strip() and
             p["text"]==event["evidence"]["quote"],
             "V013_DOCUMENT_APPEND_CONTENT_OR_CAS_INVALID")
    # Missing action-time data is intentional. No wall-clock fields
    # exist in the event contract: even explicit extra keys are rejected.

def _aspect_shape(ref,aspect):
    need(isinstance(aspect,dict) and
         aspect.get("type") in ("OPENABLE","DOCUMENT"),
         "V013_ASPECT_TYPE_INVALID:"+ref)
    if aspect["type"]=="OPENABLE":
        need(set(aspect)=={"type","position","baseline_observed"} and
             aspect["position"] in OPENABLE_VALUES and
             type(aspect["baseline_observed"]) is bool and
             (aspect["position"]=="UNKNOWN")==(not aspect["baseline_observed"]),
             "V013_OPENABLE_STATE_INVALID:"+ref)
    else:
        need(set(aspect)=={"type","preexisting_content","observed_appends"} and
             aspect["preexisting_content"]=="UNKNOWN" and
             isinstance(aspect["observed_appends"],list) and
             all(isinstance(x,dict) and set(x)=={
                 "text","sentence_id","evidence"
             } and isinstance(x["text"],str) and bool(x["text"]) and
             isinstance(x["sentence_id"],str) and bool(x["sentence_id"]) and
             isinstance(x["evidence"],dict) and
             x["evidence"].get("quote")==x["text"]
             for x in aspect["observed_appends"]),
             "V013_DOCUMENT_STATE_INVALID:"+ref)

def validate(state:dict,*,prose:str):
    need(isinstance(state,dict) and set(state)==STATE_KEYS and
         state["schema"]==SCHEMA and
         state["commit_mode"]==MODE and
         state["production_commit_authorized"] is False and
         state["source_prose_sha256"]==prose_hash(prose),
         "V013_STATE_SCHEMA_OR_AUTHORITY_INVALID")
    need(state["base_world_sha256"]==base_sha(state["base_world"]) and
         isinstance(state["aspects"],dict) and
         state["aspects"] and
         type(state["revision"]) is int and state["revision"]>=0 and
         type(state["last_source_offset"]) is int and
         isinstance(state["events"],list) and
         len(state["events"])==state["revision"] and
         isinstance(state["head_hash"],str) and
         len(state["head_hash"])==64,
         "V013_STATE_INTEGRITY_INVALID")
    for ref,aspect in state["aspects"].items():
        _entity(state["base_world"],ref,"OBJECT")
        _aspect_shape(ref,aspect)
    for item in state["events"]:
        need(isinstance(item,dict) and set(item)=={
            "event","prior_hash","receipt_hash","simulation_approval"
        } and isinstance(item["event"],dict) and
             item["simulation_approval"]==MODE and
             isinstance(item["prior_hash"],str) and
             isinstance(item["receipt_hash"],str),
             "V013_RECEIPT_FORMAT_INVALID")
        _proof(item["event"].get("evidence"),prose)
    canonical(state)

def _step(state:dict,event:dict,prose:str)->dict:
    validate_event(event=event,state=state,prose=prose)
    out=deepcopy(state)
    aspect=out["aspects"][event["object_id"]]
    p=event["payload"]
    if event["type"]=="OBSERVE_OPENABLE":
        aspect["position"]=p["observed"]
        aspect["baseline_observed"]=True
    elif event["type"]=="SET_OPENABLE":
        aspect["position"]=p["next"]
    elif event["type"]=="APPEND_DOCUMENT_ENTRY":
        aspect["observed_appends"].append({
            "text":p["text"],
            "sentence_id":event["sentence_id"],
            "evidence":deepcopy(event["evidence"]),
        })
    prior=out["head_hash"]
    current=sha256((prior+":"+digest(event)).encode("utf-8")).hexdigest()
    out["events"].append({
        "event":deepcopy(event),"prior_hash":prior,
        "receipt_hash":current,"simulation_approval":MODE,
    })
    out["revision"]+=1
    out["last_source_offset"]=event["evidence"]["start"]
    out["head_hash"]=current
    validate(out,prose=prose)
    return out

def apply_simulated(*,state:dict,event:dict,prose:str,
                    approvals:dict[str,str],mode:str)->dict:
    """Explicitly simulation-only. An LLM cannot authorize a real commit."""
    validate(state,prose=prose)
    need(mode==MODE,"V013_REAL_COMMIT_API_NOT_AVAILABLE")
    need(isinstance(approvals,dict) and
         approvals.get(event.get("event_id"))==digest(event),
         "V013_SEPARATE_SIMULATED_APPROVAL_REQUIRED")
    return _step(state,event,prose)

def verify_replay(*,state:dict,prose:str)->bool:
    """Reconstruct every versioned facet from immutable base and receipts."""
    validate(state,prose=prose)
    openables=[k for k,v in state["aspects"].items()
               if v["type"]=="OPENABLE"]
    documents=[k for k,v in state["aspects"].items()
               if v["type"]=="DOCUMENT"]
    rebuilt=create(base_world=state["base_world"],prose=prose,
                   openables=openables,documents=documents)
    for receipt in state["events"]:
        need(receipt["prior_hash"]==rebuilt["head_hash"],
             "V013_REPLAY_HASH_CHAIN_MISMATCH")
        rebuilt=_step(rebuilt,receipt["event"],prose)
        need(rebuilt["events"][-1]==receipt,
             "V013_REPLAY_RECEIPT_MISMATCH")
    need(rebuilt==state,"V013_REPLAY_SNAPSHOT_DIVERGENCE")
    return True

def simulate_batch(*,state:dict,events:list[dict],prose:str,
                   approvals:dict[str,str],mode:str)->dict:
    """Atomic relative to supplied input: failures never mutate it."""
    validate(state,prose=prose)
    need(isinstance(events,list) and bool(events),
         "V013_EMPTY_BATCH_INVALID")
    result=deepcopy(state)
    for event in events:
        result=apply_simulated(
            state=result,event=event,prose=prose,
            approvals=approvals,mode=mode)
    verify_replay(state=result,prose=prose)
    return result

def restore_simulated_revision(*,state:dict,prose:str,revision:int)->dict:
    """Return a detached historical replay, not destructive store rollback."""
    verify_replay(state=state,prose=prose)
    need(type(revision) is int and 0<=revision<=state["revision"],
         "V013_REVISION_OUTSIDE_HISTORY")
    snapshot=create(
        base_world=state["base_world"],prose=prose,
        openables=[k for k,v in state["aspects"].items()
                   if v["type"]=="OPENABLE"],
        documents=[k for k,v in state["aspects"].items()
                   if v["type"]=="DOCUMENT"])
    for item in state["events"][:revision]:
        snapshot=_step(snapshot,item["event"],prose)
    return snapshot
