import json
import unittest
from pathlib import Path

from src.story_defect_corpus import load_clean_admission


FIXTURE = Path("experiments/fixtures/story_defect_natural_e2e_repair_proof.v1.json")
NATURAL = Path("experiments/fixtures/story_defect_natural_positive_pool.tr-age4.v0.1.json")


class NaturalE2ERepairProofContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.natural = json.loads(NATURAL.read_text(encoding="utf-8"))
        cls.admission = load_clean_admission()

    def test_fixture_is_four_natural_defects_plus_one_clean(self):
        cases = self.fixture["cases"]
        self.assertEqual(len(cases), 5)
        self.assertEqual(sum(row["kind"] == "defect" for row in cases), 4)
        self.assertEqual(sum(row["kind"] == "clean" for row in cases), 1)

    def test_frozen_scoring_fields_match_natural_positive_pool(self):
        by_source = {row["source_id"]: row for row in self.natural["cases"]}
        scopes = []
        families = set()

        for spec in self.fixture["cases"]:
            if spec["kind"] != "defect":
                continue
            self.assertIn(spec["source_id"], by_source)
            findings = [
                finding
                for finding in by_source[spec["source_id"]]["findings"]
                if finding["defect_family"] == spec["expected_family"]
            ]
            self.assertEqual(len(findings), 1)
            gold = findings[0]
            self.assertEqual(spec["expected_span_ids"], gold["span_ids"])
            self.assertEqual(spec["expected_repair_scope"], gold["repair_scope"])
            self.assertIn(gold["severity"], {"serious", "critical"})
            families.add(spec["expected_family"])
            scopes.append(spec["expected_repair_scope"])

        self.assertEqual(
            families,
            {"response_causality", "state_continuity", "causal_logic", "closure_integrity"},
        )
        self.assertEqual(scopes.count("LOCAL_REPAIR"), 3)
        self.assertEqual(scopes.count("STRUCTURAL_REPAIR"), 1)

    def test_first_execution_gate_is_n1_local_repair(self):
        self.assertEqual(self.fixture["execution_gate"]["first_proof_id"], "N1_RESPONSE")
        n1 = next(row for row in self.fixture["cases"] if row["proof_id"] == "N1_RESPONSE")
        self.assertEqual(n1["expected_family"], "response_causality")
        self.assertEqual(n1["expected_repair_scope"], "LOCAL_REPAIR")

    def test_clean_control_is_admitted_clean(self):
        admitted = {
            row["source_id"]
            for row in self.admission["entries"]
            if row["admitted_as_clean_source"] is True
        }
        clean = next(row for row in self.fixture["cases"] if row["kind"] == "clean")
        self.assertIn(clean["source_id"], admitted)

    def test_success_gate_is_five_of_five(self):
        self.assertEqual(self.fixture["success_gate"]["required_passes"], 5)


if __name__ == "__main__":
    unittest.main()
