"""SERA v0.20 pure offline self-healing scene-loop tests, no paid calls."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.tests.test_world_state_v013 import base
from experiments.sera.typed_aspect_recovery_v020 import fingerprint
from experiments.sera.unattended_scene_rewrite_v020 import execute

ORIGINAL = "The notebook said that the train had arrived."


def analysis(*, prose, world):
    ready = "Recorded as a report." in prose
    return {
        "projection": {
            "schema": "sera.event-candidate-repair.v0.19",
            "prose_sha256": prose_hash(prose),
            "status": ("CANDIDATES_STRUCTURALLY_CLEAN_NONCANONICAL"
                       if ready else
                       "AUTO_REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL"),
            "next_automatic_action": (
                "CONTINUE_FULL_SCENE_GATES" if ready else
                "AUTO_EVENT_REEXTRACTION_OR_REPLAN"),
            "remaining_semantic_task_codes": (
                [] if ready else ["REPORTED_CLAIM_WRONG_EFFECT"]),
            "unsupported_semantic_tasks": [],
            "canonical_commit_authorized": False,
            "world_db_writes": 0,
        },
        "typed": {
            "schema": "sera.typed-aspect-candidate-recovery.v0.20",
            "prose_sha256": prose_hash(prose),
            "world_sha256": fingerprint(world),
            "status": ("TYPED_FACETS_SIMULATED_NONCANONICAL"
                       if ready else
                       "AUTO_REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL"),
            "next_automatic_action": (
                "CONTINUE_INDEPENDENT_SCENE_QUALIFICATION" if ready else
                "AUTO_REEXTRACT_OR_REPLAN_SCENE"),
            "blocker_codes": [] if ready else ["REPORT_MISREAD_AS_WORLD_FACT"],
            "canonical_commit_authorized": False,
            "world_db_writes": 0,
            "requires_manual_intervention": False,
        },
    }


def good_rewrite(*, source, defects):
    assert "REPORT_MISREAD_AS_WORLD_FACT" in defects
    return {
        "prose": "The train's arrival was unverified. Recorded as a report.",
        "receipt": {
            "source_prose_sha256": prose_hash(source),
            "response_id": "synthetic-paid-response-1",
            "model": "synthetic-no-provider",
            "finish_reason": "stop",
            "cost_usd": "0.002",
        },
    }


def run(folder, *, checker=analysis, writer=good_rewrite,
        prose=ORIGINAL, max_rewrites=2,
        observed_spend_guard_usd="0.15"):
    return execute(
        prose=prose, world=base(),
        check_scene=checker, rewrite_scene=writer,
        output_dir=folder, max_rewrites=max_rewrites,
        observed_spend_guard_usd=observed_spend_guard_usd,
    )


class UnattendedSceneControllerV020Tests(unittest.TestCase):
    def test_auto_rewrites_wrong_report_and_rechecks_from_source(self):
        scans = []
        writes = []
        def check(*, prose, world):
            scans.append(prose)
            return analysis(prose=prose, world=world)
        def rewrite(*, source, defects):
            writes.append((source, deepcopy(defects)))
            return good_rewrite(source=source, defects=defects)
        with TemporaryDirectory() as root:
            folder = Path(root) / "stage"
            out = run(folder, checker=check, writer=rewrite)
        self.assertEqual(len(scans), 2)
        self.assertEqual(len(writes), 1)
        self.assertEqual(out["status"], "SCENE_CANDIDATE_READY_NONCANONICAL")
        self.assertEqual(out["rewrite_count"], 1)
        self.assertEqual(out["provider_reported_spend_usd"], "0.002")
        self.assertEqual(out["next_automatic_action"],
                         "CONTINUE_OTHER_FULL_STORY_GATES")
        self.assertFalse(out["canonical_commit_authorized"])
        self.assertEqual(out["world_db_writes"], 0)
        self.assertFalse(out["requires_manual_intervention"])

    def test_durable_replay_does_not_repeat_fully_receipted_billable_rewrite(self):
        checks = []
        calls = []
        def check(*, prose, world):
            checks.append(prose)
            return analysis(prose=prose, world=world)
        def writer(*, source, defects):
            calls.append(source)
            return good_rewrite(source=source, defects=defects)
        with TemporaryDirectory() as root:
            folder = Path(root) / "stage"
            first = run(folder, checker=check, writer=writer)
            (folder / "final.json").unlink()
            second = run(folder, checker=check, writer=writer)
        self.assertEqual(first, second)
        self.assertEqual(len(checks), 2)
        self.assertEqual(len(calls), 1)

    def test_interrupted_free_validator_automatically_recomputes_from_archive(self):
        scans = []
        writes = []
        def checker(*, prose, world):
            scans.append(prose)
            return analysis(prose=prose, world=world)
        def writer(*, source, defects):
            writes.append(source)
            return good_rewrite(source=source, defects=defects)
        with TemporaryDirectory() as temp:
            root = Path(temp) / "stage"
            first = run(root, checker=checker, writer=writer)
            (root / "final.json").unlink()
            (root / "check_01.json").unlink()
            resumed = run(root, checker=checker, writer=writer)
        self.assertEqual(first, resumed)
        self.assertEqual(len(scans), 3)  # no billed check
        self.assertEqual(len(writes), 1)  # paid rewrite not repeated
        self.assertFalse(resumed["requires_manual_intervention"])

    def test_corrupted_started_validator_source_never_rechecks_wrong_story(self):
        calls = []
        def checker(*, prose, world):
            calls.append(prose)
            return analysis(prose=prose, world=world)
        with TemporaryDirectory() as temp:
            root = Path(temp) / "stage"
            run(root, checker=checker)
            (root / "final.json").unlink()
            (root / "check_00.json").unlink()
            (root / "check_00.started").write_text(
                '{"prose_sha256":"WRONG_SOURCE"}', encoding="utf-8"
            )
            out = run(root, checker=checker)
        self.assertEqual(len(calls), 2)
        self.assertEqual(out["status"], "FAILED_SAFE_FINAL")
        self.assertEqual(out["reason_code"],
                         "V020_CHECKPOINT_SOURCE_MISMATCH")

    def test_lost_provider_reply_stops_without_double_bill_or_human(self):
        calls = []
        def unavailable(*, source, defects):
            calls.append(source)
            raise ConnectionError("Provider may have billed before timeout")
        with TemporaryDirectory() as root:
            folder = Path(root) / "stage"
            first = run(folder, writer=unavailable)
            (folder / "final.json").unlink()
            second = run(folder, writer=unavailable)
        self.assertEqual(len(calls), 1)
        self.assertEqual(first["status"], "FAILED_SAFE_FINAL")
        self.assertEqual(second["reason_code"],
                         "V020_UNKNOWN_IN_FLIGHT_REWRITE_NO_AUTO_RESEND")
        self.assertEqual(second["world_db_writes"], 0)

    def test_narrative_rewrite_without_change_is_failed_safe(self):
        def same(*, source, defects):
            return {
                "prose": source,
                "receipt": {
                    "source_prose_sha256": prose_hash(source),
                    "response_id": "unchanged", "model": "synthetic",
                    "finish_reason": "stop", "cost_usd": 0,
                },
            }
        with TemporaryDirectory() as root:
            out = run(Path(root) / "stage", writer=same)
        self.assertEqual(out["status"], "FAILED_SAFE_FINAL")
        self.assertEqual(out["reason_code"], "V020_REWRITE_NO_SOURCE_CHANGE")
        self.assertEqual(out["world_db_writes"], 0)

    def test_no_retry_budget_yields_explicit_safe_terminal_state(self):
        calls = []
        def rewrite(*, source, defects):
            calls.append(source)
            return good_rewrite(source=source, defects=defects)
        with TemporaryDirectory() as root:
            out = run(Path(root) / "stage", writer=rewrite, max_rewrites=0)
        self.assertEqual(calls, [])
        self.assertEqual(out["reason_code"], "V020_REWRITE_ATTEMPTS_EXHAUSTED")
        self.assertFalse(out["requires_manual_intervention"])

    def test_forged_analysis_world_commit_is_rejected_not_used(self):
        def malicious(*, prose, world):
            payload = analysis(prose=prose, world=world)
            payload["typed"]["canonical_commit_authorized"] = True
            return payload
        with TemporaryDirectory() as root:
            out = run(Path(root) / "stage", checker=malicious)
        self.assertEqual(out["reason_code"], "V020_SCENE_CHECK_FAILED_SAFE")
        self.assertFalse(out["canonical_commit_authorized"])

    def test_observed_usd_spend_stops_autonomous_extra_charge(self):
        calls = []
        def writer(*, source, defects):
            calls.append(source)
            result = good_rewrite(source=source, defects=defects)
            result["prose"] = "The notebook still mentioned a train."
            return result
        with TemporaryDirectory() as root:
            out = run(
                Path(root) / "stage", writer=writer, max_rewrites=2,
                observed_spend_guard_usd="0.001",
            )
        self.assertEqual(len(calls), 1)
        self.assertEqual(out["provider_reported_spend_usd"], "0.002")
        self.assertEqual(out["reason_code"],
                         "V020_REWRITE_OBSERVED_SPEND_GUARD")
        self.assertEqual(out["status"], "FAILED_SAFE_FINAL")

    def test_no_evidence_defects_cannot_trigger_unfocused_writer(self):
        calls = []
        def missing(*, prose, world):
            result = analysis(prose=prose, world=world)
            result["projection"]["remaining_semantic_task_codes"] = []
            result["typed"]["blocker_codes"] = []
            return result
        def rewrite(*, source, defects):
            calls.append(source)
            return good_rewrite(source=source, defects=defects)
        with TemporaryDirectory() as root:
            result = run(Path(root) / "stage", checker=missing, writer=rewrite)
        self.assertEqual(calls, [])
        self.assertEqual(result["reason_code"], "V020_SCENE_CHECK_FAILED_SAFE")
        self.assertFalse(result["canonical_commit_authorized"])

    def test_source_change_or_attempt_policy_mismatch_refuses_replay(self):
        with TemporaryDirectory() as root:
            folder = Path(root) / "stage"
            run(folder)
            with self.assertRaisesRegex(
                CoverageError, "V020_REWRITE_RESUME_CONTRACT_MISMATCH"
            ):
                run(folder, max_rewrites=3)
            with self.assertRaisesRegex(
                CoverageError, "V020_REWRITE_RESUME_CONTRACT_MISMATCH"
            ):
                run(folder, prose="different frozen initial source")

    def test_no_model_calls_when_structural_candidate_is_already_ready(self):
        original = "Recorded as a report."
        calls = []
        def rewrite(*, source, defects):
            calls.append(source)
            return good_rewrite(source=source, defects=defects)
        with TemporaryDirectory() as root:
            out = run(Path(root) / "stage", writer=rewrite, prose=original)
        self.assertEqual(calls, [])
        self.assertEqual(out["rewrite_count"], 0)
        self.assertEqual(out["status"], "SCENE_CANDIDATE_READY_NONCANONICAL")

    def test_v054_multifacet_ready_requires_independent_full_v023_gate(self):
        # Synthetic checker contract only; this is NOT a Mara model PASS.
        # v0.54 cannot enter READY through the legacy v0.20 facet shortcut.
        prose = "Recorded as a report."
        def checker(*, prose, world, full=True, defects=None, preview=True):
            outcome = analysis(prose=prose, world=world)
            typed = outcome["typed"]
            typed["status"] = "TYPED_MULTIFACET_SIMULATED_NONCANONICAL"
            typed.pop("next_automatic_action", None)
            typed["multifacet_preview"] = {
                "schema": "sera.multifacet-physical-preview.v0.54",
                "simulation_is_not_world_truth": preview,
            }
            if full:
                bad = [] if defects is None else defects
                outcome["qualification"] = {
                    "schema": "sera.full-scene-qualification.v0.23",
                    "prose_sha256": prose_hash(prose),
                    "world_sha256": fingerprint(world),
                    "status": ("FULL_SCENE_COVERAGE_CANDIDATE_NONCANONICAL"
                               if not bad else
                               "REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL"),
                    "next_automatic_action": (
                        "CONTINUE_INDEPENDENT_CANON_QUALIFICATION"
                        if not bad else "AUTO_REEXTRACT_OR_REPLAN_SCENE"),
                    "defects": bad,
                    "canonical_commit_authorized": False,
                    "world_db_writes": 0,
                    "requires_manual_intervention": False,
                }
            return outcome
        def no_writer(**_):
            self.fail("A synthetic check must not call Writer")
        with TemporaryDirectory() as root:
            passed = run(Path(root)/"v054-qualified", prose=prose,
                         checker=checker, writer=no_writer, max_rewrites=0)
            unqualified = run(
                Path(root)/"v054-without-v023", prose=prose, writer=no_writer,
                checker=lambda **kw: checker(**kw, full=False), max_rewrites=0)
            defective = run(
                Path(root)/"v054-v023-defect", prose=prose, writer=no_writer,
                checker=lambda **kw: checker(
                    **kw, defects=[{"code":"SOURCE_EVENT_MISMATCH"}]),
                max_rewrites=0)
            untrusted_preview = run(
                Path(root)/"v054-forged-preview", prose=prose,
                writer=no_writer,
                checker=lambda **kw: checker(**kw, preview=False),
                max_rewrites=0)
        self.assertEqual(passed["status"], "SCENE_CANDIDATE_READY_NONCANONICAL")
        self.assertEqual(passed["rewrite_count"], 0)
        self.assertEqual(unqualified["reason_code"],
                         "V020_SCENE_CHECK_FAILED_SAFE")
        self.assertEqual(defective["status"], "FAILED_SAFE_FINAL")
        self.assertEqual(defective["reason_code"],
                         "V020_REWRITE_ATTEMPTS_EXHAUSTED")
        self.assertEqual(untrusted_preview["reason_code"],
                         "V020_SCENE_CHECK_FAILED_SAFE")
        for output in (passed, unqualified, defective, untrusted_preview):
            self.assertFalse(output["canonical_commit_authorized"])
            self.assertEqual(output["world_db_writes"], 0)

    def test_receipt_cannot_represent_unbound_source_or_model_incomplete(self):
        def wrong(*, source, defects):
            payload = good_rewrite(source=source, defects=defects)
            payload["receipt"]["source_prose_sha256"] = "forged"
            return payload
        with TemporaryDirectory() as root:
            out = run(Path(root) / "stage", writer=wrong)
        self.assertEqual(out["status"], "FAILED_SAFE_FINAL")
        self.assertEqual(out["reason_code"], "V020_REWRITE_PROVIDER_FAILED_SAFE")
        self.assertEqual(out["world_db_writes"], 0)


if __name__ == "__main__":
    unittest.main()
