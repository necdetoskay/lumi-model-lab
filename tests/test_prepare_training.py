import unittest

from src.prepare_training import build_training_rows, has_mojibake


class PrepareTrainingTests(unittest.TestCase):
    def config(self) -> dict:
        return {
            "required_status": "ready",
            "expected_examples": 1,
            "fields": ["instruction", "input", "output"],
            "metadata_fields": ["id", "example_type", "source_story_id"],
        }

    def test_only_ready_examples_are_prepared(self) -> None:
        payload = {
            "examples": [
                {
                    "id": "ex_1",
                    "example_type": "continuation",
                    "instruction": "Hikâyeyi devam ettir.",
                    "input": "Çocuk bahçeye çıktı.",
                    "output": "Bahçede yeni bir iz fark etti.",
                    "source_story_id": "story_1",
                    "curation": {"status": "ready"},
                },
                {
                    "id": "ex_2",
                    "example_type": "continuation",
                    "instruction": "Devam et.",
                    "input": "Başlangıç",
                    "output": "Bitiş",
                    "source_story_id": "story_1",
                    "curation": {"status": "review"},
                },
            ]
        }
        rows = build_training_rows(payload, self.config())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["metadata"]["id"], "ex_1")

    def test_mojibake_is_detected(self) -> None:
        self.assertTrue(has_mojibake("hikÃ¢ye"))
        self.assertFalse(has_mojibake("hikâye ve çiçek"))

    def test_mojibake_in_training_field_fails(self) -> None:
        payload = {
            "examples": [
                {
                    "id": "ex_1",
                    "example_type": "continuation",
                    "instruction": "HikÃ¢yeyi devam ettir.",
                    "input": "Başlangıç",
                    "output": "Devam",
                    "source_story_id": "story_1",
                    "curation": {"status": "ready"},
                }
            ]
        }
        with self.assertRaises(RuntimeError):
            build_training_rows(payload, self.config())


if __name__ == "__main__":
    unittest.main()
