import copy
import unittest

import yaml

from src.judge_atomic_rubric import validate_rubric


VALID = yaml.safe_load(
    """
rubric_id: test-rubric
rubric_version: "1"
score_range: [0, 4]
aggregate_story_verdict: forbidden_in_p3
evidence_gate:
  version: "1"
  required_for_all_dimensions: true
  question_id_pattern: "{dimension_id}__evidence"
  type: choice
  choices: [SUFFICIENT, INSUFFICIENT_EVIDENCE]
  tr_instruction_template: yeterli mi
  en_instruction_template: sufficient evidence
  insufficient_policy: ignore_score_and_abstain
  escalation_eligible: true
language_variants:
  - {id: TR_NATIVE}
  - {id: EN_REFERENCE}
  - {id: CONTROLLED_EN_PROJECTION}
dimensions:
  - id: contract_alignment
    owner_candidate: decision_engine
    critical_capable: true
    question: {type: score, tr: soru, en: question}
    levels: {tr: [a,b,c,d,e], en: [a,b,c,d,e]}
    anchors: {bad: x, borderline: y, good: z}
  - id: world_state_consistency
    owner_candidate: decision_engine
    critical_capable: true
    question: {type: score, tr: soru, en: question}
    levels: {tr: [a,b,c,d,e], en: [a,b,c,d,e]}
    anchors: {bad: x, borderline: y, good: z}
  - id: age_fit
    owner_candidate: decision_engine
    critical_capable: true
    question: {type: score, tr: soru, en: question}
    levels: {tr: [a,b,c,d,e], en: [a,b,c,d,e]}
    anchors: {bad: x, borderline: y, good: z}
  - id: relationship_consistency
    owner_candidate: decision_engine
    critical_capable: true
    question: {type: score, tr: soru, en: question}
    levels: {tr: [a,b,c,d,e], en: [a,b,c,d,e]}
    anchors: {bad: x, borderline: y, good: z}
  - id: knowledge_consistency
    owner_candidate: decision_engine
    critical_capable: true
    question: {type: score, tr: soru, en: question}
    levels: {tr: [a,b,c,d,e], en: [a,b,c,d,e]}
    anchors: {bad: x, borderline: y, good: z}
  - id: narrative_progression
    owner_candidate: hybrid
    critical_capable: false
    question: {type: score, tr: soru, en: question}
    levels: {tr: [a,b,c,d,e], en: [a,b,c,d,e]}
    anchors: {bad: x, borderline: y, good: z}
llm_retained_dimensions:
  - {id: creativity}
  - {id: literary_style_quality}
  - {id: deep_holistic_coherence}
calibration:
  anchor_source: dedicated_synthetic_descriptions
  final_holdout_examples_allowed_as_anchors: false
  thresholds_frozen: false
  status: PENDING_HUMAN_CALIBRATION
"""
)


class JudgeAtomicRubricTests(unittest.TestCase):
    def test_frozen_structure_is_valid_but_not_calibrated(self) -> None:
        result = validate_rubric(copy.deepcopy(VALID))
        self.assertTrue(result["valid"])
        self.assertFalse(result["calibration_ready"])


    def test_missing_evidence_gate_is_rejected(self) -> None:
        data = copy.deepcopy(VALID)
        data.pop("evidence_gate")
        result = validate_rubric(data)
        self.assertFalse(result["valid"])
        self.assertTrue(any("evidence_gate" in e for e in result["errors"]))

    def test_evidence_gate_cannot_force_score_on_missing_evidence(self) -> None:
        data = copy.deepcopy(VALID)
        data["evidence_gate"]["insufficient_policy"] = "use_midpoint_score"
        result = validate_rubric(data)
        self.assertFalse(result["valid"])
        self.assertTrue(any("ignore score and abstain" in e for e in result["errors"]))

    def test_aggregate_story_verdict_is_rejected(self) -> None:
        data = copy.deepcopy(VALID)
        data["aggregate_story_verdict"] = "average_threshold"
        result = validate_rubric(data)
        self.assertFalse(result["valid"])
        self.assertTrue(any("aggregate story verdict" in e for e in result["errors"]))

    def test_missing_language_variant_is_rejected(self) -> None:
        data = copy.deepcopy(VALID)
        data["language_variants"] = data["language_variants"][:2]
        result = validate_rubric(data)
        self.assertFalse(result["valid"])
        self.assertTrue(any("language variants" in e for e in result["errors"]))

    def test_final_holdout_anchor_leak_is_rejected(self) -> None:
        data = copy.deepcopy(VALID)
        data["calibration"]["final_holdout_examples_allowed_as_anchors"] = True
        result = validate_rubric(data)
        self.assertFalse(result["valid"])
        self.assertTrue(any("final holdout" in e for e in result["errors"]))

    def test_calibration_ready_requires_frozen_thresholds_and_status(self) -> None:
        data = copy.deepcopy(VALID)
        data["calibration"]["thresholds_frozen"] = True
        data["calibration"]["status"] = "CALIBRATED"
        result = validate_rubric(data)
        self.assertTrue(result["valid"])
        self.assertTrue(result["calibration_ready"])


if __name__ == "__main__":
    unittest.main()
