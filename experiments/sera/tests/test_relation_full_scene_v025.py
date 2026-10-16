"""v0.25 full-scene gate: source-certified holder/fact CAS, all noncanonical."""
from copy import deepcopy
import unittest

from experiments.sera.artifact_scene_checker_v021 import digest
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.full_scene_qualification_v023 import qualify
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.tests.test_relation_knowledge_v025 import (
    SOURCE, report, case,
)
from experiments.sera.tests.test_world_state_v02 import base


def evidence():
    world = base()
    extraction = report()
    ids = [s["id"] for s in sentences(SOURCE)]
    for event, sid in zip(extraction["candidate_events"], ids):
        event["sentence_id"] = sid
    extraction.update({
        "schema": "sera.blind-sweep-bound.v0.10",
        "canonical_commit_authorized": False,
        "world_state_writes": 0,
        "sentences_accounted_for": len(ids),
        "findings": [],
    })
    bundle = {
        "schema": "sera.recheck-evidence-bundle.v0.21",
        "prose_sha256": prose_hash(SOURCE),
        "world_sha256": digest(world),
        "extraction_report": extraction,
        "typed_registry": {"openables": [], "documents": []},
        "typed_candidates": [],
        "relation_case": case(world),
        "temporal_case": None,
    }
    projected = {
        "schema": "sera.event-candidate-repair.v0.19",
        "prose_sha256": prose_hash(SOURCE),
        "original_report_sha256": digest(extraction),
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
        "original_candidates_sha256": digest([]),
        "status": "NO_APPLICABLE_TYPED_FACETS_NONCANONICAL",
        "empty_facet_scope_requires_full_gate": True,
        "blocker_codes": [], "canonical_commit_authorized": False,
        "world_db_writes": 0,
    }
    return world, bundle, projected, typed


def check(world, bundle, projection, typed):
    return qualify(prose=SOURCE, world=world, bundle=bundle,
                   projection=projection, typed=typed)


class FullSceneRelationGateV025Tests(unittest.TestCase):
    def test_verified_handoff_and_new_fact_are_supported_not_world_committed(self):
        w,b,p,t = evidence()
        original = deepcopy(w)
        output = check(w,b,p,t)
        self.assertEqual(output["status"],
                         "FULL_SCENE_COVERAGE_CANDIDATE_NONCANONICAL")
        self.assertEqual(output["defects"], [])
        self.assertEqual(output["relation_preview"]["transition_count"], 2)
        preview = output["relation_preview"]["isolated_preview_state"]
        self.assertEqual(preview["entities"]["vane_watch"]["holder"], "mara")
        self.assertEqual(preview["entities"]["vane_watch"]["owner"], "vane")
        self.assertIn("station_clock_stopped",
                      preview["entities"]["mara"]["knowledge"])
        self.assertEqual(w, original)
        self.assertFalse(output["canonical_commit_authorized"])

    def test_missing_trusted_policy_cannot_silently_accept_deed_or_fact(self):
        w,b,p,t = evidence()
        b["relation_case"] = None
        out = check(w,b,p,t)
        self.assertEqual(out["status"],
                         "REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL")
        self.assertIn("STATE_EFFECT_WITHOUT_QUALIFIED_REDUCER",
                      [e["code"] for e in out["defects"]])

    def test_handoff_allegation_cannot_transfer_physical_object(self):
        w,b,p,t = evidence()
        b["extraction_report"]["candidate_events"][0]["epistemic"] = (
            "REPORTED_CLAIM"
        )
        p["original_report_sha256"] = digest(b["extraction_report"])
        out = check(w,b,p,t)
        codes = [e["code"] for e in out["defects"]]
        self.assertIn("RELATION_OR_KNOWLEDGE_SOURCE_UNQUALIFIED", codes)
        self.assertIn("NONOBJECTIVE_CLAIM_HAS_PHYSICAL_EFFECT", codes)
        self.assertFalse(out["canonical_commit_authorized"])

    def test_fact_is_rumored_in_app_registry_even_if_models_agree(self):
        w,b,p,t = evidence()
        b["relation_case"]["verified_fact_registry"][
            "station_clock_stopped"]["truth_status"] = "RUMORED"
        out = check(w,b,p,t)
        self.assertEqual(out["status"],
                         "REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL")
        self.assertIn("V025_FACT_UNVERIFIED_OR_UNGROUNDED",
                      out["relation_failure"])

    def test_swapped_model_report_digest_cannot_receive_old_qualifier(self):
        w,b,p,t = evidence()
        b["extraction_report"]["candidate_events"][0]["quote"] = (
            "forged report"
        )
        with self.assertRaisesRegex(
            CoverageError, "V023_UPSTREAM_CHECK_SOURCE_OR_AUTHORITY_MISMATCH"
        ):
            check(w,b,p,t)


if __name__ == "__main__":
    unittest.main()
