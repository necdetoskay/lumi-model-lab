"""P3.1 exact historical audit/repair/reaudit chain, deterministic STOP only."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import src.story_harness_p31 as p31
from src.story_harness_v1 import HarnessStop, digest, load_json, secure_artifact

ROOT=Path(__file__).resolve().parents[1]


def pinned():
    v=os.environ.get("STORY_HARNESS_PINNED_P31_ROOT")
    return Path(v).resolve(strict=True) if v else None


def inventory():
    return load_json(secure_artifact(ROOT,p31.MANIFEST))


@unittest.skipUnless(os.environ.get("STORY_HARNESS_PINNED_P31_ROOT"),
                     "Real exact pinned historical source is required")
class P31RealQualityChainTests(unittest.TestCase):
    def qualify(self,inv=None,src=None):
        return p31.qualify(repo_root=ROOT,pinned_source_root=pinned() if src is None else src,
                           inventory=inv)

    def test_real_historical_chain_stops_unaccepted_quality(self):
        r=self.qualify()
        self.assertEqual(r,self.qualify())
        self.assertEqual(r["schema"],p31.SCHEMA)
        self.assertEqual(r["cohort_manifest_sha256"],p31.MANIFEST_SHA)
        self.assertEqual(r["stop_reason"],"STORY_QUALITY_NOT_ACCEPTED")
        self.assertEqual(r["state"],"STOPPED_UNACCEPTED_STORY")
        self.assertTrue(r["original_deterministic_spine_writer_validators_reexecuted"])
        self.assertTrue(r["full_cycle3_to_cycle10_lineage_ids_and_hashes_verified"])
        self.assertEqual(r["last_generated_repair_cycle"],10)
        self.assertEqual(r["last_completed_reaudit_cycle"],9)
        self.assertTrue(r["unreviewed_cycle10_story_pending_reaudit"])
        self.assertEqual(r["last_verified_story_audit_decision"],"LOCAL_REPAIR_REQUIRED")
        self.assertEqual(len(r["repair_reaudit_cycles"]),8)
        self.assertEqual(len(r["failed_reaudit_attempts"]),2)
        self.assertEqual([x["story_audit_decision"] for x in r["repair_reaudit_cycles"]],
                         ["LOCAL_REPAIR_REQUIRED"]*7 + ["NOT_REAUDITED"])
        self.assertEqual([x["qualification"] for x in r["original_audit_records"]],
                         ["FAIL_KNOWN_DEFECT_MISSED","PASS"])
        self.assertEqual([x["story_audit_decision"] for x in r["original_audit_records"]],
                         ["LOCAL_REPAIR_REQUIRED"]*2)

    def test_never_confuses_audit_qualification_pass_with_story_accept(self):
        r=self.qualify()
        self.assertTrue(r["original_audit_records"][1]["qualification_pass"])
        self.assertEqual(r["original_audit_records"][1]["story_audit_decision"],
                         "LOCAL_REPAIR_REQUIRED")
        self.assertFalse(r["qualification_pass_is_story_accept"])
        self.assertFalse(r["original_story_quality_accepted"])
        self.assertFalse(r["historical_paid_audit_or_repair_models_reexecuted"])
        self.assertFalse(r["historical_reaudit_quality_gate_reexecuted"])
        for key in ("repair_execution_authorized","q25_execution_authorized",
                    "english_master_seal_authorized","state_commit_authorized",
                    "downstream_execution_authorized","production_write_performed",
                    "same_story_q25_evidence_present"):
            self.assertIs(r[key],False,key)
        self.assertEqual((r["provider_calls"],r["provider_cost_usd"]),(0,"0"))

    def test_history_contains_actual_cycle2_root_and_connected_reaudits(self):
        r=self.qualify()
        self.assertEqual(r["cycle2_root_record"]["story_sha"],
                         r["repair_reaudit_cycles"][0]["source_story_sha256"])
        for i in range(1,len(r["repair_reaudit_cycles"])):
            self.assertEqual(r["repair_reaudit_cycles"][i]["source_story_sha256"],
                             r["repair_reaudit_cycles"][i-1]["repaired_story_sha256"])
        self.assertIsNone(r["repair_reaudit_cycles"][-1]["reaudit_run"])

    def test_every_hist_source_matches_pinned_sha(self):
        manifest=inventory()
        self.assertEqual(digest((ROOT/p31.MANIFEST).read_bytes()),p31.MANIFEST_SHA)
        for role in manifest["anchors"].values():
            raw=(pinned()/role["path"]).read_bytes()
            self.assertEqual(digest(raw),role["sha256"])
        for row in manifest["cycles"]:
            for key,value in row.items():
                if isinstance(value,dict):
                    self.assertEqual(digest((pinned()/value["path"]).read_bytes()),
                                     value["sha256"],(row["cycle"],key))
        for row in manifest["failed_reaudit_attempts"]:
            self.assertEqual(digest((pinned()/row["result"]["path"]).read_bytes()),
                             row["result"]["sha256"])

    def test_changed_source_commit_or_wrong_repair_cycle_rejected(self):
        with self.assertRaises(HarnessStop):
            self.qualify(src=ROOT)
        for mutated in (
            lambda a:a.update(source_commit="f"*40),
            lambda a:a["cycles"].reverse(),
            lambda a:a["cycles"][3].update(repair_run=37112601598),
            lambda a:a["cycles"].pop(),
            lambda a:a["cycles"][7].update(reaudit_run=99999999),
            lambda a:a["failed_reaudit_attempts"][0].update(run=37118083538),
        ):
            m=inventory()
            mutated(m)
            with self.assertRaises(HarnessStop):
                self.qualify(inv=m)

    def test_replay_receipt_cannot_claim_quality_or_q25_accept(self):
        legitimate=self.qualify()
        self.assertTrue(p31.verify_report(legitimate,repo_root=ROOT,pinned_source_root=pinned()))
        for key,value in (
            ("original_story_quality_accepted",True),
            ("english_master_seal_authorized",True),
            ("q25_execution_authorized",True),
            ("state_commit_authorized",True),
            ("historical_reaudit_quality_gate_reexecuted",True),
            ("stop_reason","ACCEPT"),
            ("last_verified_story_audit_decision","ACCEPT"),
            ("last_completed_reaudit_cycle",10),
        ):
            fake=copy.deepcopy(legitimate)
            fake[key]=value
            with self.subTest(key=key),self.assertRaises(HarnessStop):
                p31.verify_report(fake,repo_root=ROOT,pinned_source_root=pinned())

    def test_modified_source_sha_or_path_is_rejected(self):
        m=inventory()
        tampered=copy.deepcopy(m["cycles"][0]["repair_story"])
        tampered["sha256"]="0"*64
        with self.assertRaisesRegex(HarnessStop,"bytes mismatch"):
            p31._source_file(pinned(),tampered,kind="txt")
        tampered=copy.deepcopy(m["cycles"][0]["repair_story"])
        tampered["path"]="../unexpected.txt"
        with self.assertRaisesRegex(HarnessStop,"Unsafe"):
            p31._source_file(pinned(),tampered,kind="txt")
        tampered["path"]="/tmp/unexpected.txt"
        with self.assertRaisesRegex(HarnessStop,"Unsafe"):
            p31._source_file(pinned(),tampered,kind="txt")

    def test_forged_qualified_audit_story_accept_rejected(self):
        inv=inventory()
        a=inv["original_audits"][1]["audit_result"]
        original=p31._source_role
        def adjusted(root,role,match_path=None,kind="json"):
            result=original(root,role,match_path,kind)
            if role["path"]==a["path"]:
                result=copy.deepcopy(result)
                result["audit_artifact"]["decision"]="ACCEPT"
            return result
        with patch.object(p31,"_source_role",side_effect=adjusted):
            with self.assertRaises(HarnessStop):
                self.qualify()

    def test_forged_reaudit_accept_and_swapped_story_rejected(self):
        inv=inventory()
        artifact_path=inv["cycles"][4]["reaudit_result"]["path"]
        original=p31._source_role
        for field,value in (
            ("decision","ACCEPT"),
            ("source_repaired_story_sha256","f"*64),
            ("source_story_artifact_id","story-quality-story:forged"),
        ):
            def malicious(root,role,match_path=None,kind="json",field=field,value=value):
                result=original(root,role,match_path,kind)
                if role["path"]==artifact_path:
                    result=copy.deepcopy(result)
                    result["reaudit_artifact"][field]=value
                return result
            with self.subTest(field=field),patch.object(p31,"_source_role",side_effect=malicious):
                with self.assertRaises(HarnessStop):
                    self.qualify()

    def test_promoted_handoff_or_fake_failed_reaudit_rejected(self):
        inv=inventory()
        selected=inv["cycles"][5]["repair_handoff"]["path"]
        failed=inv["failed_reaudit_attempts"][0]["result"]["path"]
        original=p31._source_role
        for candidate,modification in [
            (selected,("paid_execution_authorized",True)),
            (selected,("status","APPROVED")),
            (failed,("status","reaudit_completed")),
            (failed,("state_commit_executed",True)),
        ]:
            def malicious(root,role,match_path=None,kind="json",
                          candidate=candidate,modification=modification):
                result=original(root,role,match_path,kind)
                if role["path"]==candidate:
                    result=copy.deepcopy(result)
                    result[modification[0]]=modification[1]
                return result
            with self.subTest(candidate=candidate,change=modification),patch.object(
                p31,"_source_role",side_effect=malicious):
                with self.assertRaises(HarnessStop):
                    self.qualify()

    def test_never_inherits_model_keys_or_runs_provider(self):
        with patch.dict(os.environ,{"OPENROUTER_API_KEY":"fake","OPENAI_API_KEY":"fake",
                                    "ANTHROPIC_API_KEY":"fake"}):
            r=self.qualify()
        self.assertEqual(r["provider_calls"],0)
        self.assertEqual(r["provider_cost_usd"],"0")


if __name__=="__main__":
    unittest.main()

