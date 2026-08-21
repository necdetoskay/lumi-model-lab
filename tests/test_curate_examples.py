import unittest

from src.curate_examples import apply_manual_overrides, audit_examples, summarize, validate_expected_shape


class CurateExamplesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "min_output_words": {"continuation": 5},
            "max_output_words": {"continuation": 50},
            "expected_total_examples": 2,
            "expected_source_stories": 1,
            "expected_examples_per_story": 2,
        }

    def row(self, example_id: str, output: str) -> dict:
        return {
            "id": example_id,
            "example_type": "continuation",
            "instruction": f"Continue {example_id}",
            "input": f"Context {example_id}",
            "output": output,
            "source_excerpt": "Anchor",
            "source_story_id": "story_1",
        }

    def test_exact_duplicate_output_is_rejected(self) -> None:
        rows = [self.row("a", "one two three four five"), self.row("b", "one two three four five")]
        audited = audit_examples(rows, self.config)
        self.assertEqual([row["curation"]["status"] for row in audited], ["reject", "reject"])

    def test_short_output_requires_review(self) -> None:
        audited = audit_examples([self.row("a", "too short")], self.config)
        self.assertEqual(audited[0]["curation"]["status"], "review")
        self.assertIn("output_too_short:2<5", audited[0]["curation"]["review_reasons"])

    def test_manual_repair_accept_preserves_original_output(self) -> None:
        audited = audit_examples([self.row("a", "too short")], self.config)
        repaired = apply_manual_overrides(
            audited,
            {
                "a": {
                    "action": "repair_accept",
                    "note": "Manual repair for test",
                    "output": "one two three four five six",
                }
            },
            self.config,
        )
        self.assertEqual(repaired[0]["original_output"], "too short")
        self.assertEqual(repaired[0]["output"], "one two three four five six")
        self.assertEqual(repaired[0]["curation"]["status"], "ready")
        self.assertEqual(repaired[0]["curation"]["manual_action"], "repair_accept")

    def test_expected_shape_has_no_warnings(self) -> None:
        rows = [self.row("a", "one two three four five"), self.row("b", "six seven eight nine ten")]
        summary = summarize(audit_examples(rows, self.config))
        self.assertEqual(validate_expected_shape(summary, self.config), [])


if __name__ == "__main__":
    unittest.main()
