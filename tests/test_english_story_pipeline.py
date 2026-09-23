from __future__ import annotations

import unittest
from unittest.mock import patch

from src.english_story_pipeline import (
    allocate_scene_budgets,
    build_scene_jev_questions,
    build_whole_story_jev_questions,
    evaluate_scene_jev,
    jev_needs_targeted_repair,
    jev_requires_final_escalation,
    jev_targeted_repair_reasons,
    plan_repair_feedback,
    repair_plan_once,
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

    def test_scene_hard_bound_allows_small_overage_after_repair(self):
        envelope = good_envelope(118)
        errors, _ = validate_scene_envelope(
            envelope,
            target_words=100,
        )
        self.assertEqual(errors, [])

    def test_scene_hard_bound_rejects_large_overage(self):
        envelope = good_envelope(121)
        errors, _ = validate_scene_envelope(
            envelope,
            target_words=100,
        )
        self.assertTrue(
            any(error.startswith("above_scene_word_budget:") for error in errors)
        )

    def test_scene_jev_questions_are_atomic(self):
        questions = build_scene_jev_questions(3, False)
        self.assertEqual(len(questions), 8)
        self.assertEqual(questions["no_contradiction"]["type"], "noul")
        self.assertEqual(questions["next_action"]["type"], "choice")

    def test_jev_below_threshold_triggers_targeted_repair(self):
        evidence = {
            "threshold": 0.8,
            "below_threshold": {"no_unexplained_dependency": 0.74},
            "next_action": "CONTINUE",
        }
        self.assertTrue(jev_needs_targeted_repair(evidence))
        self.assertEqual(
            jev_targeted_repair_reasons(evidence),
            ["jev:no_unexplained_dependency:0.740<0.800"],
        )

    def test_jev_clean_continue_does_not_trigger_repair(self):
        evidence = {
            "threshold": 0.8,
            "below_threshold": {},
            "next_action": "CONTINUE",
        }
        self.assertFalse(jev_needs_targeted_repair(evidence))
        self.assertFalse(jev_requires_final_escalation(evidence))

    def test_jev_targeted_repair_choice_triggers_even_without_low_metric(self):
        evidence = {
            "threshold": 0.8,
            "below_threshold": {},
            "next_action": "TARGETED_REPAIR",
        }
        self.assertTrue(jev_needs_targeted_repair(evidence))
        self.assertTrue(jev_requires_final_escalation(evidence))

    def test_jev_escalate_without_low_metric_skips_blind_repair_but_escalates(self):
        evidence = {
            "threshold": 0.8,
            "below_threshold": {},
            "next_action": "ESCALATE",
        }
        self.assertFalse(jev_needs_targeted_repair(evidence))
        self.assertTrue(jev_requires_final_escalation(evidence))

    @patch("src.english_story_pipeline.call_openrouter_jev")
    def test_scene_jev_receives_story_contract(self, mock_jev):
        questions = build_scene_jev_questions(2, False)
        answers = {
            key: {"type": "noul", "noul": 0.95}
            for key in questions
            if key != "next_action"
        }
        answers["next_action"] = {
            "type": "choice",
            "choice": "CONTINUE",
            "confidence": 0.9,
        }
        mock_jev.return_value = {"answers": answers}
        contract = {"protagonist_goal": "understand the signal"}
        evaluate_scene_jev(
            api_key="test",
            scene_index=2,
            story_contract=contract,
            scene_contract={"purpose": "follow evidence"},
            next_scene={"purpose": "combine clues"},
            ledger=[],
            envelope=good_envelope(100),
        )
        sent_state = mock_jev.call_args.kwargs["state"]
        self.assertEqual(sent_state["story_contract"], contract)

    def test_whole_story_jev_questions_are_atomic(self):
        questions = build_whole_story_jev_questions()
        self.assertEqual(len(questions), 7)
        self.assertEqual(questions["clue_solution_progression"]["type"], "noul")
        self.assertEqual(questions["next_action"]["type"], "choice")

    def test_scene_five_future_leakage_question_is_phase_aware(self):
        questions = build_scene_jev_questions(5, False)
        instructions = questions["no_future_leakage"]["instructions"]
        self.assertIn("Scene 5", instructions)
        self.assertIn("Scene 6", instructions)
        self.assertIn("decisive payoff", instructions)

    def test_final_scene_future_leakage_question_is_closure_aware(self):
        questions = build_scene_jev_questions(6, True)
        instructions = questions["no_future_leakage"]["instructions"]
        self.assertIn("final scene", instructions.lower())
        self.assertIn("new main problem", instructions.lower())

    def test_whole_story_contradiction_question_defines_material_scope(self):
        questions = build_whole_story_jev_questions()
        instructions = questions["no_contradictions"]["instructions"]
        self.assertIn("ContinuityLedger", instructions)
        self.assertIn("cannot both be true", instructions)

    def test_plan_repair_feedback_preserves_only_gate_evidence(self):
        plan_result = {
            "deterministic_errors": ["scene_constraint_schedule_mismatch"],
            "jev": {
                "threshold": 0.8,
                "below_threshold": {"no_early_resolution": 0.58},
                "next_action": "CONTINUE",
                "next_action_confidence": 0.82,
            },
            "haiku": {
                "scores": {"no_early_resolution": 3},
                "critical_failures": [],
                "scene_risks": [{"scene": 5, "risk": "payoff leaks early"}],
                "summary": "repair needed",
            },
        }
        feedback = plan_repair_feedback(plan_result)
        self.assertEqual(
            feedback["jev"]["below_threshold"],
            {"no_early_resolution": 0.58},
        )
        self.assertEqual(feedback["haiku"]["scene_risks"][0]["scene"], 5)

    @patch("src.english_story_pipeline.evaluate_plan_candidate")
    @patch("src.english_story_pipeline.call_openrouter")
    def test_plan_repair_uses_unbounded_story_plan_request(
        self,
        mock_call,
        mock_evaluate,
    ):
        mock_call.return_value = (
            '{"story_title":"Signal","story_contract":{},"scenes":[]}',
            {
                "choices": [{"finish_reason": "stop"}],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                    "cost": 0.001,
                },
            },
            {
                "reasoning": {"effort": "none", "exclude": True},
                "response_format": {"type": "json_object"},
            },
        )
        mock_evaluate.return_value = {
            "accepted": True,
            "deterministic_errors": [],
            "jev": {
                "threshold": 0.8,
                "below_threshold": {},
                "next_action": "CONTINUE",
            },
            "haiku": {
                "scores": {},
                "critical_failures": [],
                "scene_risks": [],
                "summary": "ok",
            },
            "costs": {"jev": 0.0, "haiku": {"usd": 0.0}},
            "usage": {"jev": {}, "haiku": {}},
            "request_evidence": {"haiku": {}},
        }
        spec = __import__("src.schemas", fromlist=["StorySpec"]).StorySpec(
            age_min=6,
            age_max=8,
            language="en",
            target_words=2000,
            title_hint="Signal",
            protagonist="Ada",
            setting="coast",
            theme="observation",
            premise="Ada investigates a signal.",
            constraints=["Use two clues."],
        )
        current = {
            "plan": {"story_title": "Signal", "story_contract": {}, "scenes": []},
            "deterministic_errors": [],
            "jev": {
                "threshold": 0.8,
                "below_threshold": {"no_early_resolution": 0.58},
                "next_action": "CONTINUE",
                "next_action_confidence": 0.82,
            },
            "haiku": {
                "scores": {"no_early_resolution": 3},
                "critical_failures": [],
                "scene_risks": [],
                "summary": "repair",
            },
        }
        repaired, attempt = repair_plan_once(
            api_key="test",
            model="qwen/qwen3.8-flash",
            judge_model="anthropic/claude-haiku-4.5",
            spec=spec,
            plan_result=current,
            repair_index=1,
        )
        self.assertTrue(repaired["accepted"])
        self.assertTrue(attempt["accepted"])
        kwargs = mock_call.call_args.kwargs
        self.assertIsNone(kwargs["max_tokens"])
        self.assertEqual(kwargs["request_class"], "story_plan")
        self.assertTrue(kwargs["structured_output"])

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
