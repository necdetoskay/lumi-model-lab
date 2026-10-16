"""SERA v0.14 — reconcile 16 identity hypotheses with all 25 event holds.

Two original *separately sourced* provider ledgers must agree on the
spelling and use of any provisional event object. Relationship proposals
remain REVIEW_REQUIRED; no identity, presence or authority is granted.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy

from experiments.sera.coverage import CoverageError,prose_hash
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.identity_resolution_v014 import resolve
from experiments.sera.mara_s1_identity_rules_v014 import MARA_RULES
from experiments.sera.mara_s1_v04_audit import EXPECTED_SHA
from experiments.sera.mara_s1_typed_live_v05 import entry_state

def require(ok,code):
    if not ok:
        raise CoverageError(code)

def qualify(*,prose:str,mentions:dict,events:dict)->dict:
    identities=resolve(
        prose=prose,world=entry_state(),mention_census=mentions,
        rules=MARA_RULES,
    )
    require(prose_hash(prose)==EXPECTED_SHA and
            identities["source_prose_sha256"]==EXPECTED_SHA and
            identities["all_unregistered_refs_accounted_for"]==16 and
            identities["automatic_entity_creations"]==0 and
            identities["automatic_relation_links"]==0 and
            identities["model_claims_promoted_to_physical_facts"]==0,
            "V014_MARA_IDENTITY_SCOPE_CHANGED")
    require(isinstance(events,dict) and
            events.get("schema")==
                "sera.mara-s1-event-qualification-census.v0.13" and
            events.get("source_prose_sha256")==EXPECTED_SHA and
            events.get("source_model_event_count")==25 and
            events.get("events_qualified_for_canonical_commit")==0 and
            events.get("canonical_commit_authorized") is False and
            len(events.get("rows",[]))==25,
            "V014_EVENT_CENSUS_NOT_SOURCE_BOUND")
    proposals={x["source_entity_ref"]:x for x in identities["proposals"]}
    rows=[]
    source_sentences={s["id"]:s for s in sentences(prose)}
    mention_sids={
        item["entity_ref"]:{
            h["sentence_id"] for h in item["source_evidence"]
        } for item in mentions["items"]
    }
    event_ids=set()
    for event in events["rows"]:
        eid=event.get("source_event_id")
        sentence=source_sentences.get(event.get("sentence_id"))
        ev=event.get("source_evidence")
        require(isinstance(eid,str) and eid and eid not in event_ids and
                sentence is not None and isinstance(ev,dict) and
                type(ev.get("start")) is int and
                type(ev.get("end")) is int and
                sentence["start"]<=ev["start"]<ev["end"]<=sentence["end"] and
                prose[ev["start"]:ev["end"]]==ev.get("quote"),
                "V014_EVENT_SOURCE_SPAN_OR_ID_TAMPERED")
        event_ids.add(eid)
        missing=event["registry_unresolved_refs"]
        require(isinstance(missing,list) and
                all(isinstance(x,str) for x in missing) and
                set(missing).issubset(proposals) and
                all(event["sentence_id"] in mention_sids.get(ref,set())
                    for ref in missing) and
                event.get("status")=="HOLD_NOT_CANONICAL" and
                event.get("canonical_commit_authorized") is False,
                "V014_EVENT_UNMAPPED_OR_PROMOTED_ENTITY")
        rows.append({
            "source_event_id":event["source_event_id"],
            "sentence_id":event["sentence_id"],
            "model_kind":event["model_event_kind"],
            "event_source_quote":event["source_evidence"]["quote"],
            "unregistered_references":missing,
            "proposed_entity_resolutions":[{
                "ref":ref,
                "hypothesis":proposals[ref]["proposed_classification"],
                "candidate_parent_or_alias_target":
                    proposals[ref]["proposed_relation_target"],
                "relation_proven":False,
            } for ref in missing],
            "qualification_status":"HOLD_CANNOT_COMMIT",
            "canonical_commit_authorized":False,
        })
    unresolved=[x for x in rows if x["unregistered_references"]]
    counts=Counter(
        proposal["proposed_classification"] for p in proposals.values()
        for proposal in (p,)
    )
    return {
        "schema":"sera.mara-s1-identity-and-events-review.v0.14",
        "source_prose_sha256":EXPECTED_SHA,
        "original_model_entity_mentions":mentions["total_source_bound_mentions"],
        "original_model_event_candidates":len(rows),
        "all_unregistered_refs_proposed":len(proposals),
        "classification_counts":dict(sorted(counts.items())),
        "physical_item_candidate_refs":identities["potential_physical_new_objects"],
        "source_events_with_unregistered_refs":len(unresolved),
        "source_events_without_unregistered_refs":len(rows)-len(unresolved),
        "entity_identity_proposals":deepcopy(identities["proposals"]),
        "source_event_identity_dependencies":rows,
        "negative_markers_must_not_be_created":[
            p["source_entity_ref"] for p in identities["proposals"]
            if p["proposed_classification"]=="NEGATED_DOCUMENT_MARKER"
        ],
        "registered_base_entities_unchanged":identities["registered_refs_unchanged"],
        "approved_relation_links":0,
        "created_entities":0,
        "allowed_physical_train_arrivals":0,
        "new_model_calls":0,
        "actual_event_commits":0,
        "canonical_commit_authorized":False,
        "status":"ALL_16_REFERENCES_CLASSIFIED_AS_PROPOSALS_25_EVENTS_HOLD",
    }
