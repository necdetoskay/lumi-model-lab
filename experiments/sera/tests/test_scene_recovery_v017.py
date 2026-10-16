"""SERA v0.17: unattended re-extraction and crash/payment-safe replay tests."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.scene_recovery_v017 import execute
from experiments.sera.mara_s1_typed_live_v05 import entry_state
from experiments.sera.tests.test_identity_stage_v016 import envelope
from experiments.sera.tests.test_identity_auto_repair_v016 import problem_response
from experiments.sera.tests.test_identity_resolution_v014 import (
    PROSE, synthetic_mention_census,
)
from experiments.sera.tests.test_blind_identity_v015 import synthetic_model_rows


def run(path, provider, **extra):
    return execute(
        prose=PROSE, world=entry_state(),
        census=synthetic_mention_census(),
        call_model=provider, output_dir=path, **extra,
    )


class AutonomousSceneRecoveryTests(unittest.TestCase):
    def test_healthy_scene_needs_one_primary_and_no_manual_step(self):
        calls = []
        def provider(*, model, prepared):
            calls.append(prepared)
            return envelope(synthetic_model_rows())
        with TemporaryDirectory() as directory:
            result = run(Path(directory) / "stage", provider)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["status"], "IDENTITY_CANDIDATES_READY_NONCANONICAL")
        self.assertEqual(result["attempt_count"], 1)
        self.assertFalse(result["requires_manual_intervention"])
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(result["world_db_writes"], 0)

    def test_bad_row_automatically_reextracts_entire_scene_without_operator(self):
        calls = []
        def provider(*, model, prepared):
            calls.append(prepared)
            if len(calls) == 1:
                return envelope(problem_response())
            messages = prepared["request"]["messages"]
            self.assertIn("new:strike_record", messages[-1]["content"])
            self.assertIn("Reassess ALL requested refs", messages[-1]["content"])
            return envelope(synthetic_model_rows())
        with TemporaryDirectory() as directory:
            path = Path(directory) / "stage"
            out = run(path, provider, repair_calls_allowed=0)
            self.assertTrue((path / "attempt_01" / "primary.json").is_file())
            self.assertTrue((path / "attempt_02" / "primary.json").is_file())
            self.assertEqual(json.loads((path / "final.json").read_text()),
                             out)
        self.assertEqual(len(calls), 2)
        self.assertEqual(out["status"], "IDENTITY_CANDIDATES_READY_NONCANONICAL")
        self.assertEqual(out["attempt_count"], 2)
        self.assertEqual(out["attempts"][0]["automatic_abstain_count"], 1)
        self.assertEqual(out["attempts"][1]["automatic_abstain_count"], 0)
        self.assertEqual(out["provider_reported_total_spend_usd"], "0.002")

    def test_repeated_unresolved_candidate_exits_failed_safe_not_review_queue(self):
        calls = []
        def provider(*, model, prepared):
            calls.append(prepared)
            return envelope(problem_response())
        with TemporaryDirectory() as directory:
            out = run(Path(directory) / "stage", provider,
                      repair_calls_allowed=0, max_scene_attempts=2)
        self.assertEqual(len(calls), 2)
        self.assertEqual(out["status"], "FAILED_SAFE_FINAL")
        self.assertEqual(out["reason_code"], "V017_RECOVERY_ATTEMPTS_EXHAUSTED")
        self.assertFalse(out["requires_manual_intervention"])
        self.assertEqual(out["world_db_writes"], 0)

    def test_unknown_in_flight_provider_attempt_does_not_double_charge(self):
        calls = []
        def provider(*, model, prepared):
            calls.append(prepared)
            return {"error": "HTTP_502_MAY_HAVE_CHARGED"}
        with TemporaryDirectory() as directory:
            out = run(Path(directory) / "stage", provider)
        self.assertEqual(len(calls), 1)
        self.assertEqual(out["status"], "FAILED_SAFE_FINAL")
        self.assertEqual(out["reason_code"],
                         "V017_UNCONFIRMED_IN_FLIGHT_PROVIDER_ATTEMPT")
        self.assertEqual(out["attempt_count"], 1)

    def test_completed_replay_returns_cached_result_without_provider_calls(self):
        calls = []
        def provider(*, model, prepared):
            calls.append(prepared)
            return envelope(synthetic_model_rows())
        with TemporaryDirectory() as directory:
            folder = Path(directory) / "stage"
            first = run(folder, provider)
            again = run(folder, provider)
        self.assertEqual(first, again)
        self.assertEqual(len(calls), 1)

    def test_resume_previous_complete_partial_attempt_without_double_call(self):
        calls = []
        def provider(*, model, prepared):
            calls.append(prepared)
            if len(calls) == 1:
                return envelope(problem_response())
            return envelope(synthetic_model_rows())
        with TemporaryDirectory() as directory:
            folder = Path(directory) / "stage"
            first = run(folder, provider, repair_calls_allowed=0,
                        max_scene_attempts=2)
            (folder / "final.json").unlink()
            resumed = run(folder, provider, repair_calls_allowed=0,
                          max_scene_attempts=2)
        self.assertEqual(len(calls), 2)
        self.assertEqual(first, resumed)

    def test_resume_unfinished_attempt_fails_safe_without_new_billable_call(self):
        calls = []
        def provider(*, model, prepared):
            calls.append(prepared)
            return envelope(synthetic_model_rows())
        with TemporaryDirectory() as directory:
            folder = Path(directory) / "stage"
            run(folder, provider)
            (folder / "final.json").unlink()
            (folder / "attempt_01" / "result.json").write_text(
                json.dumps({"status": "STARTED"}), encoding="utf-8")
            out = run(folder, provider)
        self.assertEqual(len(calls), 1)
        self.assertEqual(out["status"], "FAILED_SAFE_FINAL")
        self.assertEqual(out["reason_code"], "V017_INCOMPLETE_ATTEMPT_AFTER_CRASH")

    def test_changed_source_fingerprint_rejected_before_any_model_call(self):
        calls = []
        def provider(*, model, prepared):
            calls.append(prepared)
            return envelope(synthetic_model_rows())
        with TemporaryDirectory() as directory:
            folder = Path(directory) / "stage"
            run(folder, provider)
            with self.assertRaisesRegex(
                CoverageError, "V017_REPLAY_CONTRACT_MISMATCH"
            ):
                run(folder, provider, max_scene_attempts=4)
        self.assertEqual(len(calls), 1)

    def test_spend_guard_stops_additional_primary_calls(self):
        calls = []
        def provider(*, model, prepared):
            calls.append(prepared)
            packet = envelope(problem_response())
            packet["raw"]["usage"]["cost"] = 0.08
            return packet
        with TemporaryDirectory() as directory:
            out = run(Path(directory) / "stage", provider,
                      repair_calls_allowed=0,
                      observed_spend_guard_usd="0.05")
        self.assertEqual(len(calls), 1)
        self.assertEqual(out["status"], "FAILED_SAFE_FINAL")
        self.assertEqual(out["reason_code"], "V017_OBSERVED_SPEND_GUARD")

    def test_no_generation_output_token_limit_is_sent(self):
        calls = []
        def provider(*, model, prepared):
            calls.append(json.loads(json.dumps(prepared)))
            return envelope(synthetic_model_rows())
        with TemporaryDirectory() as directory:
            run(Path(directory) / "stage", provider)
        outgoing = json.dumps(calls)
        for forbidden in ("max_tokens", "max_output_tokens",
                          "max_completion_tokens", "max_new_tokens"):
            self.assertNotIn(forbidden, outgoing)


if __name__ == "__main__":
    unittest.main()
