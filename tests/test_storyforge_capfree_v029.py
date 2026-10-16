"""SERA v0.29: enforce no application output ceilings in StoryForge.

Offline network mocks exercise final normalized OpenRouter payloads and
model-profile preflight; never incur provider charges or human review.
"""
from __future__ import annotations

import ast
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

from experiments.sera.request_policy import UserOutputLimitPolicyError
from src.generate import call_openrouter
from src.storyforge.runtime import (
    _preflight_storyforge_output_policy, _structured_call,
)

ROOT = Path(__file__).resolve().parents[1]


def models():
    return {
        "planner": "qualified/planner",
        "plan_validator": "qualified/auditor",
        "writer": "qualified/writer",
        "primary_auditor": "qualified/auditor",
        "secondary_auditor": "qualified/auditor",
        "repair": "qualified/repair",
        "translator": "qualified/translator",
        "fidelity": "qualified/auditor",
    }


class OutputCapFreeStoryForgeV029Tests(unittest.TestCase):
    def test_no_numerical_output_token_ceiling_in_storyforge_runtime(self):
        source = (ROOT/"src/storyforge/runtime.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for kw in node.keywords:
                if kw.arg in (
                    "max_tokens", "max_output_tokens",
                    "max_completion_tokens", "num_predict",
                ):
                    self.assertIsInstance(kw.value, ast.Constant)
                    self.assertIsNone(kw.value.value)
        self.assertNotIn("max_tokens: int | None =", source)
        self.assertIn("_preflight_storyforge_output_policy(models)", source)

    @patch("src.generate.requests.post")
    @patch("src.generate.normalize_openrouter_request")
    def test_profile_injected_ceiling_blocks_before_network(
        self, normalized, send
    ):
        def capped(_model, payload, **_kwargs):
            return {**payload, "max_tokens": 1200}
        normalized.side_effect = capped
        with self.assertRaisesRegex(
            UserOutputLimitPolicyError,
            "USER_OUTPUT_TOKEN_LIMIT_FORBIDDEN",
        ):
            call_openrouter(
                api_key="fake", model="qualified/planner",
                system_prompt="system", user_prompt="input",
                temperature=0.0, max_tokens=None, seed=None,
                request_class="editorial_audit", structured_output=True,
                forbid_output_token_limit=True,
            )
        send.assert_not_called()

    @patch("src.generate.requests.post")
    @patch("src.generate.normalize_openrouter_request")
    def test_outbound_without_caps_is_allowed_and_unchanged(
        self, normalized, send
    ):
        normalized.side_effect=lambda _m,payload,**_:dict(payload)
        response=MagicMock()
        response.ok=True
        response.json.return_value={
            "choices":[{"message":{"content":"Hello"},
                        "finish_reason":"stop"}],
            "usage":{"prompt_tokens":1,"completion_tokens":1,
                     "total_tokens":2,"cost":0.0},
        }
        send.return_value=response
        _,_,actual=call_openrouter(
            api_key="fake", model="qualified/writer",
            system_prompt="system", user_prompt="input",
            temperature=0.7, max_tokens=None, seed=None,
            request_class="teacher_story_medium_reasoning",
            structured_output=False,
            forbid_output_token_limit=True,
        )
        self.assertNotIn("max_tokens", actual)
        self.assertNotIn("max_completion_tokens", actual)
        self.assertEqual(send.call_count,1)
        self.assertNotIn("max_tokens",send.call_args.kwargs["json"])

    @patch("src.storyforge.runtime.call_structured_json_with_retry")
    def test_storyforge_structured_stage_enables_final_outbound_guard(
        self, structured
    ):
        structured.return_value=(
            {"valid":True},
            {"usage":{"prompt_tokens":1,"completion_tokens":1,
                      "total_tokens":2,"cost":0.0}},
            {"temperature":0,"response_format":{"type":"json_object"}},
            [],
        )
        response,meta=_structured_call(
            api_key="fake",model="qualified/auditor",
            system="system",payload={"x":"test"},
            seed=1,request_class="editorial_audit",
        )
        self.assertEqual(response,{"valid":True})
        self.assertIsNone(structured.call_args.kwargs["max_tokens"])
        self.assertIs(structured.call_args.kwargs
                      ["forbid_output_token_limit"],True)
        self.assertIsNone(meta["request"]["max_tokens"])

    @patch("src.english_story_pipeline.call_openrouter")
    def test_structured_retry_forwards_explicit_cap_free_mode(self, provider):
        from src.english_story_pipeline import call_structured_json_with_retry
        provider.return_value=(
            '{"valid":true}',
            {"choices":[{"finish_reason":"stop"}],
             "usage":{"prompt_tokens":1,"completion_tokens":1,
                      "total_tokens":2,"cost":0}},
            {"model":"qualified/auditor"},
        )
        parsed,_,_,_=call_structured_json_with_retry(
            api_key="fake",model="qualified/auditor",
            system_prompt="system",user_prompt="{}",temperature=0,
            max_tokens=None,seed=None,request_class="editorial_audit",
            forbid_output_token_limit=True,
        )
        self.assertTrue(parsed["valid"])
        self.assertIsNone(provider.call_args.kwargs["max_tokens"])
        self.assertIs(provider.call_args.kwargs
                      ["forbid_output_token_limit"],True)

    @patch("src.storyforge.runtime.normalize_openrouter_request")
    def test_storyforge_preflight_rejects_profile_cap_before_other_calls(
        self, normalized
    ):
        normalized.side_effect=lambda _m,p,**_: {**p,"max_tokens":2000}
        with self.assertRaisesRegex(
            UserOutputLimitPolicyError,"USER_OUTPUT_TOKEN_LIMIT_FORBIDDEN"
        ):
            _preflight_storyforge_output_policy(models())
        self.assertEqual(normalized.call_count,1)

    @patch("src.storyforge.runtime.normalize_openrouter_request")
    def test_preflight_checks_all_eight_editorial_roles(self, normalized):
        normalized.side_effect=lambda _m,p,**_:dict(p)
        _preflight_storyforge_output_policy(models())
        self.assertEqual(normalized.call_count,8)
        args=[x.kwargs["request_class"] for x in
              normalized.call_args_list]
        self.assertIn("story_plan",args)
        self.assertIn("editorial_audit",args)
        self.assertIn("teacher_story_medium_reasoning",args)
        self.assertIn("translation",args)


if __name__=="__main__":
    unittest.main()
