import unittest

from src.local_endpoint_baseline import build_payload, extract_story, technical_result


class LocalEndpointBaselineTests(unittest.TestCase):
    def test_payload_preserves_story_constraints(self) -> None:
        config = {
            "model": "ornith-ai/Ornith-1.5-9B",
            "max_tokens": 4200,
            "seed": 42,
            "generation": {"temperature": 0.0, "top_p": 1.0},
        }
        spec = {
            "title_hint": "Rüzgâr Bahçesi",
            "age_min": 6,
            "age_max": 8,
            "language": "tr",
            "target_words": 1800,
            "protagonist": "Ada",
            "setting": "uçan bahçe",
            "theme": "merak",
            "premise": "Ada kaybolan rüzgârı arar.",
            "constraints": ["Korkutucu içerik olmasın", "Tamamlanmış son olsun"],
        }

        payload = build_payload(config, spec)

        self.assertEqual(payload["model"], "ornith-ai/Ornith-1.5-9B")
        self.assertEqual(payload["max_tokens"], 4200)
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["chat_template_kwargs"], {"enable_thinking": False})
        user_prompt = payload["messages"][1]["content"]
        self.assertIn("Ada", user_prompt)
        self.assertIn("1800", user_prompt)
        self.assertIn("Tamamlanmış son olsun", user_prompt)

    def test_payload_can_leave_thinking_enabled_when_explicitly_requested(self) -> None:
        config = {
            "model": "ornith-ai/Ornith-1.5-9B",
            "disable_thinking": False,
        }
        payload = build_payload(config, {})
        self.assertNotIn("chat_template_kwargs", payload)

    def test_extract_story_reads_openai_chat_shape(self) -> None:
        response = {"choices": [{"message": {"content": "Bir varmış bir yokmuş."}}]}
        self.assertEqual(extract_story(response), "Bir varmış bir yokmuş.")

    def test_extract_story_reads_llamacpp_reasoning_fallback(self) -> None:
        response = {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "reasoning_content": "Ada rüzgârın peşinden gitti.",
                    }
                }
            ]
        }
        self.assertEqual(extract_story(response), "Ada rüzgârın peşinden gitti.")

    def test_extract_story_rejects_empty_choices(self) -> None:
        with self.assertRaises(RuntimeError):
            extract_story({"choices": []})

    def test_extract_story_reports_message_shape_when_text_is_missing(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "message_keys"):
            extract_story({"choices": [{"message": {"role": "assistant"}}]})

    def test_technical_gate_checks_target_window(self) -> None:
        passing = technical_result(words=1800, target=2000, min_ratio=0.8, max_ratio=1.2)
        failing = technical_result(words=1200, target=2000, min_ratio=0.8, max_ratio=1.2)
        self.assertTrue(passing["pass"])
        self.assertFalse(failing["pass"])


if __name__ == "__main__":
    unittest.main()
