"""SERA v0.15 model-hypothesis comparison is never truth qualification."""
from __future__ import annotations
from copy import deepcopy
import json
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.tests.test_identity_resolution_v014 import (
    PROSE,synthetic_mention_census,synthetic_event_census,
)
from experiments.sera.mara_s1_identity_review_v014 import qualify
from experiments.sera.tests.test_blind_identity_v015 import (
    preflight,synthetic_model_rows,
)
from experiments.sera.blind_identity_v015 import bind
from experiments.sera.identity_disagreement_v015 import compare

def fixtures():
    prior=qualify(prose=PROSE,mentions=synthetic_mention_census(),
                  events=synthetic_event_census())
    world,census,req=preflight()
    candidate=bind(prose=PROSE,world=world,census=census,request=req,
                   raw_response=json.dumps(synthetic_model_rows()))
    forensic={
        "schema":"sera.paid-blind-identity-forensic-recovery.v0.15.1",
        "source_run_id":38872615837,
        "source_prose_sha256":req["source_prose_sha256"],
        "all_original_model_rows_returned":16,
        "paid_model_calls_during_recovery":0,
        "new_entity_creations":0,
        "new_relation_attachments":0,
        "human_gold_adjudicated":False,
        "canonical_commit_authorized":False,
        "source_bound_model_proposals":candidate["items"],
        "quarantined_original_model_rows":[],
    }
    return forensic,prior

class IdentityDisagreementV015Tests(unittest.TestCase):
    def test_two_identical_but_untrusted_inputs_are_not_accuracy_or_truth(self):
        forensic,prior=fixtures()
        out=compare(forensic=forensic,prior=prior)
        self.assertEqual(out["original_model_mentioned_refs"],16)
        self.assertEqual(out["blind_source_bound_proposal_count"],16)
        self.assertEqual(out["blind_quarantined_count"],0)
        self.assertEqual(
            out["category_agreement_count_NOT_SEMANTIC_ACCURACY"],16)
        self.assertEqual(out["full_tuple_agreement_count_NOT_GOLD"],16)
        self.assertFalse(out["human_gold_adjudicated"])
        self.assertFalse(out["canonical_commit_authorized"])
        self.assertEqual(out["world_db_writes"],0)
        self.assertEqual(out["entity_creations"],0)
        self.assertTrue(all(x["status"]==
                "INDEPENDENT_REVIEW_STILL_REQUIRED" for x in out["rows"]))

    def test_cross_model_disagreements_reported_not_overwritten(self):
        forensic,prior=fixtures()
        archive=next(x for x in forensic["source_bound_model_proposals"]
                     if x["entity_ref"]=="new:archive")
        archive["proposed_classification"]="DOCUMENT_ALIAS_CANDIDATE"
        archive["proposed_relation"]="POTENTIAL_ALIAS_OF"
        archive["proposed_relation_target"]="archive_telegram"
        out=compare(forensic=forensic,prior=prior)
        self.assertEqual(
            out["category_agreement_count_NOT_SEMANTIC_ACCURACY"],15)
        mismatch=next(x for x in out["rows"]
                      if x["entity_ref"]=="new:archive")
        self.assertIn("BLIND_CLASS_DISAGREES_WITH_PRIOR_HYPOTHESIS",
                      mismatch["semantic_review_flags"])
        self.assertFalse(mismatch["canonical_commit_authorized"])

    def test_quarantined_and_unregistered_refs_are_not_silent_consensus(self):
        forensic,prior=fixtures()
        sample=forensic["source_bound_model_proposals"].pop()
        forensic["quarantined_original_model_rows"].append({
            "entity_ref":sample["entity_ref"],
            "error_code":"V015_RELATION_UNGROUNDED",
            "model_row_unmodified":{
                "classification":sample["proposed_classification"],
                "relation":sample["proposed_relation"],
                "relation_target":sample["proposed_relation_target"],
                "support_quote":sample["source_support"]["quote"],
            },
        })
        out=compare(forensic=forensic,prior=prior)
        self.assertEqual(out["blind_quarantined_count"],1)
        item=next(x for x in out["rows"]
                  if x["entity_ref"]==sample["entity_ref"])
        self.assertEqual(item["blind_deterministic_binding"],
                         "QUARANTINED_SOURCE_OR_SCHEMA_INVALID")
        self.assertIn("BLIND_ROW_QUARANTINED_INVALID_CONTRACT",
                      item["semantic_review_flags"])

    def test_malformed_count_or_fake_authority_fail_closed(self):
        forensic,prior=fixtures()
        forged=deepcopy(forensic)
        forged["source_bound_model_proposals"].pop()
        with self.assertRaisesRegex(
            CoverageError,"V015_CONTRAST_ENTITY_COVERAGE_INVALID"
        ):
            compare(forensic=forged,prior=prior)
        forged=deepcopy(forensic)
        forged["canonical_commit_authorized"]=True
        with self.assertRaisesRegex(
            CoverageError,"V015_CONTRAST_PAID_FORENSIC_PROVENANCE_INVALID"
        ):
            compare(forensic=forged,prior=prior)

if __name__=="__main__":
    unittest.main()
