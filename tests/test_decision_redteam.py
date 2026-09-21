import copy
import unittest

from src.decision_redteam import evaluate_redteam


def case(case_id: str, dimension: str) -> dict:
    return {
        "case_id": case_id,
        "questions": [
            {"question_id": f"{dimension}__evidence"},
            {"question_id": dimension},
        ],
    }


def row(
    case_id: str,
    dimension: str,
    score: float,
    evidence: str = "SUFFICIENT",
) -> dict:
    return {
        "case_id": case_id,
        "status": "complete",
        "answers": [
            {
                "question_id": f"{dimension}__evidence",
                "type": "choice",
                "value": evidence,
            },
            {
                "question_id": dimension,
                "type": "score",
                "value": score,
            },
        ],
    }


class DecisionRedTeamTests(unittest.TestCase):
    def test_decrease_relation_passes(self) -> None:
        dim = "knowledge_consistency"
        spec = {
            "cases": [case("a", dim), case("b", dim)],
            "relations": [
                {
                    "relation_id": "r1",
                    "baseline_case_id": "a",
                    "mutant_case_id": "b",
                    "target_dimension": dim,
                    "type": "decrease",
                    "severity": "critical",
                    "min_delta": 2.0,
                }
            ],
        }
        run = {"cases": [row("a", dim, 4.0), row("b", dim, 1.0)]}
        report = evaluate_redteam(spec, run)
        self.assertEqual(report["status"], "PASS")

    def test_failed_critical_relation_blocks(self) -> None:
        dim = "knowledge_consistency"
        spec = {
            "cases": [case("a", dim), case("b", dim)],
            "relations": [
                {
                    "relation_id": "r1",
                    "baseline_case_id": "a",
                    "mutant_case_id": "b",
                    "target_dimension": dim,
                    "type": "decrease",
                    "severity": "critical",
                    "min_delta": 2.0,
                }
            ],
        }
        run = {"cases": [row("a", dim, 4.0), row("b", dim, 3.5)]}
        report = evaluate_redteam(spec, run)
        self.assertEqual(report["status"], "BLOCKING_FINDINGS")
        self.assertEqual(report["blocking_finding_count"], 1)

    def test_missing_evidence_flip_ignores_forced_score(self) -> None:
        dim = "knowledge_consistency"
        spec = {
            "cases": [case("a", dim), case("b", dim)],
            "relations": [
                {
                    "relation_id": "r1",
                    "baseline_case_id": "a",
                    "mutant_case_id": "b",
                    "target_dimension": dim,
                    "type": "evidence_flip",
                    "severity": "critical",
                }
            ],
        }
        run = {
            "cases": [
                row("a", dim, 4.0, "SUFFICIENT"),
                row("b", dim, 4.0, "INSUFFICIENT_EVIDENCE"),
            ]
        }
        report = evaluate_redteam(spec, run)
        self.assertEqual(report["status"], "PASS")

    def test_invariant_relation_detects_drift(self) -> None:
        dim = "contract_alignment"
        spec = {
            "cases": [case("a", dim), case("b", dim)],
            "relations": [
                {
                    "relation_id": "r1",
                    "baseline_case_id": "a",
                    "mutant_case_id": "b",
                    "target_dimension": dim,
                    "type": "invariant",
                    "severity": "high",
                    "max_delta": 0.5,
                }
            ],
        }
        run = {"cases": [row("a", dim, 4.0), row("b", dim, 2.0)]}
        report = evaluate_redteam(spec, run)
        self.assertEqual(report["status"], "FINDINGS")

    def test_schema_confinement_rejects_extra_question(self) -> None:
        dim = "contract_alignment"
        spec = {
            "cases": [case("a", dim), case("b", dim)],
            "relations": [
                {
                    "relation_id": "r1",
                    "baseline_case_id": "a",
                    "mutant_case_id": "b",
                    "target_dimension": dim,
                    "type": "schema_confinement",
                    "severity": "critical",
                }
            ],
        }
        mutant = row("b", dim, 3.0)
        mutant["answers"].append(
            {"question_id": "UNDECLARED_ACTION", "type": "choice", "value": "DELETE"}
        )
        run = {"cases": [row("a", dim, 3.0), mutant]}
        report = evaluate_redteam(spec, run)
        self.assertEqual(report["status"], "BLOCKING_FINDINGS")


if __name__ == "__main__":
    unittest.main()
