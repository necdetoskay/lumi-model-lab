"""P4.17: provider-shaped mock tests; never invoke model in CI."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
import io
import sys

from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p416_input_bridge import (
    compile_case, build_spine_request, approve_spine_for_writer,
    build_writer_request,
)
from src.story_harness_p417_live_pilot import (
    MODEL, ENDPOINT, OUTPUT_CAPS, USD_CAP, SCHEMA,
    wire, BoundedOncePilot, public_offline_status, money, main,
)
from src.story_harness_v1 import HarnessStop

ROOT = Path(__file__).resolve().parents[1]


def valid_spine(pack):
    locations = pack["canonical_state"]["locations"]
    beats = []
    for i in range(4):
        beats.append({
            "id": f"BEAT_{i+1:02d}",
            "location": locations[0] if i < 2 else locations[1],
            "goal": f"Character learns about the difficult quest at moment {i}.",
            "choice": f"Character bravely decides how to respond at moment {i}.",
            "consequence": f"Character faces meaningful consequences at moment {i}.",
            "obligation_reference": pack["open_obligations"][0] if i == 3 else None,
        })
    return {"source_pack_sha256": pack["pack_sha256"],
            "spine_summary": "A heartfelt adventure with a strong emotional transformation.",
            "beats": beats}


def generate_approved_words():
    return "Lumi found a tiny blue star. She listened closely and tried to understand. " * 29


class FakeProvider:
    def __init__(self, pack):
        self.pack = pack
        self.calls = []
        self.spine = valid_spine(pack)

    def __call__(self, body):
        self.calls.append(deepcopy(body))
        stage = body["response_format"]["json_schema"]["name"]
        if stage == "lumi_p417_spineforge_v1":
            content = self.spine
        elif stage == "lumi_p417_writer_v1":
            content = {
                "source_pack_sha256": self.pack["pack_sha256"],
                "spine_sha256": __import__("src.story_harness_p416_input_bridge",
                                          fromlist=["sha"]).sha(self.spine),
                "story_text": generate_approved_words(),
                "beat_ids": [x["id"] for x in self.spine["beats"]],
            }
        else:
            raise AssertionError("Wrong stage")
        return {
            "model": MODEL,
            "usage": {"prompt_tokens": 1024, "completion_tokens": 500,
                      "total_tokens": 1524, "cost": 0.012},
            "choices": [{"finish_reason": "stop", "message": {
                "content": json.dumps(content, ensure_ascii=False)}}],
        }


class P417Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = load_plan(ROOT)
        cls.case = cls.plan["cases"][0]
        cls.pack = compile_case(cls.case)

    def test_offline_report_no_models_or_fake_acceptance(self):
        r = public_offline_status(ROOT)
        self.assertEqual(r["case_count"], 10)
        self.assertEqual(r["per_pilot_maximum_usd"], "0.35")
        self.assertEqual(r["aggregate_user_budget_usd"], "10")
        self.assertFalse(r["genuine_independent_story_quality_accepted"])
        self.assertFalse(r["master_q25_state_authorized"])
        self.assertEqual(r["real_provider_calls"], 0)

    def test_exact_no_temperature_provider_route_and_usage(self):
        r = wire("SPINEFORGE", build_spine_request(self.pack))
        self.assertNotIn("temperature", r)
        self.assertEqual(r["model"], MODEL)
        self.assertEqual(r["usage"], {"include": True})
        self.assertEqual(r["provider"]["only"], ["Anthropic"])
        self.assertFalse(r["provider"]["allow_fallbacks"])
        self.assertTrue(r["provider"]["require_parameters"])
        self.assertEqual(r["provider"]["max_price"], {"prompt":2,"completion":10})
        self.assertTrue(r["response_format"]["json_schema"]["strict"])
        self.assertEqual(r["max_tokens"], OUTPUT_CAPS["SPINEFORGE"])

    def test_both_mock_stages_produce_unaccepted_story_and_cost_receipts(self):
        with TemporaryDirectory() as td:
            runner = BoundedOncePilot(td, case_id="B01", plan=self.plan)
            fake = FakeProvider(self.pack)
            r = runner.execute(transport=fake)
            self.assertEqual(len(fake.calls), 2)
            self.assertEqual(r["case_id"], "B01")
            self.assertEqual(r["story_words"], len(generate_approved_words().split()))
            self.assertEqual(r["two_stage_cost_usd"], "0.024")
            self.assertFalse(r["quality_accepted"])
            self.assertTrue((runner.dir / "story-draft.json").is_file())
            rec = json.loads((runner.dir / "02-writer-receipt.json").read_text())
            self.assertEqual(rec["outcome"], "SETTLED")
            self.assertEqual(rec["provider_reported_cost_usd"], "0.012")
            story = json.loads((runner.dir / "story-draft.json").read_text())
            self.assertTrue(story["model_generated"])
            self.assertFalse(story["english_master_authorized"])
            self.assertFalse(story["quality_accepted"])
            self.assertEqual(len(list(runner.dir.glob("*-intent.json"))), 2)

    def test_duplicate_run_directory_prevents_replay(self):
        with TemporaryDirectory() as td:
            BoundedOncePilot(td, case_id="B01", plan=self.plan)
            with self.assertRaises(FileExistsError):
                BoundedOncePilot(td, case_id="B01", plan=self.plan)

    def test_only_two_calls_no_retries_or_extra_writer(self):
        with TemporaryDirectory() as td:
            runner = BoundedOncePilot(td, case_id="B01", plan=self.plan)
            provider = FakeProvider(self.pack)
            runner.execute(transport=provider)
            with self.assertRaises(HarnessStop):
                runner.call("WRITER", build_writer_request(
                    self.pack, runner.prepared_spine), transport=provider)
            self.assertEqual(len(provider.calls), 2)

    def test_bad_model_response_stops_and_consumes_intent(self):
        with TemporaryDirectory() as td:
            runner = BoundedOncePilot(td, case_id="B01", plan=self.plan)
            provider = FakeProvider(self.pack)
            def bad(body):
                result = provider(body)
                result["model"] = "wrong-model"
                return result
            with self.assertRaises(HarnessStop):
                runner.execute(transport=bad)
            self.assertEqual(len(provider.calls), 1)
            self.assertTrue(runner.halted)
            self.assertTrue((runner.dir / "01-spineforge-receipt.json").exists())

    def test_unknown_cost_no_retry_even_on_successful_text(self):
        with TemporaryDirectory() as td:
            runner = BoundedOncePilot(td, case_id="B01", plan=self.plan)
            provider = FakeProvider(self.pack)
            def no_cost(body):
                r = provider(body)
                del r["usage"]["cost"]
                return r
            with self.assertRaises(HarnessStop):
                runner.execute(transport=no_cost)
            self.assertEqual(len(provider.calls), 1)
            self.assertTrue(runner.halted)

    def test_cost_over_stage_limit_stops_before_writer(self):
        with TemporaryDirectory() as td:
            runner = BoundedOncePilot(td, case_id="B01", plan=self.plan)
            provider = FakeProvider(self.pack)
            def expensive(body):
                r = provider(body)
                r["usage"]["cost"] = 0.10
                return r
            with self.assertRaises(HarnessStop):
                runner.execute(transport=expensive)
            self.assertEqual(len(provider.calls), 1)

    def test_network_exception_consumes_once_only(self):
        with TemporaryDirectory() as td:
            runner = BoundedOncePilot(td, case_id="B01", plan=self.plan)
            n = []
            def broken(body):
                n.append(1)
                raise TimeoutError("unknown")
            with self.assertRaises(HarnessStop):
                runner.execute(transport=broken)
            self.assertEqual(n, [1])
            with self.assertRaises(HarnessStop):
                runner.call("SPINEFORGE", build_spine_request(self.pack),
                            transport=broken)
            self.assertEqual(n, [1])

    def test_writers_invalid_words_beat_sequence_and_source_hash_stop(self):
        for field in ("story_text", "beat_ids", "source_pack_sha256", "spine_sha256"):
            with self.subTest(field=field), TemporaryDirectory() as td:
                runner = BoundedOncePilot(td, case_id="B01", plan=self.plan)
                provider = FakeProvider(self.pack)
                def attack(body):
                    r = provider(body)
                    if body["response_format"]["json_schema"]["name"] == "lumi_p417_writer_v1":
                        obj = json.loads(r["choices"][0]["message"]["content"])
                        obj[field] = ("too short" if field == "story_text" else
                                      [] if field == "beat_ids" else "fake")
                        r["choices"][0]["message"]["content"] = json.dumps(obj)
                    return r
                with self.assertRaises(HarnessStop):
                    runner.execute(transport=attack)
                self.assertEqual(len(provider.calls), 2)
                self.assertFalse((runner.dir / "story-draft.json").exists())

    def test_output_token_overrun_or_incomplete_finish_stops(self):
        for broken in ("tokens", "finish"):
            with TemporaryDirectory() as td:
                runner = BoundedOncePilot(td, case_id="B01", plan=self.plan)
                provider = FakeProvider(self.pack)
                def attack(body):
                    r = provider(body)
                    if broken == "tokens":
                        r["usage"]["completion_tokens"] = 9000
                    else:
                        r["choices"][0]["finish_reason"] = "length"
                    return r
                with self.assertRaises(HarnessStop):
                    runner.execute(transport=attack)
                self.assertEqual(len(provider.calls), 1)

    def test_invalid_money_values_are_denied(self):
        for v in (None, "NaN", "Infinity", -1, True, {}, "bad"):
            with self.subTest(value=v), self.assertRaises(HarnessStop):
                money(v)

    def test_missing_signed_paid_flag_rejects_before_key(self):
        with patch.object(sys, "argv", ["p417", "--paid-one-shot", "--case-id",
                                        "B01", "--run-root", "/not/reachable"]),              patch.dict(os.environ, {"LUMI_P417_ENABLE_PAID": ""}):
            with self.assertRaises(HarnessStop):
                main()

    def test_default_cli_never_touches_key_or_network(self):
        with patch.object(sys, "argv", ["p417", "--repo-root", str(ROOT)]),              patch.dict(os.environ, {}, clear=True):
            buff = io.StringIO()
            with redirect_stdout(buff):
                main()
            result = json.loads(buff.getvalue())
            self.assertEqual(result["real_provider_calls"], 0)


if __name__ == "__main__":
    unittest.main()
