"""Offline adversarial v0.14 resolver tests, no provider or canonical state."""
from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch
import unittest

from experiments.sera.coverage import CoverageError,prose_hash
from experiments.sera.mara_s1_typed_live_v05 import entry_state
from experiments.sera.mara_s1_v04_audit import PATH
from experiments.sera.mara_s1_identity_rules_v014 import MARA_RULES
from experiments.sera.identity_resolution_v014 import resolve
from experiments.sera.mara_s1_identity_review_v014 import qualify
from experiments.sera.sentence_ledger_v06 import sentences
import json

PROSE=json.loads(PATH.read_text(encoding="utf-8"))["prose"]
REGISTRY={
    "archive_telegram":"archive telegram",
    "mara":"Mara",
    "mara_notebook":"notebook",
    "platform_clock":"platform clock",
    "vane":"Vane",
    "vane_watch":"pocket watch",
}

def hit_for(ref,anchor):
    row=next((x for x in sentences(PROSE) if
              anchor.casefold() in x["quote"].casefold()),None)
    if row is None:
        raise AssertionError("Fixture source anchor missing "+str(ref))
    pos=row["quote"].casefold().find(anchor.casefold())
    return {"sentence_id":row["id"],
            "quote":row["quote"][pos:pos+len(anchor)],
            "role_model_proposed":"MENTIONED",
            "source_start":row["start"]+pos,
            "source_end":row["start"]+pos+len(anchor)}

def synthetic_mention_census():
    items=[]
    world=entry_state()
    for ref,anchor in {**REGISTRY,
                        **{k:v["anchor"] for k,v in MARA_RULES.items()}}.items():
        registered=ref in world["entities"]
        items.append({
            "entity_ref":ref,
            "registered_in_world_v02":registered,
            "classification":"EXISTING_REGISTERED_ENTITY" if registered
               else "PROVISIONAL_ENTITY_IDENTITY_NEEDS_REVIEW",
            "occurrences":1,
            "model_roles":{"MENTIONED":1},
            "source_evidence":[hit_for(ref,anchor)],
            "suggest_introduce_entity":False,
            "status":"HOLD_MENTION_NOT_AUTHORITY",
        })
    return {
        "schema":"sera.mara-s1-entity-mention-census.v0.13",
        "source_prose_sha256":prose_hash(PROSE),
        "source_sentence_count":28,
        "bound_source_batches":7,
        "automatic_new_entities_created":0,
        "canonical_commit_authorized":False,
        "items":items,
        "unique_mentioned_refs":22,
        "total_source_bound_mentions":22,
        "unregistered_or_provisional_mentions":sorted(MARA_RULES),
    }

def synthetic_event_census():
    ids=list(MARA_RULES)
    rows=[]
    for i in range(25):
        ref=ids[i] if i<len(ids) else "mara"
        anchor=MARA_RULES[ref]["anchor"] if ref in MARA_RULES else "Mara"
        hit=hit_for(ref,anchor)
        rows.append({
            "source_event_id":f"synthetic-event-{i:03d}",
            "sentence_id":hit["sentence_id"],
            "model_event_kind":"OBSERVE",
            "source_evidence":{
                "start":hit["source_start"],"end":hit["source_end"],
                "quote":hit["quote"],
            },
            "registry_unresolved_refs":[ref] if ref in MARA_RULES else [],
            "status":"HOLD_NOT_CANONICAL",
            "canonical_commit_authorized":False,
        })
    return {
        "schema":"sera.mara-s1-event-qualification-census.v0.13",
        "source_prose_sha256":prose_hash(PROSE),
        "source_model_event_count":25,
        "events_qualified_for_canonical_commit":0,
        "canonical_commit_authorized":False,
        "rows":rows,
    }

class IdentityV014Tests(unittest.TestCase):
    def test_all_16_rules_source_bound_no_world_creation(self):
        world=entry_state()
        origin=deepcopy(world)
        a=resolve(prose=PROSE,world=world,
                  mention_census=synthetic_mention_census(),
                  rules=MARA_RULES)
        self.assertEqual(len(a["proposals"]),16)
        self.assertEqual(set(a["potential_physical_new_objects"]),
                         {"new:bench","new:pencil"})
        by={x["source_entity_ref"]:x for x in a["proposals"]}
        self.assertEqual(by["new:watch_hands"]["proposed_relation_target"],
                         "vane_watch")
        self.assertEqual(by["new:watch_hands"]["proposed_classification"],
                         "OBJECT_COMPONENT_CANDIDATE")
        self.assertEqual(by["new:vane_thumb"]["proposed_relation_target"],
                         "vane")
        self.assertEqual(by["new:watch_case"]["proposed_relation_target"],
                         "vane_watch")
        self.assertEqual(by["new:north_quay_station"]["proposed_relation_target"],
                         "north_quay_station")
        self.assertEqual(by["new:train_41"]["proposed_classification"],
                         "REPORTED_TOPIC_NONPHYSICAL")
        self.assertEqual(set(a["proposals"][0]),{
            "source_entity_ref","source_mentions","model_role_counts",
            "proposed_classification","proposed_relation",
            "proposed_relation_target","independent_review_action",
            "anchor_text","anchor_sentence_ids",
            "identity_model_is_not_authority",
            "entity_creation_authorized","relation_attachment_authorized",
            "physical_presence_confirmed",
            "canonical_commit_authorized","status"})
        self.assertTrue(all(x["status"]=="REVIEW_REQUIRED_NOT_CANONICAL"
                            for x in a["proposals"]))
        self.assertTrue(all(not x["physical_presence_confirmed"] and
                            not x["entity_creation_authorized"] for x in a["proposals"]))
        self.assertEqual(a["automatic_entity_creations"],0)
        self.assertEqual(world,origin)

    def test_unreviewed_alias_and_anatomical_relation_is_not_truth(self):
        report=qualify(prose=PROSE,mentions=synthetic_mention_census(),
                       events=synthetic_event_census())
        self.assertEqual(report["all_unregistered_refs_proposed"],16)
        self.assertEqual(report["original_model_event_candidates"],25)
        self.assertEqual(len(report["source_event_identity_dependencies"]),25)
        self.assertEqual(set(report["physical_item_candidate_refs"]),
                         {"new:bench","new:pencil"})
        self.assertIn("new:mark",report["negative_markers_must_not_be_created"])
        self.assertIn("new:strike_mark",report["negative_markers_must_not_be_created"])
        self.assertEqual(report["created_entities"],0)
        self.assertEqual(report["approved_relation_links"],0)
        self.assertEqual(report["allowed_physical_train_arrivals"],0)
        self.assertFalse(report["canonical_commit_authorized"])

    def test_no_provisional_ref_left_out_silently(self):
        c=synthetic_mention_census()
        incomplete=deepcopy(MARA_RULES)
        incomplete.pop("new:pencil")
        with self.assertRaisesRegex(
            CoverageError,"IDENTITY_RULES_MUST_COVER_ALL_UNREGISTERED"
        ):
            resolve(prose=PROSE,world=entry_state(),
                    mention_census=c,rules=incomplete)
        c["unregistered_or_provisional_mentions"].remove("new:pencil")
        with self.assertRaisesRegex(CoverageError,
                                    "IDENTITY_RULES_MUST_COVER_ALL_UNREGISTERED"):
            resolve(prose=PROSE,world=entry_state(),
                    mention_census=c,rules=MARA_RULES)

    def test_anchor_and_model_evidence_tampering_fails(self):
        c=synthetic_mention_census()
        wrong=deepcopy(c)
        x=next(x for x in wrong["items"] if x["entity_ref"]=="new:watch_hands")
        x["source_evidence"][0]["quote"]="his literal human hands"
        with self.assertRaisesRegex(
            CoverageError,"IDENTITY_MENTION_EVIDENCE_NOT_SOURCE_BOUND"
        ):
            resolve(prose=PROSE,world=entry_state(),
                    mention_census=wrong,rules=MARA_RULES)
        wrong_rules=deepcopy(MARA_RULES)
        wrong_rules["new:watch_case"]["anchor"]="Watch case made of gold"
        with self.assertRaisesRegex(
            CoverageError,"IDENTITY_RULE_ANCHOR_NOT_IN_MENTION_SENTENCE"
        ):
            resolve(prose=PROSE,world=entry_state(),
                    mention_census=c,rules=wrong_rules)

    def test_bad_kinship_target_and_self_alias_blocked(self):
        wrong=deepcopy(MARA_RULES)
        wrong["new:vane_thumb"]["relation_target"]="vane_watch"
        with self.assertRaisesRegex(CoverageError,
                                    "IDENTITY_ANATOMICAL_PARENT_INVALID"):
            resolve(prose=PROSE,world=entry_state(),
                    mention_census=synthetic_mention_census(),rules=wrong)
        wrong=deepcopy(MARA_RULES)
        wrong["new:platform_record"]["relation_target"]="new:platform_record"
        with self.assertRaisesRegex(CoverageError,
                                    "IDENTITY_RULE_TARGET_NOT_GROUNDED"):
            resolve(prose=PROSE,world=entry_state(),
                    mention_census=synthetic_mention_census(),rules=wrong)

    def test_event_unknown_ref_and_fabricated_claim_authority_blocked(self):
        events=synthetic_event_census()
        events["rows"][0]["registry_unresolved_refs"]=["new:spaceship"]
        with self.assertRaisesRegex(
            CoverageError,"V014_EVENT_UNMAPPED_OR_PROMOTED_ENTITY"
        ):
            qualify(prose=PROSE,mentions=synthetic_mention_census(),events=events)
        events=synthetic_event_census()
        events["rows"][0]["canonical_commit_authorized"]=True
        with self.assertRaisesRegex(
            CoverageError,"V014_EVENT_UNMAPPED_OR_PROMOTED_ENTITY"
        ):
            qualify(prose=PROSE,mentions=synthetic_mention_census(),events=events)

if __name__=="__main__":
    unittest.main()
