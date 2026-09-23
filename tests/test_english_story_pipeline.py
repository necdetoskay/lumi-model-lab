from __future__ import annotations

import unittest

from src.english_story_pipeline import (
    allocate_scene_budgets,
    build_scene_jev_questions,
    build_whole_story_jev_questions,
    validate_final_judge,
    validate_scene_envelope,
)


def good_envelope(words: int = 100) -> dict:
    return {
        "prose": "word " * words,
        "state_delta": {
            "location": "coastal path",
            "character_goal": "understand the signal",
            "knowledge_gained": ["The tide changes access."],
            "facts_established": ["A marker is visible at low tide."],
            "clues_added": ["marker"],
            "objects_changed": [],
            "relationships_changed": [],
            "threads_opened": ["signal source"],
            "threads_resolved": [],
            "handoff_state": "Ada reaches the next marker.",
        },
    }


class EnglishStoryPipelineTests(unittest.TestCase):
    def test_default_2000_word_budget_distribution(self):
        self.assertEqual(
            allocate_scene_budgets(2000),
            [260, 310, 340, 340, 410, 340],
        )
        self.assertEqual(sum(allocate_scene_budgets(2000)), 2000)

    def test_scene_envelope_passes_inside_budget(self):
        envelope = good_envelope(100)
        errors, word_count = validate_scene_envelope(
            envelope,
            target_words=100,
        )
        self.assertEqual(errors, [])
        self.assertEqual(word_count, 100)

    def test_scene_envelope_triggers_local_word_repair(self):
        envelope = good_envelope(50)
        errors, _ = validate_scene_envelope(
            envelope,
            target_words=100,
        )
        self.assertTrue(
            any(error.startswith("below_scene_word_budget:") for error in errors)
        )

    def test_scene_jev_questions_are_atomic(self):
        questions = build_scene_jev_questions(3, False)
        self.assertEqual(len(questions), 8)
        self.assertEqual(questions["no_contradiction"]["type"], "noul")
        self.assertEqual(questions["next_action"]["type"], "choice")

    def test_whole_story_jev_questions_are_atomic(self):
        questions = build_whole_story_jev_questions()
        self.assertEqual(len(questions), 7)
        self.assertEqual(questions["clue_solution_progression"]["type"], "noul")
        self.assertEqual(questions["next_action"]["type"], "choice")

    def test_final_haiku_gate_accepts_strong_story(self):
        payload = {
            "scores": {
                "instruction_following": 5,
                "coherence": 5,
                "character_consistency": 5,
                "age_appropriateness": 5,
                "creativity": 4,
                "style_quality": 4,
                "continuity": 5,
                "ending_quality": 4,
            },
            "critical_failures": [],
            "repair_targets": [],
            "summary": "Strong.",
        }
        result = validate_final_judge(payload)
        self.assertTrue(result["accepted"])
        self.assertGreaterEqual(result["average"], 4.0)

    def test_final_haiku_gate_rejects_critical_failure(self):
        payload = {
            "scores": {
                "instruction_following": 5,
                "coherence": 5,
                "character_consistency": 5,
                "age_appropriateness": 5,
                "creativity": 5,
                "style_quality": 5,
                "continuity": 5,
                "ending_quality": 5,
            },
            "critical_failures": ["Story contradicts the immutable contract."],
            "repair_targets": [{"scene": 4, "issue": "contradiction"}],
            "summary": "Blocked.",
        }
        self.assertFalse(validate_final_judge(payload)["accepted"])


if __name__ == "__main__":
    unittest.main()
