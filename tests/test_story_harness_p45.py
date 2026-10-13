"""P4.5 actual 2494-word editorial draft; real frozen v21 scoped rewrite."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import src.story_harness_p45 as p45
from src.story_harness_v1 import HarnessStop,load_json,secure_artifact

ROOT=Path(__file__).resolve().parents[1]


def pinned():
    value=os.environ.get("STORY_HARNESS_PINNED_P45_ROOT")
    return Path(value).resolve(strict=True) if value else None


def manifest():
    return load_json(secure_artifact(ROOT,p45.MANIFEST))


def candidate_scene():
    return (ROOT/p45.SCENE).read_text().strip()


def candidate_full():
    return (ROOT/p45.FULL_STORY).read_text().rstrip("\n")


@unittest.skipUnless(os.environ.get("STORY_HARNESS_PINNED_P45_ROOT"),
                     "Original source frozen at commit 2eb3d8 is mandatory")
class P45EditorialBridgeSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=p45._manifest(ROOT)
        cls.original=(pinned()/(p45.PINNED_WRITER+
            "age12-island-v20-story-quality-repair-c10-story.txt")).read_text().rstrip("\n")
        cls.scene=candidate_scene()
        cls.full=candidate_full()

    def test_original_quality_runtime_applies_only_s159_to_s177(self):
        result=p45._execute_original_v21(ROOT,pinned(),__import__("sys").executable)
        self.assertTrue(result["outside_cluster_unchanged"])
        self.assertFalse(result["original_mutated"])
        self.assertEqual((result["source_char_start"],result["source_char_end"]),(9993,11495))
        self.assertEqual(result["candidate_full_story_sha256"],
                         self.m["complete_candidate_story_sha256"])
        self.assertEqual(result["source_story_sha256"],self.m["source_story_sha256"])
        self.assertEqual(result["replacement_scene_sha256"],
                         self.m["editorial_scene_sha256"])
        self.assertEqual(result["source_span_count"],199)
        self.assertGreater(result["new_span_count"],199)

    def test_prose_artifact_is_real_complete_replacement_not_historical_repair(self):
        self.assertEqual(len(self.original.split()),2407)
        self.assertEqual(len(self.scene.split()),370)
        self.assertEqual(len(self.full.split()),2494)
        self.assertNotEqual(self.original,self.full)
        self.assertNotIn('clipped the other end to his harness, swung the free end',
                         self.full)
        self.assertTrue(self.full.startswith(self.original[:9993]))
        self.assertTrue(self.full.endswith(self.original[11495:]))
        self.assertEqual(self.full[9993:9993+len(self.scene)],self.scene)

    def test_unchanged_entry_exit_story_boundaries_and_mystery(self):
        prefix=self.original[:9993]
        suffix=self.original[11495:]
        self.assertIn('"Hurry, the light\'s dimming',prefix[-130:])
        self.assertTrue(suffix.startswith("\n\nHe pulled himself up onto solid root"))
        self.assertIn("journal",self.full)
        self.assertIn("glider-tag",self.full)
        self.assertIn("stone gate",self.full)
        self.assertIn("they landed",self.full.lower())
        self.assertIn("Behind them, the island went into the wall.",self.full)
        self.assertNotIn("an adult saved Arda",self.scene)

    def test_visible_physical_order_has_no_teleporting_nisa(self):
        checks=p45._validate_editorial_candidate(
            self.m,self.original,self.scene,self.full)
        self.assertEqual(len(checks),6)
        self.assertTrue(all(x["mechanical_phrase_check_passed"] for x in checks))
        self.assertTrue(all(x["semantic_reviewer_accept_proven"] is False
                            for x in checks))
        i={t: self.scene.index(t) for t in (
            "He tied one end","clipped the other end","She ran three steps",
            '"Made it!" She unclipped',"tied it off",
            "Arda clipped his harness","The bridge shuddered",
            "root hooked the taut rope","Its gate jammed",
            "sliced the loaded stretch","His clip went slack",
            "She dropped flat, seized his wrist","held him at the rim")}
        self.assertEqual(list(i.values()),sorted(i.values()))

    def test_scene_uses_trunk_branch_clip_belay_and_only_one_cut(self):
        self.assertIn("bough stretching past the middle",self.scene)
        self.assertIn("lower far ledge",self.scene)
        self.assertIn("wrapped the free end around a stout root, and tied it off",self.scene)
        self.assertIn("last bridge anchor groaned",self.scene)
        self.assertEqual(self.scene.count("sliced the loaded stretch"),1)
        self.assertIn("The rope had marked every turn back to the shore",self.scene)
        self.assertIn("The line now linked both banks.",self.scene)
        self.assertIn("cut halves of their line dangled out of reach",self.scene)

    def test_separate_targeted_audit_payload_is_not_an_actual_model_call(self):
        result=p45._execute_original_v21(ROOT,pinned(),__import__("sys").executable)
        self.assertEqual(result["targeted_final_audit_scope"],
                         "REPAIRED_SCENE_PLUS_BOUNDARIES")
        self.assertTrue(result["full_story_reaudit_forbidden"])
        self.assertTrue(result["another_repair_forbidden"])
        self.assertEqual(result["entry_boundary_span_id"],"S158")
        self.assertEqual(result["exit_boundary_span_id"],"S178")
        self.assertEqual(result["actual_new_provider_quality_calls"],0)
        self.assertFalse(result["real_quality_accepted"])

    def test_tampered_annotated_scene_or_missing_causal_step_rejected(self):
        for modified in (
            self.scene.replace("She ran three steps and jumped.",""),
            self.scene.replace("sliced the loaded stretch","repaired the loaded stretch"),
            self.scene.replace("tied it off","held it loosely"),
            self.scene.replace("She dropped flat, seized his wrist","Nisa stood apart"),
            self.scene.replace("Its gate jammed tight against his harness.",""),
        ):
            with self.subTest(modified=modified[:90]),self.assertRaises(HarnessStop):
                p45._validate_editorial_candidate(self.m,self.original,modified,
                   self.full.replace(self.scene,modified))

    def test_wrong_scene_source_fingerprint_or_blocker_claim_rejected(self):
        for change in (
           lambda a:a.update(editorial_scene_sha256="e"*64),
           lambda a:a.update(complete_candidate_story_sha256="e"*64),
           lambda a:a["brief_structural_obligations"].pop(),
           lambda a:a["brief_structural_obligations"][0]["evidence"].reverse(),
           lambda a:a["brief_structural_obligations"][4].update(
                evidence=["Nisa teleported across the bridge"]),
        ):
            corrupted=copy.deepcopy(self.m)
            change(corrupted)
            with self.assertRaises(HarnessStop):
                p45._validate_editorial_candidate(
                    corrupted,self.original,self.scene,self.full)

    def test_rejected_paid_quality_remains_rejected_and_seal_denied(self):
        out=p45.qualify(repo_root=ROOT,pinned_source_root=pinned())
        self.assertEqual(out["status"],"EDITORIAL_TEXT_CREATED_BUT_UNREVIEWED")
        self.assertEqual(out["historical_paid_quality_status"],"REJECT_PROVIDER_FAILURE")
        self.assertFalse(out["real_independent_semantic_audit_passed"])
        self.assertFalse(out["real_provider_quality_accept"])
        self.assertFalse(out["english_master_seal_emitted"])
        self.assertFalse(out["q25_extraction_authorized"])
        self.assertFalse(out["story_state_commit_authorized"])
        self.assertFalse(out["real_paid_execution_authorized"])
        self.assertEqual((out["provider_calls"],out["provider_cost_usd"]),(0,"0"))

    def test_proposed_budget_is_not_paid_user_grant(self):
        report=p45.qualify(repo_root=ROOT,pinned_source_root=pinned())
        self.assertEqual(report["requested_one_attempt_budget_ceiling_usd"],0.25)
        self.assertTrue(report["budget_ceiling_is_only_a_proposal"])
        self.assertFalse(report["real_paid_execution_authorized"])
        self.assertEqual(report["provider_calls"],0)

    def test_full_immutable_proof_replay_and_stored_receipt(self):
        result=p45.qualify(repo_root=ROOT,pinned_source_root=pinned())
        self.assertEqual(result,p45.qualify(repo_root=ROOT,pinned_source_root=pinned()))
        self.assertEqual(result,load_json(secure_artifact(
            ROOT,"evidence/story_harness_p45/pinned-editorial-rewrite-receipt.json")))
        self.assertEqual(result["new_full_story_words"],2494)
        self.assertEqual(result["stop_reason"],
                         "EDITORIAL_REWRITE_READY_FOR_INDEPENDENT_QUALITY_REVIEW")
        self.assertTrue(result["mechanical_order_checks_are_not_semantic_quality_proof"])

    def test_wrong_source_and_symlink_story_artifact_denied(self):
        with self.assertRaises(HarnessStop):
            p45.qualify(repo_root=ROOT,pinned_source_root=ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)/"evidence/story_harness_p45"
            d.mkdir(parents=True)
            link=d/"offline-editorial-bridge-scene.txt"
            link.symlink_to(ROOT/p45.SCENE)
            with self.assertRaises(HarnessStop):
                p45._fixed_text_artifact(Path(tmp),p45.SCENE,self.m["editorial_scene_file_sha256"])

    def test_manifest_tamper_cannot_switch_candidate_to_accepted(self):
        self.assertEqual(p45._manifest(ROOT),self.m)
        for field in ("independent_quality_accept","paid_quality_authorized",
                      "english_master_seal_issued","q25_extraction_allowed",
                      "canonical_state_write_allowed"):
            fake=copy.deepcopy(self.m)
            fake[field]=True
            with self.subTest(field=field):
                self.assertNotEqual(fake,self.m)
        with patch.object(p45,"MANIFEST_SHA","f"*64),self.assertRaises(HarnessStop):
            p45._manifest(ROOT)


if __name__=="__main__":unittest.main()

