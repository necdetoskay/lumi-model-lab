from __future__ import annotations

import unittest
from unittest.mock import patch

from src.english_story_pipeline import (
    allocate_chunk_word_ceilings,
    allocate_scene_budgets,
    build_scene_jev_questions,
    build_whole_story_jev_questions,
    call_structured_json_with_retry,
    compress_scene_in_chunks,
    evaluate_completed_story,
    evaluate_scene_jev,
    jev_needs_targeted_repair,
    jev_requires_final_escalation,
    jev_targeted_repair_reasons,
    final_repair_scene_ids,
    only_word_budget_errors,
    plan_repair_feedback,
    repair_plan_once,
    repair_scene_word_budget,
    repair_scene_for_final_judge,
    run_final_polish_cycles,
    scene_request_payload,
    split_scene_for_compression,
    validate_final_judge,
    validate_prose_only_repair,
    validate_scene_envelope,
    verify_final_repair_target,
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
    @patch("src.english_story_pipeline.call_openrouter")
    def test_structured_json_retry_recovers_malformed_response(self, mock_call):
        valid = good_envelope(100)
        mock_call.side_effect = [
            (
                '{"prose":"unfinished',
                {
                    "choices": [{"finish_reason": "stop"}],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 5,
                        "total_tokens": 15,
                        "cost": 0.001,
                    },
                },
                {
                    "temperature": 0.7,
                    "reasoning": {"effort": "none", "exclude": True},
                    "response_format": {"type": "json_object"},
                },
            ),
            (
                __import__("json").dumps(valid),
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
                    "temperature": 0.2,
                    "reasoning": {"effort": "none", "exclude": True},
                    "response_format": {"type": "json_object"},
                },
            ),
        ]

        payload, _, _, failures = call_structured_json_with_retry(
            api_key="test",
            model="qwen/qwen3.8-flash",
            system_prompt="system",
            user_prompt="user",
            temperature=0.7,
            max_tokens=None,
            seed=42,
            request_class="scene_story",
        )

        self.assertEqual(payload, valid)
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["parse_attempt"], 1)
        self.assertEqual(mock_call.call_count, 2)
        second = mock_call.call_args_list[1].kwargs
        self.assertEqual(second["temperature"], 0.2)
        self.assertNotEqual(second["seed"], 42)
        self.assertIn("FORMAT RECOVERY", second["user_prompt"])

    def test_default_2000_word_budget_distribution(self):
        self.assertEqual(
            allocate_scene_budgets(2000),
            [260, 310, 340, 340, 410, 340],
        )
        self.assertEqual(sum(allocate_scene_budgets(2000)), 2000)

    def test_scene_request_uses_tighter_writer_word_range(self):
        StorySpec = __import__("src.schemas", fromlist=["StorySpec"]).StorySpec
        spec = StorySpec(
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
        payload = __import__("json").loads(
            scene_request_payload(
                spec=spec,
                plan={"story_contract": {}, "scenes": []},
                ledger=[],
                scene_contract={"purpose": "observe"},
                next_scene=None,
                previous_prose="",
                target_words=100,
                plan_review={},
            )
        )
        self.assertEqual(payload["allowed_word_range"], [90, 110])

    def test_chunk_split_and_ceilings_preserve_total_budget(self):
        prose = (
            "One two three. Four five six. Seven eight nine. "
            "Ten eleven twelve. Thirteen fourteen fifteen. "
            "Sixteen seventeen eighteen."
        )
        chunks = split_scene_for_compression(prose, 3)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(
            sum(__import__("src.generate", fromlist=["count_words"]).count_words(chunk) for chunk in chunks),
            18,
        )
        ceilings = allocate_chunk_word_ceilings(
            chunks,
            total_target_words=90,
        )
        self.assertEqual(len(ceilings), 3)
        self.assertEqual(sum(ceilings), 90)
        self.assertTrue(all(value >= 20 for value in ceilings))

    @patch("src.english_story_pipeline.call_structured_json_with_retry")
    def test_chunked_compression_can_rescue_large_overage(self, mock_structured):
        original = good_envelope(180)
        response = (
            {"prose": "word " * 22},
            {
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 10,
                    "total_tokens": 20,
                    "cost": 0.001,
                }
            },
            {
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
            },
            [],
        )
        mock_structured.side_effect = [response, response, response, response]

        repaired, errors, word_count, attempt = compress_scene_in_chunks(
            api_key="test",
            model="qwen/qwen3.8-flash",
            envelope=original,
            scene_contract={"purpose": "observe"},
            target_words=100,
            seed=500,
        )

        self.assertEqual(errors, [])
        self.assertEqual(word_count, 88)
        self.assertEqual(repaired["state_delta"], original["state_delta"])
        self.assertEqual(attempt["kind"], "chunked_word_budget_compress")
        self.assertEqual(attempt["chunk_count"], 4)
        self.assertEqual(mock_structured.call_count, 4)
        self.assertIsNone(
            mock_structured.call_args_list[0].kwargs["max_tokens"]
        )

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

    def test_only_word_budget_errors_detects_budget_only_failure(self):
        self.assertTrue(
            only_word_budget_errors(["above_scene_word_budget:130>120"])
        )
        self.assertFalse(
            only_word_budget_errors(
                [
                    "above_scene_word_budget:130>120",
                    "state_delta_location_missing",
                ]
            )
        )

    @patch("src.english_story_pipeline.call_openrouter")
    def test_word_budget_repair_compresses_without_state_change(self, mock_call):
        original = good_envelope(130)
        repaired_prose = {"prose": "word " * 105}
        mock_call.return_value = (
            __import__("json").dumps(repaired_prose),
            {
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                    "cost": 0.001,
                }
            },
            {
                "reasoning": {"effort": "none", "exclude": True},
                "response_format": {"type": "json_object"},
            },
        )
        result, errors, word_count, attempt = repair_scene_word_budget(
            api_key="test",
            model="qwen/qwen3.8-flash",
            envelope=original,
            target_words=100,
            seed=100,
            repair_index=1,
        )
        self.assertEqual(errors, [])
        self.assertEqual(word_count, 105)
        self.assertEqual(result["state_delta"], original["state_delta"])
        self.assertEqual(attempt["mode"], "COMPRESS")
        self.assertEqual(attempt["kind"], "word_budget_repair_1")
        self.assertEqual(attempt["required_word_range"], [92, 108])
        self.assertIsNone(mock_call.call_args.kwargs["max_tokens"])
        self.assertEqual(mock_call.call_args.kwargs["temperature"], 0.0)

    @patch("src.english_story_pipeline.call_openrouter")
    def test_second_word_budget_repair_is_more_aggressive(self, mock_call):
        original = good_envelope(130)
        mock_call.return_value = (
            __import__("json").dumps({"prose": "word " * 95}),
            {
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                    "cost": 0.001,
                }
            },
            {
                "reasoning": {"effort": "none", "exclude": True},
                "response_format": {"type": "json_object"},
            },
        )
        _, errors, word_count, attempt = repair_scene_word_budget(
            api_key="test",
            model="qwen/qwen3.8-flash",
            envelope=original,
            target_words=100,
            seed=100,
            repair_index=2,
        )
        self.assertEqual(errors, [])
        self.assertEqual(word_count, 95)
        self.assertEqual(attempt["required_word_range"], [88, 98])
        self.assertEqual(attempt["aggressiveness"], "high")
        sent = __import__("json").loads(
            mock_call.call_args.kwargs["user_prompt"]
        )
        self.assertTrue(sent["previous_attempt_missed_target"])
        self.assertEqual(sent["minimum_words_to_remove"], 32)
        self.assertEqual(sent["maximum_output_words"], 98)
        self.assertEqual(sent["maximum_sentences"], 8)

    @patch("src.english_story_pipeline.call_openrouter")
    def test_word_budget_repair_ignores_model_state_delta_output(self, mock_call):
        original = good_envelope(130)
        payload = {
            "prose": "word " * 105,
            "state_delta": {"location": "new location"},
        }
        mock_call.return_value = (
            __import__("json").dumps(payload),
            {
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                    "cost": 0.001,
                }
            },
            {
                "reasoning": {"effort": "none", "exclude": True},
                "response_format": {"type": "json_object"},
            },
        )
        repaired, errors, _, _ = repair_scene_word_budget(
            api_key="test",
            model="qwen/qwen3.8-flash",
            envelope=original,
            target_words=100,
            seed=100,
            repair_index=1,
        )
        self.assertEqual(errors, [])
        self.assertEqual(repaired["state_delta"], original["state_delta"])

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

    def test_final_repair_scene_ids_are_bounded_and_deduplicated(self):
        final_judge = {
            "critical_failures": [],
            "repair_targets": [
                {"scene": 4, "issue": "a"},
                {"scene": 4, "issue": "b"},
                {"scene": 5, "issue": "c"},
                {"scene": 6, "issue": "d"},
                {"scene": 2, "issue": "e"},
            ],
        }
        self.assertEqual(final_repair_scene_ids(final_judge), [4, 5, 6])

    def test_final_repair_skips_critical_failure(self):
        final_judge = {
            "critical_failures": ["contract violation"],
            "repair_targets": [{"scene": 4, "issue": "a"}],
        }
        self.assertEqual(final_repair_scene_ids(final_judge), [])

    def test_prose_only_repair_rejects_state_delta_change(self):
        original = good_envelope(100)
        repaired = good_envelope(100)
        repaired["state_delta"]["location"] = "different location"
        errors, _ = validate_prose_only_repair(
            original_envelope=original,
            repaired_envelope=repaired,
            target_words=100,
        )
        self.assertIn("final_repair_state_delta_changed", errors)

    @patch("src.english_story_pipeline.call_openrouter_jev")
    def test_final_repair_target_verification_uses_atomic_jev_question(
        self,
        mock_jev,
    ):
        mock_jev.return_value = {
            "answers": {
                "target_resolved": {
                    "type": "noul",
                    "noul": 0.91,
                }
            },
            "usage": {"cost": 0.00001},
            "model": "typesafe/jev-1.13-20260917",
            "provider": "TypeSafe",
        }
        scenes = [
            {
                "scene": 1,
                "contract": {"purpose": "observe"},
                "envelope": good_envelope(100),
            }
        ]
        result = verify_final_repair_target(
            api_key="test",
            plan={"story_contract": {"central_problem": "signal"}},
            scenes=scenes,
            scene_index=1,
            issue="The timing statement is contradictory.",
        )
        self.assertTrue(result["verified"])
        self.assertEqual(result["probability"], 0.91)
        questions = mock_jev.call_args.kwargs["questions"]
        self.assertEqual(list(questions), ["target_resolved"])
        self.assertEqual(questions["target_resolved"]["type"], "noul")
        sent_state = mock_jev.call_args.kwargs["state"]
        self.assertEqual(
            sent_state["repair_issue"],
            "The timing statement is contradictory.",
        )

    @patch("src.english_story_pipeline.call_openrouter")
    def test_final_scene_repair_is_token_uncapped_and_state_preserving(
        self,
        mock_call,
    ):
        envelope = good_envelope(100)
        mock_call.return_value = (
            __import__("json").dumps(envelope),
            {
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                    "cost": 0.001,
                }
            },
            {
                "reasoning": {"effort": "none", "exclude": True},
                "response_format": {"type": "json_object"},
            },
        )
        scenes = [
            {
                "scene": 1,
                "target_words": 100,
                "contract": {"purpose": "observe"},
                "envelope": envelope,
            }
        ]
        repaired, errors, word_count, attempt = repair_scene_for_final_judge(
            api_key="test",
            model="qwen/qwen3.8-flash",
            plan={"story_contract": {}, "scenes": [{"purpose": "observe"}]},
            ledger=[{"scene": 1, "word_count": 100}],
            scenes=scenes,
            scene_index=1,
            issue="add one clarifying sentence",
            seed=7601,
        )
        self.assertEqual(errors, [])
        self.assertEqual(word_count, 100)
        self.assertEqual(repaired["state_delta"], envelope["state_delta"])
        self.assertIsNone(mock_call.call_args.kwargs["max_tokens"])
        self.assertEqual(attempt["kind"], "final_haiku_targeted_repair")

    @patch("src.english_story_pipeline.call_openrouter")
    @patch("src.english_story_pipeline.call_openrouter_jev")
    def test_completed_story_evaluation_returns_final_request(
        self,
        mock_jev,
        mock_openrouter,
    ):
        whole_questions = build_whole_story_jev_questions()
        answers = {
            key: {"type": "noul", "noul": 0.95}
            for key in whole_questions
            if key != "next_action"
        }
        answers["next_action"] = {
            "type": "choice",
            "choice": "CONTINUE",
            "confidence": 0.95,
        }
        mock_jev.return_value = {
            "answers": answers,
            "usage": {
                "input_tokens": 100,
                "output_tokens": 10,
                "cost": 0.0001,
            },
        }
        final_payload = {
            "scores": {
                "instruction_following": 4,
                "coherence": 4,
                "character_consistency": 4,
                "age_appropriateness": 4,
                "creativity": 4,
                "style_quality": 4,
                "continuity": 4,
                "ending_quality": 4,
            },
            "critical_failures": [],
            "repair_targets": [],
            "summary": "Accepted.",
        }
        mock_openrouter.return_value = (
            __import__("json").dumps(final_payload),
            {
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                    "cost": 0.002,
                }
            },
            {
                "temperature": 0.0,
                "max_tokens": 2500,
                "response_format": {"type": "json_object"},
            },
        )
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
        plan = {
            "story_contract": {},
            "scenes": [{"purpose": f"Scene {i}"} for i in range(1, 7)],
        }
        scenes = []
        for i in range(1, 7):
            envelope = good_envelope(334)
            envelope["prose"] = " ".join(
                f"scene{i}word{j}" for j in range(334)
            )
            scenes.append(
                {
                    "scene": i,
                    "envelope": envelope,
                    "jev_history": [],
                    "semantic_repairs": [],
                    "continuity_escalation_required": False,
                }
            )
        result = evaluate_completed_story(
            api_key="test",
            judge_model="anthropic/claude-haiku-4.5",
            spec=spec,
            plan=plan,
            ledger=[{"scene": i} for i in range(1, 7)],
            scenes=scenes,
        )
        self.assertTrue(result["accepted"])
        self.assertEqual(result["word_count"], 2004)
        self.assertEqual(result["final_judge_request"]["temperature"], 0.0)
        self.assertEqual(result["final_judge_request"]["max_tokens"], 2500)

    @patch("src.english_story_pipeline.apply_final_haiku_repairs")
    @patch("src.english_story_pipeline.evaluate_completed_story")
    def test_final_polish_can_run_two_bounded_cycles(
        self,
        mock_evaluate,
        mock_repair,
    ):
        eval1 = {
            "accepted": False,
            "word_count": 2000,
            "deterministic_errors": [],
            "whole_story_jev": {},
            "whole_jev_cost": 0.001,
            "final_judge_cost": {"usd": 0.01},
            "final_judge": {
                "accepted": False,
                "critical_failures": [],
                "repair_targets": [
                    {"scene": 5, "issue": "clarify payoff"},
                    {"scene": 6, "issue": "smooth transition"},
                ],
            },
        }
        eval2 = {
            "accepted": False,
            "word_count": 2002,
            "deterministic_errors": [],
            "whole_story_jev": {},
            "whole_jev_cost": 0.001,
            "final_judge_cost": {"usd": 0.01},
            "final_judge": {
                "accepted": False,
                "critical_failures": [],
                "repair_targets": [
                    {"scene": 1, "issue": "clarify setup"},
                ],
            },
        }
        eval3 = {
            "accepted": True,
            "word_count": 2004,
            "deterministic_errors": [],
            "whole_story_jev": {},
            "whole_jev_cost": 0.001,
            "final_judge_cost": {"usd": 0.01},
            "final_judge": {
                "accepted": True,
                "critical_failures": [],
                "repair_targets": [],
            },
        }
        mock_evaluate.side_effect = [eval1, eval2, eval3]
        mock_repair.side_effect = [
            [
                {"scene": 5, "accepted": True, "target_verified": True},
                {"scene": 6, "accepted": True, "target_verified": True},
            ],
            [
                {"scene": 1, "accepted": True, "target_verified": True},
            ],
        ]

        final_eval, history, repairs, cycles = run_final_polish_cycles(
            api_key="test",
            model="qwen/qwen3.8-flash",
            judge_model="anthropic/claude-haiku-4.5",
            spec=object(),
            plan={},
            ledger=[],
            scenes=[],
            max_cycles=2,
        )

        self.assertTrue(final_eval["accepted"])
        self.assertEqual(len(history), 3)
        self.assertEqual(mock_repair.call_count, 2)
        self.assertEqual(
            [cycle["requested_scenes"] for cycle in cycles],
            [[5, 6], [1]],
        )
        self.assertEqual([repair["cycle"] for repair in repairs], [1, 1, 2])

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
