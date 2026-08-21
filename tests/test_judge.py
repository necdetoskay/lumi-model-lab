import unittest

from src.judge import extract_json_object, make_decision, validate_judge_payload
from src.schemas import JudgePayload


GOOD_PAYLOAD = {
    "scores": {
        "instruction_following": 5,
        "coherence": 4,
        "character_consistency": 4,
        "age_appropriateness": 5,
        "creativity": 4,
        "style_quality": 4,
    },
    "reasons": {
        "instruction_following": "Brief ve kısıtlar karşılanmış.",
        "coherence": "Olaylar neden-sonuç ilişkisiyle ilerliyor.",
        "character_consistency": "Karakter davranışı tutarlı.",
        "age_appropriateness": "Dil hedef yaşa uygun.",
        "creativity": "Özgün keşif unsurları var.",
        "style_quality": "Akıcı ve anlaşılır.",
    },
    "critical_failures": [],
}


class JudgeTests(unittest.TestCase):
    def test_extracts_json_from_fence(self) -> None:
        text = "```json\n" + __import__("json").dumps(GOOD_PAYLOAD) + "\n```"
        self.assertEqual(extract_json_object(text)["scores"]["coherence"], 4)

    def test_good_payload_is_accepted(self) -> None:
        result = validate_judge_payload(GOOD_PAYLOAD)
        decision = make_decision(
            result,
            acceptance_threshold=4.0,
            minimum_criterion_score=3,
        )
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.reasons, [])

    def test_critical_failure_rejects_even_with_high_scores(self) -> None:
        payload = {**GOOD_PAYLOAD, "critical_failures": ["major_constraint_violation"]}
        result = JudgePayload.model_validate(payload)
        decision = make_decision(
            result,
            acceptance_threshold=4.0,
            minimum_criterion_score=3,
        )
        self.assertFalse(decision.accepted)
        self.assertIn("critical_failures_present", decision.reasons)


if __name__ == "__main__":
    unittest.main()
