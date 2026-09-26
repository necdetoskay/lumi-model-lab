import unittest

from src.story_narrative_load_plan import (
    can_advance_to_writer,
    candidate_requires_supporting_thread,
    validate_narrative_load_plan,
)


class StoryNarrativeLoadPlanTests(unittest.TestCase):
    def valid_plan(self):
        functions = [
            "setup",
            "signal",
            "hypothesis",
            "test",
            "complication",
            "observation",
            "decision",
            "payoff",
        ]
        return {
            "supporting_thread": {
                "used": False,
                "description": "",
                "why_it_belongs": "",
            },
            "spine": [
                {
                    "density": "develop",
                    "function": function,
                    "beat": f"Concrete event {i}",
                }
                for i, function in enumerate(functions)
            ],
        }

    def test_valid_eight_beat_main_arc_can_advance(self):
        plan = self.valid_plan()
        self.assertEqual(validate_narrative_load_plan(plan), [])
        self.assertTrue(can_advance_to_writer(plan))

    def test_supporting_thread_is_optional(self):
        plan = self.valid_plan()
        self.assertFalse(candidate_requires_supporting_thread(plan))
        self.assertTrue(can_advance_to_writer(plan))

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
        plan["spine"] = plan["spine"] + [
            {"density": "develop", "function": "observation", "beat": "x"},
            {"density": "develop", "function": "decision", "beat": "y"},
            {"density": "develop", "function": "payoff", "beat": "z"},
            {"density": "brief", "function": "closure", "beat": "end"},
            {"density": "brief", "function": "closure", "beat": "extra"},
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


if __name__ == "__main__":
    unittest.main()
