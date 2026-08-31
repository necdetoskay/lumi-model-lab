import unittest

from src.generate import build_model_options, validate_generation
from src.schemas import StorySpec


class GenerationValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = StorySpec(
            age_min=6,
            age_max=8,
            language="tr",
            target_words=300,
            protagonist="Mira",
            setting="Kuzey Ormanı",
            theme="merak",
            premise="Bir ışığın kaynağını araştırır.",
        )

    def test_complete_story_is_eligible_for_judge(self) -> None:
        story = "kelime " * 300
        result = validate_generation(
            story=story,
            spec=self.spec,
            finish_reason="stop",
            min_word_ratio=0.8,
            max_word_ratio=1.2,
        )
        self.assertTrue(result.eligible_for_judge)
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.reasons, [])

    def test_length_finish_is_incomplete_even_when_word_count_matches(self) -> None:
        story = "kelime " * 300
        result = validate_generation(
            story=story,
            spec=self.spec,
            finish_reason="length",
            min_word_ratio=0.8,
            max_word_ratio=1.2,
        )
        self.assertFalse(result.eligible_for_judge)
        self.assertIn("model_hit_output_token_limit", result.reasons)

    def test_short_story_is_incomplete(self) -> None:
        story = "kelime " * 150
        result = validate_generation(
            story=story,
            spec=self.spec,
            finish_reason="stop",
            min_word_ratio=0.8,
            max_word_ratio=1.2,
        )
        self.assertFalse(result.eligible_for_judge)
        self.assertIn("below_minimum_word_count", result.reasons)

    def test_gemini_37_flash_keeps_reasoning_enabled(self) -> None:
        options = build_model_options("google/gemini-3.7-flash", 42)
        self.assertTrue(options["reasoning"]["enabled"])
        self.assertEqual(options["reasoning"]["effort"], "low")
        self.assertTrue(options["reasoning"]["exclude"])
        self.assertEqual(options["seed"], 42)


if __name__ == "__main__":
    unittest.main()
