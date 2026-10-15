"""Story Harness P4.0 genuine frozen v21 executable/offline producer preflight."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import src.story_harness_p40 as p40
from src.story_harness_v1 import HarnessStop, load_json, secure_artifact

ROOT=Path(__file__).resolve().parents[1]


def pinned():
    value=os.environ.get("STORY_HARNESS_PINNED_P40_ROOT")
    return Path(value).resolve(strict=True) if value else None


def inventory():
    return load_json(secure_artifact(ROOT,p40.MANIFEST_PATH))


@unittest.skipUnless(os.environ.get("STORY_HARNESS_PINNED_P40_ROOT"),
                     "Pinned original v21 runtime source is required")
class P40ActualV21ProducerPreflightTests(unittest.TestCase):
    def full(self,override_manifest=None,override_simulation=None,source=None):
        return p40.qualify(repo_root=ROOT,pinned_source_root=source or pinned(),
                           override_manifest=override_manifest,
                           override_simulation=override_simulation)

    def test_six_actual_original_v21_scenarios_stay_offline(self):
        r=self.full()
        self.assertEqual(r,self.full())
        self.assertEqual(r["schema"],p40.SCHEMA)
        self.assertTrue(r["real_frozen_v21_engine_executed_with_mock_transport"])
        self.assertTrue(r["real_frozen_v21_profile_verified"])
        self.assertEqual(r["simulated_case_count"],6)
        self.assertEqual([v["status"] for v in r["original_six_synthetic_scenarios"]],
                         ["ACCEPT","ACCEPT","REJECT_NON_CONVERGENT",
                          "REJECT_COST_CEILING","REJECT_COST_CEILING","REJECT_COST_CEILING"])
        self.assertEqual([v["calls"] for v in r["original_six_synthetic_scenarios"]],
                         [1,3,3,1,2,3])
        for r0 in r["original_six_synthetic_scenarios"]:
            self.assertTrue(r0["mocked_provider"])
            self.assertFalse(r0["real_story_quality_accept_proven"])
            self.assertFalse(r0["eligible_for_english_master_seal"])

    def test_not_a_real_english_master_or_paid_authorization(self):
        r=self.full()
        self.assertEqual(r["stop_reason"],"REAL_BOUNDED_QUALITY_ACCEPT_MISSING")
        self.assertEqual(r["state"],"STOPPED_BEFORE_ENGLISH_MASTER_SEAL")
        self.assertFalse(r["synthetic_ACCEPT_is_genuine_story_quality"])
        self.assertFalse(r["actual_accepted_english_master_source_present"])
        self.assertFalse(r["real_authorized_accepted_story_generated"])
        self.assertTrue(r["english_master_seal_contract_ready_for_separate_positive_qualification"])
        for k in ("english_master_seal_emitted","q25_handoff_emitted",
                  "bounded_paid_attempt_authorized","english_master_seal_authorized",
                  "q25_extraction_authorized","final_story_state_authorized",
                  "state_commit_authorized","production_write_performed"):
            self.assertIs(r[k],False,k)
        self.assertEqual((r["provider_calls"],r["provider_cost_usd"]),(0,"0"))

    def test_actual_historical_paid_failure_and_ledger_not_a_success(self):
        r=self.full()["historical_paid_quality_failure"]
        self.assertEqual(r["historical_run_id"],37230896244)
        self.assertEqual(r["historical_quality_status"],"REJECT_PROVIDER_FAILURE")
        self.assertEqual(r["historical_failure_reason"],"FINAL_AUDIT: AdapterResponseError")
        self.assertEqual(r["historical_calls"],3)
        self.assertEqual(r["historical_cost_usd"],0.057988)
        self.assertEqual(r["historical_total_tokens"],21870)
        self.assertFalse(r["historical_cost_is_new_spend"])
        self.assertFalse(r["historical_quality_accept"])
        self.assertFalse(r["historical_story_sealed"])

    def test_real_v21_runtime_source_and_stage_caps_integrity(self):
        r=self.full()
        freeze=r["v21_frozen_contract"]
        self.assertEqual(freeze["runtime_revision"],
                         "SPINEFORGE-BOUNDED-QUALITY-FROZEN-v21.4")
        self.assertEqual(freeze["cost_limits_usd"],
                         {"initial_audit":0.04,"scene_repair":0.035,"final_audit":0.025})
        self.assertTrue(freeze["no_paid_authorization"])
        self.assertTrue(freeze["automatic_repair_loop_forbidden"])
        self.assertFalse(freeze["provider_spend_hard_cap_guaranteed"])
        self.assertEqual(freeze["total_cost_target_usd"],0.1)

    def test_manifest_mutation_or_forged_seal_denied(self):
        changes=[
            lambda m:m.update(admitted_historical_english_master={"story_sha256":"a"*64}),
            lambda m:m.update(admitted_historical_real_quality_result={"status":"ACCEPT"}),
            lambda m:m.update(historic_paid_v21_run_id=0),
            lambda m:m.update(source_commit="f"*40),
            lambda m:m.update(simulation_scenarios=["clean"]),
            lambda m:m["seal_admission_source"].update(simulation_receipts_forbidden=False),
            lambda m:m["seal_admission_source"].update(max_quality_calls=1000),
            lambda m:m["seal_admission_source"].update(quality_accept_does_not_automatically_seal=False),
        ]
        for i,change in enumerate(changes):
            modified=inventory()
            change(modified)
            with self.subTest(i=i),self.assertRaises(HarnessStop):
                self.full(override_manifest=modified)

    def test_swapped_original_v21_module_or_paid_result_denied(self):
        m=inventory()
        for target in [0,2,3,7,9,10]:
            item=m["source_sha256_roles"][target]
            fake=copy.deepcopy(item)
            fake["sha256"]="f"*64
            row=copy.deepcopy(m)
            row["source_sha256_roles"][target]=fake
            # Test byte pin in the source validator directly; caller manifest
            # also refuses the edited version.
            with self.subTest(path=item["path"]),self.assertRaises(HarnessStop):
                p40._source_roles(pinned(),row)

    def test_substituted_clean_git_worktree_fails(self):
        with self.assertRaises(HarnessStop):
            self.full(source=ROOT)

    def test_invalid_mock_accept_cannot_create_story_quality_proof(self):
        data=p40._run_real_v21_simulation(pinned(),__import__("sys").executable)
        base=self.full()["v21_frozen_contract"]
        m=inventory()
        for candidate in [
            lambda x:x["scenarios"][1].update(calls=4),
            lambda x:x["scenarios"][1].update(status="ACCEPTED_FOR_PRODUCTION"),
            lambda x:x["scenarios"][1].update(simulated_cost_usd=9.5),
            lambda x:x["scenarios"][2].update(status="ACCEPT"),
            lambda x:x["scenarios"].pop(),
            lambda x:x["freeze"].update(runtime_revision="unfrozen"),
        ]:
            fake=copy.deepcopy(data)
            candidate(fake)
            with self.assertRaises(HarnessStop):
                p40._validate_simulation(fake,base,m)

    def test_pretend_old_rejected_story_is_accepted_denied(self):
        data=self.full()
        self.assertFalse(data["historical_paid_quality_failure"]["historical_quality_accept"])
        real=p40._real_paid_history
        def modified(sources):
            fake=copy.deepcopy(sources)
            path=f"evidence/spineforge-v21-paid-quality/{p40.HISTORIC_RUN}/v21-bounded-quality-result.json"
            old=json.loads(fake[path])
            old["status"]="ACCEPT"
            fake[path]=json.dumps(old).encode()
            return real(fake)
        with self.assertRaises(HarnessStop):
            modified(p40._source_roles(pinned(),inventory()))

    def test_false_p40_receipt_promotions_rejected(self):
        original=self.full()
        self.assertTrue(p40.verify_report(original,repo_root=ROOT,pinned_source_root=pinned()))
        for k,v in [
            ("synthetic_ACCEPT_is_genuine_story_quality",True),
            ("english_master_seal_authorized",True),
            ("english_master_seal_emitted",True),
            ("q25_handoff_emitted",True),
            ("q25_extraction_authorized",True),
            ("bounded_paid_attempt_authorized",True),
            ("state_commit_authorized",True),
            ("stop_reason","ACCEPT"),
        ]:
            candidate=copy.deepcopy(original)
            candidate[k]=v
            with self.subTest(field=k),self.assertRaises(HarnessStop):
                p40.verify_report(candidate,repo_root=ROOT,pinned_source_root=pinned())

    def test_simulator_no_provider_credentials_required(self):
        with patch.dict(os.environ,{"OPENROUTER_API_KEY":"fake",
                                    "OPENAI_API_KEY":"fake",
                                    "ANTHROPIC_API_KEY":"fake"}):
            report=self.full()
        self.assertEqual(report["provider_calls"],0)
        self.assertEqual(report["provider_cost_usd"],"0")


if __name__=="__main__":
    unittest.main()

