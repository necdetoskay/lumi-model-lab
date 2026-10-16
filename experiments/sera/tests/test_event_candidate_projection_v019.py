"""SERA v0.19: autonomous noncanonical event correction and temporal guard."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.event_candidate_projection_v019 import project
from experiments.sera.semantic_recovery_v018 import execute as probe
from experiments.sera.tests.test_semantic_risks_v011 import SOURCE, report
from experiments.sera.tests.test_temporal_domains_v05 import (
    base, SCENE, WINDOW, ROUTES, evt,
)


def model(*, model, prepared):
    data = json.loads(prepared["request"]["messages"][1]["content"])
    question = data["independent_question"]
    if "physically change location" in question:
        verdict, kind, effect, quote = (
            "STATE_OBSERVATION", "OBSERVE", "CHARACTER_KNOWLEDGE", "turned"
        )
    elif "speech or writing" in question:
        verdict, kind, effect, quote = (
            "DOCUMENT_WRITE", "WRITE", "DOCUMENT", "added"
        )
    elif "reported statement" in question:
        verdict, kind, effect, quote = (
            "REPORTED_CLAIM", "CLAIM_MENTION", "NONE", "Arrival recorded"
        )
    else:
        verdict, kind, effect, quote = (
            "STATE_OBSERVATION", "OPEN", "OBJECT", "pocket watch open"
        )
    response = {
        "verdict": verdict, "operation_kind": kind,
        "effect": effect, "evidence_quote": quote,
        "reason": "Untrusted synthetic independent model proposal",
    }
    return {"error": None, "raw": {
        "model": model, "id": "fake-response-id",
        "usage": {"cost": 0.001},
        "choices": [{
            "finish_reason": "stop",
            "message": {"content": json.dumps(response)},
        }],
    }}


class CandidateProjectionV019Tests(unittest.TestCase):
    def get_probe(self, source_report):
        with TemporaryDirectory() as d:
            return probe(
                prose=SOURCE, extraction_report=source_report, call_model=model,
                output_dir=Path(d) / "semantic",
            )

    def test_model_corrections_are_source_bound_and_reaudited_noncanonically(self):
        original = report()
        snapshot = deepcopy(original)
        summary = self.get_probe(original)
        result = project(
            prose=SOURCE, extraction_report=original,
            semantic_summary=summary,
        )
        self.assertEqual(original, snapshot)
        self.assertEqual(len(result["reclassification_proposals"]), 2)
        projected = {
            row["event_id"]: row
            for row in result["projected_report_noncanonical"]["candidate_events"]
        }
        self.assertEqual(projected["synthetic:e4"]["kind"], "WRITE")
        self.assertEqual(projected["synthetic:e4"]["effect"], "DOCUMENT")
        self.assertEqual(projected["synthetic:e5"]["kind"], "OBSERVE")
        self.assertEqual(projected["synthetic:e5"]["effect"],
                         "CHARACTER_KNOWLEDGE")
        self.assertEqual(result["status"],
                         "AUTO_REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL")
        self.assertTrue(any("OPENABLE_BEFORE_CLOSE" in x for x in
                            result["remaining_semantic_task_codes"]))
        self.assertEqual(len(result["unsupported_semantic_tasks"]), 1)
        self.assertEqual(result["world_db_writes"], 0)
        self.assertEqual(result["auto_entity_creations"], 0)
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertFalse(result["requires_manual_intervention"])

    def test_false_objective_train_arrival_is_only_uncommitted_reclassification(self):
        original = report()
        source = SOURCE.index("Arrival recorded")
        original["candidate_events"].append({
            "event_id": "e_fake_arrival",
            "sentence_id": "s003",
            "kind": "CLAIM_MENTION",
            "epistemic": "REPORTED_CLAIM",
            "effect": "WORLD",
            "start": source, "end": source + len("Arrival recorded"),
            "quote": "Arrival recorded",
            "entity_refs": ["new:train"],
            "reason": "Synthetic incorrect state promotion",
        })
        summary = self.get_probe(original)
        result = project(prose=SOURCE, extraction_report=original,
                         semantic_summary=summary)
        correction = next(
            x for x in result["reclassification_proposals"]
            if x["event_id"] == "e_fake_arrival"
        )
        self.assertEqual(correction["proposed_candidate"],
                         {"kind": "CLAIM_MENTION", "effect": "NONE"})
        self.assertEqual(original["candidate_events"][-1]["effect"], "WORLD")
        self.assertFalse(result["canonical_commit_authorized"])

    def test_tampered_model_advisory_rejected_before_projection(self):
        original = report()
        summary = self.get_probe(original)
        summary["independent_advisories"][0]["kind_model_proposed"] = "MOVE"
        with self.assertRaisesRegex(
            CoverageError, "V019_ADVISORY_HASH_MISMATCH"
        ):
            project(prose=SOURCE, extraction_report=original,
                    semantic_summary=summary)

    def test_failed_semantic_stage_cannot_be_imported_as_valid(self):
        original = report()
        summary = self.get_probe(original)
        summary["status"] = "FAILED_SAFE_FINAL"
        with self.assertRaisesRegex(
            CoverageError, "V019_SEMANTIC_SOURCE_INVALID"
        ):
            project(prose=SOURCE, extraction_report=original,
                    semantic_summary=summary)

    def test_temporal_feasibility_can_be_checked_without_invented_clock(self):
        original = report()
        summary = self.get_probe(original)
        temporal = {
            "entry": base(), "scene_key": SCENE, "scene_window": WINDOW,
            "events": [
                evt("a", 1, actor="vane", kind="TESTIMONY"),
                evt("b", 2, actor="mara", kind="ACTION"),
            ],
            "travel_minutes": ROUTES,
        }
        result = project(
            prose=SOURCE, extraction_report=original,
            semantic_summary=summary, temporal_case=temporal,
        )
        self.assertEqual(result["temporal_domains"]["status"],
                         "FEASIBLE_NOT_AUTHORIZED")
        self.assertTrue(all(
            x["narrative_exact_minute"] is None for x in
            result["temporal_domains"]["domains"]
        ))
        self.assertIsNone(result["temporal_failure"])

    def test_impossible_travel_time_auto_routes_replan_no_fake_fix(self):
        original = report()
        summary = self.get_probe(original)
        temporal = {
            "entry": base(), "scene_key": SCENE, "scene_window": WINDOW,
            "events": [
                evt("look", 1, actor="mara", exact=140),
                evt("walk", 2, actor="mara", kind="MOVEMENT",
                    to="archive", exact=145),
            ],
            "travel_minutes": ROUTES,
        }
        result = project(
            prose=SOURCE, extraction_report=original,
            semantic_summary=summary, temporal_case=temporal,
        )
        self.assertIn("TIME_EVENT_INFEASIBLE:walk",
                      result["temporal_failure"])
        self.assertEqual(result["next_automatic_action"],
                         "AUTO_EVENT_REEXTRACTION_OR_REPLAN")
        self.assertFalse(result["canonical_commit_authorized"])


if __name__ == "__main__":
    unittest.main()
