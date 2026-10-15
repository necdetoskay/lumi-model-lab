"""P4.7 single Writer route-truth correction; independent quality gate stays shut."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src import story_harness_p47 as p47
from src.story_harness_v1 import HarnessStop,secure_artifact,load_json

ROOT=Path(__file__).resolve().parents[1]


def pinned():
    return Path(os.environ["STORY_HARNESS_PINNED_P47_ROOT"]).resolve(strict=True)


@unittest.skipUnless(os.environ.get("STORY_HARNESS_PINNED_P47_ROOT"),
                     "Exact original v21.4 pinned checkout required")
class P47EditorAndNewStoryTrustTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=p47._manifest(ROOT)
        cls.original=p47._read_exact(ROOT,p47.PARENT,allow_evidence=True).decode()
        cls.candidate=p47._read_exact(ROOT,p47.CHILD,allow_evidence=True).decode()

    def test_revision_is_only_one_source_bound_prose_change(self):
        r=p47.qualify(repo_root=ROOT,pinned_source_root=pinned())
        self.assertTrue(r["other_prose_bytes_unchanged"])
        self.assertEqual(r["story_word_count"],2491)
        self.assertEqual(r["single_change_id"],"ROUTE_CAUSAL_TRUTH_001")
        self.assertEqual(self.original.replace(
            self.manifest["editorial_single_substitution"]["old"],
            self.manifest["editorial_single_substitution"]["new"],1),
            self.candidate)

    def test_old_knot_trail_is_distinct_from_ardas_carried_rope(self):
        self.assertIn("The old knots continued inland.",self.candidate)
        self.assertIn("Arda free his expedition line",self.candidate)
        self.assertIn("The old explorers' knots showed the way.",self.candidate)
        self.assertIn("This was Arda's own line",self.candidate)
        self.assertNotIn("The rope had marked every turn back to the shore.",
                         self.candidate)
        self.assertLess(self.candidate.index("The old knots continued inland."),
                        self.candidate.index("The old explorers' knots showed the way."))

    def test_prior_p46_closure_and_bridge_physics_text_unchanged(self):
        self.assertIn("both gliders' landing tethers to separate living roots",
                      self.candidate)
        self.assertIn("The line now linked both banks.",self.candidate)
        self.assertIn("Its gate jammed tight against his harness.",self.candidate)
        self.assertIn("The wrenching pull vanished.",self.candidate)
        self.assertIn("The Island That Wasn't on Any Map",self.candidate)
        self.assertIn("Behind them, the island went into the wall",self.candidate)
        self.assertEqual(self.candidate.count("The old explorers' knots showed the way."),1)

    def test_old_frozen_v21_source_bound_to_other_story(self):
        old=p47._real_profile_denial(pinned(),self.manifest)
        self.assertEqual(old,"4f64a28eca70f29689e06d1baad3d3a471682bf3e4fce86dabad1c641410f636")
        self.assertNotEqual(old,self.manifest["p47_story_sha256"])
        with self.assertRaises(HarnessStop):
            p47._real_profile_denial(ROOT,self.manifest)

    def test_semantic_review_is_explicitly_not_independent(self):
        n=p47._editorial_review(ROOT,self.manifest,self.candidate)
        self.assertEqual(n,6)
        r=p47.qualify(repo_root=ROOT,pinned_source_root=pinned())
        self.assertEqual(r["editorial_open_semantic_risk_count"],5)
        self.assertEqual(r["independent_reviewer_findings_total"],0)
        self.assertFalse(r["independent_semantic_quality_accept"])
        self.assertTrue(r["new_quality_model_profile_required"])
        self.assertEqual(r["stop_reason"],
                         "NEW_STORY_SHA_REQUIRES_SEPARATE_QUALITY_RUNNER_QUALIFICATION")

    def test_quote_offset_or_forged_quality_receipt_is_rejected(self):
        with patch.object(p47,"REVIEW_SHA","0"*64),self.assertRaises(HarnessStop):
            p47._editorial_review(ROOT,self.manifest,self.candidate)
        m=copy.deepcopy(self.manifest)
        m["p47_story_sha256"]=m["original_v21_4_bound_story_sha256"]
        with self.assertRaises(HarnessStop):
            p47._real_profile_denial(pinned(),m)

    def test_manifest_mutation_or_paid_grant_cannot_promote_story(self):
        m=self.manifest
        self.assertIsNone(m["paid_total_ceiling_usd"])
        self.assertFalse(m["real_authorized_paid_attempt"])
        self.assertFalse(m["english_master_authorized"])
        self.assertFalse(m["q25_authorized"])
        self.assertFalse(m["canonical_state_commit_authorized"])
        with patch.object(p47,"MANIFEST_SHA","0"*64),self.assertRaises(HarnessStop):
            p47._manifest(ROOT)

    def test_literal_evidence_has_pinned_sha_and_exact_receipt(self):
        r=p47.qualify(repo_root=ROOT,pinned_source_root=pinned())
        self.assertEqual(r,load_json(secure_artifact(ROOT,
              "evidence/story_harness_p47/pinned-route-truth-preflight.json")))
        self.assertEqual(r["p47_candidate_story_sha256"],
                         self.manifest["p47_story_sha256"])
        self.assertEqual(r["previous_p46_story_sha256"],
                         self.manifest["p46_story_sha256"])

    def test_bad_path_and_symlinked_candidate_rejected(self):
        with self.assertRaises(HarnessStop):
            p47._read_exact(ROOT,"evidence/story_harness_p47/../../secrets",
                            allow_evidence=True)
        with self.assertRaises(HarnessStop):
            p47._read_exact(ROOT,"src/story_harness_p47.py",allow_evidence=True)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            dest=root/p47.CHILD
            dest.parent.mkdir(parents=True)
            dest.symlink_to(ROOT/p47.CHILD)
            with self.assertRaises(HarnessStop):
                p47._read_exact(root,p47.CHILD,allow_evidence=True)

    def test_zero_paid_calls_and_english_master_q25_state_closed(self):
        r=p47.qualify(repo_root=ROOT,pinned_source_root=pinned())
        self.assertEqual(r["status"],"OFFLINE_WRITER_CANDIDATE_UNREVIEWED")
        self.assertFalse(r["real_paid_attempt_authorized"])
        self.assertFalse(r["finite_explicit_paid_grant_present"])
        self.assertFalse(r["original_frozen_model_runner_reusable_for_new_story"])
        self.assertEqual(r["new_model_quality_calls"],0)
        self.assertEqual(r["provider_cost_usd"],"0")
        self.assertFalse(r["english_master_seal_emitted"])
        self.assertFalse(r["q25_admission_authorized"])
        self.assertFalse(r["state_commit_authorized"])
        self.assertTrue(r["budget_target_overrun_previously_permitted"])
        self.assertEqual(r["proposed_paid_attempt_usd"],0.25)


if __name__=="__main__":unittest.main()

