from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from src.judge import call_judge
from src.model_registry import normalize_openrouter_request, require_judge_runtime_profile


class _FakeResponse:
    ok = True
    status_code = 200
    text = ""

    def json(self):
        payload = {
            "scores": {
                "instruction_following": 5,
                "coherence": 5,
                "character_consistency": 5,
                "age_appropriateness": 5,
                "creativity": 4,
                "style_quality": 5,
            },
            "reasons": {
                "instruction_following": "brief followed",
                "coherence": "coherent",
                "character_consistency": "consistent",
                "age_appropriateness": "appropriate",
                "creativity": "creative",
                "style_quality": "clear style",
            },
            "critical_failures": [],
            "summary": "Strong story.",
        }
        return {
            "id": "judge-1",
            "model": "anthropic/claude-haiku-4.5",
            "provider": "Anthropic",
            "choices": [{"message": {"content": json.dumps(payload)}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 300, "total_tokens": 1300, "cost": 0.0025},
        }


class JudgeRuntimeProfileTests(unittest.TestCase):
    def test_haiku45_exact_judge_profile(self) -> None:
        profile = require_judge_runtime_profile("anthropic/claude-haiku-4.5")
        self.assertEqual(profile["match"]["type"], "exact")
        self.assertTrue(profile["judge"]["ready"])
        payload = normalize_openrouter_request(
            "anthropic/claude-haiku-4.5",
            {
                "temperature": 0.0,
                "max_tokens": 2500,
                "reasoning": {"effort": "low"},
                "response_format": {"type": "json_object"},
            },
            request_class="judge",
            structured_output=True,
        )
        self.assertEqual(payload["reasoning"], {"effort": "none", "exclude": True})
        self.assertEqual(payload["temperature"], 0.0)
        self.assertEqual(payload["max_tokens"], 2500)
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertNotIn("seed", payload)
        self.assertNotIn("stream", payload)

    def test_unprofiled_model_is_blocked_as_judge(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "MODEL_JUDGE_RUNTIME_PROFILE_MISSING"):
            require_judge_runtime_profile("vendor/unverified-judge")

    @patch("src.judge.requests.post")
    def test_call_judge_normalizes_through_haiku_profile(self, mock_post) -> None:
        mock_post.return_value = _FakeResponse()
        result, _ = call_judge(
            api_key="test-key",
            model="anthropic/claude-haiku-4.5",
            system_prompt="system",
            user_prompt="story",
            temperature=0.0,
            max_tokens=2500,
            reasoning={"effort": "low", "exclude": True},
            response_format={"type": "json_object"},
        )
        self.assertEqual(result.scores["coherence"], 5)
        _, kwargs = mock_post.call_args
        sent = kwargs["json"]
        self.assertEqual(sent["reasoning"], {"effort": "none", "exclude": True})
        self.assertEqual(sent["response_format"], {"type": "json_object"})
        self.assertEqual(sent["max_tokens"], 2500)


if __name__ == "__main__":
    unittest.main()
