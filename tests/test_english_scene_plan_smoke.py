from __future__ import annotations

import unittest

from src.english_scene_plan_smoke import build_jev_questions, summarize_jev, validate_haiku, validate_plan
from src.schemas import StorySpec

def _spec() -> StorySpec:
    return StorySpec(age_min=6, age_max=8, language="en", target_words=2000, title_hint="Signal", protagonist="Ada", setting="coast", theme="observation", premise="Ada investigates a signal.", constraints=["Ada corrects a wrong assumption.", "Use two clues."])

def _plan() -> dict:
    return {
        "story_title": "Signal",
        "story_contract": {
            "protagonist_goal": "Find the signal source.",
            "central_problem": "The signal appears briefly.",
            "solution_principle": "Combine tide and marker clues.",
            "theme_thread": "Patient observation.",
            "ending_state": "Source understood.",
            "required_constraints": ["Ada corrects a wrong assumption.", "Use two clues."],
            "prohibited_events": ["Do not solve before Scene 5."],
        },
        "scenes": [
            {
                "index": i,
                "purpose": f"Purpose {i}",
                "entry_state": f"Entry {i}",
                "beats": [f"Beat {i}a", f"Beat {i}b"],
                "must_include": [f"Required {i}"],
                "must_not_do": [f"Guard {i}"],
                "handoff": f"Handoff {i}",
                "open_threads_after": [f"Thread {i}"],
            }
            for i in range(1, 7)
        ],
    }

class EnglishScenePlanSmokeTests(unittest.TestCase):
    def test_valid_plan_shape(self):
        self.assertEqual(validate_plan(_plan(), _spec()), [])

    def test_constraint_underrepresentation_fails(self):
        value = _plan()
        value["story_contract"]["required_constraints"] = ["one"]
        self.assertIn("required_constraints_underrepresented", validate_plan(value, _spec()))

    def test_jev_question_set_is_atomic(self):
        questions = build_jev_questions()
        self.assertEqual(len(questions), 8)
        self.assertEqual(questions["causal_continuity"]["type"], "noul")
        self.assertEqual(questions["next_action"]["type"], "choice")

    def test_jev_summary_continue(self):
        keys = ("causal_continuity", "goal_continuity", "constraint_coverage", "information_progression", "no_unexplained_dependencies", "no_early_resolution", "ending_coherence")
        body = {"answers": {key: {"type": "noul", "noul": 0.95} for key in keys}}
        body["answers"]["next_action"] = {"type": "choice", "choice": "CONTINUE", "confidence": 0.93}
        result = summarize_jev(body)
        self.assertEqual(result["mode"], "shadow")
        self.assertEqual(result["shadow_signal"], "CONTINUE")
        self.assertEqual(result["below_threshold"], {})

    def test_haiku_plan_gate(self):
        payload = {"scores": {"causal_continuity": 5, "protagonist_goal_continuity": 5, "constraint_coverage": 5, "information_progression": 4, "no_unexplained_dependencies": 5, "no_early_resolution": 5, "ending_coherence": 4}, "critical_failures": [], "scene_risks": [], "summary": "coherent"}
        self.assertTrue(validate_haiku(payload)["accepted"])

if __name__ == "__main__":
    unittest.main()