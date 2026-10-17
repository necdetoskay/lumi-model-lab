"""SERA v0.54: source-bound multi-capability physical-object preview.

A notebook can be OPENABLE and DOCUMENT simultaneously. Existing v0.13
single-facet reducer stays unchanged. This detached opt-in simulator never
authorizes a world/DB commit, never invents an action timestamp, and treats
model event suggestions as noncanonical until v0.23 independent review.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import re

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.world_state_v02 import canonical,validate as validate_world
from experiments.sera.world_state_v013 import EVENT_KEYS,TYPES
from experiments.sera.typed_aspect_recovery_v020 import (
    SCHEMA as RECOVERY_SCHEMA, MAX_CANDIDATES,
)

SCHEMA="sera.multifacet-physical-preview.v0.54"
EVENT_ROLES={
    "OBSERVE_OPENABLE":"openables",
    "SET_OPENABLE":"openables",
    "APPEND_DOCUMENT_ENTRY":"documents",
}
TYPE_KINDS={
    "OBSERVE_OPENABLE":frozenset({"OBSERVE"}),
    "SET_OPENABLE":frozenset({"OPEN","CLOSE","CHANGE_STATE"}),
    "APPEND_DOCUMENT_ENTRY":frozenset({"WRITE"}),
}


def need(ok,code):
    if not ok:
        raise CoverageError(code)


def source_backed_typed_match(*, prose, event, candidate):
    """Bind separate source assertions, NEVER manufacture a WRITE event.

    A blind sweep may cite just "wrote" while a typed proposal must cite
    the actual quoted text appended to a document. Allow those disjoint
    spans only when the same original sentence has a literal write-verb
    followed immediately by colon + opening quote + EXACT content +
    matching closing quote. All other types still require overlap.
    This is evidence linkage, not independent semantic authority.
    """
    if not isinstance(event, dict) or not isinstance(candidate, dict):
        return False
    kind=event.get("kind")
    op=candidate.get("type")
    span=candidate.get("evidence")
    if (not isinstance(span, dict) or
        event.get("sentence_id")!=candidate.get("sentence_id") or
        type(event.get("start")) is not int or
        type(event.get("end")) is not int or
        type(span.get("start")) is not int or
        type(span.get("end")) is not int or
        not (0<=event["start"]<event["end"] and
             0<=span["start"]<span["end"]) or
        (isinstance(prose,str) and
         (event["end"]>len(prose) or span["end"]>len(prose)))):
        return False
    if op=="APPEND_DOCUMENT_ENTRY":
        if kind!="WRITE":
            return False
    elif op=="OBSERVE_OPENABLE":
        if kind!="OBSERVE":
            return False
    elif op=="SET_OPENABLE":
        if kind not in ("OPEN","CLOSE","CHANGE_STATE"):
            return False
        expected={"OPEN":"OPEN","CLOSE":"CLOSED"}
        if (kind in expected and
            (not isinstance(candidate.get("payload"),dict) or
             candidate["payload"].get("next")!=expected[kind])):
            return False
    else:
        return False
    if event["start"]<span["end"] and span["start"]<event["end"]:
        return True
    if (not isinstance(prose,str) or op!="APPEND_DOCUMENT_ENTRY" or
            event["end"]>span["start"]):
        return False
    # Never bridge a normal mention, dialogue, a remote quotation, or a
    # different sentence. A matching write verb alone is insufficient.
    verb=prose[event["start"]:event["end"]]
    between=prose[event["end"]:span["start"]]
    content=prose[span["start"]:span["end"]]
    payload=candidate.get("payload")
    if (not re.search(r"\b(?:wrote|writes|write|writing|added|jotted|scribbled|inscribed)\b\s*$",
                      verb, re.IGNORECASE) or
        not re.fullmatch(r"""\s*[:,]\s*(["“‘'])""",between) or
        not isinstance(payload,dict) or
        payload.get("text")!=content or
        span.get("quote")!=content):
        return False
    opener=between.strip()[-1]
    closer={"“":"”","‘":"’",'"':'"',"'":"'"}.get(opener)
    return prose[span["end"]:].startswith(closer)


def digest(value):
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def _registered(world,registry):
    need(isinstance(registry,dict) and
         set(registry)=={"openables","documents"},
         "V054_REGISTRY_KEYS_INVALID")
    out={}
    for role in ("openables","documents"):
        refs=registry[role]
        need(isinstance(refs,list) and bool(refs) and
             len(refs)==len(set(refs)) and
             all(isinstance(x,str) and x for x in refs),
             "V054_REGISTRY_ROLE_INVALID")
        for ref in refs:
            obj=world["entities"].get(ref)
            need(isinstance(obj,dict) and obj.get("kind")=="OBJECT" and
                 obj.get("lifecycle")=="ACTIVE",
                 "V054_REGISTRY_OBJECT_NOT_ACTIVE")
            out.setdefault(ref,{})[role]=(
                {"position":"UNKNOWN","baseline_observed":False}
                if role=="openables" else
                {"preexisting_content":"UNKNOWN","observed_appends":[]})
    need(any(len(v)==2 for v in out.values()),
         "V054_MULTIFACET_REQUIRES_SHARED_OBJECT")
    return out


def preview(*,prose,world,registry,candidates,extraction_report):
    """Execute guarded noncanonical multi-capability simulation from source."""
    validate_world(world)
    baseline=digest(world)
    facets=_registered(world,registry)
    need(isinstance(extraction_report,dict) and
         extraction_report.get("source_prose_sha256")==prose_hash(prose) and
         extraction_report.get("canonical_commit_authorized") is False and
         extraction_report.get("world_state_writes")==0 and
         isinstance(extraction_report.get("candidate_events"),list) and
         isinstance(candidates,list) and 0<len(candidates)<=MAX_CANDIDATES,
         "V054_SOURCE_OR_CANDIDATES_INVALID")
    source={s["id"]:s for s in sentences(prose)}
    events=extraction_report["candidate_events"]
    observed=set()
    last_start=-1
    proof_chain="0"*64
    trace=[]
    # Explicitly stage all changes on independent copy; errors never mutate
    # the caller's world, extraction report or original candidate collection.
    for proposed in candidates:
        need(isinstance(proposed,dict) and set(proposed)==EVENT_KEYS and
             proposed.get("type") in TYPES and
             isinstance(proposed.get("payload"),dict) and
             set(proposed["payload"])==TYPES[proposed["type"]] and
             isinstance(proposed.get("event_id"),str) and
             proposed["event_id"] and
             proposed["event_id"] not in observed,
             "V054_EVENT_SCHEMA_OR_REPLAY")
        observed.add(proposed["event_id"])
        ident=proposed["object_id"]
        role=EVENT_ROLES[proposed["type"]]
        need(ident in facets and role in facets[ident],
             "V054_UNREGISTERED_OBJECT_CAPABILITY")
        actor=world["entities"].get(proposed["actor_id"])
        obj=world["entities"][ident]
        need(isinstance(actor,dict) and actor.get("kind")=="CHARACTER" and
             actor.get("lifecycle")=="ACTIVE" and
             actor["location"]==obj["location"],
             "V054_ACTOR_OBJECT_LOCATION_CONFLICT")
        sid=proposed["sentence_id"]
        span=proposed["evidence"]
        row=source.get(sid)
        need(isinstance(row,dict) and isinstance(span,dict) and
             set(span)=={"start","end","quote"} and
             type(span["start"]) is int and type(span["end"]) is int and
             row["start"]<=span["start"]<row["end"] and
             span["start"]<span["end"]<=len(prose) and
             (proposed["type"]=="APPEND_DOCUMENT_ENTRY" or
              span["end"]<=row["end"]) and
             prose[span["start"]:span["end"]]==span["quote"] and
             span["start"]>last_start,
             "V054_SOURCE_SPAN_OR_ORDER_INVALID")
        need(any(
            isinstance(e,dict) and e.get("sentence_id")==sid and
            e.get("kind") in TYPE_KINDS[proposed["type"]] and
            source_backed_typed_match(
                prose=prose,event=e,candidate=proposed) and
            proposed["actor_id"] in e.get("entity_refs",[]) and
            ident in e.get("entity_refs",[]) and
            e.get("epistemic") in ("OBSERVED_ACTION","NARRATOR_ASSERTION") and
            type(e.get("start")) is int and type(e.get("end")) is int and
            0<=e["start"]<e["end"]<=len(prose) and
            prose[e["start"]:e["end"]]==e.get("quote")
            for e in events),
            "V054_NOT_BACKED_BY_INDEPENDENT_SOURCE_EVENT")
        facet=facets[ident][role]
        payload=proposed["payload"]
        if proposed["type"]=="OBSERVE_OPENABLE":
            need(facet["position"]=="UNKNOWN" and
                 facet["baseline_observed"] is False and
                 payload["expected"]=="UNKNOWN" and
                 payload["observed"] in ("OPEN","CLOSED"),
                 "V054_OPENABLE_INITIAL_OBSERVATION_INVALID")
            facet["position"]=payload["observed"]
            facet["baseline_observed"]=True
        elif proposed["type"]=="SET_OPENABLE":
            # Source may explicitly say "opened" while prior OPEN/CLOSED
            # state is unobserved. UNKNOWN is epistemic uncertainty, not
            # an invented CLOSED baseline. Only a source-backed action may
            # establish the next state in this case.
            prior=facet["position"]
            need(prior in ("UNKNOWN","OPEN","CLOSED") and
                 payload["expected"]==prior and
                 payload["next"] in ("OPEN","CLOSED") and
                 payload["next"]!=prior,
                 "V054_OPENABLE_COMPARE_AND_SWAP_INVALID")
            facet["position"]=payload["next"]
        else:
            need(type(payload["expected_append_count"]) is int and
                 payload["expected_append_count"]==
                    len(facet["observed_appends"]) and
                 isinstance(payload["text"],str) and payload["text"].strip() and
                 payload["text"]==span["quote"],
                 "V054_DOCUMENT_APPEND_COMPARE_AND_SWAP_INVALID")
            facet["observed_appends"].append({
                "text":span["quote"],"sentence_id":sid,
                "evidence":deepcopy(span)})
        proof_chain=sha256((proof_chain+":"+digest(proposed)).encode()).hexdigest()
        trace.append({"event_id":proposed["event_id"],
                      "sentence_id":sid,"source_start":span["start"],
                      "receipt_hash":proof_chain,
                      "action_minute":None})
        last_start=span["start"]
    need(digest(world)==baseline,
         "V054_ATTEMPTED_BASE_WORLD_MUTATION")
    result={
        "schema":RECOVERY_SCHEMA,"status":"TYPED_MULTIFACET_SIMULATED_NONCANONICAL",
        "prose_sha256":prose_hash(prose),"world_sha256":baseline,
        "original_candidates_sha256":digest(candidates),
        "registered_capabilities_sha256":digest(registry),
        "multifacet_preview":{
            "schema":SCHEMA,"facets":facets,"receipts":trace,
            "head_hash":proof_chain,"event_count":len(trace),
            "simulation_is_not_world_truth":True},
        "blocker_codes":[],"requires_manual_intervention":False,
        "canonical_commit_authorized":False,"world_db_writes":0,
    }
    return result
