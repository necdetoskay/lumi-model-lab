from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from src.generate import call_openrouter


class FakeStreamingResponse:
    ok = True
    status_code = 200

    def __init__(self, chunks: list[dict | str]):
        self._chunks = chunks
        self.text = ""

    def iter_lines(self, decode_unicode: bool = False):
        for chunk in self._chunks:
            if chunk == "[DONE]":
                yield "data: [DONE]"
            else:
                yield "data: " + json.dumps(chunk)

    def json(self):
        raise AssertionError("streaming response must not call response.json()")




class FakeJsonSuccessResponse:
    ok = True
    status_code = 200
    text = ""
    headers = {}

    def __init__(self, body: dict):
        self._body = body

    def json(self):
        return self._body


class FakeErrorResponse:
    ok = False

    def __init__(
        self,
        status_code: int,
        body: dict,
        *,
        retry_after: str | None = None,
    ):
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body)
        self.headers = {}
        if retry_after is not None:
            self.headers["Retry-After"] = retry_after

    def json(self):
        return self._body


class GenerateStreamingTests(unittest.TestCase):
    @patch("src.generate.requests.post")
    def test_qwen_stream_aggregates_content_and_final_usage(self, mock_post) -> None:
        mock_post.return_value = FakeStreamingResponse(
            [
                {
                    "id": "gen-1",
                    "model": "qwen/qwen3.8-flash",
                    "provider": "Alibaba Cloud Int.",
                    "choices": [{"delta": {"reasoning": "thinking"}, "finish_reason": None}],
                },
                {
                    "id": "gen-1",
                    "model": "qwen/qwen3.8-flash",
                    "choices": [{"delta": {"content": "Bir varmış "}, "finish_reason": None}],
                },
                {
                    "id": "gen-1",
                    "model": "qwen/qwen3.8-flash",
                    "choices": [{"delta": {"content": "bir yokmuş."}, "finish_reason": "stop"}],
                },
                {
                    "id": "gen-1",
                    "model": "qwen/qwen3.8-flash",
                    "choices": [],
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 250,
                        "total_tokens": 350,
                        "completion_tokens_details": {"reasoning_tokens": 120},
                        "cost": 0.0002,
                    },
                },
                "[DONE]",
            ]
        )

        story, body, payload = call_openrouter(
            api_key="test-key",
            model="qwen/qwen3.8-flash",
            system_prompt="system",
            user_prompt="user",
            temperature=0.8,
            max_tokens=7000,
            seed=42,
        )

        self.assertEqual(story, "Bir varmış bir yokmuş.")
        self.assertEqual(body["choices"][0]["finish_reason"], "stop")
        self.assertEqual(body["usage"]["completion_tokens_details"]["reasoning_tokens"], 120)
        self.assertTrue(payload["stream"])
        self.assertNotIn("usage", payload)
        self.assertNotIn("stream_options", payload)
        self.assertEqual(payload["max_tokens"], 7000)
        self.assertEqual(payload["temperature"], 0.8)
        self.assertEqual(payload["seed"], 42)
        self.assertEqual(payload["reasoning"], {"effort": "none", "exclude": True})
        _, kwargs = mock_post.call_args
        self.assertTrue(kwargs["stream"])

    @patch("src.generate.time.sleep")
    @patch("src.generate.requests.post")
    def test_transient_429_retries_then_succeeds(
        self,
        mock_post,
        mock_sleep,
    ) -> None:
        success = FakeJsonSuccessResponse(
            {
                "id": "gen-retry",
                "model": "qwen/qwen3.8-flash",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Recovered.",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 2,
                    "total_tokens": 12,
                },
            }
        )
        mock_post.side_effect = [
            FakeErrorResponse(
                429,
                {"error": {"message": "temporarily rate-limited upstream"}},
                retry_after="0.25",
            ),
            success,
        ]

        story, _, _ = call_openrouter(
            api_key="test-key",
            model="qwen/qwen3.8-flash",
            system_prompt="system",
            user_prompt="user",
            temperature=0.8,
            max_tokens=None,
            seed=42,
            request_class="scene_story",
            structured_output=True,
        )

        self.assertEqual(story, "Recovered.")
        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_once_with(0.25)

    @patch("src.generate.time.sleep")
    @patch("src.generate.requests.post")
    def test_transient_520_retries_then_succeeds(
        self,
        mock_post,
        mock_sleep,
    ) -> None:
        success = FakeJsonSuccessResponse(
            {
                "id": "gen-520",
                "model": "qwen/qwen3.8-flash",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Recovered from gateway error.",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 4,
                    "total_tokens": 14,
                },
            }
        )
        mock_post.side_effect = [
            FakeErrorResponse(
                520,
                {"error": {"message": "temporary gateway error"}},
            ),
            success,
        ]

        story, _, _ = call_openrouter(
            api_key="test-key",
            model="qwen/qwen3.8-flash",
            system_prompt="system",
            user_prompt="user",
            temperature=0.8,
            max_tokens=None,
            seed=42,
            request_class="scene_story",
            structured_output=True,
        )

        self.assertEqual(story, "Recovered from gateway error.")
        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_once_with(2.0)

    @patch("src.generate.time.sleep")
    @patch("src.generate.requests.post")
    def test_non_transient_400_fails_without_retry(
        self,
        mock_post,
        mock_sleep,
    ) -> None:
        mock_post.return_value = FakeErrorResponse(
            400,
            {"error": {"message": "bad request"}},
        )

        with self.assertRaisesRegex(RuntimeError, "OpenRouter HTTP 400"):
            call_openrouter(
                api_key="test-key",
                model="qwen/qwen3.8-flash",
                system_prompt="system",
                user_prompt="user",
                temperature=0.8,
                max_tokens=None,
                seed=42,
                request_class="scene_story",
                structured_output=True,
            )

        self.assertEqual(mock_post.call_count, 1)
        mock_sleep.assert_not_called()

    @patch("src.generate.requests.post")
    def test_qwen_stream_without_visible_content_fails_with_usage_diagnostics(self, mock_post) -> None:
        mock_post.return_value = FakeStreamingResponse(
            [
                {
                    "id": "gen-2",
                    "model": "qwen/qwen3.8-flash",
                    "choices": [{"delta": {"reasoning": "thinking"}, "finish_reason": "length"}],
                    "usage": {
                        "completion_tokens": 12000,
                        "completion_tokens_details": {"reasoning_tokens": 12000},
                    },
                },
                "[DONE]",
            ]
        )

        with self.assertRaisesRegex(RuntimeError, "reasoning_tokens=12000"):
            call_openrouter(
                api_key="test-key",
                model="qwen/qwen3.8-flash",
                system_prompt="system",
                user_prompt="user",
                temperature=0.8,
                max_tokens=7000,
                seed=42,
            )


if __name__ == "__main__":
    unittest.main()
