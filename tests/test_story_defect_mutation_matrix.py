import unittest

from src.story_defect_mutation_matrix import (
    expected_case_count,
    load_mutation_matrix,
    matrix_summary,
    mutation_recipes,
    validate_mutation_matrix,
)


class StoryDefectMutationMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = load_mutation_matrix()

    def test_matrix_is_frozen_before_detector_threshold_selection(self):
        self.assertEqual(self.matrix["status"], "FROZEN_BEFORE_D2")
        self.assertTrue(
            self.matrix["split_policy"]["held_out_mutations_never_used_for_threshold_selection"]
        )

    def test_matrix_has_15_corrupt_and_4_benign_recipes_per_source(self):
        self.assertEqual(len(mutation_recipes(self.matrix)), 15)
        self.assertEqual(
            len(self.matrix["benign_hard_negative_recipes"]),
            4,
        )
        self.assertEqual(self.matrix["cases_per_source"]["total"], 20)

    def test_expected_corpus_size_is_280_cases(self):
        self.assertEqual(expected_case_count(matrix=self.matrix), 280)

    def test_critical_focus_families_are_oversampled(self):
        summary = matrix_summary(self.matrix)
        self.assertGreaterEqual(
            summary["family_recipe_counts"]["physical_feasibility"], 3
        )
        self.assertGreaterEqual(
            summary["family_recipe_counts"]["causal_logic"], 3
        )
        self.assertGreaterEqual(
            summary["family_recipe_counts"]["state_continuity"], 3
        )

    def test_matrix_contains_critical_cases_and_difficulty_mix(self):
        summary = matrix_summary(self.matrix)
        self.assertGreater(summary["severity_recipe_counts"].get("critical", 0), 0)
        self.assertGreater(summary["difficulty_recipe_counts"].get("subtle", 0), 0)
        self.assertGreater(summary["difficulty_recipe_counts"].get("medium", 0), 0)

    def test_matrix_contract_is_self_consistent(self):
        self.assertEqual(validate_mutation_matrix(self.matrix), [])


if __name__ == "__main__":
    unittest.main()
