"""P4.8: genuinely new P47 Writer text to frozen v21 adapter, NO real provider."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src import story_harness_p48 as p48
from src.story_harness_v1 import HarnessStop,secure_artifact,load_json

ROOT=Path(__file__).resolve().parents[1]


def pinned():
    return Path(os.environ["STORY_HARNESS_PINNED_P48_ROOT"]).resolve(strict=True)


@unittest.skipUnless(os.environ.get("STORY_HARNESS_PINNED_P48_ROOT"),
                     "Original pinned v21.4 code/approval required")
class P48ActualNewStoryQualityQualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile,cls.writer,cls.old=p48._source_profile(ROOT,pinned())

    def test_source_story_is_new_2491_word_writer_and_not_original_v21_story(self):
        self.assertEqual(self.writer["word_count"],2491)
        self.assertEqual(len(self.writer["repaired_segments"]),228)
        self.assertEqual(self.writer["status"],"FROZEN")
        self.assertTrue(self.writer["immutable"])
        self.assertFalse(self.writer["model_generated"])
        self.assertFalse(self.writer["semantic_quality_accepted"])
        self.assertEqual(self.writer["repaired_story_text_sha256"],p48.STORY_SHA)
        self.assertNotEqual(p48.OLD_STORY_SHA,p48.STORY_SHA)
        self.assertNotIn("story-quality-story:",self.writer["artifact_id"])

    def test_original_approved_spine_context_and_age_bound(self):
        self.assertEqual(self.profile["approved_spine_hash"],p48.SPINE)
        self.assertEqual(self.writer["approved_spine_hash"],p48.SPINE)
        self.assertEqual(self.profile["reader_profile"]["exact_age"],12)
        self.assertEqual(self.profile["candidate_scene_scope_review_status"],
                         "REMAP_OF_ORIGINAL_APPROVED_BEAT_NOT_HUMAN_REAPPROVED")
        self.assertFalse(self.profile["real_provider_dispatch_allowed"])

    def test_separate_new_segments_cover_story_and_are_228(self):
        paragraphs=self.writer["repaired_segments"]
        story=(ROOT/self.writer["repaired_story_path"]).read_text().rstrip("\n")
        cursor=0
        for n,row in enumerate(paragraphs,1):
            self.assertEqual(row["span_id"],f"S{n:03d}")
            value=row["repaired_text"]
            index=story.find(value,cursor)
            self.assertGreaterEqual(index,0)
            self.assertFalse(story[cursor:index].strip())
            cursor=index+len(value)
        self.assertFalse(story[cursor:].strip())
        self.assertEqual(len(paragraphs),228)

    def test_bridge_is_larger_than_single_40_segment_repair_scope(self):
        self.assertEqual(self.profile["bridge_full_scene_span_range"]["span_count"],45)
        self.assertFalse(self.profile["bridge_full_scene_span_range"]
                         ["fully_bounded_one_scene_repair_feasible"])
        self.assertEqual(self.profile["candidate_scene_scope"]["span_count"],37)
        self.assertEqual(self.profile["candidate_scene_scope"]["start_span_id"],"S167")
        self.assertEqual(self.profile["candidate_scene_scope"]["end_span_id"],"S203")
        self.assertEqual(self.profile["candidate_scene_scope"]
                         ["outside_scope_blocking_policy"],
                         "REJECT_UNBOUNDED_REPAIR_SCOPE")

    def test_actual_original_model_adapter_invoked_offline_for_new_story(self):
        r=p48._run_original_callbacks(ROOT,pinned(),__import__("sys").executable)
        self.assertEqual(r["source_story_sha256"],p48.STORY_SHA)
        self.assertTrue(r["original_v21_4_profile_verified"])
        self.assertTrue(r["new_profile_is_purely_offline_provisional"])
        self.assertFalse(r["real_paid_dispatch_possible"])
        self.assertFalse(r["independent_story_quality_accepted"])
        self.assertEqual(r["real_provider_calls"],0)
        self.assertEqual(r["provider_cost_usd"],"0")
        self.assertEqual(len(r["synthetic_scenarios"]),5)

    def test_synthetic_cases_include_single_bounded_repair_and_scope_denial(self):
        x=p48._run_original_callbacks(ROOT,pinned(),__import__("sys").executable)
        cases={r["scenario"]:r for r in x["synthetic_scenarios"]}
        self.assertEqual(set(cases),set(p48.CALL_CASES))
        for k,r in cases.items():
            self.assertEqual((r["runtime_status"],r["stage_attempts"]),
                             p48.CALL_CASES[k])
            self.assertEqual(r["model_call_records"],r["stage_attempts"])
            self.assertFalse(r["synthetic_quality_accept_is_real"])
            self.assertFalse(r["english_master_allowed"])
            self.assertFalse(r["q25_allowed"])
        self.assertEqual(cases["one_repair_synthetic"]["scene_repair_count"],1)
        self.assertEqual(cases["out_of_bounded_scope"]["stage_attempts"],1)

    def test_no_real_cost_authority_or_trusted_english_master(self):
        r=p48.qualify(repo_root=ROOT,pinned_source_root=pinned())
        self.assertEqual(r["stop_reason"],"P48_OFFLINE_NEW_STORY_ADAPTER_BOUND_PAID_DISABLED")
        self.assertFalse(r["independent_semantic_quality_accepted"])
        self.assertTrue(r["synthetic_accept_is_not_real_quality_accepted"])
        self.assertFalse(r["finite_explicit_paid_authorization_issued"])
        self.assertFalse(r["provider_price_route_and_input_exposure_verified"])
        self.assertFalse(r["english_master_seal_emitted"])
        self.assertFalse(r["q25_admission_authorized"])
        self.assertFalse(r["canonical_state_commit_authorized"])
        self.assertEqual(r["actual_new_paid_provider_calls"],0)
        self.assertEqual(r["actual_new_paid_cost_usd"],"0")

    def test_budget_target_overrun_not_user_spend_grant(self):
        self.assertTrue(self.profile["user_quality_target_overrun_permitted"])
        self.assertEqual(self.profile["proposed_paid_total_ceiling_usd"],0.25)
        self.assertEqual(self.profile["old_quality_total_target_usd"],0.1)
        self.assertIsNone(self.profile["explicit_finite_paid_execution_grant"])
        self.assertFalse(self.profile["real_provider_spend_guaranteed"])

    def test_compromised_artifact_new_profile_or_runner_hash_denied(self):
        with patch.object(p48,"PROFILE_SHA","0"*64),self.assertRaises(HarnessStop):
            p48._source_profile(ROOT,pinned())
        with patch.object(p48,"RUNNER_SHA","0"*64),self.assertRaises(HarnessStop):
            p48._run_original_callbacks(ROOT,pinned(),__import__("sys").executable)
        with patch.object(p48,"STORY_SHA","0"*64),self.assertRaises(HarnessStop):
            p48._source_profile(ROOT,pinned())

    def test_stored_immutable_receipt_replays_identically(self):
        a=p48.qualify(repo_root=ROOT,pinned_source_root=pinned())
        b=p48.qualify(repo_root=ROOT,pinned_source_root=pinned())
        self.assertEqual(a,b)
        self.assertEqual(a,load_json(secure_artifact(
            ROOT,"evidence/story_harness_p48/new-story-adapter-preflight.json")))

    def test_wrong_original_code_source_and_artifact_paths_denied(self):
        with self.assertRaises(HarnessStop):
            p48.qualify(repo_root=ROOT,pinned_source_root=ROOT)
        with self.assertRaises(HarnessStop):
            p48._local_bytes(ROOT,"../../etc/passwd")

    def test_source_lock_when_running_with_provider_keys(self):
        with patch.dict(os.environ,{
            "OPENROUTER_API_KEY":"should_not_leave_runner",
            "ANTHROPIC_API_KEY":"fake",
            "OPENAI_API_KEY":"fake",
        }):
            r=p48.qualify(repo_root=ROOT,pinned_source_root=pinned())
        self.assertEqual(r["actual_new_paid_provider_calls"],0)
        self.assertTrue(r["synthetic_accept_is_not_real_quality_accepted"])


if __name__=="__main__":unittest.main()

