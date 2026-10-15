"""P4.9 negative proofs: source identity/scope/budget grant never imply live calls."""
from __future__ import annotations

import copy
from decimal import Decimal
import json
from pathlib import Path
import unittest

from src.story_harness_p49 import (
    PROFILE_PATH, conditional_three_stage_cost, exact_file, inspect,
    require_paid_dispatch, review_packet,
)
from src.story_harness_v1 import HarnessStop

ROOT = Path(__file__).resolve().parents[1]


class PaidReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads(exact_file(ROOT, PROFILE_PATH))
        cls.writer = json.loads(exact_file(ROOT, cls.profile["source_story"]["artifact_path"]))
        cls.story_bytes = exact_file(ROOT, cls.writer["repaired_story_path"])

    def assess(self, profile=None, writer=None, manuscript=None):
        return review_packet(
            self.profile if profile is None else profile,
            self.writer if writer is None else writer,
            self.story_bytes if manuscript is None else manuscript,
        )

    def test_exact_frozen_artifact_packet_always_blocks_paid(self):
        result = inspect(repo_root=ROOT)
        self.assertEqual(result["story_sha256"], self.profile["source_story"]["story_sha256"])
        self.assertEqual(result["full_story_word_count"], 2491)
        self.assertEqual(result["full_story_segment_count"], 228)
        self.assertEqual(result["full_bridge_scene"]["count"], 45)
        self.assertEqual(result["provisional_scene_repair"]["count"], 37)
        self.assertFalse(result["provisional_scene_repair"]["human_reapproved"])
        self.assertEqual(len(result["blockers"]), 5)
        self.assertEqual(result["stop_reason"], "P49_SOURCE_VERIFIED_LIVE_PAID_ATTEMPT_NOT_READY")
        self.assertFalse(result["paid_dispatch_possible"])
        self.assertFalse(result["paid_attempt_authorized"])
        self.assertFalse(result["independent_quality_accepted"])
        self.assertFalse(result["english_master_authorized"])
        self.assertFalse(result["q25_authorized"])
        self.assertFalse(result["state_write_authorized"])
        self.assertEqual(result["new_provider_calls"], 0)
        self.assertEqual(result["new_provider_cost_usd"], "0")

    def test_pretend_paid_grant_is_rejected(self):
        changed = copy.deepcopy(self.profile)
        changed["explicit_finite_paid_execution_grant"] = {
            "run_id": "fake", "total_usd": 0.25, "approved": True
        }
        with self.assertRaises(HarnessStop):
            self.assess(profile=changed)

    def test_false_scene_review_and_expanded_scope_rejected(self):
        changed = copy.deepcopy(self.profile)
        changed["candidate_scene_scope_review_status"] = "APPROVED"
        with self.assertRaises(HarnessStop):
            self.assess(profile=changed)
        changed = copy.deepcopy(self.profile)
        changed["candidate_scene_scope"] = {
            "start_span_id": "S162", "end_span_id": "S206",
            "span_count": 45,
            "outside_scope_blocking_policy": "REJECT_UNBOUNDED_REPAIR_SCOPE",
        }
        with self.assertRaises(HarnessStop):
            self.assess(profile=changed)

    def test_swapped_story_sha_and_spine_are_rejected(self):
        changed = copy.deepcopy(self.writer)
        changed["repaired_story_text_sha256"] = "0" * 64
        with self.assertRaises(HarnessStop):
            self.assess(writer=changed)
        changed = copy.deepcopy(self.profile)
        changed["approved_spine_hash"] = "1" * 64
        with self.assertRaises(HarnessStop):
            self.assess(profile=changed)

    def test_text_or_span_tampering_rejected(self):
        changed = copy.deepcopy(self.writer)
        changed["repaired_segments"][184]["repaired_text"] += " extra"
        with self.assertRaises(HarnessStop):
            self.assess(writer=changed)
        with self.assertRaises(HarnessStop):
            self.assess(manuscript=self.story_bytes.replace(b"A living tree leaned", b"A dead tree leaned"))

    def test_budget_and_provider_forgery_rejected(self):
        for key, value in (
            ("real_provider_dispatch_allowed", True),
            ("pricing_routing_request_count_verified", True),
            ("independent_quality_accept", True),
            ("english_master_authorized", True),
            ("q25_authorized", True),
            ("state_write_authorized", True),
            ("max_quality_calls", 4),
        ):
            with self.subTest(key=key):
                changed = copy.deepcopy(self.profile)
                changed[key] = value
                with self.assertRaises(HarnessStop):
                    self.assess(profile=changed)

    def test_illustrative_cost_is_not_guaranteed_cap(self):
        result = inspect(repo_root=ROOT)
        self.assertEqual(
            conditional_three_stage_cost((9949, 5034, 5106)), Decimal("0.123178")
        )
        self.assertEqual(result["conditional_old_input_plus_max_output_cost_usd"], "0.123178")
        self.assertFalse(result["conditional_estimate_is_actual_new_request"])
        self.assertFalse(result["price_or_hard_cap_provider_authenticated"])
        self.assertFalse(result["proposed_limit_is_approved_grant"])

    def test_nan_negative_boolean_and_extra_stage_blocked(self):
        for inputs, outputs, price in (
            ((True, 2, 3), (1, 2, 3), "2"),
            ((1, -2, 3), (1, 2, 3), "2"),
            ((1, 2, 3, 4), (1, 2, 3, 4), "2"),
            ((1, 2, 3), (1, 2, 3), "NaN"),
            ((1, 2, 3), (1, 2, 3), "-3"),
        ):
            with self.subTest(inputs=inputs, price=price):
                with self.assertRaises(HarnessStop):
                    conditional_three_stage_cost(inputs, outputs, price)

    def test_live_dispatch_has_no_implementation_even_if_called(self):
        with self.assertRaisesRegex(HarnessStop, "OFFLINE_ONLY"):
            require_paid_dispatch(
                model="anthropic/claude-sonnet-5.5",
                paid_authorized=True, max_total_usd="0.25",
            )

    def test_exact_file_forbids_path_escape(self):
        for path in ("../configs/story_harness_p48_source_profile.json",
                     "/etc/passwd", "evidence/../../etc/passwd"):
            with self.subTest(path=path):
                with self.assertRaises(HarnessStop):
                    exact_file(ROOT, path)


if __name__ == "__main__":
    unittest.main()
