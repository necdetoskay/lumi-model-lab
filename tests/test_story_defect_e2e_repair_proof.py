import json
import unittest
from pathlib import Path

from src.story_defect_corpus import load_clean_admission
from src.story_defect_synthetic_corpus import load_synthetic_corpus


FIXTURE = Path("experiments/fixtures/story_defect_e2e_repair_proof.v1.json")
MANIFEST = Path("experiments/fixtures/story_defect_d1_validation_manifest.tr-age4.v1.json")


class StoryDefectE2ERepairProofContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.corpus = load_synthetic_corpus()
        cls.admission = load_clean_admission()

    def test_fixture_has_four_defects_and_one_clean_control(self):
        cases = self.fixture["cases"]
        self.assertEqual(len(cases), 5)
        self.assertEqual(sum(row["kind"] == "defect" for row in cases), 4)
        self.assertEqual(sum(row["kind"] == "clean" for row in cases), 1)

    def test_defect_cases_are_validated_gold_local_repair_cases(self):
        gold_by_id = {
            row["case_id"]: row
            for row in self.manifest["validated_cases"]
        }
        corpus_by_id = {
            row["case_id"]: row
            for row in self.corpus["cases"]
        }
        sources = set()
        families = set()
        for spec in self.fixture["cases"]:
            if spec["kind"] != "defect":
                continue
            gold = gold_by_id[spec["case_id"]]
            case = corpus_by_id[spec["case_id"]]
            self.assertEqual(gold["family"], spec["expected_family"])
            self.assertEqual(case["gold"]["repair_scope"], "LOCAL_REPAIR")
            self.assertTrue(case["mutation"]["injected_text"])
            self.assertIn(gold["severity"], {"serious", "critical"})
            sources.add(case["source_id"])
            families.add(gold["family"])

        self.assertEqual(len(sources), 4)
        self.assertEqual(
            families,
            {
                "response_causality",
                "state_continuity",
                "physical_feasibility",
                "closure_integrity",
            },
        )

    def test_clean_control_is_independently_admitted(self):
        admitted = {
            row["source_id"]
            for row in self.admission["entries"]
            if row["admitted_as_clean_source"] is True
        }
        clean = next(row for row in self.fixture["cases"] if row["kind"] == "clean")
        self.assertIn(clean["source_id"], admitted)

    def test_success_gate_is_exactly_five_of_five(self):
        self.assertEqual(self.fixture["success_gate"]["required_passes"], 5)


if __name__ == "__main__":
    unittest.main()
