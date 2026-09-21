import copy
import unittest

from src.judge_gold_corpus import validate_manifest


def make_case(index: int, partition: str = "calibration") -> dict:
    return {
        "case_id": f"jg-{index:03d}",
        "source_family_id": f"sf-{index:03d}",
        "source_path": f"data/raw/story_{index:04d}.json",
        "source_blob_sha": "a" * 40,
        "partition": partition,
        "case_kind": "source",
        "language_variants": ["tr_native"],
        "critical_protected": index == 99,
        "mutation": None,
        "materialization": {"status": "source_artifact", "content_sha256": None},
        "human_reference": {"status": "pending_blind_review"},
    }


class JudgeGoldCorpusTests(unittest.TestCase):
    def test_structural_plan_can_be_valid_but_not_promotion_ready(self) -> None:
        cases = []
        for i in range(1, 101):
            partition = "calibration" if i <= 40 else "development_holdout" if i <= 70 else "final_holdout"
            case = make_case(i, partition)
            if i == 100:
                case["language_variants"] = ["tr_native", "controlled_en_projection"]
            cases.append(case)
        result = validate_manifest({"cases": cases})
        self.assertTrue(result["valid"])
        self.assertFalse(result["promotion_ready"])
        self.assertEqual(result["case_count"], 100)

    def test_source_family_partition_leak_is_rejected(self) -> None:
        cases = []
        for i in range(1, 101):
            partition = "calibration" if i <= 40 else "development_holdout" if i <= 70 else "final_holdout"
            case = make_case(i, partition)
            if i == 100:
                case["language_variants"] = ["tr_native", "controlled_en_projection"]
            cases.append(case)
        leaked = copy.deepcopy(cases[50])
        leaked["case_id"] = "jg-101"
        leaked["source_family_id"] = cases[0]["source_family_id"]
        leaked["partition"] = "final_holdout"
        cases.append(leaked)
        result = validate_manifest({"cases": cases})
        self.assertFalse(result["valid"])
        self.assertTrue(any("leaks across" in e for e in result["errors"]))

    def test_final_label_requires_all_criteria(self) -> None:
        cases = []
        for i in range(1, 101):
            partition = "calibration" if i <= 40 else "development_holdout" if i <= 70 else "final_holdout"
            case = make_case(i, partition)
            if i == 100:
                case["language_variants"] = ["tr_native", "controlled_en_projection"]
            cases.append(case)
        cases[0]["human_reference"] = {
            "status": "final",
            "decision": "PASS",
            "scores": {"coherence": 5},
        }
        result = validate_manifest({"cases": cases})
        self.assertFalse(result["valid"])
        self.assertTrue(any("instruction_following" in e for e in result["errors"]))


if __name__ == "__main__":
    unittest.main()
