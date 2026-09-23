import unittest

from src.generate import _aggregate_openrouter_stream, build_model_options


class _FakeStreamResponse:
    def __init__(self, lines):
        self._lines = lines

    def iter_lines(self, decode_unicode=True):
        del decode_unicode
        yield from self._lines


class OpenRouterStreamingTests(unittest.TestCase):
    def test_qwen38_teacher_story_profile_disables_reasoning_and_streams(self) -> None:
        options = build_model_options("qwen/qwen3.8-flash", 42)
        self.assertEqual(
            options,
            {
                "seed": 42,
                "reasoning": {"effort": "none", "exclude": True},
                "stream": True,
            },
        )

    def test_stream_aggregates_content_finish_reason_and_final_usage(self) -> None:
        response = _FakeStreamResponse(
            [
                'data: {"id":"gen-1","model":"qwen/qwen3.8-flash","provider":"Alibaba","choices":[{"delta":{"content":"Bir "},"finish_reason":null}]}',
                'data: {"id":"gen-1","model":"qwen/qwen3.8-flash","choices":[{"delta":{"content":"hikaye."},"finish_reason":"stop"}]}',
                'data: {"id":"gen-1","model":"qwen/qwen3.8-flash","choices":[],"usage":{"prompt_tokens":100,"completion_tokens":30,"total_tokens":130,"completion_tokens_details":{"reasoning_tokens":20},"cost":0.0001}}',
                'data: [DONE]',
            ]
        )
        body = _aggregate_openrouter_stream(response, "qwen/qwen3.8-flash")
        self.assertEqual(body["choices"][0]["message"]["content"], "Bir hikaye.")
        self.assertEqual(body["choices"][0]["finish_reason"], "stop")
        self.assertEqual(body["usage"]["completion_tokens"], 30)
        self.assertEqual(body["usage"]["completion_tokens_details"]["reasoning_tokens"], 20)
        self.assertEqual(body["provider"], "Alibaba")

    def test_stream_rejects_provider_error_chunk(self) -> None:
        response = _FakeStreamResponse(
            ['data: {"error":{"message":"provider failed"}}']
        )
        with self.assertRaisesRegex(RuntimeError, "OpenRouter streaming error"):
            _aggregate_openrouter_stream(response, "qwen/qwen3.8-flash")


if __name__ == "__main__":
    unittest.main()
