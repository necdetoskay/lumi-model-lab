"""SERA v0.12 — deterministic proposed OPENABLE and DOCUMENT shadow aspects.

Do not alter v0.2 canonical schema, WorldStore, EventGraph or model output.
These are additive NONCANONICAL facet projections for evaluating potential
new reducer contracts. Unknown notebook baseline never becomes an empty
document; source ordinal is not an invented wall-clock timestamp.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256

from experiments.sera.coverage import CoverageError,prose_hash
from experiments.sera.world_state_v02 import canonical,validate as validate_world

SCHEMA="sera.shadow-aspect-projection.v0.12"
POSITIONS=("UNKNOWN","OPEN","CLOSED")
PROPOSALS_SCHEMA="sera.mara-s1-provisional-corrections.v0.12"

def require(flag,code):
    if not flag:
        raise CoverageError(code)

def world_fingerprint(world:dict)->str:
    validate_world(world)
    return sha256(canonical(world).encode("utf-8")).hexdigest()

def initialize(*,world:dict,prose:str,
               openable_object_id:str,document_id:str)->dict:
    validate_world(world)
    require(isinstance(prose,str) and prose.strip(),"SHADOW_PROSE_REQUIRED")
    objects=world["entities"]
    for object_id in (openable_object_id,document_id):
        require(object_id in objects and
                objects[object_id]["kind"]=="OBJECT" and
                objects[object_id]["lifecycle"]=="ACTIVE",
                "SHADOW_OBJECT_NOT_REGISTERED:"+object_id)
    require(openable_object_id!=document_id,"SHADOW_SAME_ASPECT_OBJECT")
    return {
        "schema":SCHEMA,
        "source_prose_sha256":prose_hash(prose),
        "source_world_sha256":world_fingerprint(world),
        "source_world_revision":world["revision"],
        "openable_object_id":openable_object_id,
        "document_id":document_id,
        "facets":{
            "openable":{
                "case_position":"UNKNOWN",
                "source_observed":False,
            },
            "document":{
                "preexisting_content":"UNKNOWN",
                "observed_appends":[],
            },
        },
        "last_narrative_source_offset":-1,
        "applied_source_evidence":[],
        "status":"SHADOW_ONLY_NOT_CANONICAL",
        "canonical_commit_authorized":False,
    }

def validate_shadow(*,shadow:dict,world:dict,prose:str):
    require(isinstance(shadow,dict) and set(shadow)=={
        "schema","source_prose_sha256","source_world_sha256",
        "source_world_revision","openable_object_id","document_id",
        "facets","last_narrative_source_offset","applied_source_evidence",
        "status","canonical_commit_authorized",
    } and shadow["schema"]==SCHEMA and
            shadow["source_prose_sha256"]==prose_hash(prose) and
            shadow["source_world_sha256"]==world_fingerprint(world) and
            shadow["source_world_revision"]==world["revision"] and
            shadow["canonical_commit_authorized"] is False and
            shadow["status"]=="SHADOW_ONLY_NOT_CANONICAL",
            "SHADOW_SOURCE_OR_AUTHORITY_MISMATCH")
    facets=shadow["facets"]
    require(isinstance(facets,dict) and set(facets)=={
        "openable","document"
    } and set(facets["openable"])=={
        "case_position","source_observed"
    } and set(facets["document"])=={
        "preexisting_content","observed_appends"
    } and facets["openable"]["case_position"] in POSITIONS and
            type(facets["openable"]["source_observed"]) is bool and
            facets["document"]["preexisting_content"]=="UNKNOWN" and
            isinstance(facets["document"]["observed_appends"],list),
            "SHADOW_FACET_STRUCTURE_INVALID")
    require(type(shadow["last_narrative_source_offset"]) is int and
            isinstance(shadow["applied_source_evidence"],list),
            "SHADOW_HISTORY_STRUCTURE_INVALID")
    require(all(isinstance(x,dict) and
                set(x)=={"facet","owner_object_id","start","end","quote"} and
                type(x["start"]) is int and type(x["end"]) is int and
                0<=x["start"]<x["end"]<=len(prose) and
                prose[x["start"]:x["end"]]==x["quote"]
                for x in shadow["applied_source_evidence"]),
            "SHADOW_APPLIED_EVIDENCE_INVALID")

def _source_proof(prose,prop):
    evidence=prop.get("evidence")
    require(isinstance(evidence,dict) and set(evidence)=={
        "start","end","quote"
    } and type(evidence["start"]) is int and
            type(evidence["end"]) is int and
            0<=evidence["start"]<evidence["end"]<=len(prose) and
            prose[evidence["start"]:evidence["end"]]==evidence["quote"],
            "SHADOW_PROPOSED_SOURCE_EVIDENCE_INVALID")
    return evidence

def apply_shadow(*,shadow:dict,world:dict,prose:str,
                 proposal:dict)->dict:
    """Pure deterministic noncanonical projection, CAS + ordinal only."""
    validate_shadow(shadow=shadow,world=world,prose=prose)
    require(isinstance(proposal,dict) and
            proposal.get("status") in (
                "PROPOSED_SOURCE_OBSERVATION_NOT_CANONICAL",
                "PROPOSED_TRANSITION_NOT_CANONICAL",
                "PROPOSED_APPEND_NOT_CANONICAL",
            ) and proposal.get("action_time_minute") is None,
            "SHADOW_PROPOSAL_TIME_OR_STATUS_UNAUTHORIZED")
    proof=_source_proof(prose,proposal)
    require(proof["start"]>shadow["last_narrative_source_offset"],
            "SHADOW_NARRATIVE_ORDER_OR_REPLAY_INVALID")
    target=proposal.get("owner_object_id")
    kind=proposal.get("facet")
    require(target in world["entities"] and
            world["entities"][target]["kind"]=="OBJECT",
            "SHADOW_TARGET_NOT_WORLD_OBJECT")
    original=deepcopy(shadow)
    out=deepcopy(shadow)
    if kind=="openable.case_position":
        require(target==out["openable_object_id"] and
                set(proposal)=={
                    "facet","owner_object_id","old","new","evidence",
                    "observation_not_scene_action","source_sentence_id",
                    "action_time_minute","status",
                } or (
                    target==out["openable_object_id"] and set(proposal)=={
                        "facet","owner_object_id","old","new","evidence",
                        "source_sentence_id","action_time_minute","status",
                    }
                ),"SHADOW_OPENABLE_PROPOSAL_FIELDS_INVALID")
        old,new=proposal["old"],proposal["new"]
        require(old in POSITIONS and new in POSITIONS and old!=new and
                old==out["facets"]["openable"]["case_position"],
                "SHADOW_OPENABLE_CAS_MISMATCH")
        if old=="UNKNOWN":
            require(new=="OPEN" and
                    proposal.get("observation_not_scene_action") is True,
                    "SHADOW_OPEN_BASELINE_NEEDS_OBSERVATION")
        else:
            require(old=="OPEN" and new=="CLOSED" and
                    "observation_not_scene_action" not in proposal,
                    "SHADOW_OPENABLE_UNSUPPORTED_TRANSITION")
        out["facets"]["openable"]["case_position"]=new
        out["facets"]["openable"]["source_observed"]=True
    elif kind=="document.written_entries":
        require(target==out["document_id"] and set(proposal)=={
            "facet","owner_object_id","operation","quoted_entry",
            "evidence","source_sentence_id","action_time_minute","status",
        } and proposal["operation"]=="APPEND_VERBATIM" and
                isinstance(proposal["quoted_entry"],str) and
                proposal["quoted_entry"].strip() and
                proposal["quoted_entry"]==proof["quote"] and
                target in world["entities"],
                "SHADOW_DOCUMENT_APPEND_INVALID")
        out["facets"]["document"]["observed_appends"].append({
            "text":proposal["quoted_entry"],
            "source_sentence_id":proposal["source_sentence_id"],
            "source_span":proof,
        })
    else:
        raise CoverageError("SHADOW_FACET_UNSUPPORTED")
    out["last_narrative_source_offset"]=proof["start"]
    out["applied_source_evidence"].append({
        "facet":kind,"owner_object_id":target,
        **proof,
    })
    validate_shadow(shadow=out,world=world,prose=prose)
    require(world_fingerprint(world)==original["source_world_sha256"],
            "SHADOW_CANONICAL_WORLD_MUTATED")
    return out

def project_mara(*,world:dict,prose:str,corrections:dict)->dict:
    require(isinstance(corrections,dict) and
            corrections.get("schema")==PROPOSALS_SCHEMA and
            corrections.get("source_prose_sha256")==prose_hash(prose) and
            corrections.get("status")=="PROPOSED_REPAIR_ONLY_CANNOT_COMMIT" and
            corrections.get("canonical_commit_authorized") is False and
            corrections.get("world_state_writes")==0,
            "SHADOW_UNQUALIFIED_CORRECTIONS")
    proposals=corrections.get("shadow_facet_proposals")
    require(isinstance(proposals,list) and len(proposals)==3,
            "SHADOW_EXPECT_THREE_PROPOSALS")
    before=world_fingerprint(world)
    staged=initialize(
        world=world,prose=prose,
        openable_object_id="vane_watch",document_id="mara_notebook",
    )
    for proposal in proposals:
        staged=apply_shadow(
            shadow=staged,world=world,prose=prose,proposal=proposal)
    require(world_fingerprint(world)==before,"SHADOW_WORLD_CHANGED")
    return {
        "schema":"sera.shadow-mara-s1-run.v0.12",
        "source_world_sha256":before,
        "world_sha256_after_projection":world_fingerprint(world),
        "world_state_unchanged":True,
        "source_prose_sha256":prose_hash(prose),
        "typed_shadow_facet_state":staged,
        "facets_applied_noncanonically":len(proposals),
        "source_action_clock_minutes_invented":0,
        "canonical_db_writes":0,
        "canonical_commit_authorized":False,
        "status":"SHADOW_FACET_PROJECTION_PASS_NOT_WORLD_COMMIT",
    }
