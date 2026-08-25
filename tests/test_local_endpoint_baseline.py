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
        user_prompt = payload["messages"][1]["content"]
        self.assertIn("Ada", user_prompt)
        self.assertIn("1800", user_prompt)
        self.assertIn("Tamamlanmış son olsun", user_prompt)

    def test_extract_story_reads_openai_chat_shape(self) -> None:
        response = {"choices": [{"message": {"content": "Bir varmış bir yokmuş."}}]}
        self.assertEqual(extract_story(response), "Bir varmış bir yokmuş.")

    def test_extract_story_rejects_empty_choices(self) -> None:
        with self.assertRaises(RuntimeError):
            extract_story({"choices": []})

    def test_technical_gate_checks_target_window(self) -> None:
        passing = technical_result(words=1800, target=2000, min_ratio=0.8, max_ratio=1.2)
        failing = technical_result(words=1200, target=2000, min_ratio=0.8, max_ratio=1.2)
        self.assertTrue(passing["pass"])
        self.assertFalse(failing["pass"])


if __name__ == "__main__":
    unittest.main()
