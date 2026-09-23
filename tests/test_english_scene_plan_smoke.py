from __future__ import annotations

import unittest
from unittest.mock import patch

from src.english_scene_plan_smoke import build_jev_questions, call_structured_json_with_retry, summarize_jev, validate_haiku, validate_plan
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
            "required_constraint_ids": ["C1", "C2"],
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
                "constraint_ids": ["C1"] if i < 6 else ["C2"],
                "prior_evidence": [] if i == 1 else [f"Evidence from scene {i - 1}"],
                "handoff": f"Handoff {i}",
                "open_threads_after": [f"Thread {i}"],
            }
            for i in range(1, 7)
        ],
    }

class EnglishScenePlanSmokeTests(unittest.TestCase):
    @patch("src.english_scene_plan_smoke.call_openrouter")
    def test_plan_structured_json_retry_recovers(self, mock_call):
        body1 = {
            "choices": [{"finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 10,
                "total_tokens": 20,
                "cost": 0.001,
            },
        }
        body2 = {
            "choices": [{"finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
                "cost": 0.001,
            },
        }
        mock_call.side_effect = [
            (
                '{"story_title":"unfinished',
                body1,
                {"temperature": 0.2, "response_format": {"type": "json_object"}},
            ),
            (
                __import__("json").dumps(_plan()),
                body2,
                {"temperature": 0.2, "response_format": {"type": "json_object"}},
            ),
        ]
        payload, _, _, failures = call_structured_json_with_retry(
            api_key="test",
            model="qwen/qwen3.8-flash",
            system_prompt="system",
            user_prompt="user",
            temperature=0.2,
            max_tokens=None,
            seed=42,
            request_class="story_plan",
        )
        self.assertEqual(payload["story_title"], "Signal")
        self.assertEqual(len(failures), 1)
        self.assertEqual(mock_call.call_count, 2)
        self.assertIn(
            "FORMAT RECOVERY",
            mock_call.call_args_list[1].kwargs["user_prompt"],
        )

    def test_valid_plan_shape(self):
        self.assertEqual(validate_plan(_plan(), _spec()), [])

    def test_constraint_id_mismatch_fails(self):
        value = _plan()
        value["story_contract"]["required_constraint_ids"] = ["C1"]
        self.assertIn("required_constraint_ids_mismatch", validate_plan(value, _spec()))

    def test_scene_constraint_schedule_mismatch_fails(self):
        value = _plan()
        for scene in value["scenes"]:
            scene["constraint_ids"] = ["C1"]
        self.assertIn("scene_constraint_schedule_mismatch", validate_plan(value, _spec()))

    def test_scene_six_may_close_with_no_open_threads(self):
        value = _plan()
        value["scenes"][5]["open_threads_after"] = []
        self.assertEqual(validate_plan(value, _spec()), [])

    def test_pre_final_scene_still_requires_open_thread(self):
        value = _plan()
        value["scenes"][4]["open_threads_after"] = []
        self.assertIn(
            "scene_5_open_threads_after_missing",
            validate_plan(value, _spec()),
        )

    def test_prior_evidence_required_after_scene_one(self):
        value = _plan()
        value["scenes"][2]["prior_evidence"] = []
        self.assertIn("scene_3_prior_evidence_missing", validate_plan(value, _spec()))

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
        self.assertEqual(result["mode"], "advisory_repair")
        self.assertEqual(result["shadow_signal"], "CONTINUE")
        self.assertEqual(result["below_threshold"], {})

    def test_haiku_plan_gate(self):
        payload = {"scores": {"causal_continuity": 5, "protagonist_goal_continuity": 5, "constraint_coverage": 5, "information_progression": 4, "no_unexplained_dependencies": 5, "no_early_resolution": 5, "ending_coherence": 4}, "critical_failures": [], "scene_risks": [], "summary": "coherent"}
        self.assertTrue(validate_haiku(payload)["accepted"])

if __name__ == "__main__":
    unittest.main()