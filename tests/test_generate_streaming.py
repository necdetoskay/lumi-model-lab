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
        self.assertNotIn("max_tokens", payload)
        self.assertNotIn("temperature", payload)
        self.assertNotIn("seed", payload)
        _, kwargs = mock_post.call_args
        self.assertTrue(kwargs["stream"])

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
