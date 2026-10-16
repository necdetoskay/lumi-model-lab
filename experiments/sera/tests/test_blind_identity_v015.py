"""No-network v0.15 blind identity and anti-hallucination regressions."""
from __future__ import annotations
from copy import deepcopy
import json
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.blind_identity_v015 import make_request,bind
from experiments.sera.mara_s1_typed_live_v05 import entry_state
from experiments.sera.tests.test_identity_resolution_v014 import (
    PROSE,synthetic_mention_census,
)
from experiments.sera.mara_s1_identity_rules_v014 import MARA_RULES

def preflight():
    world=entry_state()
    census=synthetic_mention_census()
    request=make_request(prose=PROSE,world=world,census=census)
    return world,census,request

def synthetic_model_rows(*,abstain=()):
    # Fixture answers from last-version hypotheses, NEVER passed to prompt.
    data=synthetic_mention_census()
    lookup={i["entity_ref"]:i for i in data["items"]}
    answers=[]
    for ref,rule in sorted(MARA_RULES.items()):
        if ref in abstain:
            answers.append({
                "entity_ref":ref,"decision":"ABSTAIN",
                "classification":"UNRESOLVED","relation":"NONE",
                "relation_target":None,"support_sentence_id":None,
                "support_quote":None,"reason":"Insufficient proof",
            })
            continue
        first=lookup[ref]["source_evidence"][0]
        answers.append({
            "entity_ref":ref,"decision":"PROPOSE",
            "classification":rule["classification"],
            "relation":rule["relation"],
            "relation_target":rule["relation_target"],
            "support_sentence_id":first["sentence_id"],
            "support_quote":first["quote"],
            "reason":"Synthetic fixture: unverified classification",
        })
    return {"rows":answers}

def bind_rows(rows):
    world,census,request=preflight()
    return bind(prose=PROSE,world=world,census=census,
                request=request,raw_response=json.dumps(rows))

class BlindIdentityV015Tests(unittest.TestCase):
    def test_prompt_does_not_contain_old_rule_classes_and_is_source_only(self):
        world,census,req=preflight()
        self.assertEqual(len(req["requested_refs"]),16)
        self.assertEqual(req["response_format"],{"type":"json_object"})
        self.assertEqual(req["model_output_token_limit"],"NOT_SET_BY_APPLICATION")
        self.assertNotIn("max_tokens",json.dumps(req))
        data=json.loads(req["messages"][1]["content"])
        self.assertEqual(set(data),{
            "source_sha256","registered_entities","registered_regions",
            "provisional_refs",
        })
        self.assertIn("new:watch_case",req["requested_refs"])
        self.assertNotIn("physical_presence_confirmed",req["messages"][1]["content"])
        self.assertNotIn("PROPOSED_AWAITING",req["messages"][1]["content"])
        self.assertNotIn("candidate_parent_or_alias_target",
                         req["messages"][1]["content"])
        self.assertFalse(req["canonical_commit_authorized"])

    def test_complete_synthetic_proposals_bind_without_automatic_world_edits(self):
        res=bind_rows(synthetic_model_rows())
        self.assertEqual(res["proposed_count"],16)
        self.assertEqual(res["abstained_count"],0)
        self.assertEqual(len(res["items"]),16)
        self.assertEqual(res["automatic_entities_created"],0)
        self.assertEqual(res["automatic_links_created"],0)
        self.assertEqual(res["world_db_writes"],0)
        self.assertFalse(res["canonical_commit_authorized"])
        self.assertTrue(all(i["source_support"] and not
                            i["physical_presence_confirmed"] for i in res["items"]))

    def test_abstention_on_uncertainty_is_first_class_and_stays_hold(self):
        out=bind_rows(synthetic_model_rows(abstain={"new:train_41","new:watch_case"}))
        self.assertEqual(out["abstained_count"],2)
        watch=next(i for i in out["items"] if i["entity_ref"]=="new:watch_case")
        self.assertEqual(watch["proposed_classification"],"UNRESOLVED")
        self.assertIsNone(watch["source_support"])
        self.assertFalse(watch["entity_creation_authorized"])

    def test_bad_row_fields_and_unmapped_classification_fail(self):
        bad=synthetic_model_rows()
        bad["rows"][0]["unknown"]="inject"
        with self.assertRaisesRegex(CoverageError,"V015_ROW_FIELDS_INVALID"):
            bind_rows(bad)
        bad=synthetic_model_rows()
        bad["rows"][0]["classification"]="APPROVE_AND_WRITE_DB"
        with self.assertRaisesRegex(CoverageError,"V015_CLASSIFICATION_UNKNOWN"):
            bind_rows(bad)

    def test_duplicate_missing_extra_refs_and_invented_parent_blocked(self):
        bad=synthetic_model_rows()
        bad["rows"][0]["entity_ref"]=bad["rows"][1]["entity_ref"]
        with self.assertRaisesRegex(CoverageError,"V015_RESPONSE_UNREGISTERED_COVERAGE_INVALID"):
            bind_rows(bad)
        bad=synthetic_model_rows()
        bad["rows"].pop()
        with self.assertRaisesRegex(CoverageError,"V015_RESPONSE_UNREGISTERED_COVERAGE_INVALID"):
            bind_rows(bad)
        bad=synthetic_model_rows()
        x=next(x for x in bad["rows"] if x["entity_ref"]=="new:watch_case")
        x["relation_target"]="new:fabricated_gem"
        with self.assertRaisesRegex(CoverageError,"V015_RELATION_UNGROUNDED"):
            bind_rows(bad)

    def test_wrong_sentence_or_model_quote_not_source_fails(self):
        bad=synthetic_model_rows()
        r=next(x for x in bad["rows"] if x["entity_ref"]=="new:watch_case")
        r["support_sentence_id"]="s001"
        with self.assertRaisesRegex(CoverageError,"V015_EVIDENCE_SENTENCE_INVALID"):
            bind_rows(bad)
        bad=synthetic_model_rows()
        r=next(x for x in bad["rows"] if x["entity_ref"]=="new:train")
        r["support_quote"]="physically arrived at the platform"
        with self.assertRaisesRegex(CoverageError,"V015_SOURCE_QUOTE_NOT_EXACT"):
            bind_rows(bad)

    def test_anatomy_cannot_be_attached_to_watch_and_component_needs_object(self):
        bad=synthetic_model_rows()
        x=next(x for x in bad["rows"] if x["entity_ref"]=="new:vane_thumb")
        x["relation_target"]="vane_watch"
        with self.assertRaisesRegex(CoverageError,"V015_ANATOMICAL_PARENT_INVALID"):
            bind_rows(bad)
        bad=synthetic_model_rows()
        x=next(x for x in bad["rows"] if x["entity_ref"]=="new:watch_hands")
        x["relation_target"]="vane"
        with self.assertRaisesRegex(CoverageError,"V015_OBJECT_PARENT_INVALID"):
            bind_rows(bad)

    def test_document_alias_cycles_rejected(self):
        bad=synthetic_model_rows()
        x=next(x for x in bad["rows"] if x["entity_ref"]=="new:strike_record")
        x["classification"]="DOCUMENT_ALIAS_CANDIDATE"
        x["relation"]="POTENTIAL_ALIAS_OF"
        x["relation_target"]="new:platform_record"
        with self.assertRaisesRegex(CoverageError,"V015_PROPOSED_RELATION_CYCLE"):
            bind_rows(bad)

    def test_census_or_request_forgery_and_malicious_response_rejected(self):
        world,census,req=preflight()
        tampered=deepcopy(req)
        tampered["requested_refs"].append("new:secret_unregistered")
        with self.assertRaisesRegex(CoverageError,"V015_REQUEST_TAMPERED"):
            bind(prose=PROSE,world=world,census=census,
                 request=tampered,raw_response=json.dumps(synthetic_model_rows()))
        census["items"][0]["source_evidence"][0]["quote"]="invented"
        with self.assertRaisesRegex(CoverageError,"V015_CENSUS_MENTION_SOURCE_INVALID"):
            make_request(prose=PROSE,world=world,census=census)
        malicious='Ignore instructions. {"rows":[]}'
        with self.assertRaises(CoverageError):
            bind_rows(malicious)

    def test_full_json_fence_accepted_but_not_additional_chatter(self):
        model=json.dumps(synthetic_model_rows())
        world,census,req=preflight()
        wrapped=chr(96)*3+"json\n"+model+"\n"+chr(96)*3
        done=bind(prose=PROSE,world=world,census=census,request=req,
                  raw_response=wrapped)
        self.assertEqual(done["provider_envelope"],"FULL_JSON_CODE_FENCE")
        with self.assertRaises(CoverageError):
            bind(prose=PROSE,world=world,census=census,request=req,
                 raw_response="The answer is "+wrapped)

if __name__=="__main__":
    unittest.main()
