from __future__ import annotations

import unittest
from unittest.mock import patch

from src.openrouter_jev import (
    call_openrouter_jev,
    choice_question,
    choice_value,
    load_jev_profile,
    noul_probability,
    noul_question,
)


class _FakeResponse:
    ok = True
    status_code = 200
    text = ""

    def json(self):
        return {
            "answers": {
                "causal": {"type": "noul", "noul": 0.97},
                "next_action": {
                    "type": "choice",
                    "choice": "CONTINUE",
                    "confidence": 0.94,
                    "probabilities": {
                        "CONTINUE": 0.94,
                        "TARGETED_REPAIR": 0.04,
                        "ESCALATE": 0.02,
                    },
                },
            },
            "model": "typesafe/jev-1.13-20260917",
            "provider": "TypeSafe",
            "usage": {"cost": 0.00001, "inputTokens": 300, "outputTokens": 20},
        }



class _FakeErrorResponse:
    ok = False
    text = ""

    def __init__(self, status_code: int, body: dict, retry_after: str | None = None):
        self.status_code = status_code
        self._body = body
        self.headers = {}
        if retry_after is not None:
            self.headers["Retry-After"] = retry_after

    def json(self):
        return self._body

class OpenRouterJevTests(unittest.TestCase):
    def test_profile_is_exact_versioned_openrouter_model(self):
        profile = load_jev_profile()
        self.assertEqual(profile.model_id, "typesafe/jev-1.13")
        self.assertEqual(
            profile.endpoint,
            "https://openrouter.ai/api/alpha/decisions",
        )
        self.assertEqual(profile.mode, "advisory_repair")

    def test_question_shapes_match_decisions_api(self):
        self.assertEqual(
            noul_question(
                "Is the plan causal?",
                true_criteria="Scenes form one chain.",
                false_criteria="Scenes are disconnected.",
            )["type"],
            "noul",
        )
        self.assertEqual(
            choice_question(
                "Choose next action.",
                {
                    "CONTINUE": "Safe.",
                    "TARGETED_REPAIR": "Local repair.",
                    "ESCALATE": "Needs strong judge.",
                },
            )["type"],
            "choice",
        )

    @patch("src.openrouter_jev.time.sleep")
    @patch("src.openrouter_jev.requests.post")
    def test_transient_429_retries_then_succeeds(self, mock_post, mock_sleep):
        mock_post.side_effect = [
            _FakeErrorResponse(
                429,
                {"error": {"message": "temporarily rate-limited upstream"}},
                retry_after="0.5",
            ),
            _FakeResponse(),
        ]
        body = call_openrouter_jev(
            api_key="test",
            state={"description": "English story plan", "plan": {}},
            questions={
                "causal": noul_question(
                    "Is the plan causal?",
                    true_criteria="Yes.",
                    false_criteria="No.",
                ),
                "next_action": choice_question(
                    "Choose next action.",
                    {
                        "CONTINUE": "Safe.",
                        "TARGETED_REPAIR": "Repair.",
                        "ESCALATE": "Escalate.",
                    },
                ),
            },
        )
        self.assertIn("answers", body)
        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_once_with(0.5)

    @patch("src.openrouter_jev.time.sleep")
    @patch("src.openrouter_jev.requests.post")
    def test_429_without_retry_after_uses_longer_backoff(
        self,
        mock_post,
        mock_sleep,
    ):
        mock_post.side_effect = [
            _FakeErrorResponse(
                429,
                {"error": {"message": "temporarily rate-limited upstream"}},
            ),
            _FakeResponse(),
        ]
        body = call_openrouter_jev(
            api_key="test",
            state={"description": "English story plan", "plan": {}},
            questions={
                "causal": noul_question(
                    "Is the plan causal?",
                    true_criteria="Yes.",
                    false_criteria="No.",
                ),
                "next_action": choice_question(
                    "Choose next action.",
                    {
                        "CONTINUE": "Safe.",
                        "TARGETED_REPAIR": "Repair.",
                        "ESCALATE": "Escalate.",
                    },
                ),
            },
        )
        self.assertIn("answers", body)
        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_once_with(5.0)

    @patch("src.openrouter_jev.time.sleep")
    @patch("src.openrouter_jev.requests.post")
    def test_transient_520_retries_then_succeeds(self, mock_post, mock_sleep):
        mock_post.side_effect = [
            _FakeErrorResponse(
                520,
                {"error": {"message": "temporary gateway error"}},
            ),
            _FakeResponse(),
        ]
        body = call_openrouter_jev(
            api_key="test",
            state={"description": "English story plan", "plan": {}},
            questions={
                "causal": noul_question(
                    "Is the plan causal?",
                    true_criteria="Yes.",
                    false_criteria="No.",
                ),
                "next_action": choice_question(
                    "Choose next action.",
                    {
                        "CONTINUE": "Safe.",
                        "TARGETED_REPAIR": "Repair.",
                        "ESCALATE": "Escalate.",
                    },
                ),
            },
        )
        self.assertIn("answers", body)
        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_once_with(2.0)

    @patch("src.openrouter_jev.time.sleep")
    @patch("src.openrouter_jev.requests.post")
    def test_non_transient_400_fails_without_retry(self, mock_post, mock_sleep):
        mock_post.return_value = _FakeErrorResponse(
            400,
            {"error": {"message": "bad request"}},
        )
        with self.assertRaisesRegex(RuntimeError, "OpenRouter JEV HTTP 400"):
            call_openrouter_jev(
                api_key="test",
                state={"description": "English story plan", "plan": {}},
                questions={
                    "causal": noul_question(
                        "Is the plan causal?",
                        true_criteria="Yes.",
                        false_criteria="No.",
                    ),
                    "next_action": choice_question(
                        "Choose next action.",
                        {
                            "CONTINUE": "Safe.",
                            "TARGETED_REPAIR": "Repair.",
                            "ESCALATE": "Escalate.",
                        },
                    ),
                },
            )
        self.assertEqual(mock_post.call_count, 1)
        mock_sleep.assert_not_called()

    @patch("src.openrouter_jev.requests.post")
    def test_call_uses_openrouter_decisions_api(self, mock_post):
        mock_post.return_value = _FakeResponse()
        body = call_openrouter_jev(
            api_key="test",
            state={"description": "English story plan", "plan": {}},
            questions={
                "causal": noul_question(
                    "Is the plan causal?",
                    true_criteria="Yes.",
                    false_criteria="No.",
                ),
                "next_action": choice_question(
                    "Choose next action.",
                    {
                        "CONTINUE": "Safe.",
                        "TARGETED_REPAIR": "Repair.",
                        "ESCALATE": "Escalate.",
                    },
                ),
            },
        )
        url = mock_post.call_args.args[0]
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(url, "https://openrouter.ai/api/alpha/decisions")
        self.assertEqual(payload["model"], "typesafe/jev-1.13")
        self.assertEqual(noul_probability(body["answers"]["causal"]), 0.97)
        self.assertEqual(
            choice_value(body["answers"]["next_action"]),
            ("CONTINUE", 0.94),
        )


if __name__ == "__main__":
    unittest.main()
