import unittest

from src.judge_local_endpoint import build_local_judge_input


class JudgeLocalEndpointTests(unittest.TestCase):
    def test_build_input_includes_brief_story_and_technical_context(self) -> None:
        local_record = {
            "story": "Ada sisli bahçede küçük bir ipucu buldu.",
            "technical": {"word_count": 915, "pass": False},
        }
        spec = {
            "language": "tr",
            "age_min": 6,
            "age_max": 8,
            "target_words": 1800,
            "title_hint": "Rüzgâr Bahçesi",
            "protagonist": "Ada",
            "setting": "sisli bahçe",
            "theme": "merak",
            "premise": "Ada kaybolan rüzgârı arar.",
            "constraints": ["Korkutucu içerik olmasın"],
        }

        prompt = build_local_judge_input(local_record, spec)

        self.assertIn("Ada", prompt)
        self.assertIn("915", prompt)
        self.assertIn("False", prompt)
        self.assertIn("Korkutucu içerik olmasın", prompt)
        self.assertIn(local_record["story"], prompt)


if __name__ == "__main__":
    unittest.main()
