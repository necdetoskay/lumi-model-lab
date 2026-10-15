"""P4.3: offline-only one-shot v21.5 runner; real paid dispatch impossible."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import src.story_harness_p43 as p43
from src.story_harness_v1 import HarnessStop,load_json,secure_artifact

ROOT=Path(__file__).resolve().parents[1]


def pinned():
    p=os.environ.get("STORY_HARNESS_PINNED_P43_ROOT")
    return Path(p).resolve(strict=True) if p else None


def offline_policy():
    return load_json(secure_artifact(ROOT,p43.CONFIG))


def runner():
    spec=importlib.util.spec_from_file_location(
        "p43runner",ROOT/"src/story_harness_p43_runner.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(os.environ.get("STORY_HARNESS_PINNED_P43_ROOT"),
                     "Exact pinned original v21.4 source required")
class P43OfflineRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pinned_root=pinned()
        cls.conf=offline_policy()
        cls.runner=runner()
        cls.original=json.loads((cls.pinned_root/cls.runner.PROFILE_RELPATH).read_text())

    def test_original_source_pinned_and_read_only(self):
        conf=self.conf
        orig=self.original
        self.assertEqual(conf["source_story_sha256"],orig["source_story"]["story_sha256"])
        self.assertEqual(conf["source_story_artifact_id"],orig["source_story"]["artifact_id"])
        self.assertEqual(conf["approved_spine_hash"],orig["source_story"]["approved_spine_hash"])
        self.assertFalse(orig["paid_boundary"]["paid_execution_authorized"])
        self.assertTrue(orig["paid_boundary"]["authorization_consumed"])
        self.assertEqual(self.runner._sha(
            (self.pinned_root/self.runner.PROFILE_RELPATH).read_bytes()),
            self.runner.PINNED_PROFILE_SHA)

    def test_offline_only_pre_dispatch_default(self):
        x=self.runner.pre_dispatch_gate(self.conf,self.original)
        self.assertEqual(x["status"],"OFFLINE_PRE_DISPATCH_ONLY")
        self.assertFalse(x["real_network_dispatch_possible"])
        self.assertFalse(x["user_paid_grant_consumed"])
        self.assertFalse(x["real_price_quote_verified"])
        self.assertFalse(x["real_request_token_count_verified"])
        self.assertFalse(x["hard_provider_spend_limit_guaranteed"])
        self.assertEqual(x["target_quality_budget_usd"],0.1)

    def test_explicit_real_mode_and_fake_user_grants_are_rejected(self):
        r=self.runner
        for options in (
            {"mode":"REAL_PROVIDER"},
            {"grant":{"signature":"fake","approved":True}},
            {"endpoint":"https://openrouter.ai/api/v1/chat/completions"},
            {"verified_pricing":{"model":"anthropic/claude-sonnet-5.5"}},
            {"quoted_input_tokens":1024},
            {"run_attempt":2},
            {"mode":"REAL_PROVIDER","grant":{"signature":"fake"},
             "endpoint":"https://openrouter.ai/api/v1/chat/completions",
             "quoted_input_tokens":100,
             "verified_pricing":{"max_cost":.01}},
        ):
            with self.subTest(options=options),self.assertRaises(r.RunnerStop):
                r.pre_dispatch_gate(self.conf,self.original,**options)

    def test_budget_topology_and_production_state_changes_rejected(self):
        for field,new in (
            ("billing_permitted",True),
            ("provider_network_allowed",True),
            ("automatic_retry_enabled",True),
            ("production_state_writes_allowed",True),
            ("real_english_master_admission_allowed",True),
            ("max_quality_calls",10),
            ("max_repairs",3),
            ("targeted_final_audit_only",False),
            ("quality_target_usd",2.5),
            ("provider_spend_hard_cap_guaranteed",True),
            ("pricing_status","CURRENT_PRICING_VERIFIED"),
            ("provider_endpoint_status","OPENROUTER"),
            ("request_token_count_status","FAKE_VERIFIED"),
        ):
            cfg=copy.deepcopy(self.conf)
            cfg[field]=new
            with self.subTest(field=field),self.assertRaises(self.runner.RunnerStop):
                self.runner.pre_dispatch_gate(cfg,self.original)
        c=copy.deepcopy(self.conf)
        c["quality_stage_caps_usd"]["FINAL_AUDIT"]=99.0
        with self.assertRaises(self.runner.RunnerStop):
            self.runner.pre_dispatch_gate(c,self.original)

    def test_unapproved_route_or_original_paid_state_rejected(self):
        r=self.runner
        c=copy.deepcopy(self.original)
        c["model_slots"]["BLOCKING_AUDITOR"]="other-model"
        with self.assertRaises(r.RunnerStop):
            r.pre_dispatch_gate(self.conf,c)
        c=copy.deepcopy(self.original)
        c["paid_boundary"]["paid_execution_authorized"]=True
        with self.assertRaises(r.RunnerStop):
            r.pre_dispatch_gate(self.conf,c)
        c=copy.deepcopy(self.original)
        c["cost_policy"]["provider_spend_cap_guaranteed"]=True
        with self.assertRaises(r.RunnerStop):
            r.pre_dispatch_gate(self.conf,c)

    def test_once_claim_is_atomic_and_no_rerun(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            claim=self.runner._claim_once(root,"offline-one")
            self.assertTrue(claim.is_file())
            self.assertEqual(claim.stat().st_mode & 0o777,0o600)
            raw=claim.read_bytes()
            with self.assertRaises(FileExistsError):
                self.runner._claim_once(root,"offline-one")
            self.assertEqual(claim.read_bytes(),raw)
            for bad in ("../evil","evil/evil","ABCD","", "a"*60):
                with self.subTest(bad=bad),self.assertRaises(self.runner.RunnerStop):
                    self.runner._claim_once(root,bad)

    def test_output_symlink_is_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            real=Path(tmp)/"real"
            real.mkdir()
            alias=Path(tmp)/"alias"
            alias.symlink_to(real,target_is_directory=True)
            with self.assertRaises(self.runner.RunnerStop):
                self.runner._claim_once(alias,"offline-test")

    def test_original_adapter_callback_integration_four_cases(self):
        rows=p43._exec_callbacks(ROOT,pinned(),__import__("sys").executable)
        verified=p43._validate_observed(rows,None,self.conf)
        self.assertEqual(len(verified),4)
        self.assertEqual([x["quality_status_from_original_runtime"] for x in verified],
                         ["ACCEPT"]+["REJECT_PROVIDER_FAILURE"]*3)
        self.assertEqual([x["model_call_attempts"] for x in verified],[3]*4)
        self.assertTrue(all(x["provider_network_requests"]==0 for x in verified))
        self.assertTrue(all(not x["real_story_quality_accepted"] for x in verified))
        self.assertTrue(all(not x["english_master_seal_authorized"] for x in verified))
        self.assertTrue(all(not x["q25_extraction_authorized"] for x in verified))
        self.assertEqual([x["diagnostic_phase"] for x in verified],
                         [None,"response_validation","usage_validation","structured_parse"])

    def test_fake_attempts_cannot_promote_english_master_or_provider_calls(self):
        x=p43.qualify(repo_root=ROOT,pinned_source_root=pinned())
        self.assertEqual(x["stop_reason"],
                         "REAL_PAID_DISPATCH_DISABLED_OFFLINE_RUNNER_QUALIFIED")
        self.assertEqual(x["state"],"STOPPED_BEFORE_ANY_REAL_PROVIDER_EXECUTION")
        self.assertTrue(x["offline_qualification_once_claim_consumed"])
        self.assertTrue(x["original_v21_4_source_and_adapter_executed"])
        self.assertTrue(x["original_provider_callback_shape_injected"])
        self.assertFalse(x["real_paid_user_authorization_granted"])
        self.assertFalse(x["real_provider_spend_hard_cap_guaranteed"])
        self.assertFalse(x["actual_english_master_accepted"])
        self.assertFalse(x["english_master_seal_emitted"])
        self.assertFalse(x["q25_handoff_emitted"])
        self.assertFalse(x["production_state_write_executed"])
        self.assertEqual((x["provider_calls"],x["provider_cost_usd"]),(0,"0"))

    def test_bad_quality_case_or_missing_redacted_evidence_rejected(self):
        x=p43._exec_callbacks(ROOT,pinned(),__import__("sys").executable)
        variants=(
            lambda a:a["cases"][0].update(real_story_quality_accepted=True),
            lambda a:a["cases"][1].update(quality_status_from_original_runtime="ACCEPT"),
            lambda a:a["cases"][2].update(diagnostic_accounting_complete=True),
            lambda a:a["cases"][3].update(provider_network_requests=1),
            lambda a:a["cases"][0].update(q25_extraction_authorized=True),
            lambda a:a["cases"][1].update(final_diagnostic_present=False),
            lambda a:a["cases"][0].update(model_call_attempts=4),
            lambda a:a["cases"][0].update(source_story_sha256="0"*64),
            lambda a:a["pre_dispatch_negative_rejections"].update(real_mode=False),
            lambda a:a["cases"].pop(),
        )
        for i,change in enumerate(variants):
            fake=copy.deepcopy(x)
            change(fake)
            with self.subTest(i=i),self.assertRaises(HarnessStop):
                p43._validate_observed(fake,None,self.conf)

    def test_config_changed_or_mismatched_diagnostic_adapter_rejected(self):
        self.assertEqual(p43._source_conf(ROOT),self.conf)
        with patch.object(p43,"CONFIG_SHA","0"*64),self.assertRaises(HarnessStop):
            p43._source_conf(ROOT)
        with patch.object(p43,"DIAGNOSTIC","README.md"),self.assertRaises(HarnessStop):
            p43._source_conf(ROOT)

    def test_unpinned_profile_and_source_invalid(self):
        with self.assertRaises(self.runner.RunnerStop):
            self.runner.pinned_config(ROOT,self.runner.PROFILE_RELPATH,
                                      self.runner.PINNED_PROFILE_SHA)

    def test_no_network_or_credentials_inherited(self):
        with patch.dict(os.environ,{"OPENROUTER_API_KEY":"secret",
                                    "ANTHROPIC_API_KEY":"secret",
                                    "OPENAI_API_KEY":"secret"}):
            x=p43.qualify(repo_root=ROOT,pinned_source_root=pinned())
        self.assertEqual(x["provider_calls"],0)
        self.assertFalse(x["real_paid_user_authorization_granted"])


if __name__=="__main__":unittest.main()

