"""SERA v0.13 — all 7 paid model batches' entity mention census.

This fills an intentional blind spot in the 25-event census: entity
mentions with NO event (e.g., bench) still need identity review.
Source/evidence/role normalization and exact seven-batch coverage must
pass. Role PRESENT is a MODEL opinion, not world presence or identity
authority. No new object is created by this report.
"""
from __future__ import annotations

from collections import Counter,defaultdict

from experiments.sera.coverage import CoverageError,prose_hash
from experiments.sera.world_state_v02 import validate as validate_v02

SCHEMA="sera.mara-s1-entity-mention-census.v0.13"
BODYPART={"thumb","finger","hand","palm","arm","eye","head"}
POSSIBLE_PLACE={"station","platform","north_quay_station","quay"}
REPORTED_REF={"train","train_41","entry_train_41"}
KNOWN_STATUSES={"PRESENT","MENTIONED","INTERACTED","REPORTED_ONLY","AMBIGUOUS"}

def need(ok,why):
    if not ok:raise CoverageError(why)

def run(*,prose:str,world:dict,plan:dict,bound_batches:list[dict])->dict:
    validate_v02(world)
    need(plan.get("schema")=="sera.blind-sentence-sweep.v0.10" and
         plan.get("source_prose_sha256")==prose_hash(prose) and
         plan.get("sentence_count")==28 and len(plan.get("batches",[]))==7 and
         isinstance(bound_batches,list) and len(bound_batches)==7,
         "V013_MENTIONS_PLAN_OR_SOURCE_INVALID")
    expected={b["batch_id"]:b for b in plan["batches"]}
    seen={}
    for item in bound_batches:
        need(isinstance(item,dict) and
             item.get("schema")=="sera.sweep-batch-bound.v0.10" and
             item.get("batch_id") in expected and
             item["batch_id"] not in seen and
             item.get("prose_sha256")==prose_hash(prose) and
             item.get("canonical_commit_authorized") is False and
             item.get("provider_response_complete") is True and
             isinstance(item.get("rows"),list),
             "V013_MENTIONS_BATCH_NOT_SOURCE_BOUND")
        seen[item["batch_id"]]=item
    need(set(seen)==set(expected),"V013_MENTIONS_SEVEN_BATCHES_REQUIRED")
    sentence_map={x["id"]:x for x in plan["source_sentences"]}
    evidence_by_ref=defaultdict(list)
    rows_count=0
    total_mentions=0
    for b in plan["batches"]:
        report=seen[b["batch_id"]]
        ids=b["sentence_ids"]
        rows=report["rows"]
        need(len(rows)==len(ids) and
             [x["sentence_id"] for x in rows]==ids,
             "V013_MENTIONS_SENTENCE_COVERAGE_MISMATCH")
        for row in rows:
            sid=row["sentence_id"];source=sentence_map[sid]
            rows_count+=1
            for mention in row["mentions"]:
                need(isinstance(mention,dict) and
                     isinstance(mention.get("entity_ref"),str) and
                     mention["entity_ref"] and
                     mention.get("role") in KNOWN_STATUSES and
                     type(mention.get("start")) is int and
                     type(mention.get("end")) is int and
                     source["start"]<=mention["start"]<mention["end"]<=
                         source["end"] and
                     prose[mention["start"]:mention["end"]]==mention.get("quote"),
                     "V013_MENTION_SOURCE_EVIDENCE_INVALID")
                total_mentions+=1
                evidence_by_ref[mention["entity_ref"]].append({
                    "sentence_id":sid,
                    "quote":mention["quote"],
                    "role_model_proposed":mention["role"],
                    "source_start":mention["start"],
                    "source_end":mention["end"],
                })
    need(rows_count==28,"V013_MENTIONS_MISSING_SOURCE_SENTENCES")
    inventory=[]
    missing=[]
    bodypart=[]
    for ref,hits in sorted(evidence_by_ref.items()):
        registered=ref in world["entities"]
        token=ref.rsplit(":",1)[-1].casefold()
        if registered:
            cls="EXISTING_REGISTERED_ENTITY"
        elif any(part in token.split("_") for part in BODYPART):
            cls="ANATOMICAL_PART_NO_INDEPENDENT_ITEM"
            bodypart.append(ref)
        elif token in REPORTED_REF or (
            token.startswith("train") or token.startswith("entry_train")
        ):
            cls="REPORTED_TOPIC_DO_NOT_CREATE_PHYSICAL_TRAIN"
        elif token in POSSIBLE_PLACE or token.endswith("_station"):
            cls="LOCATION_IDENTITY_REQUIRES_MAPPING_NOT_NEW_OBJECT"
        else:
            cls="PROVISIONAL_ENTITY_IDENTITY_NEEDS_REVIEW"
        if not registered:missing.append(ref)
        inventory.append({
            "entity_ref":ref,
            "registered_in_world_v02":registered,
            "classification":cls,
            "occurrences":len(hits),
            "model_roles":dict(sorted(Counter(
                x["role_model_proposed"] for x in hits).items())),
            "source_evidence":hits,
            "suggest_introduce_entity":False,
            "status":"HOLD_MENTION_NOT_AUTHORITY",
        })
    return {
        "schema":SCHEMA,
        "scene_key":plan["scene_key"],
        "source_prose_sha256":prose_hash(prose),
        "source_sentence_count":28,
        "bound_source_batches":7,
        "total_source_bound_mentions":total_mentions,
        "unique_mentioned_refs":len(inventory),
        "unregistered_or_provisional_mentions":missing,
        "anatomical_parts_not_inventory":bodypart,
        "items":inventory,
        "automatic_new_entities_created":0,
        "physical_train_arrival_authorized":False,
        "events_qualified_for_commit":0,
        "canonical_commit_authorized":False,
        "status":"ALL_MENTIONS_SOURCE_BOUND_IDENTITIES_AND_PRESENCE_HOLD",
    }
