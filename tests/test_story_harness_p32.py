"""P3.2 English Master admission denial on actual unaccepted island evidence."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import src.story_harness_p32 as p32
from src.story_harness_v1 import HarnessStop, digest, load_json, secure_artifact

ROOT=Path(__file__).resolve().parents[1]


def pinned():
    value=os.environ.get("STORY_HARNESS_PINNED_P32_ROOT")
    return Path(value).resolve(strict=True) if value else None


def inventory():
    return load_json(secure_artifact(ROOT,p32.SOURCES))


def source_role(name):
    return inventory()["terminal_quality_candidate"][name]


@unittest.skipUnless(os.environ.get("STORY_HARNESS_PINNED_P32_ROOT"),
                     "Actual immutable P3.2 source worktree required")
class P32EnglishMasterAdmissionTests(unittest.TestCase):
    def full(self,override=None,src=None):
        return p32.qualify(repo_root=ROOT,pinned_source_root=src or pinned(),
                           override_inventory=override)

    def test_historical_admission_stops_without_master_seal(self):
        r=self.full()
        self.assertEqual(r,self.full())
        self.assertEqual(r["schema"],p32.SCHEMA)
        self.assertEqual(r["source_commit"],
                         "2eb3d825b5baf8f0f16ccb23805f619d433c7236")
        self.assertEqual(r["stop_reason"],"ENGLISH_MASTER_NOT_ADMISSIBLE")
        self.assertEqual(r["state"],"STOPPED_UNSEALED_UNACCEPTED_STORY")
        self.assertEqual(r["historical_island_tracked_source_file_count"],152)
        self.assertEqual(r["historical_english_master_named_files"],[])
        self.assertFalse(r["historical_english_master_artifact_found"])
        self.assertFalse(r["historical_quality_accept_receipt_found"])
        self.assertTrue(r["historical_runtime_source_ast_checked"])
        self.assertEqual(r["terminal_candidate"]["next_state_action"],"REAUDIT")
        self.assertEqual(r["terminal_candidate"]["next_state_status"],
                         "NEXT_ACTION_READY_NOT_AUTHORIZED")
        self.assertEqual(r["terminal_candidate"]["last_qualified_cycle"],9)
        self.assertEqual(r["terminal_candidate"]["on_accept_policy_route"],
                         "ENGLISH_MASTER_SEAL")
        self.assertIsNone(r["admitted_english_master_story_sha256"])
        self.assertIsNone(r["final_english_master_artifact_id"])

    def test_policy_accept_branch_is_conditional_not_executed(self):
        r=self.full()
        policy=r["historical_policy"]
        self.assertTrue(policy["policy_has_accept_branch"])
        self.assertFalse(policy["accept_branch_is_actual_history"])
        self.assertFalse(policy["policy_automatic_paid_transition_authorized"])
        self.assertEqual(policy["policy_accept_route"],"ENGLISH_MASTER_SEAL")
        pth=pinned()/inventory()["historical_policy_sources"]["quality_loop_runtime"]["path"]
        self.assertEqual(
            p32._inspect_original_quality_accept_branch(pth.read_bytes()),policy)

    def test_qualification_pass_does_not_grant_master_admission(self):
        r=self.full()
        required=r["required_admission_checks"]
        self.assertTrue(required["same_story_lineage_proven"])
        self.assertFalse(required["original_completed_story_quality_ACCEPT"])
        self.assertFalse(required["cycle10_completed_reaudit_proven"])
        self.assertFalse(required["latest_accepted_story_sha256_proven"])
        self.assertFalse(required["registered_exact_same_story_english_master_seal"])
        self.assertFalse(required["english_master_admission_authorized"])
        for flag in ("q25_extraction_authorized","final_story_state_authorized",
                     "english_master_seal_execution_authorized",
                     "english_master_story_accepted",
                     "state_commit_authorized","production_write_performed"):
            self.assertFalse(r[flag],flag)
        self.assertEqual(r["provider_calls"],0)
        self.assertEqual(r["provider_cost_usd"],"0")

    def test_lighthouse_accept_cannot_be_substituted(self):
        r=self.full()
        lighthouse=r["unrelated_accepted_story_reference"]
        self.assertEqual(lighthouse["counterexample_status"],"ACCEPT")
        self.assertEqual(lighthouse["counterexample_origin"],"lighthouse-patch-campaign")
        self.assertFalse(lighthouse["accepted_as_island_english_master"])
        self.assertNotEqual(lighthouse["counterexample_sha256"],
                            r["terminal_candidate"]["candidate_source_story_sha256"])
        self.assertNotEqual(lighthouse["counterexample_sha256"],p32.WRITER_SHA)

    def test_modified_manifest_registry_or_cycle_is_rejected(self):
        modifications=[
           lambda obj:obj["admissible_english_master_seals"].append("fake-seal"),
           lambda obj:obj["admissible_accepted_reaudit_artifacts"].append("fake-accept"),
           lambda obj:obj["admissible_q25_sources"].append("fake-q25"),
           lambda obj:obj["terminal_quality_candidate"].update(cycle=9),
           lambda obj:obj.update(source_cohort_prefix="evidence/lighthouse"),
           lambda obj:obj.update(source_commit="1"*40),
        ]
        for i,change in enumerate(modifications):
            bad=inventory()
            change(bad)
            with self.subTest(i=i),self.assertRaises(HarnessStop):
                self.full(override=bad)

    def test_wrong_commit_not_qualified(self):
        with self.assertRaises(HarnessStop):
            self.full(src=ROOT)

    def test_modified_tracked_source_hash_is_rejected(self):
        for role in (
            inventory()["historical_policy_sources"]["quality_loop_runtime"],
            inventory()["historical_policy_sources"]["quality_loop_contract"],
            inventory()["terminal_quality_candidate"]["reaudit_handoff"],
            inventory()["terminal_quality_candidate"]["next_state"],
        ):
            bad=copy.deepcopy(role)
            bad["sha256"]="f"*64
            with self.subTest(path=role["path"]),self.assertRaisesRegex(
                HarnessStop,"bytes differ"):
                p32._pinned_bytes(pinned(),bad)

    def test_untracked_or_changed_git_file_inventory_fails_closed(self):
        original=p32._tracked_scope
        def substitute(root,commit,prefix):
            paths=original(root,commit,prefix)
            return paths+["evidence/spineforge-v20-paid-writer/FAKE-english-master.json"]
        with patch.object(p32,"_tracked_scope",side_effect=substitute):
            with self.assertRaisesRegex(HarnessStop,"Unexpected unqualified English Master"):
                self.full()

    def test_fake_completed_cycle10_or_authorizing_handoff_rejected(self):
        original=p32._pinned_bytes
        roles=inventory()["terminal_quality_candidate"]
        trials=[
          ("next_state","status","QUALITY_LOOP_ACCEPTED"),
          ("next_state","current_action","ENGLISH_MASTER_SEAL"),
          ("next_state","paid_execution_authorized",True),
          ("reaudit_handoff","paid_execution_authorized",True),
          ("reaudit_handoff","status","APPROVED"),
          ("reaudit_handoff","cycle_index",9),
          ("reaudit_handoff","next_stage_on_accept","Q25"),
          ("story_product","repaired_story_text_sha256","0"*64),
        ]
        for role,field,value in trials:
            target=roles[role]["path"]
            def malicious(root,item,expected=None,roots=("evidence/","src/"),
                          target=target,field=field,value=value):
                raw=original(root,item,expected=expected,roots=roots)
                if item["path"]==target:
                    obj=json.loads(raw)
                    obj[field]=value
                    return json.dumps(obj).encode("utf8")
                return raw
            with self.subTest(role=role,field=field),patch.object(
                    p32,"_pinned_bytes",side_effect=malicious):
                with self.assertRaises(HarnessStop):
                    self.full()

    def test_policy_claiming_accept_unconditionally_is_rejected(self):
        runtime=inventory()["historical_policy_sources"]["quality_loop_runtime"]
        content=p32._pinned_bytes(pinned(),runtime)
        changed=content.replace(b'elif decision == "ACCEPT":',b'elif decision == "REPAIR":')
        self.assertNotEqual(changed,content)
        with self.assertRaisesRegex(HarnessStop,"routing branches not found"):
            p32._inspect_original_quality_accept_branch(changed)

    def test_fake_counterexample_same_story_hash_rejected(self):
        original=p32._pinned_bytes
        role=inventory()["cross_story_counterexample"]["path"]
        candidate=self.full()["terminal_candidate"]["candidate_source_story_sha256"]
        def bad(root,item,expected=None,roots=("evidence/","src/")):
            raw=original(root,item,expected=expected,roots=roots)
            if item["path"]==role:
                obj=json.loads(raw)
                obj["accepted_story_sha256"]=candidate
                return json.dumps(obj).encode("utf8")
            return raw
        with patch.object(p32,"_pinned_bytes",side_effect=bad),self.assertRaises(
                HarnessStop):
            self.full()

    def test_forced_quality_accept_even_with_fake_seal_not_admitted(self):
        real=self.full()
        q=load_json(secure_artifact(ROOT,"evidence/story_harness_p31/pinned-quality-chain-receipt.json"))
        forged=copy.deepcopy(q)
        forged["original_story_quality_accepted"]=True
        with self.assertRaises(HarnessStop):
            p32._admission_prerequisite_contract(
                forged,real["terminal_candidate"],["fake-seal"],["fake-accept"])

    def test_receipt_cannot_be_manually_promoted(self):
        valid=self.full()
        self.assertTrue(p32.verify_report(valid,repo_root=ROOT,pinned_source_root=pinned()))
        trials=[
           ("english_master_story_accepted",True),
           ("english_master_seal_execution_authorized",True),
           ("q25_extraction_authorized",True),
           ("state_commit_authorized",True),
           ("final_english_master_artifact_id","sealed:fake"),
           ("historical_english_master_artifact_found",True),
           ("stop_reason","ACCEPT"),
           ("state","ENGLISH_MASTER_SEALED"),
        ]
        for k,v in trials:
            candidate=copy.deepcopy(valid)
            candidate[k]=v
            with self.subTest(key=k),self.assertRaisesRegex(
                    HarnessStop,"edited/forged"):
                p32.verify_report(candidate,repo_root=ROOT,pinned_source_root=pinned())

    def test_provider_tokens_not_forwarded_or_model_called(self):
        with patch.dict(os.environ,{"OPENROUTER_API_KEY":"fake","OPENAI_API_KEY":"fake",
                                    "ANTHROPIC_API_KEY":"fake"}):
            report=self.full()
        self.assertEqual(report["provider_calls"],0)
        self.assertEqual(report["provider_cost_usd"],"0")


if __name__=="__main__":
    unittest.main()

