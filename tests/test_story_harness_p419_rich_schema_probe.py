"""P4.19 exact nested schema single-use paid diagnostic, fake provider only."""
import json
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest

from src.story_harness_p419_rich_schema_probe import (
    full_rich_wire, run_once, DIR, PUBLIC_SYSTEM, PUBLIC_USER
)
from src.story_harness_v1 import HarnessStop

class P419Tests(unittest.TestCase):
    def test_exact_rich_schema_stays_unchanged_after_public_prompt_substitution(self):
        from src.story_harness_p415_benchmark import load_plan
        from src.story_harness_p416_input_bridge import compile_case, build_spine_request
        from src.story_harness_p417_live_pilot import wire
        case=load_plan(".")["cases"][0]
        expected=wire("SPINEFORGE",build_spine_request(compile_case(case)))
        actual=full_rich_wire(".")
        self.assertEqual(actual["response_format"],expected["response_format"])
        self.assertEqual(actual["provider"],expected["provider"])
        self.assertEqual(actual["model"],expected["model"])
        self.assertNotEqual(actual["messages"],expected["messages"])
        self.assertIn(PUBLIC_SYSTEM,actual["messages"][0]["content"])
        self.assertIn(PUBLIC_USER,actual["messages"][1]["content"])
        self.assertEqual(actual["max_tokens"],512)
        self.assertNotIn(case["input"]["topic"],str(actual["messages"]))

    def test_400_redacted_provider_error_is_saved_no_retries(self):
        with TemporaryDirectory() as td:
            calls=[]
            def fake(key,body):
                calls.append(body)
                return {"http_status":400,"error":{
                    "category":"PROVIDER_REJECTED",
                    "message":"schema keyword not valid",
                    "code":"invalid_request"}}
            r=run_once(repo_root=".",root=td,api_key="fake",post=fake)
            self.assertEqual(len(calls),1)
            self.assertEqual(r["http_status"],400)
            self.assertFalse(r["successful_http"])
            self.assertFalse(r["quality_accepted"])
            self.assertFalse(r["real_story_generated"])
            saved=json.loads((Path(td)/DIR/"01-provider-receipt.json").read_text())
            self.assertEqual(saved["safe_provider_error"]["message"],"schema keyword not valid")
            with self.assertRaises(FileExistsError):
                run_once(repo_root=".",root=td,api_key="fake",post=fake)
            self.assertEqual(len(calls),1)

    def test_200_is_only_format_acceptance_not_quality_acceptance(self):
        with TemporaryDirectory() as td:
            r=run_once(repo_root=".",root=td,api_key="fake",post=lambda key,body:{
                "http_status":200,"body":{
                    "model":body["model"],
                    "usage":{"cost":0.0022,"prompt_tokens":100,
                             "completion_tokens":110},
                }})
            self.assertTrue(r["successful_http"])
            self.assertTrue(r["model_identity_matches"])
            self.assertEqual(r["known_cost_usd"],"0.0022")
            self.assertFalse(r["real_story_generated"])
            self.assertFalse(r["quality_accepted"])

    def test_missing_usage_consumes_attempt_with_unknown_cost(self):
        with TemporaryDirectory() as td:
            with self.assertRaises(HarnessStop):
                run_once(repo_root=".",root=td,api_key="fake",post=lambda k,b:{
                    "http_status":200,"body":{"model":b["model"]}})
            saved=json.loads((Path(td)/DIR/"01-provider-receipt.json").read_text())
            self.assertIsNone(saved["known_cost_usd"])
            self.assertFalse(saved["retry_allowed"])

    def test_cost_above_tiny_cap_rejected(self):
        with TemporaryDirectory() as td:
            with self.assertRaises(HarnessStop):
                run_once(repo_root=".",root=td,api_key="fake",post=lambda k,b:{
                    "http_status":200,"body":{"model":b["model"],
                        "usage":{"cost":0.031,"prompt_tokens":100,
                                 "completion_tokens":30}}})
    def test_unknown_failure_consumes_no_retry(self):
        with TemporaryDirectory() as td:
            calls=[]
            def fail(k,b):
                calls.append(1)
                raise TimeoutError("uncertain billed cost")
            with self.assertRaises(HarnessStop):
                run_once(repo_root=".",root=td,api_key="fake",post=fail)
            with self.assertRaises(FileExistsError):
                run_once(repo_root=".",root=td,api_key="fake",post=fail)
            self.assertEqual(len(calls),1)

if __name__=="__main__":
    unittest.main()
