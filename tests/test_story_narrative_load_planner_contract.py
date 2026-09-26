import unittest

from src.story_spine_contract import load_profile, validate_spine


PROFILE_PATH = "configs/story_planning_profiles/tr_age4_narrative_load.v1.candidate.json"


class NarrativeLoadPlannerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = load_profile(PROFILE_PATH)

    def valid_plan(self):
        return {
            "design_rationale": "test",
            "supporting_thread": {
                "used": False,
                "description": "",
                "why_it_belongs": "",
            },
            "spine": [
                {"density": "brief", "function": "setup", "beat": "A başlar."},
                {"density": "develop", "function": "signal", "beat": "Bir işaret belirir."},
                {"density": "develop", "function": "hypothesis", "beat": "Karakter bir ihtimal düşünür."},
                {"density": "develop", "function": "test", "beat": "İhtimali dener."},
                {"density": "anchor", "function": "observation", "beat": "Yeni bir şey fark eder."},
                {"density": "develop", "function": "decision", "beat": "Bir karar verir."},
                {"density": "anchor", "function": "payoff", "beat": "Kararın sonucu görünür."},
                {"density": "anchor", "function": "closure", "beat": "Hikâye somut biçimde kapanır."},
            ],
        }

    def test_valid_minimum_spine_passes(self):
        self.assertEqual(validate_spine(self.profile, self.valid_plan()), [])

    def test_beat_count_is_bounded(self):
        plan = self.valid_plan()
        plan["spine"] = plan["spine"][:7]
        self.assertIn("beat_count_out_of_range:7", validate_spine(self.profile, plan))

    def test_required_setup_payoff_closure_are_locked(self):
        plan = self.valid_plan()
        plan["spine"][0]["function"] = "signal"
        errors = validate_spine(self.profile, plan)
        self.assertIn("missing_required_function:setup", errors)

    def test_closure_must_be_terminal(self):
        plan = self.valid_plan()
        plan["spine"][-1]["function"] = "observation"
        errors = validate_spine(self.profile, plan)
        self.assertIn("missing_required_function:closure", errors)
        self.assertIn("closure_not_terminal", errors)

    def test_duplicate_beat_text_is_rejected(self):
        plan = self.valid_plan()
        plan["spine"][3]["beat"] = plan["spine"][2]["beat"]
        self.assertIn("duplicate_beat_text", validate_spine(self.profile, plan))

    def test_unknown_density_is_rejected(self):
        plan = self.valid_plan()
        plan["spine"][1]["density"] = "huge"
        self.assertIn("invalid_density:1:huge", validate_spine(self.profile, plan))

    def test_supporting_thread_requires_description_and_rationale(self):
        plan = self.valid_plan()
        plan["supporting_thread"] = {
            "used": True,
            "description": "",
            "why_it_belongs": "",
        }
        errors = validate_spine(self.profile, plan)
        self.assertIn("supporting_thread_description_missing", errors)
        self.assertIn("supporting_thread_rationale_missing", errors)

    def test_supporting_thread_is_optional(self):
        plan = self.valid_plan()
        self.assertEqual(validate_spine(self.profile, plan), [])

    def test_policy_keeps_length_soft(self):
        self.assertEqual(
            self.profile["length_policy"]["generation_target_mode"],
            "soft",
        )
        self.assertFalse(
            self.profile["length_policy"]["publication_length_is_primary"]
        )
        self.assertTrue(self.profile["length_policy"]["quality_over_word_count"])

    def test_supporting_thread_cannot_exist_only_for_length(self):
        policy = self.profile["supporting_thread_policy"]
        self.assertTrue(policy["must_not_exist_only_for_length"])
        self.assertTrue(policy["must_rejoin_main_arc"])
        self.assertFalse(policy["may_add_named_character"])
        self.assertFalse(policy["may_add_relationship_canon"])
        self.assertFalse(policy["may_add_durable_world_fact"])


if __name__ == "__main__":
    unittest.main()
