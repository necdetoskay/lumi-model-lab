"""SERA v0.14 — generic source-bound entity identity decision *proposals*.

A lexical/model mention is not a registered world identity. This pure
resolver refuses silent create, alias merge, component attach, physical
presence, ownership or location changes. Rules may propose classification
and relationships, but every unregistered reference stays REVIEW_REQUIRED.

No provider calls, no token limits, no EventGraph/WorldState writes.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.world_state_v02 import canonical,validate as validate_world

SCHEMA="sera.identity-resolution-proposals.v0.14"
RULE_KEYS={"classification","anchor","relation","relation_target","review_action"}
CLASSIFICATIONS={
    "PHYSICAL_OBJECT_CANDIDATE",
    "OBJECT_COMPONENT_CANDIDATE",
    "ANATOMICAL_PART_CANDIDATE",
    "REGION_ALIAS_CANDIDATE",
    "SUBLOCATION_CANDIDATE",
    "DOCUMENT_COMPONENT_CANDIDATE",
    "DOCUMENT_SUBENTRY_CANDIDATE",
    "DOCUMENT_ALIAS_CANDIDATE",
    "NEGATED_DOCUMENT_MARKER",
    "REPORTED_TOPIC_NONPHYSICAL",
    "ABSTRACT_SOURCE_COLLECTION",
}
RELATIONS={
    "NONE","POTENTIAL_PART_OF","POTENTIAL_ALIAS_OF",
    "POTENTIAL_LOCATION_WITHIN",
    "POTENTIAL_DOCUMENT_ENTRY_OF","POTENTIAL_ANATOMICAL_PART_OF",
    "EXISTING_REGION_NAME_CANDIDATE",
}
ACTIONS={
    "INDEPENDENT_PHYSICAL_IDENTITY_REVIEW",
    "PART_OF_RELATION_REVIEW",
    "ANATOMICAL_NOT_INVENTORY",
    "LOCATION_MAPPING_REVIEW",
    "DOCUMENT_STRUCTURE_REVIEW",
    "NEGATED_EVIDENCE_NOT_ENTITY",
    "REPORTED_TOPIC_NOT_WORLD_TRUTH",
    "ABSTRACT_DISCOURSE_NOT_PHYSICAL",
}
KNOWN_MODEL_ROLES={"PRESENT","MENTIONED","INTERACTED","REPORTED_ONLY","AMBIGUOUS"}
NO_ENTITY_CLASSES={"NEGATED_DOCUMENT_MARKER","REPORTED_TOPIC_NONPHYSICAL",
                   "ABSTRACT_SOURCE_COLLECTION"}
RELATION_REQUIRED={
    "OBJECT_COMPONENT_CANDIDATE":"POTENTIAL_PART_OF",
    "ANATOMICAL_PART_CANDIDATE":"POTENTIAL_ANATOMICAL_PART_OF",
    "REGION_ALIAS_CANDIDATE":"EXISTING_REGION_NAME_CANDIDATE",
    "SUBLOCATION_CANDIDATE":"POTENTIAL_LOCATION_WITHIN",
    "DOCUMENT_COMPONENT_CANDIDATE":"POTENTIAL_PART_OF",
    "DOCUMENT_SUBENTRY_CANDIDATE":"POTENTIAL_DOCUMENT_ENTRY_OF",
    "DOCUMENT_ALIAS_CANDIDATE":"POTENTIAL_ALIAS_OF",
}

def require(ok,why):
    if not ok:
        raise CoverageError(why)

def sha(obj):
    return sha256(canonical(obj).encode("utf-8")).hexdigest()

def _review_rule(ref,rule,world,all_refs):
    require(isinstance(rule,dict) and set(rule)==RULE_KEYS and
            rule["classification"] in CLASSIFICATIONS and
            isinstance(rule["anchor"],str) and rule["anchor"].strip() and
            rule["relation"] in RELATIONS and
            rule["review_action"] in ACTIONS and
            (rule["relation_target"] is None or
             isinstance(rule["relation_target"],str) and
             rule["relation_target"].strip()),
            "IDENTITY_RULE_FIELDS_INVALID:"+ref)
    typ=rule["classification"]
    relation=rule["relation"]
    target=rule["relation_target"]
    if typ in RELATION_REQUIRED:
        require(relation==RELATION_REQUIRED[typ] and target is not None,
                "IDENTITY_RULE_RELATION_INVALID:"+ref)
    else:
        require(relation=="NONE" and target is None,
                "IDENTITY_RULE_UNEXPECTED_RELATION:"+ref)
    if target is not None:
        require(target != ref and
                (target in world["entities"] or
                 target in world["regions"] or target in all_refs),
                "IDENTITY_RULE_TARGET_NOT_GROUNDED:"+ref)
    if typ=="ANATOMICAL_PART_CANDIDATE":
        require(target in world["entities"] and
                world["entities"][target]["kind"]=="CHARACTER" and
                rule["review_action"]=="ANATOMICAL_NOT_INVENTORY",
                "IDENTITY_ANATOMICAL_PARENT_INVALID:"+ref)
    if typ=="OBJECT_COMPONENT_CANDIDATE":
        require(target in world["entities"] and
                world["entities"][target]["kind"]=="OBJECT",
                "IDENTITY_OBJECT_PARENT_INVALID:"+ref)
    if typ=="REGION_ALIAS_CANDIDATE":
        require(target in world["regions"],
                "IDENTITY_REGION_NOT_REGISTERED:"+ref)
    if typ in ("SUBLOCATION_CANDIDATE",):
        require(target in world["regions"],
                "IDENTITY_SUBLOCATION_PARENT_NOT_REGION:"+ref)
    if typ=="PHYSICAL_OBJECT_CANDIDATE":
        require(rule["review_action"]=="INDEPENDENT_PHYSICAL_IDENTITY_REVIEW",
                "IDENTITY_PHYSICAL_AUTO_CREATE_FORBIDDEN:"+ref)
    if typ in NO_ENTITY_CLASSES:
        require(rule["review_action"] in {
            "NEGATED_EVIDENCE_NOT_ENTITY",
            "REPORTED_TOPIC_NOT_WORLD_TRUTH",
            "ABSTRACT_DISCOURSE_NOT_PHYSICAL",
        }, "IDENTITY_NONPHYSICAL_CREATE_FORBIDDEN:"+ref)

def resolve(*,prose:str,world:dict,mention_census:dict,
            rules:dict[str,dict])->dict:
    validate_world(world)
    known_sha=prose_hash(prose)
    source_by_id={s["id"]:s for s in sentences(prose)}
    require(isinstance(mention_census,dict) and
            mention_census.get("schema")==
                "sera.mara-s1-entity-mention-census.v0.13" and
            mention_census.get("source_prose_sha256")==known_sha and
            mention_census.get("source_sentence_count")==len(source_by_id) and
            mention_census.get("bound_source_batches")==7 and
            mention_census.get("automatic_new_entities_created")==0 and
            mention_census.get("canonical_commit_authorized") is False and
            isinstance(mention_census.get("items"),list) and
            isinstance(mention_census.get("unregistered_or_provisional_mentions"),list),
            "IDENTITY_SOURCE_MENTION_CENSUS_NOT_VERIFIED")
    census_items=mention_census["items"]
    refs=[item["entity_ref"] for item in census_items]
    require(len(refs)==len(set(refs)) and
            len(refs)==mention_census["unique_mentioned_refs"] and
            sum(x["occurrences"] for x in census_items)==
                mention_census["total_source_bound_mentions"],
            "IDENTITY_MENTION_COUNTS_OR_REFS_INVALID")
    unregistered={ref for ref in refs if ref not in world["entities"]}
    require(unregistered==set(
        mention_census["unregistered_or_provisional_mentions"]) and
            isinstance(rules,dict) and set(rules)==unregistered,
            "IDENTITY_RULES_MUST_COVER_ALL_UNREGISTERED")
    known_refs=set(refs)
    # Complete source binding: don't trust labels or data from an edited
    # census without checking every exact model mention span again.
    for item in census_items:
        ref=item["entity_ref"]
        hits=item["source_evidence"]
        require(isinstance(hits,list) and len(hits)==item["occurrences"] and
                Counter(x["role_model_proposed"] for x in hits)==
                    Counter(item["model_roles"]),"IDENTITY_MENTION_ROLE_COUNT_INVALID:"+ref)
        for hit in hits:
            sid=hit.get("sentence_id")
            source=source_by_id.get(sid)
            require(source is not None and
                    hit.get("role_model_proposed") in KNOWN_MODEL_ROLES and
                    type(hit.get("source_start")) is int and
                    type(hit.get("source_end")) is int and
                    source["start"]<=hit["source_start"]<
                    hit["source_end"]<=source["end"] and
                    prose[hit["source_start"]:hit["source_end"]]==hit.get("quote"),
                    "IDENTITY_MENTION_EVIDENCE_NOT_SOURCE_BOUND:"+ref)
        require(item["registered_in_world_v02"]==(ref in world["entities"]) and
                item["suggest_introduce_entity"] is False and
                item["status"]=="HOLD_MENTION_NOT_AUTHORITY",
                "IDENTITY_MENTION_PROMOTION_FORBIDDEN:"+ref)
    rows=[]
    for ref in sorted(unregistered):
        rule=rules[ref]
        _review_rule(ref,rule,world,known_refs)
        item=next(x for x in census_items if x["entity_ref"]==ref)
        matching=[]
        for hit in item["source_evidence"]:
            sentence=source_by_id[hit["sentence_id"]]
            if rule["anchor"].casefold() in sentence["quote"].casefold():
                matching.append(hit["sentence_id"])
        require(bool(matching),"IDENTITY_RULE_ANCHOR_NOT_IN_MENTION_SENTENCE:"+ref)
        rows.append({
            "source_entity_ref":ref,
            "source_mentions":deepcopy(item["source_evidence"]),
            "model_role_counts":deepcopy(item["model_roles"]),
            "proposed_classification":rule["classification"],
            "proposed_relation":rule["relation"],
            "proposed_relation_target":rule["relation_target"],
            "independent_review_action":rule["review_action"],
            "anchor_text":rule["anchor"],
            "anchor_sentence_ids":sorted(set(matching)),
            "identity_model_is_not_authority":True,
            "entity_creation_authorized":False,
            "relation_attachment_authorized":False,
            "physical_presence_confirmed":False,
            "canonical_commit_authorized":False,
            "status":"REVIEW_REQUIRED_NOT_CANONICAL",
        })
    histogram=dict(sorted(Counter(
        x["proposed_classification"] for x in rows).items()))
    return {
        "schema":SCHEMA,
        "source_prose_sha256":known_sha,
        "source_mentions_sha256":sha(mention_census),
        "world_v02_sha256":sha(world),
        "registered_refs_unchanged":sorted(set(refs)-unregistered),
        "all_unregistered_refs_accounted_for":len(rows),
        "classification_counts":histogram,
        "proposals":rows,
        "potential_physical_new_objects":[
            x["source_entity_ref"] for x in rows if
            x["proposed_classification"]=="PHYSICAL_OBJECT_CANDIDATE"
        ],
        "potential_parts":[
            x["source_entity_ref"] for x in rows if
            x["proposed_classification"] in {
                "OBJECT_COMPONENT_CANDIDATE","ANATOMICAL_PART_CANDIDATE",
                "DOCUMENT_COMPONENT_CANDIDATE","DOCUMENT_SUBENTRY_CANDIDATE"
            }
        ],
        "automatic_entity_creations":0,
        "automatic_relation_links":0,
        "model_claims_promoted_to_physical_facts":0,
        "canonical_commit_authorized":False,
        "status":"ALL_PROVISIONAL_REFERENCES_PROPOSED_IDENTITY_HOLD",
    }
