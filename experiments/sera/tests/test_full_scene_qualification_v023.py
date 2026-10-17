"""v0.23 full-event qualification; no paid requests, DB writes or people."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.artifact_scene_checker_v021 import create_checker
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.full_scene_qualification_v023 import qualify
from experiments.sera.event_candidate_projection_v019 import project
from experiments.sera.tests.test_fresh_scene_evidence_worker_v022 import (
    SOURCE_1, SOURCE_2, entry, fake_model, preparer,
)
from experiments.sera.unattended_scene_rewrite_v020 import execute as scene_loop


def file(root, prose=SOURCE_2):
    return root / "evidence" / (prose_hash(prose)+".json")


def prepare(root, prose=SOURCE_2):
    calls = []
    result = preparer(root, fake_model(calls))(prose=prose, world=entry())
    assert result["status"] == "EVIDENCE_READY_NONCANONICAL", result
    return calls


def _checker(root):
    return create_checker(evidence_root=root/"evidence",
                          full_qualification=True)


class FullSceneQualificationV023Tests(unittest.TestCase):
    def test_generic_box_source_passes_full_noncanonical_event_gate(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            calls = prepare(root)
            response = _checker(root)(prose=SOURCE_2, world=entry())
        self.assertIn("qualification", response)
        gate = response["qualification"]
        self.assertEqual(gate["source_sentence_count"], 2)
        self.assertEqual(gate["source_event_count"], 2)
        self.assertEqual(gate["typed_candidate_count"], 2)
        self.assertEqual(gate["status"],
                         "FULL_SCENE_COVERAGE_CANDIDATE_NONCANONICAL")
        self.assertEqual(gate["defects"], [])
        self.assertFalse(gate["canonical_commit_authorized"])
        self.assertFalse(gate["semantic_truth_proven"])
        self.assertFalse(gate["all_state_types_implemented"])
        self.assertGreaterEqual(len(calls), 2)

    def test_standalone_facets_cannot_qualify_unimplemented_move_state(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            prepare(root)
            doc = file(root)
            bundle = json.loads(doc.read_text(encoding="utf-8"))
            # An independent source-bound model misclassifies mere attention
            # as MOVE WORLD; old v0.19 does not flag that combination.
            event = {
                "event_id": "extra-displacement", "sentence_id": "s001",
                "kind": "MOVE", "epistemic": "OBSERVED_ACTION",
                "effect": "WORLD", "start": 0, "end": 7,
                "quote": SOURCE_2[:7], "entity_refs": ["ari"],
                "reason": "Synthetic false world displacement",
            }
            bundle["extraction_report"]["candidate_events"].append(event)
            doc.write_text(json.dumps(bundle), encoding="utf-8")
            result = _checker(root)(prose=SOURCE_2, world=entry())
        codes = {x["code"] for x in result["qualification"]["defects"]}
        self.assertIn("STATE_EFFECT_WITHOUT_QUALIFIED_REDUCER", codes)
        self.assertEqual(
            result["qualification"]["next_automatic_action"],
            "AUTO_REEXTRACT_OR_REPLAN_SCENE",
        )
        self.assertEqual(result["typed"]["status"],
                         "TYPED_FACETS_SIMULATED_NONCANONICAL")

    def test_unimplemented_state_defect_forces_machine_rewrite_not_ready(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            prepare(root)
            doc = file(root)
            bundle = json.loads(doc.read_text(encoding="utf-8"))
            bundle["extraction_report"]["candidate_events"].append({
                "event_id": "movement-without-location-reducer",
                "sentence_id": "s001", "kind": "MOVE",
                "epistemic": "OBSERVED_ACTION", "effect": "WORLD",
                "start": 0, "end": 7, "quote": SOURCE_2[:7],
                "entity_refs": ["ari"], "reason": "Injected movement",
            })
            doc.write_text(json.dumps(bundle), encoding="utf-8")
            calls = []
            def writer(*, source, defects):
                calls.append(deepcopy(defects))
                return {
                    "prose": source,
                    "receipt": {
                        "source_prose_sha256": prose_hash(source),
                        "response_id": "synthetic-id", "model": "synthetic",
                        "finish_reason": "stop", "cost_usd": "0",
                    },
                }
            outcome = scene_loop(
                prose=SOURCE_2, world=entry(),
                check_scene=_checker(root), rewrite_scene=writer,
                output_dir=root/"loop", max_rewrites=1,
            )
        self.assertEqual(outcome["status"], "FAILED_SAFE_FINAL")
        self.assertEqual(outcome["reason_code"], "V020_REWRITE_NO_SOURCE_CHANGE")
        self.assertEqual(len(calls), 1)
        self.assertIn("STATE_EFFECT_WITHOUT_QUALIFIED_REDUCER",
                      [x["code"] for x in calls[0]
                       if isinstance(x, dict) and "code" in x])
        self.assertFalse(outcome["canonical_commit_authorized"])

    def test_blind_sweep_must_corrobate_each_typed_physical_operation(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            prepare(root)
            saved = json.loads(file(root).read_text(encoding="utf-8"))
            original = _checker(root)(prose=SOURCE_2, world=entry())
            # The independent sweep said only COMMUNICATE for the first
            # sentence. The typed model said OBSERVE_OPENABLE. A correct
            # source quote in both reports cannot replace agreement on
            # the actual physical or observation operation.
            saved["extraction_report"]["candidate_events"][0]["kind"] = (
                "COMMUNICATE"
            )
            changed = project(
                prose=SOURCE_2,
                extraction_report=saved["extraction_report"],
                semantic_summary=saved["semantic_summary"],
            )
            out = qualify(
                prose=SOURCE_2, world=entry(), bundle=saved,
                projection=changed, typed=original["typed"],
            )
        self.assertIn(
            "TYPED_OPERATION_NOT_BACKED_BY_INDEPENDENT_SWEEP",
            [x["code"] for x in out["defects"]],
        )
        self.assertEqual(out["status"],
                         "REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL")
        self.assertFalse(out["canonical_commit_authorized"])

    def test_physical_open_is_not_satisfied_by_passive_open_observation(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            prepare(root)
            saved = json.loads(file(root).read_text(encoding="utf-8"))
            observed = _checker(root)(prose=SOURCE_2, world=entry())
            # An independently emitted OPEN action cannot be laundered into
            # OBSERVE_OPENABLE merely because its quote overlaps.
            model_action = saved["extraction_report"]["candidate_events"][0]
            model_action["kind"] = "OPEN"
            model_action["effect"] = "OBJECT"
            model_action["epistemic"] = "OBSERVED_ACTION"
            projected = project(
                prose=SOURCE_2,
                extraction_report=saved["extraction_report"],
                semantic_summary=saved["semantic_summary"],
            )
            verdict = qualify(
                prose=SOURCE_2, world=entry(), bundle=saved,
                projection=projected, typed=observed["typed"],
            )
            codes = {x["code"] for x in verdict["defects"]}
            self.assertIn("PHYSICAL_EFFECT_NOT_REDUCER_COVERED", codes)
            self.assertIn("TYPED_OPERATION_NOT_BACKED_BY_INDEPENDENT_SWEEP",
                          codes)
            self.assertEqual(
                verdict["status"],"REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL")
            self.assertFalse(verdict["canonical_commit_authorized"])

    def test_mutated_report_or_typed_proof_cannot_be_exchanged_between_runs(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            prepare(root)
            doc = file(root)
            base = json.loads(doc.read_text(encoding="utf-8"))
            check = _checker(root)
            authentic = check(prose=SOURCE_2, world=entry())
            swapped = deepcopy(base)
            swapped["extraction_report"]["candidate_events"][0]["reason"] = (
                "Altered source ledger after v0.19 qualification"
            )
            with self.assertRaisesRegex(
                CoverageError, "V023_UPSTREAM_CHECK_SOURCE_OR_AUTHORITY_MISMATCH"
            ):
                qualify(
                    prose=SOURCE_2, world=entry(), bundle=swapped,
                    projection=authentic["projection"], typed=authentic["typed"],
                )
            swapped = deepcopy(base)
            swapped["typed_candidates"][0]["event_id"] = "altered"
            with self.assertRaisesRegex(
                CoverageError, "V023_UPSTREAM_CHECK_SOURCE_OR_AUTHORITY_MISMATCH"
            ):
                qualify(
                    prose=SOURCE_2, world=entry(), bundle=swapped,
                    projection=authentic["projection"], typed=authentic["typed"],
                )

    def test_full_gate_rejects_unknown_model_granted_authority(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            prepare(root)
            doc = file(root)
            bundle = json.loads(doc.read_text(encoding="utf-8"))
            bundle["extraction_report"]["candidate_events"][0]["effect"] = (
                "WORLD"
            )
            bundle["extraction_report"]["candidate_events"][0]["epistemic"] = (
                "REPORTED_CLAIM"
            )
            doc.write_text(json.dumps(bundle), encoding="utf-8")
            # Neither v0.19 nor the v0.20 object simulation alone
            # detects this OBSERVE/REPORTED contradiction. The new full
            # gate must quarantine it as a nonobjective physical effect.
            result = _checker(root)(prose=SOURCE_2, world=entry())
            self.assertIn("NONOBJECTIVE_CLAIM_HAS_PHYSICAL_EFFECT",
                          [x["code"] for x in
                           result["qualification"]["defects"]])
            self.assertFalse(result["qualification"]
                             ["canonical_commit_authorized"])

    def test_default_v021_replay_stays_legacy_but_never_canon(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            prepare(root)
            old=create_checker(evidence_root=root/"evidence")(
                prose=SOURCE_2, world=entry()
            )
        self.assertEqual(set(old), {"projection", "typed"})
        self.assertFalse(old["projection"]["canonical_commit_authorized"])
        self.assertFalse(old["typed"]["canonical_commit_authorized"])


if __name__ == "__main__":
    unittest.main()
