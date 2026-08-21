import unittest

from src.extract_examples import accepted_source_entries, validate_derived_examples


class ExtractExamplesTests(unittest.TestCase):
    def test_only_accepted_source_entries_are_selected(self) -> None:
        manifest = {
            "entries": [
                {
                    "story_id": "story_1",
                    "generation_status": "complete",
                    "technical_pass": True,
                    "judge_status": "complete",
                    "judge_accepted": True,
                },
                {
                    "story_id": "story_2",
                    "generation_status": "complete",
                    "technical_pass": True,
                    "judge_status": "complete",
                    "judge_accepted": False,
                },
            ]
        }
        selected = accepted_source_entries(manifest)
        self.assertEqual([row["story_id"] for row in selected], ["story_1"])

    def test_validates_exact_example_type_counts(self) -> None:
        counts = {"continuation": 2, "ending_generation": 1}
        payload = {
            "examples": [
                {
                    "example_type": "continuation",
                    "instruction": "Continue.",
                    "input": "Context A",
                    "output": "Output A",
                    "source_excerpt": "Anchor A",
                },
                {
                    "example_type": "continuation",
                    "instruction": "Continue again.",
                    "input": "Context B",
                    "output": "Output B",
                    "source_excerpt": "Anchor B",
                },
                {
                    "example_type": "ending_generation",
                    "instruction": "Write the ending.",
                    "input": "Context C",
                    "output": "Output C",
                    "source_excerpt": "Anchor C",
                },
            ]
        }
        rows = validate_derived_examples(payload, counts)
        self.assertEqual(len(rows), 3)

    def test_rejects_wrong_example_type_counts(self) -> None:
        counts = {"continuation": 2}
        payload = {
            "examples": [
                {
                    "example_type": "continuation",
                    "instruction": "Continue.",
                    "input": "Context",
                    "output": "Output",
                    "source_excerpt": "Anchor",
                }
            ]
        }
        with self.assertRaises(RuntimeError):
            validate_derived_examples(payload, counts)


if __name__ == "__main__":
    unittest.main()
