"""P4.4: source-grounded literary/causal review and conservative price exposure."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import src.story_harness_p44 as p44
from src.story_harness_v1 import HarnessStop,load_json,secure_artifact

ROOT=Path(__file__).resolve().parents[1]


def pinned():
    x=os.environ.get("STORY_HARNESS_PINNED_P44_ROOT")
    return Path(x).resolve(strict=True) if x else None


def manifest():
    return load_json(secure_artifact(ROOT,p44.MANIFEST))


@unittest.skipUnless(os.environ.get("STORY_HARNESS_PINNED_P44_ROOT"),
                     "Exact frozen original island Writer and paid v21 archive required")
class P44GroundedStoryAndPaidBudgetPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=p44._policy(ROOT)
        cls.story,cls.repair,cls.paid,cls.words=p44._genuine_history(
            cls.manifest,pinned())

    def test_original_story_is_2407_words_not_synthetic_accepted(self):
        self.assertEqual(self.words,2407)
        self.assertEqual(self.manifest["reader_age"],12)
        self.assertTrue(1600<=self.words<=2500)
        self.assertEqual(self.paid["status"],"REJECT_PROVIDER_FAILURE")
        self.assertIsNone(self.paid["accepted_story_sha256"])
        self.assertIsNone(self.paid["accepted_story"])
        self.assertTrue(self.paid["final_audit_executed"])
        self.assertEqual(self.paid["failure_reason"],"FINAL_AUDIT: AdapterResponseError")

    def test_real_audit_raised_four_affected_root_bridge_spans(self):
        call=self.paid["quality_calls"][0]
        self.assertEqual(call["response"]["findings"][0]["family"],
                         "physical_feasibility")
        self.assertEqual(call["response"]["findings"][0]["span_ids"],
                         ["S167","S172","S173","S175"])
        self.assertEqual(call["response"]["findings"][0]["severity"],"serious")
        self.assertEqual(self.paid["quality_calls"][1]["input"]["scene_cluster"]["start_span_id"],"S159")
        self.assertEqual(self.paid["quality_calls"][1]["input"]["scene_cluster"]["end_span_id"],"S177")
        self.assertEqual(self.paid["quality_calls"][1]["input"]["entry_boundary"]["span_id"],"S158")
        self.assertEqual(self.paid["quality_calls"][1]["input"]["exit_boundary"]["span_id"],"S178")

    def test_failed_paid_repair_is_not_semantic_quality_accept(self):
        self.assertIn("He threw the coil across the gap.",self.repair)
        self.assertIn("Nisa caught it.",self.repair)
        self.assertIn("hauled herself across hand over hand",self.repair)
        self.assertEqual(self.paid["quality_calls"][2]["status"],"FAILED")
        self.assertIsNone(self.paid["accepted_story_sha256"])

    def test_source_anchored_bridge_obligations_are_not_freeform_guesses(self):
        findings=p44._validate_source_anchored_findings(
            self.manifest,self.story,self.repair)
        self.assertEqual([f["id"] for f in findings],list(p44._EXPECTED_FINDING_IDS))
        self.assertEqual(sum(f["classification"]=="BLOCKING" for f in findings),5)
        self.assertEqual(sum(f["classification"]=="ADVISORY" for f in findings),2)
        self.assertTrue(all(not f["independent_semantic_accept_proven"] for f in findings))
        self.assertEqual(len({f["quote_sha256"] for f in findings}),7)

    def test_spatial_obligation_cannot_be_deleted(self):
        edited=copy.deepcopy(self.manifest)
        edited["manual_source_anchored_findings"].pop(3)
        with self.assertRaises(HarnessStop):
            p44._validate_source_anchored_findings(edited,self.story,self.repair)

    def test_quote_offset_and_cross_story_evidence_swap_rejected(self):
        for modifier in (
           lambda x:x["manual_source_anchored_findings"][0].update(char_start=0),
           lambda x:x["manual_source_anchored_findings"][4].update(
               evidence_source_sha256="f"*64),
           lambda x:x["manual_source_anchored_findings"][1].update(
               quote="Nisa had teleported safely to the opposite bank"),
           lambda x:x["manual_source_anchored_findings"][0].update(
               classification="ACCEPTED"),
        ):
            edited=copy.deepcopy(self.manifest)
            modifier(edited)
            with self.assertRaises(HarnessStop):
                p44._validate_source_anchored_findings(edited,self.story,self.repair)

    def test_historical_exact_provider_cost_arithmetic(self):
        result=p44._exposure(self.manifest,self.paid)
        self.assertEqual(result["historical_token_input_total"],20089)
        self.assertEqual(result["historical_token_output_total"],1781)
        self.assertEqual(result["historical_paid_cost_usd"],0.057988)
        self.assertEqual(result["historical_paid_api_calls"],3)
        self.assertEqual(result["total_target_usd"],0.1)
        self.assertFalse(result["paid_dispatch_budget_safe"])
        self.assertTrue(result["quality_target_overrun_user_permitted"])
        self.assertIsNone(result["authorized_paid_spend_ceiling_usd"])

    def test_indicative_upper_output_exposure_exceeds_target(self):
        x=p44._exposure(self.manifest,self.paid)
        self.assertEqual(x["conditional_exposure_original_output_caps_usd"],0.123178)
        self.assertTrue(x["conditional_exposure_exceeds_total_target"])
        self.assertTrue(all(i["conditional_exposure_exceeds_stage_target"]
                            for i in x["stage_risks"]))
        self.assertEqual([i["original_runtime_output_cap_tokens"] for i in x["stage_risks"]],
                         [3000,3500,1800])
        self.assertEqual([i["only_if_input_unchanged_max_output_to_meet_target"]
                          for i in x["stage_risks"]],[2010,2493,1478])
        self.assertFalse(x["provider_hard_budget_guaranteed"])
        self.assertFalse(x["runtime_input_tokens_upper_bound_verified"])
        self.assertFalse(x["pricing_technically_reverified_at_request_time"])

    def test_missing_or_nonfinite_actual_accounting_cannot_be_zero(self):
        for value in (float("nan"),-1,None):
            edited=copy.deepcopy(self.paid)
            edited["quality_calls"][1]["usage"]["input_tokens"]=value
            with self.assertRaises(HarnessStop):
                p44._exposure(self.manifest,edited)

    def test_changes_to_signed_off_prices_or_tampered_cost_rejected(self):
        original=copy.deepcopy(self.manifest)
        original["current_provider_price_reference"]["input_usd_per_1m"]=0.5
        with self.assertRaises(HarnessStop):
            p44._exposure(original,self.paid)
        paid=copy.deepcopy(self.paid)
        paid["quality_calls"][2]["usage"]["cost_usd"]=0
        with self.assertRaises(HarnessStop):
            p44._exposure(self.manifest,paid)

    def test_fixed_registry_cannot_authorize_real_execution(self):
        original=p44._policy(ROOT)
        self.assertTrue(original["quality_target_overrun_user_permitted"])
        self.assertIsNone(original["authorized_paid_spend_ceiling_usd"])
        self.assertFalse(original["user_permission_is_unlimited_spend"])
        self.assertFalse(original["real_dispatch_enabled"])
        self.assertIsNone(original["real_budget_authorization_id"])
        self.assertFalse(original["provider_credentials_may_be_used"])
        self.assertFalse(original["english_master_or_q25_enabled"])
        self.assertFalse(original["automatic_retries_enabled"])
        for name in ("real_dispatch_enabled","english_master_or_q25_enabled",
                     "provider_credentials_may_be_used","automatic_retries_enabled"):
            injected=copy.deepcopy(original)
            injected[name]=True
            with self.subTest(field=name):
                self.assertNotEqual(injected,original)
        with patch.object(p44,"MANIFEST_SHA","f"*64),self.assertRaises(HarnessStop):
            p44._policy(ROOT)

    def test_historical_source_and_review_sha_guard_rejected(self):
        for row in (self.manifest["story_source"],
                    self.manifest["original_paid_v21_result"],
                    self.manifest["original_paid_review"]):
            changed=copy.deepcopy(row);changed["sha256"]="0"*64
            with self.subTest(path=row["path"]),self.assertRaises(HarnessStop):
                p44._source_bytes(pinned(),changed)

    def test_full_offline_preflight_stops_but_remains_reproducible(self):
        a=p44.qualify(repo_root=ROOT,pinned_source_root=pinned())
        b=p44.qualify(repo_root=ROOT,pinned_source_root=pinned())
        self.assertEqual(a,b)
        self.assertEqual(a["stop_reason"],"NOT_READY_FOR_REAL_BOUNDED_QUALITY_ATTEMPT")
        self.assertEqual(a["state"],"STOPPED_EDITORIAL_AND_BUDGET_PREFLIGHT_BLOCKERS")
        self.assertEqual(a["confirmed_preliminary_blockers"],5)
        self.assertEqual(a["paid_initial_audit_original_blocking_finding_count"],1)
        self.assertFalse(a["real_final_quality_accept_present"])
        self.assertFalse(a["paid_execution_authorized"])
        self.assertTrue(a["quality_target_overrun_user_permitted"])
        self.assertIsNone(a["authorized_paid_spend_ceiling_usd"])
        self.assertFalse(a["new_story_generation_executed"])
        self.assertFalse(a["english_master_seal_emitted"])
        self.assertFalse(a["q25_request_authorized"])
        self.assertFalse(a["story_state_commit_authorized"])
        self.assertFalse(a["production_write_performed"])
        self.assertEqual(a["provider_calls"],0)
        self.assertEqual(a["provider_cost_usd"],"0")

    def test_different_unpinned_root_fails_closed(self):
        with self.assertRaises(HarnessStop):
            p44.qualify(repo_root=ROOT,pinned_source_root=ROOT)


if __name__=="__main__":unittest.main()

