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

    def test_real_strict_schema_enums_bind_only_known_places_and_obligations(self):
        req = wire("SPINEFORGE", build_spine_request(self.pack))
        schema = req["response_format"]["json_schema"]["schema"]
        props = schema["properties"]["beats"]["items"]["properties"]
        self.assertEqual(schema["properties"]["source_pack_sha256"]["enum"],
                         [self.pack["pack_sha256"]])
        self.assertEqual(props["id"]["enum"][0], "BEAT_01")
        self.assertEqual(props["id"]["enum"][-1], "BEAT_08")
        self.assertEqual(props["location"]["enum"],
                         self.pack["canonical_state"]["locations"])
        self.assertIn(None, props["obligation_reference"]["enum"])
        self.assertEqual(props["obligation_reference"]["enum"][1:],
                         self.pack["open_obligations"])

    def test_writer_schema_enforces_actual_spine_hash_and_beat_set(self):
        pack = self.pack
        ready = approve_spine_for_writer(pack, valid_spine(pack))
        req = wire("WRITER", build_writer_request(pack, ready))
        schema = req["response_format"]["json_schema"]["schema"]
        fields = schema["properties"]
        self.assertEqual(fields["spine_sha256"]["enum"], [ready["spine_sha256"]])
        self.assertEqual(fields["source_pack_sha256"]["enum"],
                         [pack["pack_sha256"]])
        ids = [x["id"] for x in ready["spine"]["beats"]]
        self.assertEqual(fields["beat_ids"]["items"]["enum"], ids)
        self.assertIn(str(len(ids)), fields["beat_ids"]["description"])
        self.assertNotIn("minItems", fields["beat_ids"])
        self.assertNotIn("maxItems", fields["beat_ids"])

    def test_anthropic_wire_schema_never_sends_unsupported_array_bounds(self):
        # The Anthropic native structured-output API rejects maxItems and
        # minItems greater than one with HTTP 400. We still reject invalid
        # count/order in approve_spine_for_writer and Writer lineage checks.
        from collections import deque
        p = self.pack
        ready = approve_spine_for_writer(p, valid_spine(p))
        bodies = [
            wire("SPINEFORGE", build_spine_request(p)),
            wire("WRITER", build_writer_request(p, ready)),
        ]
        for body in bodies:
            schema = body["response_format"]["json_schema"]["schema"]
            queue = deque([schema])
            while queue:
                node = queue.popleft()
                if type(node) is dict:
                    self.assertNotIn("maxItems", node)
                    if "minItems" in node:
                        self.assertIn(node["minItems"], (0, 1))
                    queue.extend(node.values())
                elif type(node) is list:
                    queue.extend(node)

    def test_local_spine_length_and_order_checks_remain_strict_without_wire_bounds(self):
        p = self.pack
        for bad in (3, 9):
            item = valid_spine(p)
            while len(item["beats"]) < bad:
                item["beats"].append(deepcopy(item["beats"][-1]))
            item["beats"] = item["beats"][:bad]
            for i, beat in enumerate(item["beats"]):
                beat["id"] = f"BEAT_{i+1:02d}"
            with self.assertRaises(HarnessStop):
                approve_spine_for_writer(p, item)

    def test_spine_schema_is_unique_for_each_distinct_canon(self):
        plans = [compile_case(self.plan["cases"][i]) for i in range(3)]
        schemas = [
            wire("SPINEFORGE", build_spine_request(p))[
                "response_format"]["json_schema"]["schema"]
            for p in plans
        ]
        self.assertEqual(len({str(s) for s in schemas}), 3)
        for p,schema in zip(plans,schemas):
            self.assertEqual(
                schema["properties"]["beats"]["items"]["properties"]["location"]["enum"],
                p["canonical_state"]["locations"],
            )

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

    def test_r02_is_separate_once_only_and_original_claim_remains_consumed(self):
        with TemporaryDirectory() as td:
            first = BoundedOncePilot(td, case_id="B01", plan=self.plan)
            second = BoundedOncePilot(td, case_id="B01", plan=self.plan,
                                      run_variant="r02")
            self.assertNotEqual(first.dir, second.dir)
            self.assertTrue((first.dir / "00-claim.json").exists())
            self.assertTrue((second.dir / "00-claim.json").exists())
            with self.assertRaises(FileExistsError):
                BoundedOncePilot(td, case_id="B01", plan=self.plan,
                                 run_variant="r02")
            with self.assertRaises(HarnessStop):
                BoundedOncePilot(td, case_id="B01", plan=self.plan,
                                 run_variant="r07")

    def test_provider_charge_recorded_even_when_spine_fails(self):
        with TemporaryDirectory() as td:
            runner = BoundedOncePilot(td, case_id="B01", plan=self.plan,
                                      run_variant="r02")
            provider = FakeProvider(self.pack)
            def charge_and_break(body):
                result = provider(body)
                result["id"] = "gen-VALIDTEST123456"
                result["usage"]["cost"] = 0.014
                obj = json.loads(result["choices"][0]["message"]["content"])
                obj["beats"][0]["location"] = "OUTSIDE_CANON"
                result["choices"][0]["message"]["content"] = json.dumps(obj)
                return result
            with self.assertRaises(HarnessStop):
                runner.execute(transport=charge_and_break)
            receipt = json.loads((runner.dir / "01-spineforge-receipt.json").read_text())
            self.assertEqual(receipt["provider_reported_cost_usd"], "0.014")
            self.assertEqual(receipt["provider_usage"]["prompt_tokens"], 1024)
            self.assertEqual(receipt["provider_generation_id"], "gen-VALIDTEST123456")
            self.assertEqual(receipt["outcome"], "STOP_UNKNOWN_OR_INVALID")
            self.assertEqual(len(provider.calls), 1)

    def test_absent_generation_id_does_not_forge_provenance(self):
        with TemporaryDirectory() as td:
            runner = BoundedOncePilot(td, case_id="B01", plan=self.plan)
            fake = FakeProvider(self.pack)
            result = runner.execute(transport=fake)
            receipt = json.loads((runner.dir / "01-spineforge-receipt.json").read_text())
            self.assertIsNone(receipt["provider_generation_id"])
            self.assertFalse(result["quality_accepted"])

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

    def test_failure_diagnostic_discloses_only_phase_not_model_text(self):
        with TemporaryDirectory() as td:
            runner = BoundedOncePilot(td, case_id="B01", plan=self.plan)
            p = FakeProvider(self.pack)
            def missing_usage(body):
                reply = p(body)
                reply["usage"] = {"prompt_tokens":100,
                                  "completion_tokens":300}
                reply["id"] = "gen-sensitive-request-trace-XYZ"
                reply["choices"][0]["message"]["content"] = (
                    "SECRET_STORY_SHOULD_NOT_BE_LOGGED")
                return reply
            with self.assertRaises(HarnessStop) as cm:
                runner.execute(transport=missing_usage)
            self.assertIn("BILLED_COST", str(cm.exception))
            receipt = json.loads((runner.dir / "01-spineforge-receipt.json").read_text())
            diag = receipt["safe_failure_diagnostic"]
            self.assertEqual(diag["phase"], "PROVIDER_USAGE")
            self.assertEqual(diag["safe_failure_code"], "BILLED_COST_NOT_PRESENT")
            self.assertTrue(diag["provider_generation_id_present"])
            self.assertFalse(diag["billable_cost_field_present"])
            self.assertIsNone(receipt["provider_reported_cost_usd"])
            self.assertNotIn("SECRET_STORY", json.dumps(receipt))
            # A generation ID is not the model prose or a bearer secret; it is
            # retained deliberately so actual billing can later be reconciled.
            self.assertEqual(receipt["provider_generation_id"],
                             "gen-sensitive-request-trace-XYZ")

    def test_http_error_status_cannot_leak_credentials_or_json(self):
        import urllib.error
        from src.story_harness_p417_live_pilot import https_post_once
        from unittest.mock import patch as monkey
        from io import BytesIO
        secret = "sk-or-offline-example-not-a-real-secret"
        http_error = urllib.error.HTTPError(
            ENDPOINT, 400,
            "SECRET_PROMPT_AND_BEARER_SHOULD_NEVER_APPEAR",
            {}, BytesIO(b"SECRET_PROVIDER_BODY"),
        )
        body = wire("SPINEFORGE", build_spine_request(self.pack))
        with monkey("urllib.request.urlopen", side_effect=http_error):
            with self.assertRaises(HarnessStop) as cm:
                https_post_once(secret, body)
        self.assertIn("HTTP_400", str(cm.exception))
        self.assertNotIn("SECRET_", str(cm.exception))
        self.assertNotIn(secret, str(cm.exception))

    def test_http400_error_hint_is_classified_without_leaking_raw_provider_message(self):
        import urllib.error
        from src.story_harness_p417_live_pilot import https_post_once
        from unittest.mock import patch as monkey
        from io import BytesIO
        body = wire("SPINEFORGE", build_spine_request(self.pack))
        key = "sk-or-FAKE-UNIT-TEST-NOT-A-CREDENTIAL"
        response = b'{"error":{"message":"SECRET_TEXT unsupported maxItems in JSON schema"}}'
        with monkey("urllib.request.urlopen",
                    side_effect=urllib.error.HTTPError(
                        ENDPOINT, 400, "RAW_SECRET_PROVIDER_HEADER",
                        {}, BytesIO(response))):
            with self.assertRaises(HarnessStop) as caught:
                https_post_once(key, body)
        self.assertEqual(caught.exception.category, "HTTP_400")
        self.assertEqual(caught.exception.hint, "SCHEMA_UNSUPPORTED_ARRAY_BOUNDS")
        self.assertNotIn("SECRET_TEXT", str(caught.exception))
        self.assertNotIn(key, str(caught.exception))

    def test_r06_immutable_full_spine_is_archived_before_writer(self):
        from src.story_harness_p416_input_bridge import sha
        with TemporaryDirectory() as td:
            pilot=BoundedOncePilot(td,case_id="B01",plan=self.plan,
                                   run_variant="r06")
            provider=FakeProvider(self.pack)
            def flat_provider(body):
                # P4.18-approved flat schema wraps the same approved scenes
                # as JSON-in-string, not a nested provider output schema.
                request=deepcopy(body)
                request["response_format"]["json_schema"]["name"]=(
                    request["response_format"]["json_schema"]["name"]
                    .replace("_flat_v2","_v1"))
                reply=provider(request)
                value=json.loads(reply["choices"][0]["message"]["content"])
                if "beats" in value:
                    value={"source_pack_sha256":value["source_pack_sha256"],
                           "spine_summary":value["spine_summary"],
                           "beats_json":json.dumps(value["beats"])}
                else:
                    value={"source_pack_sha256":value["source_pack_sha256"],
                           "spine_sha256":value["spine_sha256"],
                           "story_text":value["story_text"],
                           "beat_ids_json":json.dumps(value["beat_ids"])}
                reply["choices"][0]["message"]["content"]=json.dumps(value)
                return reply
            output=pilot.execute(transport=flat_provider)
            plan_path=pilot.dir / "spine-plan.json"
            self.assertTrue(plan_path.is_file())
            record=json.loads(plan_path.read_text())
            story=json.loads((pilot.dir / "story-draft.json").read_text())
            self.assertEqual(record["schema"],
                "lumi.story-harness-p421-real-spine-artifact.v1")
            self.assertEqual(sha(record["spine"]),record["spine_sha256"])
            self.assertEqual(record["source_pack_sha256"],self.pack["pack_sha256"])
            self.assertEqual(story["spine_sha256"],record["spine_sha256"])
            self.assertEqual(story["spine_artifact_path"],"spine-plan.json")
            self.assertFalse(record["original_semantic_quality_accepted"])
            self.assertFalse(story["quality_accepted"])
            self.assertFalse(output["quality_accepted"])

    def test_r06_failure_on_first_stage_never_creates_fake_spine(self):
        with TemporaryDirectory() as td:
            pilot=BoundedOncePilot(td,case_id="B01",plan=self.plan,
                                   run_variant="r06")
            calls=[]
            def bad(body):
                calls.append(1)
                raise TimeoutError("fake provider failure")
            with self.assertRaises(HarnessStop):
                pilot.execute(transport=bad)
            self.assertFalse((pilot.dir / "spine-plan.json").exists())
            self.assertFalse((pilot.dir / "story-draft.json").exists())
            self.assertEqual(len(calls),1)

    def test_r06_is_distinct_one_use_from_earlier_original_claims(self):
        with TemporaryDirectory() as td:
            old=BoundedOncePilot(td,case_id="B01",plan=self.plan,
                                  run_variant="r05")
            current=BoundedOncePilot(td,case_id="B01",plan=self.plan,
                                      run_variant="r06")
            self.assertNotEqual(old.dir,current.dir)
            self.assertTrue(current.use_simple_envelope)
            with self.assertRaises(FileExistsError):
                BoundedOncePilot(td,case_id="B01",plan=self.plan,
                                 run_variant="r06")

    def test_r05_new_one_use_claim_and_higher_output_finite_caps(self):
        from src.story_harness_p417_live_pilot import OUTPUT_CAPS, STAGE_MAX_USD
        self.assertEqual(OUTPUT_CAPS, {"SPINEFORGE": 5500, "WRITER": 6500})
        self.assertLessEqual(STAGE_MAX_USD["SPINEFORGE"], __import__("decimal").Decimal("0.075"))
        self.assertLessEqual(STAGE_MAX_USD["WRITER"], __import__("decimal").Decimal("0.14"))
        with TemporaryDirectory() as td:
            former = BoundedOncePilot(td, case_id="B01", plan=self.plan,
                                       run_variant="r04")
            current = BoundedOncePilot(td, case_id="B01", plan=self.plan,
                                        run_variant="r05")
            self.assertNotEqual(former.dir, current.dir)
            self.assertTrue(current.use_simple_envelope)
            self.assertEqual(
                json.loads((current.dir / "00-claim.json").read_text())["run_variant"],
                "r05")
            with self.assertRaises(FileExistsError):
                BoundedOncePilot(td, case_id="B01", plan=self.plan,
                                 run_variant="r05")

    def test_r03_is_distinct_from_existing_first_and_second_attempt_claims(self):
        with TemporaryDirectory() as td:
            one = BoundedOncePilot(td, case_id="B01", plan=self.plan)
            two = BoundedOncePilot(td, case_id="B01", plan=self.plan,
                                   run_variant="r02")
            three = BoundedOncePilot(td, case_id="B01", plan=self.plan,
                                     run_variant="r03")
            self.assertEqual(len({str(x.dir) for x in (one,two,three)}),3)
            with self.assertRaises(FileExistsError):
                BoundedOncePilot(td, case_id="B01", plan=self.plan,
                                 run_variant="r03")
            self.assertEqual(json.loads((three.dir/"00-claim.json").read_text())
                             ["run_variant"], "r03")

    def test_transport_category_recorded_without_network_retry(self):
        from src.story_harness_p417_live_pilot import ProviderTransportFault
        with TemporaryDirectory() as td:
            runner = BoundedOncePilot(td, case_id="B01", plan=self.plan)
            calls = []
            def provider_error(body):
                calls.append(1)
                raise ProviderTransportFault("HTTP_422")
            with self.assertRaisesRegex(HarnessStop, "HTTP_422"):
                runner.execute(transport=provider_error)
            receipt = json.loads((runner.dir / "01-spineforge-receipt.json").read_text())
            diag = receipt["safe_failure_diagnostic"]
            self.assertEqual(diag["safe_failure_code"], "HTTP_422")
            self.assertEqual(diag["phase"], "TRANSPORT")
            self.assertFalse(diag["provider_envelope_received"])
            self.assertEqual(calls, [1])

    def test_default_cli_never_touches_key_or_network(self):
        with patch.object(sys, "argv", ["p417", "--repo-root", str(ROOT)]),              patch.dict(os.environ, {}, clear=True):
            buff = io.StringIO()
            with redirect_stdout(buff):
                main()
            result = json.loads(buff.getvalue())
            self.assertEqual(result["real_provider_calls"], 0)


if __name__ == "__main__":
    unittest.main()
