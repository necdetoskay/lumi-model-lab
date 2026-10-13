"""P4.18 tiny public-prompt compatibility: mock only, no paid API."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from src.story_harness_p418_compat_probe import (
    MODEL, PROMPT, build_wire, safe_error_hint, run_probe, status,
)
from src.story_harness_v1 import HarnessStop


def reply(cost="0.002"):
    return {"http_status":200,"body":{
        "id":"gen-TESTCOMPAT12345",
        "model":MODEL,
        "choices":[{"message":{"content":'{"ok":true}'},"finish_reason":"stop"}],
        "usage":{"prompt_tokens":70,"completion_tokens":25,"cost":cost},
    }}


class P418Tests(unittest.TestCase):
    def test_default_status_makes_no_calls(self):
        s=status()
        self.assertEqual(s["provider_calls"],0)
        self.assertTrue(s["paid_run_disabled_by_default"])

    def test_first_wire_is_minimal_and_no_fallback(self):
        req=build_wire("BASE_CHAT")
        self.assertEqual(req["model"],MODEL)
        self.assertNotIn("response_format",req)
        self.assertFalse(req["provider"]["allow_fallbacks"])
        self.assertEqual(req["provider"]["only"],["Anthropic"])
        self.assertEqual(req["max_tokens"],512)
        self.assertEqual(req["messages"][0]["content"],PROMPT)
        self.assertNotIn("temperature",req)

    def test_second_wire_adds_only_strict_schema_and_requirement(self):
        a=build_wire("BASE_CHAT")
        b=build_wire("STRICT_JSON")
        self.assertEqual(b["response_format"]["type"],"json_schema")
        self.assertTrue(b["response_format"]["json_schema"]["strict"])
        self.assertTrue(b["provider"]["require_parameters"])
        self.assertNotIn("require_parameters",a["provider"])
        b.pop("response_format")
        b["provider"].pop("require_parameters")
        self.assertEqual(a,b)

    def test_safe_http400_message_is_sanitized(self):
        e=safe_error_hint(b'{"error":{"code":"invalid_request","message":"Schema minItems: 4 not supported"}}')
        self.assertEqual(e["category"],"PROVIDER_REJECTED")
        self.assertIn("minItems",e["message"])
        self.assertEqual(e["code"],"invalid_request")

    def test_secret_echo_is_not_persisted(self):
        e=safe_error_hint(b'{"error":{"message":"Header Authorization: Bearer sk-or-EXAMPLE"}}')
        self.assertEqual(e["category"],"SENSITIVE_ERROR_REDACTED")
        self.assertEqual(e["message"],"REDACTED")

    def test_fake_two_stages_pass_and_is_not_story_accepted(self):
        with TemporaryDirectory() as td:
            calls=[]
            def post(key,body):
                calls.append(body)
                return reply()
            out=run_probe(td,"fake",post=post)
            self.assertEqual(len(calls),2)
            self.assertTrue(out["two_stage_wire_compatible"])
            self.assertEqual(out["known_provider_billed_cost_usd"],"0.004")
            self.assertFalse(out["quality_accepted"])
            self.assertFalse(out["production_state_write_authorized"])
            self.assertTrue((Path(td)/"p418-sonnet55-compat-v01"/"result.json").exists())

    def test_http400_at_first_step_stops_without_second_request(self):
        with TemporaryDirectory() as td:
            calls=[]
            def fail(key,body):
                calls.append(1)
                return {"http_status":400,"error":{"category":"PROVIDER_REJECTED",
                    "message":"provider rejected tiny public prompt","code":"bad_request"}}
            r=run_probe(td,"fake",post=fail)
            self.assertFalse(r["two_stage_wire_compatible"])
            self.assertEqual(len(calls),1)
            self.assertIsNone(r["stage_results"][0]["billed_cost_usd"])

    def test_http400_only_after_strict_schema_isolated(self):
        with TemporaryDirectory() as td:
            calls=[]
            def post(key,body):
                calls.append(body)
                if len(calls)==1:
                    return reply()
                return {"http_status":400,"error":{"category":"PROVIDER_REJECTED",
                    "message":"strict schema malformed","code":None}}
            r=run_probe(td,"fake",post=post)
            self.assertEqual(len(calls),2)
            self.assertEqual(r["stage_results"][0]["http_status"],200)
            self.assertEqual(r["stage_results"][1]["http_status"],400)
            self.assertFalse(r["two_stage_wire_compatible"])

    def test_no_run_id_reuse_even_if_http400(self):
        with TemporaryDirectory() as td:
            run_probe(td,"fake",post=lambda key,body:{
                "http_status":400,"error":{"category":"PROVIDER_REJECTED",
                                            "message":"blocked"}})
            with self.assertRaises(FileExistsError):
                run_probe(td,"fake",post=lambda key,body:reply())

    def test_missing_usage_cost_stops_and_consumes(self):
        with TemporaryDirectory() as td:
            r=reply()
            del r["body"]["usage"]["cost"]
            with self.assertRaises(HarnessStop):
                run_probe(td,"fake",post=lambda key,body:r)
            path=Path(td)/"p418-sonnet55-compat-v01"/"01-base_chat-receipt.json"
            self.assertEqual(json.loads(path.read_text())["outcome"],"UNKNOWN_CONSUMED")

    def test_stage_cost_ceiling_enforced(self):
        with TemporaryDirectory() as td:
            with self.assertRaises(HarnessStop):
                run_probe(td,"fake",post=lambda key,body:reply(cost="0.031"))

    def test_provider_model_mismatch_never_calls_second_stage(self):
        with TemporaryDirectory() as td:
            calls=[]
            def wrong(key,body):
                calls.append(1)
                result=reply()
                result["body"]["model"]="wrong-model"
                return result
            with self.assertRaises(HarnessStop):
                run_probe(td,"fake",post=wrong)
            self.assertEqual(len(calls),1)


if __name__=="__main__":
    unittest.main()
