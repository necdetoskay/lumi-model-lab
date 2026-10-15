"""SERA M3 JEV contract tests with simulated typed choices (no provider calls)."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import unittest

from experiments.sera.coverage import CoverageError, reconcile
from experiments.sera.gold_calibration import build_report
from experiments.sera.jev_verifier import (
    adjudicate, build_atomic_questions, call_live_jev,
)

CORPUS = json.loads((Path(__file__).resolve().parents[1]
                     / "fixtures/gold_mara_m2_v0.1.json").read_text(
    encoding="utf-8"
))


def bundle_for(case_id):
    case = next(c for c in CORPUS["cases"] if c["id"] == case_id)
    writer = build_report(case, "WRITER")
    independent = build_report(case, "INDEPENDENT")
    coverage = reconcile(
        prose=case["prose"], scene_key="hook_empty_platform",
        entry_revision=0, registry=case["registry"],
        writer=writer, independent=independent,
    )
    bundle = build_atomic_questions(
        prose=case["prose"], scene_key="hook_empty_platform",
        entry_revision=0, coverage=coverage, registry=case["registry"],
        writer=writer, independent=independent,
    )
    return bundle


def answer_all(bundle, choice="SUPPORTED", confidence=0.9):
    return {qid: {"choice": choice, "confidence": confidence}
            for qid in bundle["questions"]}


class AtomicJevTests(unittest.TestCase):
    def test_bundle_claims_are_atomic_and_producer_blind(self):
        bundle = bundle_for("manifest_is_not_physical_arrival")
        self.assertEqual(bundle["schema"], "sera.jev-atomic.v0.1")
        self.assertGreater(len(bundle["questions"]), 2)
        self.assertEqual(set(bundle["questions"]),
                         set(bundle["candidate_claims"]))
        self.assertNotIn("WRITER", json.dumps(bundle["state"]))
        self.assertNotIn("INDEPENDENT", json.dumps(bundle["state"]))
        roles = {x["claim"]["role"] for x in bundle["candidate_claims"].values()}
        self.assertIn("REPORTED_ONLY", roles)
        self.assertIn("PRESENT", roles)

    def test_jev_agreement_never_commits_state(self):
        bundle = bundle_for("aligned_watch_transfer")
        result = adjudicate(bundle=bundle, answers=answer_all(bundle))
        self.assertEqual(result["next_action"],
                         "PENDING_DETERMINISTIC_AND_COMPLETENESS_REVIEW")
        self.assertFalse(result["commit_authorized"])
        self.assertFalse(result["persistence_authorized"])

    def test_wrong_physical_arrival_can_be_marked_contradicted(self):
        bundle = bundle_for("manifest_is_not_physical_arrival")
        answers = answer_all(bundle)
        false_physical = next(qid for qid, x in bundle["candidate_claims"].items()
                              if x["claim"].get("entity_ref") == "train_41" and
                              x["claim"].get("role") == "PRESENT")
        answers[false_physical]["choice"] = "CONTRADICTED"
        result = adjudicate(bundle=bundle, answers=answers)
        self.assertEqual(result["next_action"], "LOCAL_REPAIR_REQUIRED")
        self.assertFalse(result["commit_authorized"])

    def test_insufficient_evidence_requires_escalation(self):
        bundle = bundle_for("aligned_watch_transfer")
        answers = answer_all(bundle)
        next(iter(answers.values()))["choice"] = "INSUFFICIENT_EVIDENCE"
        result = adjudicate(bundle=bundle, answers=answers)
        self.assertEqual(result["next_action"], "ESCALATE")

    def test_reconciliation_dispute_not_silently_cleared(self):
        bundle = bundle_for("independent_catches_clock")
        self.assertEqual(bundle["m2_status"], "HOLD")
        result = adjudicate(bundle=bundle, answers=answer_all(bundle))
        self.assertEqual(result["next_action"], "RECONCILIATION_REQUIRED")

    def test_both_extractors_miss_event_is_not_jev_proof(self):
        bundle = bundle_for("two_extractors_miss_new_item")
        self.assertEqual(bundle["questions"], {})
        result = adjudicate(bundle=bundle, answers={})
        self.assertEqual(result["next_action"], "ESCALATE_NO_CLAIMS")
        self.assertFalse(result["commit_authorized"])

    def test_missing_question_response_is_fail_closed(self):
        bundle = bundle_for("aligned_watch_transfer")
        answers = answer_all(bundle)
        answers.pop(next(iter(answers)))
        with self.assertRaisesRegex(CoverageError, "JEV_ANSWER_SET_MISMATCH"):
            adjudicate(bundle=bundle, answers=answers)

    def test_invalid_choice_and_nan_confidence_rejected(self):
        bundle = bundle_for("aligned_watch_transfer")
        answers = answer_all(bundle)
        qid = next(iter(answers))
        answers[qid]["choice"] = "PASS"
        with self.assertRaisesRegex(CoverageError, "JEV_CHOICE_INVALID"):
            adjudicate(bundle=bundle, answers=answers)
        answers[qid] = {"choice": "SUPPORTED", "confidence": float("nan")}
        with self.assertRaisesRegex(CoverageError, "JEV_CONFIDENCE_INVALID"):
            adjudicate(bundle=bundle, answers=answers)

    def test_stale_prose_fingerprint_blocks_questions(self):
        case = CORPUS["cases"][0]
        writer = build_report(case, "WRITER")
        independent = build_report(case, "INDEPENDENT")
        coverage = reconcile(
            prose=case["prose"], scene_key="hook_empty_platform",
            entry_revision=0, registry=case["registry"],
            writer=writer, independent=independent,
        )
        coverage["prose_sha256"] = "bad"
        with self.assertRaisesRegex(CoverageError, "JEV_COVERAGE_BINDING_INVALID"):
            build_atomic_questions(
                prose=case["prose"], scene_key="hook_empty_platform",
                entry_revision=0, coverage=coverage, registry=case["registry"],
                writer=writer, independent=independent,
            )

    def test_provider_call_has_explicit_billable_gate(self):
        bundle = bundle_for("aligned_watch_transfer")
        with self.assertRaisesRegex(CoverageError, "BILLABLE_JEV_NOT_AUTHORIZED"):
            call_live_jev(bundle=bundle, api_key="dummy", allow_billable=False)
        with self.assertRaisesRegex(CoverageError, "OPENROUTER_API_KEY_REQUIRED"):
            call_live_jev(bundle=bundle, api_key="", allow_billable=True)


if __name__ == "__main__":
    unittest.main()
