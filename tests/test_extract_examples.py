import unittest

from src.extract_examples import (
    accepted_source_entries,
    extract_first_json_object,
    plan_extraction_chunks,
    validate_derived_examples,
)


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

    def test_plans_small_extraction_chunks(self) -> None:
        counts = {
            "continuation": 2,
            "character_dialogue": 2,
            "scene_expansion": 2,
            "conflict_resolution": 1,
            "ending_generation": 1,
            "plan_to_prose": 2,
        }
        chunks = plan_extraction_chunks(counts, 4)
        self.assertEqual([sum(chunk.values()) for chunk in chunks], [4, 4, 2])
        combined = {key: 0 for key in counts}
        for chunk in chunks:
            for key, value in chunk.items():
                combined[key] += value
        self.assertEqual(combined, counts)

    def test_extracts_first_json_object_when_trailing_data_exists(self) -> None:
        text = '```json\n{"examples": []}\n```\n{"unexpected": true}'
        parsed = extract_first_json_object(text)
        self.assertEqual(parsed, {"examples": []})


if __name__ == "__main__":
    unittest.main()
