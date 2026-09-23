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
