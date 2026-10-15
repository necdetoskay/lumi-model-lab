"""P4.10 offline request and once-only budgeting tests. No provider/auth secrets."""
from __future__ import annotations

import copy
from decimal import Decimal
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.story_harness_p410 import (
    STAGES, MODEL, ENDPOINT, OfflineReservationLedger, block_live_dispatch,
    bounded_money, request_preview, request_receipt, status,
)
from src.story_harness_p49 import exact_file, PROFILE_PATH
from src.story_harness_v1 import HarnessStop

ROOT = Path(__file__).resolve().parents[1]
SMALL_STRICT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["summary"], "properties": {"summary": {"type": "string"}},
}


class RealNewStoryOfflineRequestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads(exact_file(ROOT, PROFILE_PATH))
        cls.writer = json.loads(exact_file(ROOT, cls.profile["source_story"]["artifact_path"]))
        cls.story = exact_file(ROOT, cls.writer["repaired_story_path"]).decode().rstrip("\n")
        spans, cursor = [], 0
        for row in cls.writer["repaired_segments"]:
            pos = cls.story.find(row["repaired_text"], cursor)
            if pos < cursor:
                raise AssertionError("Stored Writer segment not in source")
            spans.append([row["span_id"], cls.story[cursor:pos], row["repaired_text"]])
            cursor = pos + len(row["repaired_text"])
        cls.spans = {"spans": spans, "trailing_whitespace": cls.story[cursor:]}

    def kwargs(self, stage="INITIAL_AUDIT"):
        stage_class, tokens = STAGES[stage]
        name = {
            "INITIAL_AUDIT": "spineforge_v21_initial_blocking_audit_v1",
            "SCENE_REPAIR": "spineforge_v21_scene_repair_v1",
            "FINAL_AUDIT": "spineforge_v21_targeted_final_audit_v1",
        }[stage]
        payload = {
            "source_story_sha256": self.profile["source_story"]["story_sha256"],
        }
        if stage == "INITIAL_AUDIT":
            payload.update({
                "approved_spine_hash": self.profile["approved_spine_hash"],
                "reader_profile": {"exact_age": 12},
                "story_segments": self.spans,
            })
        if stage == "SCENE_REPAIR":
            payload.update({
                "scene_cluster": {"start_span_id": "S167", "end_span_id": "S203"},
                "entry_boundary": {"span_id": "S166"},
                "exit_boundary": {"span_id": "S204"},
                "source_scene_segments": {
                    "spans": self.spans["spans"][166:203],
                    "trailing_whitespace": "",
                },
            })
        if stage == "FINAL_AUDIT":
            payload["routing_policy"] = {"scope": "REPAIRED_SCENE_PLUS_BOUNDARIES"}
        return {
            "api_key": "", "model": MODEL, "system_prompt": "Auditor system instruction.",
            "user_prompt": json.dumps(payload, ensure_ascii=False),
            "temperature": 0.0, "max_tokens": tokens, "seed": None,
            "request_class": stage_class, "schema_name": name,
            "schema": copy.deepcopy(SMALL_STRICT_SCHEMA),
        }

    def build(self, stage="INITIAL_AUDIT", kwargs=None):
        return request_preview(
            repo_root=ROOT, stage=stage,
            callback_kwargs=kwargs if kwargs is not None else self.kwargs(stage),
        )

    def test_initial_real_source_in_preview_is_full_story(self):
        result = self.build()
        self.assertEqual(result["endpoint"], ENDPOINT)
        self.assertEqual(result["body"]["model"], MODEL)
        self.assertFalse(result["live_dispatch_allowed"])
        self.assertFalse(result["authenticated_provider_route"])
        self.assertEqual(result["body"]["provider"], {
            "only": ["Anthropic"], "allow_fallbacks": False,
            "require_parameters": True,
        })
        self.assertTrue(result["body"]["response_format"]["json_schema"]["strict"])
        self.assertEqual(result["body"]["max_tokens"], 3000)
        self.assertEqual(len(json.loads(result["body"]["messages"][1]["content"])["story_segments"]["spans"]), 228)
        receipt = request_receipt(result, 10000)
        self.assertEqual(receipt["conditional_exposure_usd"], "0.05")
        self.assertFalse(receipt["request_time_provider_price_verified"])
        self.assertFalse(receipt["input_ceiling_provider_verified"])
        self.assertEqual(receipt["stage"], "INITIAL_AUDIT")
        self.assertNotIn("Auditor system instruction", json.dumps(receipt))

    def test_three_bounded_stages_request_shapes(self):
        for stage in STAGES:
            with self.subTest(stage=stage):
                preview = self.build(stage)
                self.assertEqual(preview["stage"], stage)
                self.assertEqual(preview["body"]["max_tokens"], STAGES[stage][1])
                self.assertFalse(preview["body"]["stream"])
                receipt = request_receipt(preview, 11000)
                self.assertEqual(receipt["stage"], stage)
                self.assertFalse(receipt["fallback_allowed"])

    def test_swapped_writer_story_sha_denied(self):
        k = self.kwargs()
        payload = json.loads(k["user_prompt"])
        payload["source_story_sha256"] = "0" * 64
        k["user_prompt"] = json.dumps(payload)
        with self.assertRaises(HarnessStop):
            self.build(kwargs=k)

    def test_mutated_full_story_even_with_matching_story_sha_denied(self):
        k = self.kwargs()
        payload = json.loads(k["user_prompt"])
        payload["story_segments"]["spans"][189][2] = "Invented scene"
        k["user_prompt"] = json.dumps(payload)
        with self.assertRaises(HarnessStop):
            self.build(kwargs=k)

    def test_wrong_spine_and_age_denied(self):
        for key, newval in (("approved_spine_hash", "f" * 64), ("reader_profile", {"exact_age": 9})):
            k = self.kwargs()
            payload = json.loads(k["user_prompt"])
            payload[key] = newval
            k["user_prompt"] = json.dumps(payload)
            with self.subTest(key=key), self.assertRaises(HarnessStop):
                self.build(kwargs=k)

    def test_wrong_model_token_cap_schema_and_callback_key_denied(self):
        for field, value in (("model", "openai/gpt-4o"),
                             ("max_tokens", 12000),
                             ("request_class", "spineforge_v21_scene_repair"),
                             ("schema_name", "random_schema"),
                             ("api_key", "fake-secret")):
            k = self.kwargs()
            k[field] = value
            with self.subTest(field=field), self.assertRaises(HarnessStop):
                self.build(kwargs=k)
        k = self.kwargs()
        k["unexpected_transport_override"] = True
        with self.assertRaises(HarnessStop):
            self.build(kwargs=k)

    def test_scene_range_cannot_expand_and_final_not_full_story(self):
        k = self.kwargs("SCENE_REPAIR")
        payload = json.loads(k["user_prompt"])
        payload["scene_cluster"]["start_span_id"] = "S162"
        k["user_prompt"] = json.dumps(payload)
        with self.assertRaises(HarnessStop):
            self.build("SCENE_REPAIR", k)
        k = self.kwargs("FINAL_AUDIT")
        payload = json.loads(k["user_prompt"])
        payload["full_story"] = self.story
        k["user_prompt"] = json.dumps(payload)
        with self.assertRaises(HarnessStop):
            self.build("FINAL_AUDIT", k)

    def test_scene_prose_tampering_blocked_even_with_correct_story_sha(self):
        k = self.kwargs("SCENE_REPAIR")
        payload = json.loads(k["user_prompt"])
        payload["source_scene_segments"]["spans"][17][2] = "A fake repaired load path"
        k["user_prompt"] = json.dumps(payload)
        with self.assertRaises(HarnessStop):
            self.build("SCENE_REPAIR", k)

    def test_fallback_or_forged_routing_denied_in_receipt(self):
        preview = self.build()
        preview["body"]["provider"]["allow_fallbacks"] = True
        with self.assertRaises(HarnessStop):
            request_receipt(preview, 10000)
        preview = self.build()
        preview["authenticated_provider_route"] = True
        with self.assertRaises(HarnessStop):
            request_receipt(preview, 10000)

    def test_missing_overlarge_boolean_ceiling_and_nonfinite_budget_denied(self):
        preview = self.build()
        for count in (0, -1, True, 100001, 2.5, None):
            with self.subTest(count=count), self.assertRaises(HarnessStop):
                request_receipt(preview, count)
        for amt in ("NaN", "Infinity", "-0.1", "2", 0):
            with self.subTest(amt=amt), self.assertRaises(HarnessStop):
                bounded_money(amt)

    def test_offline_once_only_ledger_three_stage_reservation(self):
        with TemporaryDirectory() as temp:
            led = OfflineReservationLedger(temp, "p410_run1", total_limit="0.25")
            entries = []
            for stage, count in zip(STAGES, (11000, 6000, 5500)):
                receipt = request_receipt(self.build(stage), count)
                entries.append(led.reserve(receipt))
            self.assertEqual([e["stage"] for e in entries], list(STAGES))
            self.assertLess(Decimal(entries[-1]["cumulative_usd"]), Decimal("0.25"))
            self.assertTrue(all(e["provider_dispatch_count"] == 0 for e in entries))
            self.assertTrue(all(e["authenticated_user_grant"] is False for e in entries))
            with self.assertRaises(HarnessStop):
                led.reserve(request_receipt(self.build(), 10000))
            with self.assertRaises(FileExistsError):
                OfflineReservationLedger(temp, "p410_run1", total_limit="0.25")

    def test_out_of_order_and_exceeded_budget_fail_closed(self):
        with TemporaryDirectory() as temp:
            led = OfflineReservationLedger(temp, "p410_run2", total_limit="0.05")
            with self.assertRaises(HarnessStop):
                led.reserve(request_receipt(self.build("FINAL_AUDIT"), 1000))
            first = led.reserve(request_receipt(self.build(), 10000))
            self.assertEqual(first["cumulative_usd"], "0.05")
            with self.assertRaises(HarnessStop):
                led.reserve(request_receipt(self.build("SCENE_REPAIR"), 1000))

    def test_live_provider_remains_unreachable_and_status_stopped(self):
        data = status(repo_root=ROOT)
        self.assertEqual(data["stop_reason"], "P410_OFFLINE_ROUTING_AND_LEDGER_QUALIFIED_LIVE_DISABLED")
        self.assertFalse(data["live_routing_provider_authenticated"])
        self.assertFalse(data["authenticated_user_grant_consumed"])
        self.assertEqual(data["new_provider_calls"], 0)
        self.assertEqual(data["new_cost_usd"], "0")
        with self.assertRaisesRegex(HarnessStop, "OFFLINE_CONTRACT_ONLY"):
            block_live_dispatch(authenticated=True, budget_usd="0.25")


if __name__ == "__main__":
    unittest.main()
