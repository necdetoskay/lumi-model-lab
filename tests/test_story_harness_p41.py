"""P4.1 strict synthetic-positive English Master contract, real sealing DENIED."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import src.story_harness_p41 as p41
from src.story_harness_v1 import HarnessStop, canonical_bytes, digest, load_json, secure_artifact

ROOT=Path(__file__).resolve().parents[1]


def pinned():
    env=os.environ.get("STORY_HARNESS_PINNED_P41_ROOT")
    return Path(env).resolve(strict=True) if env else None


def registry():
    return load_json(secure_artifact(ROOT,p41.REGISTRY))


@unittest.skipUnless(os.environ.get("STORY_HARNESS_PINNED_P41_ROOT"),
                     "Real pinned v21 quality source required")
class P41EnglishMasterSealMechanicsTests(unittest.TestCase):
    def actual(self,**kwargs):
        return p41.qualify(repo_root=ROOT,pinned_source_root=pinned(),**kwargs)

    def source_cases(self):
        return p41._isolated_synthetic_quality(pinned(),sys.executable)["synthetic_cases"]

    def test_clean_and_repaired_positive_mechanics_but_no_real_seal(self):
        result=self.actual()
        self.assertEqual(result,self.actual())
        self.assertEqual(result["schema"],p41.SCHEMA)
        self.assertEqual(result["synthetic_positive_case_count"],2)
        self.assertEqual([r["synthetic_case"] for r in result["synthetic_previews"]],
                         ["clean","repair_succeeds"])
        self.assertEqual([r["validation"]["synthetic_quality_call_count"]
                          for r in result["synthetic_previews"]],[1,3])
        self.assertEqual(result["stop_reason"],"REAL_ENGLISH_MASTER_EVIDENCE_UNAVAILABLE")
        self.assertEqual(result["state"],"STOPPED_REAL_SEAL_AND_Q25_NOT_QUALIFIED")
        for key in ("actual_positive_model_quality_evidence_present",
                    "actual_reviewer_semantic_accept_present",
                    "real_english_master_seal_verified",
                    "real_english_master_seal_emitted","q25_source_request_produced",
                    "paid_execution_authorized","english_master_seal_authorized",
                    "q25_admission_authorized","state_commit_authorized",
                    "production_write_performed"):
            self.assertIs(result[key],False,key)
        self.assertEqual(result["provider_calls"],0)
        self.assertEqual(result["provider_cost_usd"],"0")

    def test_actual_original_v21_clean_repaired_positive_has_precise_lineage(self):
        trust=registry()
        clean,repaired=self.source_cases()
        self.assertTrue(p41._verify_synthetic_runtime_case(clean,trust))
        self.assertTrue(p41._verify_synthetic_runtime_case(repaired,trust))
        self.assertEqual(clean["accepted_story_sha256"],trust["source_story_sha256"])
        self.assertNotEqual(repaired["accepted_story_sha256"],trust["source_story_sha256"])
        self.assertTrue(repaired["rewrite_outside_cluster_unchanged"])
        self.assertEqual([r["stage"] for r in repaired["call_records"]],list(p41.STAGES))
        self.assertNotIn("full_story",repaired["call_records"][-1]["final_audit_payload_keys"])
        self.assertNotIn("story_segments",repaired["call_records"][-1]["final_audit_payload_keys"])
        self.assertEqual([r["usage"]["cost_usd"] for r in repaired["call_records"]],
                         [0.01,0.01,0.01])

    def test_candidate_is_mechanical_not_a_sealed_story(self):
        trust=registry()
        clean=self.source_cases()[0]
        preview=p41._make_preview(clean,trust)
        check=p41.validate_positive_mechanics(preview,clean,trust)
        self.assertEqual(preview["schema"],p41.CANDIDATE_SCHEMA)
        self.assertEqual(preview["seal"]["status"],"PREVIEW_NOT_A_SEAL")
        self.assertIsNone(preview["seal"]["immutable_seal_artifact_id"])
        self.assertFalse(preview["independent_review"]["real_semantic_quality_confirmed"])
        self.assertFalse(preview["provenance"]["real_provider_response_authenticated"])
        self.assertFalse(check["real_quality_evidence_verified"])
        self.assertFalse(check["english_master_seal_admitted"])

    def test_negative_identity_and_story_source_swaps(self):
        trust=registry()
        clean=self.source_cases()[0]
        for field,val in [
            ("source_story_artifact_id","story-other:fake"),
            ("source_story_sha256","0"*64),
            ("accepted_story_sha256","0"*64),
            ("stable_quality_projection_sha256","0"*64),
            ("quality_model_calls",4),
            ("envelope_simulation",False),
            ("envelope_paid_authorization",True),
            ("envelope_state_commit_executed",True),
        ]:
            fake=copy.deepcopy(clean)
            fake[field]=val
            with self.subTest(field=field),self.assertRaises(HarnessStop):
                p41._verify_synthetic_runtime_case(fake,trust)

    def test_mutated_reviewer_attestation_or_real_provider_claim_rejected(self):
        trust=registry()
        clean=self.source_cases()[0]
        good=p41._make_preview(clean,trust)
        for path,new in [
            (("independent_review","real_semantic_quality_confirmed"),True),
            (("independent_review","real_reviewer_signature_verified"),True),
            (("provenance","provider_origin"),p41.REAL_ORIGIN),
            (("provenance","real_token_cost_ledger_authenticated"),True),
            (("seal","status"),"SEALED"),
            (("seal","immutable_seal_artifact_id"),"english-master:forged"),
            (("source","context_fingerprint"),"different-world"),
            (("source","reader_exact_age"),5),
            (("proposed_english_text","sha256"),"a"*64),
            (("quality","model_call_count"),9),
        ]:
            fake=copy.deepcopy(good)
            fake[path[0]][path[1]]=new
            with self.subTest(path=path),self.assertRaises(HarnessStop):
                p41.validate_positive_mechanics(fake,clean,trust)

    def test_forged_stage_budget_ledger_or_full_story_final_rejected(self):
        trust=registry()
        repaired=self.source_cases()[1]
        for modified in (
           lambda x:x["call_records"][0]["usage"].update(cost_usd=0.05),
           lambda x:x["call_records"][1]["usage"].update(total_tokens=999999),
           lambda x:x["call_records"][2].update(stage="SCENE_REPAIR"),
           lambda x:x["call_records"][2]["final_audit_payload_keys"].append("full_story"),
           lambda x:x["quality_usage_rollup"].update(cost_usd=0.0001),
           lambda x:x["quality_usage_rollup"].update(total_tokens=1),
           lambda x:x.update(repair_count=2),
           lambda x:x.update(final_audit_validated=False),
           lambda x:x.update(rewrite_outside_cluster_unchanged=False),
       ):
            fake=copy.deepcopy(repaired)
            modified(fake)
            with self.assertRaises(HarnessStop):
                p41._verify_synthetic_runtime_case(fake,trust)

    def test_real_seal_always_denied_without_authenticated_trust_roots(self):
        trust=registry()
        clean=self.source_cases()[0]
        candidate=p41._make_preview(clean,trust)
        prior={"stop_reason":"REAL_BOUNDED_QUALITY_ACCEPT_MISSING"}
        with self.assertRaises(HarnessStop):
            p41.verify_actual_english_master_seal(candidate,trust,source_preflight=prior)
        fake=copy.deepcopy(candidate)
        fake["provenance"]["provider_origin"]=p41.REAL_ORIGIN
        fake["independent_review"]["real_reviewer_signature_verified"]=True
        fake["independent_review"]["real_semantic_quality_confirmed"]=True
        with self.assertRaisesRegex(HarnessStop,"No verified real provider"):
            p41.verify_actual_english_master_seal(fake,trust,source_preflight=prior)

    def test_q25_typed_preview_is_denied_and_cannot_be_promoted(self):
        trust=registry()
        original=self.source_cases()[0]
        candidate=p41._make_preview(original,trust)
        req=p41.build_q25_source_request_preview(candidate,trust)
        self.assertEqual(req["schema"],p41.Q25_SCHEMA)
        self.assertEqual(req["admission_status"],"DENIED_NOT_A_REAL_SEAL")
        self.assertTrue(p41.validate_q25_request_preview(req,candidate,trust))
        self.assertIsNone(req["verified_english_master_seal_artifact_id"])
        self.assertFalse(req["paid_provider_dispatch_authorized"])
        self.assertFalse(req["canonical_state_commit_authorized"])
        for key,value in (
            ("admission_status","ACCEPTED"),
            ("q25_extraction_authorized",True),
            ("actual_english_master_verified",True),
            ("verified_english_master_seal_artifact_id","english-master:fake"),
            ("preview_story_sha256","a"*64),
        ):
            forged=copy.deepcopy(req)
            forged[key]=value
            with self.subTest(field=key),self.assertRaises(HarnessStop):
                p41.validate_q25_request_preview(forged,candidate,trust)

    def test_q25_requires_separately_trusted_real_seal_and_source(self):
        trust=registry()
        for forged in [
            {},
            {"schema":"lumi.english-master-verified-seal.v1",
             "real_quality_verified":True,
             "approved_spine_hash":trust["approved_spine_hash"],
             "accepted_story_sha256":trust["source_story_sha256"]},
        ]:
            with self.assertRaisesRegex(HarnessStop,"No actual pinned Q25"):
                p41.build_q25_source_request(verified_real_seal=forged,trust=trust)

    def test_manifest_change_or_trust_root_injection_rejected(self):
        trust=registry()
        for fn in [
            lambda r:r["trusted_real_quality_receipt_sha256s"].append("0"*64),
            lambda r:r["trusted_independent_reviewer_attestation_sha256s"].append("a"*64),
            lambda r:r["registered_english_master_seal_sha256s"].append("f"*64),
            lambda r:r["registered_q25_source_sha256s"].append("d"*64),
            lambda r:r.update(automatic_paid_execution_authorized=True),
            lambda r:r.update(synthetic_fixtures_can_authorize_q25=True),
            lambda r:r.update(source_story_sha256="1"*64),
        ]:
            fake=copy.deepcopy(trust)
            fn(fake)
            with self.assertRaises(HarnessStop):
                self.actual(registry_override=fake)

    def test_real_quality_failure_historical_p40_denial_is_preserved(self):
        result=self.actual()
        self.assertTrue(result["trusted_real_quality_evidence_registered"] is False)
        self.assertFalse(result["authenticated_reviewer_attestation_registered"])
        self.assertFalse(result["independently_verified_seal_registered"])
        self.assertEqual(result["q25_source_request_schema"],p41.Q25_SCHEMA)
        self.assertTrue(result["q25_read_only_handoff_contract_defined"])

    def test_forged_stored_report_or_source_root_rejected(self):
        original=self.actual()
        self.assertTrue(p41.verify_report(original,repo_root=ROOT,pinned_source_root=pinned()))
        for key,val in [
            ("real_english_master_seal_emitted",True),
            ("q25_source_request_produced",True),
            ("state_commit_authorized",True),
            ("stop_reason","ACCEPT"),
            ("provider_calls",3),
        ]:
            forged=copy.deepcopy(original)
            forged[key]=val
            with self.subTest(field=key),self.assertRaises(HarnessStop):
                p41.verify_report(forged,repo_root=ROOT,pinned_source_root=pinned())
        with self.assertRaises(HarnessStop):
            p41.qualify(repo_root=ROOT,pinned_source_root=ROOT)

    def test_provider_secrets_are_not_used_in_real_runtime_mock(self):
        with patch.dict(os.environ,{"OPENROUTER_API_KEY":"should-not-leak",
                                    "ANTHROPIC_API_KEY":"should-not-leak",
                                    "OPENAI_API_KEY":"should-not-leak"}):
            result=self.actual()
        self.assertEqual(result["provider_calls"],0)
        self.assertEqual(result["provider_cost_usd"],"0")


if __name__=="__main__":
    unittest.main()

