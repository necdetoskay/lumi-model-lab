"""v0.24 integration into v0.23 all-event gate; zero provider calls."""
from __future__ import annotations

from copy import deepcopy
import unittest

from experiments.sera.artifact_scene_checker_v021 import digest
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.full_scene_qualification_v023 import qualify
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.tests.test_world_state_v02 import base
from experiments.sera.spatial_preview_v024 import preview

SOURCE = "Mara walked to archive."
SCENE = "movement-bound-event"
ROUTES = {"station->archive": 10}


def inputs():
    world = base()
    span = SOURCE.index("Mara walked to archive")
    report = {
        "schema": "sera.blind-sweep-bound.v0.10",
        "source_prose_sha256": prose_hash(SOURCE),
        "sentences_accounted_for": len(sentences(SOURCE)),
        "candidate_events": [{
            "event_id": "m1",
            "sentence_id": sentences(SOURCE)[0]["id"],
            "kind": "MOVE",
            "epistemic": "OBSERVED_ACTION", "effect": "WORLD",
            "entity_refs": ["mara"],
            "start": span, "end": span+len("Mara walked to archive"),
            "quote": "Mara walked to archive",
        }],
        "findings": [],
        "canonical_commit_authorized": False,
        "world_state_writes": 0,
    }
    timeline = {
        "entry": deepcopy(world), "scene_key": SCENE,
        "scene_window": {
            "scene_key": SCENE, "entry_revision": world["revision"],
            "earliest_minute": 135, "latest_minute": 175,
        },
        "events": [{
            "event_id": "m1", "ordinal": 1, "actor_id": "mara",
            "kind": "MOVEMENT", "to_location": "archive",
            "earliest_minute": None, "latest_minute": None,
            "exact_minute": None, "depends_on": [],
        }],
        "travel_minutes": dict(ROUTES),
    }
    typed_events = []
    bundle = {
        "schema": "sera.recheck-evidence-bundle.v0.21",
        "prose_sha256": prose_hash(SOURCE),
        "world_sha256": digest(world),
        "extraction_report": report,
        "typed_candidates": typed_events,
        "temporal_case": timeline,
    }
    projection = {
        "schema": "sera.event-candidate-repair.v0.19",
        "prose_sha256": prose_hash(SOURCE),
        "original_report_sha256": digest(report),
        "canonical_commit_authorized": False,
        "world_db_writes": 0,
        "remaining_semantic_task_codes": [],
        "unsupported_semantic_tasks": [],
        "temporal_failure": None,
    }
    typed = {
        "schema": "sera.typed-aspect-candidate-recovery.v0.20",
        "prose_sha256": prose_hash(SOURCE),
        "world_sha256": digest(world),
        "original_candidates_sha256": digest(typed_events),
        "canonical_commit_authorized": False,
        "world_db_writes": 0,
        "status": "TYPED_FACETS_SIMULATED_NONCANONICAL",
        "blocker_codes": [],
    }
    return world, bundle, projection, typed


def check(world, bundle, projection, typed):
    return qualify(
        prose=SOURCE, world=world, bundle=bundle,
        projection=projection, typed=typed,
    )


class SourceRouteQualifiedV024IntegrationTests(unittest.TestCase):
    def test_real_typed_route_feasibility_unblocks_only_the_supported_move(self):
        world, bundle, projection, typed = inputs()
        snapshot = deepcopy(world)
        result = check(world, bundle, projection, typed)
        self.assertEqual(result["status"],
                         "FULL_SCENE_COVERAGE_CANDIDATE_NONCANONICAL")
        self.assertEqual(result["defects"], [])
        self.assertEqual(world, snapshot)
        self.assertEqual(result["spatial_preview"]["movement_count"], 1)
        self.assertEqual(result["spatial_preview"]["isolated_preview_state"]
                         ["entities"]["mara"]["location"], "archive")
        self.assertEqual(result["spatial_preview"]["isolated_preview_state"]
                         ["entities"]["mara_coat"]["location"], "archive")
        self.assertEqual(result["spatial_preview"]["isolated_preview_state"]
                         ["entities"]["mara_notebook"]["location"], "archive")
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertFalse(result["semantic_truth_proven"])

    def test_missing_app_owned_route_keeps_move_unsupported(self):
        world, bundle, projection, typed = inputs()
        bundle["temporal_case"] = None
        result = check(world, bundle, projection, typed)
        self.assertEqual(result["status"],
                         "REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL")
        self.assertIn("STATE_EFFECT_WITHOUT_QUALIFIED_REDUCER",
                      [x["code"] for x in result["defects"]])
        self.assertIsNone(result["spatial_preview"])

    def test_too_fast_arrival_marks_machine_only_replan_and_no_world_write(self):
        world, bundle, projection, typed = inputs()
        bundle["temporal_case"]["events"][0]["exact_minute"] = 139
        result = check(world, bundle, projection, typed)
        self.assertEqual(result["status"],
                         "REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL")
        self.assertIn("SPATIAL_SOURCE_OR_ROUTE_UNQUALIFIED",
                      [x["code"] for x in result["defects"]])
        self.assertIn("TIME_EVENT_INFEASIBLE", result["spatial_failure"])
        self.assertEqual(result["world_db_writes"], 0)

    def test_model_reported_teleport_as_fact_must_not_pass(self):
        world, bundle, projection, typed = inputs()
        bundle["extraction_report"]["candidate_events"][0]["epistemic"] = (
            "REPORTED_CLAIM"
        )
        projection["original_report_sha256"] = digest(
            bundle["extraction_report"]
        )
        result = check(world, bundle, projection, typed)
        codes = [x["code"] for x in result["defects"]]
        self.assertIn("SPATIAL_SOURCE_OR_ROUTE_UNQUALIFIED", codes)
        self.assertIn("NONOBJECTIVE_CLAIM_HAS_PHYSICAL_EFFECT", codes)
        self.assertFalse(result["canonical_commit_authorized"])

    def test_swapped_paid_sweep_evidence_is_invalid_despite_true_route(self):
        world, bundle, projection, typed = inputs()
        bundle["extraction_report"]["candidate_events"][0]["quote"] = (
            "not the exact observed source"
        )
        with self.assertRaisesRegex(
            CoverageError, "V023_UPSTREAM_CHECK_SOURCE_OR_AUTHORITY_MISMATCH"
        ):
            check(world, bundle, projection, typed)

    def test_timeline_bound_to_other_entry_world_blocks_spatial_preview(self):
        world, bundle, projection, typed = inputs()
        bundle["temporal_case"]["entry"]["revision"] += 1
        result = check(world, bundle, projection, typed)
        self.assertEqual(result["status"],
                         "REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL")
        self.assertIn("V024_UNTRUSTED_TEMPORAL_WORLD",
                      result["spatial_failure"])
        self.assertEqual(result["next_automatic_action"],
                         "AUTO_REEXTRACT_OR_REPLAN_SCENE")


if __name__ == "__main__":
    unittest.main()
