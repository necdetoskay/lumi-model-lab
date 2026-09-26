import json
import unittest

from src.story_narrative_load_plan import (
    can_advance_to_writer,
    candidate_requires_supporting_thread,
    evaluate_narrative_load_promotion_gate,
    load_candidate_profile,
    validate_narrative_load_plan,
)


class StoryNarrativeLoadPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = load_candidate_profile()

    def valid_plan(self):
        rows = [
            ("brief", "setup", "A başlar."),
            ("develop", "signal", "Bir işaret belirir."),
            ("develop", "hypothesis", "Karakter bir ihtimal düşünür."),
            ("develop", "test", "İhtimali dener."),
            ("anchor", "observation", "Yeni bir şey fark eder."),
            ("develop", "decision", "Bir karar verir."),
            ("anchor", "payoff", "Kararın sonucu görünür."),
            ("anchor", "closure", "Hikâye somut biçimde kapanır."),
        ]
        return {
            "supporting_thread": {
                "used": False,
                "description": "",
                "why_it_belongs": "",
            },
            "spine": [
                {"density": density, "function": function, "beat": beat}
                for density, function, beat in rows
            ],
        }

    def test_valid_eight_beat_main_arc_can_advance(self):
        plan = self.valid_plan()
        self.assertEqual(validate_narrative_load_plan(plan), [])
        self.assertTrue(can_advance_to_writer(plan))

    def test_supporting_thread_is_optional(self):
        self.assertFalse(candidate_requires_supporting_thread(self.valid_plan()))

    def test_used_supporting_thread_requires_description_and_belonging_reason(self):
        plan = self.valid_plan()
        plan["supporting_thread"] = {
            "used": True,
            "description": "",
            "why_it_belongs": "",
        }
        errors = validate_narrative_load_plan(plan)
        self.assertIn("supporting_thread_description_missing", errors)
        self.assertIn("supporting_thread_belonging_rationale_missing", errors)

    def test_too_many_beats_fails(self):
        plan = self.valid_plan()
        plan["spine"] += [
            {"density": "develop", "function": "observation", "beat": "Ek 1"},
            {"density": "develop", "function": "decision", "beat": "Ek 2"},
            {"density": "develop", "function": "test", "beat": "Ek 3"},
            {"density": "anchor", "function": "payoff", "beat": "Ek 4"},
            {"density": "brief", "function": "closure", "beat": "Ek 5"},
        ]
        self.assertIn("spine_size_out_of_range", validate_narrative_load_plan(plan))

    def test_invalid_function_fails(self):
        plan = self.valid_plan()
        plan["spine"][3]["function"] = "padding"
        self.assertIn("beat_3_function_invalid", validate_narrative_load_plan(plan))

    def test_invalid_density_fails(self):
        plan = self.valid_plan()
        plan["spine"][0]["density"] = "verbose"
        self.assertIn("beat_0_density_invalid", validate_narrative_load_plan(plan))

    def test_empty_event_fails(self):
        plan = self.valid_plan()
        plan["spine"][0]["beat"] = " "
        self.assertIn("beat_0_text_missing", validate_narrative_load_plan(plan))

    def test_required_setup_payoff_and_closure_are_locked(self):
        plan = self.valid_plan()
        plan["spine"][0]["function"] = "signal"
        errors = validate_narrative_load_plan(plan)
        self.assertIn("required_function_missing:setup", errors)

    def test_closure_must_be_terminal(self):
        plan = self.valid_plan()
        plan["spine"][-1]["function"] = "observation"
        errors = validate_narrative_load_plan(plan)
        self.assertIn("required_function_missing:closure", errors)
        self.assertIn("closure_not_terminal", errors)

    def test_payoff_must_precede_closure(self):
        plan = self.valid_plan()
        plan["spine"][-2]["function"] = "closure"
        plan["spine"][-1]["function"] = "payoff"
        errors = validate_narrative_load_plan(plan)
        self.assertIn("closure_not_terminal", errors)
        self.assertIn("payoff_not_before_closure", errors)

    def test_duplicate_beat_text_fails(self):
        plan = self.valid_plan()
        plan["spine"][3]["beat"] = plan["spine"][2]["beat"]
        self.assertIn("duplicate_beat_text", validate_narrative_load_plan(plan))

    def test_candidate_keeps_length_soft_and_quality_primary(self):
        self.assertEqual(self.profile["writer_contract"]["target_mode"], "soft")
        self.assertEqual(self.profile["quality_priority"], "primary")
        self.assertEqual(self.profile["length_priority"], "secondary")
        self.assertTrue(self.profile["length_policy"]["do_not_pad_to_target"])

    def test_supporting_thread_has_fail_closed_boundaries(self):
        policy = self.profile["supporting_thread"]
        self.assertEqual(policy["max_count"], 1)
        self.assertTrue(policy["must_rejoin_main_arc"])
        self.assertTrue(policy["must_change_observation_decision_constraint_or_payoff"])
        self.assertTrue(policy["must_not_exist_only_for_length"])
        self.assertTrue(policy["must_preserve_main_causal_rule"])
        self.assertTrue(policy["may_not_introduce_hidden_condition_only_to_delay_payoff"])
        self.assertTrue(policy["new_named_character_forbidden"])
        self.assertTrue(policy["new_relationship_canon_forbidden"])
        self.assertTrue(policy["new_durable_world_fact_forbidden"])
        self.assertTrue(policy["new_independent_solution_forbidden"])

    def test_writer_must_preserve_committed_item_and_causal_state(self):
        writer = self.profile["writer_contract"]
        self.assertTrue(writer["must_preserve_committed_item_state"])
        self.assertTrue(writer["may_not_undo_completed_action_only_to_reuse_prop"])
        self.assertTrue(writer["must_preserve_established_causal_rules"])

    def test_architect_integration_is_preferred_over_extra_model_hop(self):
        policy = self.profile["integration_policy"]
        self.assertEqual(policy["logical_stage"], "pre_prose_story_architecture")
        self.assertTrue(policy["prefer_fold_into_existing_narrative_architect"])
        self.assertFalse(policy["separate_model_call_required"])
        self.assertFalse(policy["requires_architect_integration_probe_before_production"])
        self.assertTrue(policy["architect_integration_qualified"])
        self.assertEqual(policy["max_semantic_replans_on_invalid_plan"], 1)
        self.assertTrue(policy["semantic_replan_only_on_deterministic_validation_failure"])
        self.assertEqual(policy["normal_path_extra_model_hops"], 0)

    def test_guarded_fantastical_qualification_is_recorded(self):
        evidence = self.profile["promotion_evidence"]
        self.assertEqual(evidence["family_cases_total"], 15)
        self.assertEqual(evidence["combined_consensus"]["planned_wins"], 9)
        self.assertEqual(evidence["combined_consensus"]["baseline_wins"], 1)
        self.assertEqual(evidence["guarded_fantastical_run"], 36227255937)
        self.assertEqual(evidence["guarded_fantastical_consensus"]["guarded_planned_wins"], 3)
        self.assertEqual(evidence["guarded_fantastical_consensus"]["baseline_wins"], 0)
        self.assertFalse(evidence["known_risk"]["targeted_guard_validation_required"])
        self.assertTrue(evidence["known_risk"]["targeted_guard_validation_completed"])

    def test_writer_separates_perception_from_response(self):
        writer = self.profile["writer_contract"]
        support = self.profile["supporting_thread"]
        self.assertTrue(writer["must_distinguish_perception_from_response"])
        self.assertTrue(writer["may_not_infer_sensory_failure_from_busy_hands"])
        self.assertTrue(support["must_preserve_response_causality"])

    def test_writer_closure_is_terminal(self):
        writer = self.profile["writer_contract"]
        self.assertTrue(writer["closure_is_terminal"])
        self.assertTrue(writer["may_not_add_new_action_after_closure"])
        self.assertTrue(writer["may_not_force_post_closure_prop_convergence"])

    def test_terminal_closure_guard_qualification_is_recorded(self):
        evidence = self.profile["promotion_evidence"]["terminal_closure_guard"]
        self.assertEqual(evidence["run"], 36228845559)
        self.assertEqual(evidence["fixture"], "watering_can_busy")
        self.assertEqual(evidence["consensus"]["guarded_candidate_wins"], 1)
        self.assertEqual(evidence["consensus"]["baseline_wins"], 0)
        self.assertTrue(evidence["consensus"]["order_swapped"])
        self.assertEqual(evidence["serious_defects_guarded_candidate"], 0)
        self.assertTrue(
            self.profile["promotion_evidence"]["known_risk"][
                "terminal_closure_tail_risk_validation_completed"
            ]
        )

    def test_current_promotion_gate_awaits_explicit_decision_after_multiseed_noninferiority(self):
        result = evaluate_narrative_load_promotion_gate(self.profile)
        self.assertTrue(result["evidence_pass"])
        self.assertEqual(result["state"], "AWAIT_EXPLICIT_PROMOTION_DECISION")
        self.assertEqual(result["unresolved_families"], [])
        self.assertTrue(result["requires_explicit_promotion_decision"])
        self.assertFalse(result["production_gate_pass"])

    def test_emotional_multiseed_noninferiority_is_recorded(self):
        integration = self.profile["promotion_evidence"]["architect_integration"]
        evidence = integration["emotional_multiseed"]
        self.assertEqual(evidence["first_run"], 36228645350)
        self.assertEqual(evidence["second_run"], 36229244503)
        self.assertEqual(evidence["independent_candidate_seeds"], 2)
        self.assertEqual(evidence["consensus"]["frozen_baseline_wins"], 0)
        self.assertEqual(evidence["candidate_serious_defects_total"], 0)
        self.assertEqual(
            evidence["resolution"],
            "noninferior_position_sensitive_multiseed",
        )
        self.assertEqual(
            integration["latest_family_resolution"]["emotional_development"],
            "noninferior_position_independent_absolute_judging",
        )

    def test_emotional_absolute_tiebreak_is_required_and_recorded(self):
        integration = self.profile["promotion_evidence"]["architect_integration"]
        evidence = integration["emotional_absolute_tiebreak"]
        self.assertEqual(evidence["run"], 36229571364)
        self.assertTrue(evidence["position_independent"])
        self.assertEqual(evidence["generation_calls"], 0)
        self.assertTrue(evidence["strict_resolution_pass"])
        self.assertTrue(evidence["candidate_seed_1"]["noninferiority_pass"])
        self.assertTrue(evidence["candidate_seed_2"]["noninferiority_pass"])
        self.assertEqual(evidence["candidate_seed_1"]["serious_defect_count"], 0)
        self.assertEqual(evidence["candidate_seed_2"]["serious_defect_count"], 0)

        broken = json.loads(json.dumps(self.profile))
        broken["promotion_evidence"]["architect_integration"][
            "emotional_absolute_tiebreak"
        ]["strict_resolution_pass"] = False
        result = evaluate_narrative_load_promotion_gate(broken)
        self.assertFalse(result["evidence_pass"])
        self.assertEqual(result["state"], "BLOCKED_EVIDENCE")
        self.assertIn("emotional_absolute_tiebreak_not_passed", result["blockers"])

    def test_promotion_gate_requires_explicit_decision_after_all_families_resolve(self):
        profile = json.loads(json.dumps(self.profile))
        integration = profile["promotion_evidence"]["architect_integration"]
        integration["latest_family_resolution"]["emotional_development"] = (
            "narrative_load_architect_win_from_multi_seed"
        )
        integration["latest_resolved_summary"]["inconclusive"] = 0
        integration["latest_resolved_summary"]["narrative_load_architect_wins"] = 3
        result = evaluate_narrative_load_promotion_gate(profile)
        self.assertTrue(result["evidence_pass"])
        self.assertEqual(result["state"], "AWAIT_EXPLICIT_PROMOTION_DECISION")
        self.assertEqual(result["unresolved_families"], [])
        self.assertFalse(result["production_gate_pass"])

    def test_promotion_gate_blocks_latest_baseline_loss(self):
        profile = json.loads(json.dumps(self.profile))
        profile["promotion_evidence"]["architect_integration"][
            "latest_resolved_summary"
        ]["baseline_wins"] = 1
        result = evaluate_narrative_load_promotion_gate(profile)
        self.assertFalse(result["evidence_pass"])
        self.assertEqual(result["state"], "BLOCKED_EVIDENCE")
        self.assertIn("latest_baseline_consensus_loss", result["blockers"])

    def test_physical_affordance_and_terminal_append_guards(self):
        spine = self.profile["spine"]
        writer = self.profile["writer_contract"]
        self.assertTrue(spine["preserve_premise_physical_affordances"])
        self.assertTrue(spine["may_not_invent_unstated_physical_inability"])
        self.assertTrue(writer["may_not_append_post_closure_action"])

    def test_architect_integration_qualification_is_closed(self):
        policy = self.profile["integration_policy"]
        evidence = self.profile["promotion_evidence"]
        self.assertTrue(policy["architect_integration_qualified"])
        self.assertFalse(policy["requires_architect_integration_probe_before_production"])
        self.assertEqual(policy["max_semantic_replans_on_invalid_plan"], 1)
        self.assertTrue(policy["semantic_replan_only_on_deterministic_validation_failure"])
        self.assertEqual(policy["normal_path_extra_model_hops"], 0)
        self.assertTrue(evidence["architect_integration_qualification_completed"])
        self.assertEqual(
            evidence["architect_integration"]["targeted_v2_run"],
            36228645350,
        )
        self.assertEqual(
            evidence["architect_integration"]["latest_resolved_summary"]["baseline_wins"],
            0,
        )
        self.assertFalse(
            evidence["architect_integration"]["extra_mandatory_planner_hop"]
        )


if __name__ == "__main__":
    unittest.main()
