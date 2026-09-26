import unittest

from src.story_publication_acceptance import (
    length_observation,
    load_profile,
    publication_ready,
)


V1_PATH = "configs/story_acceptance_profiles/tr_age4.v1.json"
V2_PATH = "configs/story_acceptance_profiles/tr_age4.v2.candidate.json"


class StoryPublicationAcceptanceV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.v1 = load_profile(V1_PATH)
        cls.v2 = load_profile(V2_PATH)

    def test_v2_preserves_generation_target_500_as_soft(self) -> None:
        policy = self.v2["generation_length_policy"]
        self.assertEqual(policy["target_words"], 500)
        self.assertEqual(policy["target_mode"], "soft")

    def test_v2_removes_hard_length_failure_from_blocking_classes(self) -> None:
        self.assertIn("hard_length_failure", self.v1["hard_fail_classes"])
        self.assertNotIn("hard_length_failure", self.v2["hard_fail_classes"])

    def test_v2_preserves_all_non_length_hard_fail_classes(self) -> None:
        expected = set(self.v1["hard_fail_classes"]) - {"hard_length_failure"}
        self.assertEqual(set(self.v2["hard_fail_classes"]), expected)

    def test_v1_short_story_still_blocks_under_frozen_semantics(self) -> None:
        observation = length_observation(self.v1, 333)
        self.assertTrue(observation["outside_reference_range"])
        self.assertTrue(observation["blocking"])
        self.assertEqual(observation["class"], "hard_length_failure")

    def test_v2_short_quality_story_is_only_length_deviation(self) -> None:
        for words in (287, 292, 313, 329, 333, 340, 365, 370):
            with self.subTest(words=words):
                observation = length_observation(self.v2, words)
                self.assertTrue(observation["outside_reference_range"])
                self.assertFalse(observation["blocking"])
                self.assertEqual(observation["class"], "length_deviation")

    def test_v2_length_deviation_alone_can_publish(self) -> None:
        self.assertTrue(publication_ready(self.v2, 287, []))
        self.assertTrue(publication_ready(self.v2, 700, []))

    def test_v2_serious_existing_quality_class_still_blocks(self) -> None:
        self.assertFalse(
            publication_ready(
                self.v2,
                333,
                [{"class": "story_structure_break", "severity": "serious"}],
            )
        )

    def test_v2_critical_existing_quality_class_still_blocks(self) -> None:
        self.assertFalse(
            publication_ready(
                self.v2,
                500,
                [{"class": "canon_violation", "severity": "critical"}],
            )
        )

    def test_v2_moderate_quality_observation_is_non_blocking(self) -> None:
        self.assertTrue(
            publication_ready(
                self.v2,
                333,
                [{"class": "story_structure_break", "severity": "moderate"}],
            )
        )

    def test_v2_explicitly_disables_deterministic_length_hard_fail(self) -> None:
        policy = self.v2["publication_length_policy"]
        self.assertFalse(policy["deterministic_hard_fail"])
        self.assertFalse(policy["length_deviation_alone_is_blocking"])


if __name__ == "__main__":
    unittest.main()
