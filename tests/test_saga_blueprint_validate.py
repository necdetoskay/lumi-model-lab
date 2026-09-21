import copy
import json
import unittest
from pathlib import Path

from src.saga_blueprint_validate import (
    apply_mutations,
    run_falsification_suite,
    validate_static,
)


ROOT = Path(__file__).resolve().parents[1]
BASE_RESPONSE = (
    ROOT
    / "data"
    / "specifications"
    / "saga_lab"
    / "narrative_architect_fixture_response_v1.json"
)
FALSIFICATION = (
    ROOT
    / "data"
    / "specifications"
    / "saga_lab"
    / "blueprint_static_falsification_v1.json"
)


def base_blueprint() -> dict:
    return json.loads(BASE_RESPONSE.read_text(encoding="utf-8"))["blueprint"]


class SagaBlueprintValidatorTests(unittest.TestCase):
    def test_clean_reference_blueprint_passes_hard_gate(self) -> None:
        report = validate_static(base_blueprint())
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["semantic_evaluation_eligible"])
        self.assertEqual(report["hard_finding_count"], 0)

    def test_frozen_falsification_suite_passes(self) -> None:
        spec = json.loads(FALSIFICATION.read_text(encoding="utf-8"))
        report = run_falsification_suite(
            base_payload=base_blueprint(),
            spec=spec,
        )
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["case_count"], 9)
        self.assertEqual(report["pass_count"], 9)

    def test_mandatory_milestone_is_hard_block_and_cannot_reach_semantic_gate(self) -> None:
        payload = base_blueprint()
        payload["saga_blueprint"]["threads"][0]["milestones"][0]["required"] = True
        report = validate_static(payload)
        codes = {item["code"] for item in report["findings"]}
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["semantic_evaluation_eligible"])
        self.assertIn("MANDATORY_MILESTONE", codes)

    def test_explicit_numbered_story_sequence_is_rejected(self) -> None:
        payload = base_blueprint()
        payload["saga_blueprint"]["threads"][0]["premise"] = (
            "Story 1 finds the clue. Story 2 forces the search. Story 3 resolves it."
        )
        report = validate_static(payload)
        codes = {item["code"] for item in report["findings"]}
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("FIXED_STORY_SEQUENCE_LANGUAGE", codes)

    def test_explicit_future_choice_language_is_rejected(self) -> None:
        payload = base_blueprint()
        payload["saga_blueprint"]["threads"][0]["branches"][0]["paths"][0][
            "description"
        ] = "The character will choose to travel north and discover the answer."
        report = validate_static(payload)
        codes = {item["code"] for item in report["findings"]}
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("FORCED_FUTURE_CHOICE_LANGUAGE", codes)

    def test_near_duplicate_seed_is_review_finding_not_silent(self) -> None:
        payload = base_blueprint()
        source = copy.deepcopy(payload["saga_blueprint"]["threads"][0]["seeds"][0])
        source["key"] = "seed_03"
        source["summary"] = (
            "A catalog card points to a ledger location that no longer matches "
            "the current shelf map."
        )
        payload["saga_blueprint"]["threads"][0]["seeds"].append(source)
        report = validate_static(payload)
        codes = {item["code"] for item in report["findings"]}
        self.assertIn("NEAR_DUPLICATE_SEED_CONTENT", codes)
        self.assertEqual(report["status"], "NEEDS_REVIEW")
        self.assertTrue(report["semantic_evaluation_eligible"])

    def test_reveal_policy_exact_overlap_is_hard_block(self) -> None:
        payload = base_blueprint()
        seed = payload["saga_blueprint"]["threads"][0]["seeds"][0]
        seed["visibility_policy"]["allowed_usage"] = [
            seed["visibility_policy"]["forbidden_usage"][0]
        ]
        report = validate_static(payload)
        codes = {item["code"] for item in report["findings"]}
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("REVEAL_POLICY_CONTRADICTION", codes)

    def test_unknown_reference_is_mapped_to_critical_static_failure(self) -> None:
        payload = base_blueprint()
        payload["saga_blueprint"]["threads"][0]["seeds"][0]["may_unlock"] = [
            "missing_node"
        ]
        report = validate_static(payload)
        codes = {item["code"] for item in report["findings"]}
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("SCHEMA_OR_REFERENCE_INVALID", codes)

    def test_mutation_helper_does_not_modify_base(self) -> None:
        base = base_blueprint()
        original = copy.deepcopy(base)
        mutated = apply_mutations(
            base,
            [
                {
                    "op": "set",
                    "path": "/saga_blueprint/threads/0/milestones/0/required",
                    "value": True,
                }
            ],
        )
        self.assertFalse(base["saga_blueprint"]["threads"][0]["milestones"][0]["required"])
        self.assertTrue(mutated["saga_blueprint"]["threads"][0]["milestones"][0]["required"])
        self.assertEqual(base, original)


if __name__ == "__main__":
    unittest.main()
