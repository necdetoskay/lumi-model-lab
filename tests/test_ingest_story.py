import tempfile
import unittest
from pathlib import Path

from src.ingest_story import ExternalStory, build_source_record


class IngestStoryTests(unittest.TestCase):
    def make_source(self, words: int = 1000) -> ExternalStory:
        return ExternalStory.model_validate(
            {
                "id": "generated_story_test",
                "source_type": "generated_story",
                "source_model": "example/model",
                "language": "tr",
                "title": "Test Hikâyesi",
                "age_min": 6,
                "age_max": 8,
                "target_words": 1000,
                "protagonist": "Ada, meraklı bir çocuk",
                "setting": "Sessiz bir bahçe",
                "theme": ["merak", "iş birliği"],
                "premise": "Ada bahçedeki gizemi çözmeye çalışır.",
                "constraints": ["Şiddet olmasın"],
                "story": " ".join(["kelime"] * words),
                "training_eligible": True,
                "suitability": {"status": "pass", "reasons": []},
            }
        )

    def test_theme_list_is_normalized_for_story_spec(self):
        source = self.make_source()
        spec = source.to_story_spec()
        self.assertEqual(spec.theme, "merak, iş birliği")

    def test_declared_training_eligible_does_not_control_technical_gate(self):
        source = self.make_source(words=500)
        source.training_eligible = True
        with tempfile.TemporaryDirectory() as temp_dir:
            record = build_source_record(
                source,
                source_path=Path(temp_dir) / "story.yaml",
                prompt_version="generated_story_source_v1",
                min_word_ratio=0.80,
                max_word_ratio=1.20,
            )
        self.assertFalse(record.technical_validation.eligible_for_judge)
        self.assertIn("below_minimum_word_count", record.technical_validation.reasons)

    def test_valid_external_story_becomes_judge_eligible_generation_record(self):
        source = self.make_source(words=1000)
        with tempfile.TemporaryDirectory() as temp_dir:
            record = build_source_record(
                source,
                source_path=Path(temp_dir) / "story.yaml",
                prompt_version="generated_story_source_v1",
                min_word_ratio=0.80,
                max_word_ratio=1.20,
            )
        self.assertTrue(record.technical_validation.eligible_for_judge)
        self.assertEqual(record.teacher_model, "example/model")
        self.assertEqual(record.provider, "external")
        self.assertEqual(record.request["declared_training_eligible"], True)

    def test_invalid_age_range_is_rejected(self):
        source = self.make_source()
        source.age_min = 9
        source.age_max = 6
        with self.assertRaisesRegex(RuntimeError, "age_max"):
            source.to_story_spec()


if __name__ == "__main__":
    unittest.main()
