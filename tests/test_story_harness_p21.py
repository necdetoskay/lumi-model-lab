"""P2.1 replays ACTUAL Q25 source/structural validation, never paid generation."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src.story_harness_p21 import (
    GATE, SCHEMA, PINNED_SOURCE_COMMIT, SOURCE, VALIDATOR_SHA,
    _verify_checkout, rerun_q25, verify_pinned_report,
)
from src.story_harness_v1 import HarnessStop, canonical_bytes, digest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "configs/story_harness_p1_frozen_import.json"


def _source_root():
    path = os.environ.get("STORY_HARNESS_PINNED_Q25_ROOT")
    return Path(path).resolve() if path else None


def _manifest():
    return json.loads(MANIFEST.read_text(encoding="utf8"))


@unittest.skipUnless(_source_root(), "Real P2.1 cross-check needs explicit frozen Q25 checkout")
class P21ActualQ25ValidatorTests(unittest.TestCase):
    def run_replay(self, manifest=None, source_root=None):
        return rerun_q25(
            manifest=_manifest() if manifest is None else manifest,
            repo_root=ROOT,
            pinned_q25_root=_source_root() if source_root is None else source_root,
        )

    def test_exact_git_commit_and_source_code_identity(self):
        pinned = _source_root()
        _verify_checkout(pinned)
        commit = subprocess.check_output(
            ["git", "-C", str(pinned), "rev-parse", "HEAD"],
            text=True,
        ).strip()
        self.assertEqual(commit, PINNED_SOURCE_COMMIT)
        self.assertEqual(digest((pinned / "src/q25_extractor_adapter.py").read_bytes()),
                         VALIDATOR_SHA)

    def test_actual_offline_q25_validator_two_distinct_real_model_responses(self):
        m = _manifest()
        old = copy.deepcopy(m)
        first = self.run_replay(m)
        again = self.run_replay(m)
        self.assertEqual(first, again)
        self.assertEqual(m, old)
        self.assertEqual(first["schema"], SCHEMA)
        self.assertEqual(first["actual_q25_offline_gate_invocations"], 2)
        self.assertEqual(first["spineforge_gate_invocations"], 0)
        self.assertFalse(first["original_paid_gate_results_modified"])
        self.assertFalse(first["original_human_review_authenticated"])
        self.assertFalse(first["semantic_support_certified"])
        self.assertFalse(first["terminal_state_complete"])
        self.assertFalse(first["state_commit_authorized"])
        self.assertFalse(first["production_write_performed"])
        self.assertEqual(first["provider_calls"], 0)
        self.assertEqual(first["provider_cost_usd"], "0")
        self.assertEqual(len(first["cases"]), 2)
        kite, greenhouse = first["cases"]
        self.assertEqual(kite["case_id"], "Q25-KITE01-CANDIDATES")
        self.assertEqual(kite["original_paid_outcome_immutable"],
                         "SOURCE_BOUND_CANDIDATES_ONLY")
        self.assertEqual(kite["replay_status"], "SOURCE_BOUND_CANDIDATES_ONLY")
        self.assertEqual(kite["terminal_field_coverage_count"], 57)
        self.assertEqual(kite["terminal_field_status_counts"], {
            "CANDIDATE": 13, "PARTIAL_CANDIDATES": 2, "STRUCTURAL_ONLY": 23,
            "UNASSESSED": 17, "UNKNOWN": 2})
        self.assertEqual(kite["current_offline_source_order_adjustments"], [])
        self.assertEqual(greenhouse["case_id"], "Q25-GREENHOUSE01-REJECTED")
        self.assertEqual(greenhouse["original_paid_outcome_immutable"],
                         "REJECTED_BY_OFFLINE_GATE")
        self.assertEqual(greenhouse["replay_status"], "SOURCE_BOUND_CANDIDATES_ONLY")
        self.assertEqual(greenhouse["terminal_field_coverage_count"], 54)
        self.assertEqual(greenhouse["terminal_field_status_counts"], {
            "CANDIDATE": 14, "PARTIAL_CANDIDATES": 1,
            "STRUCTURAL_ONLY": 23, "UNASSESSED": 14, "UNKNOWN": 2})
        self.assertEqual(len(greenhouse["current_offline_source_order_adjustments"]),1)
        adjustment = greenhouse["current_offline_source_order_adjustments"][0]
        self.assertEqual(adjustment["original_offsets"], [1373,1190])
        self.assertEqual(adjustment["canonical_offsets"], [1190,1373])
        self.assertEqual(adjustment["reason"], "SOURCE_POSITION_SORT_ONLY_NOT_SEMANTIC_REPAIR")
        for item in first["cases"]:
            self.assertTrue(item["execution_actual"])
            self.assertTrue(item["replay_status_not_historical_outcome"])
            self.assertFalse(item["complete_story_state_certified"])
            self.assertFalse(item["semantic_validity_certified"])
            self.assertFalse(item["downstream_execution_authorized"])
            self.assertFalse(item["canonical_state_commit_authorized"])
            self.assertEqual(item["provider_calls_this_run"],0)
            self.assertEqual(item["validator_git_commit"],PINNED_SOURCE_COMMIT)
            self.assertEqual(item["validator_entrypoint_sha256"],VALIDATOR_SHA)

    def test_different_checkout_is_rejected_before_any_model_or_validator(self):
        with self.assertRaisesRegex(HarnessStop, "checkout|pinned commit"):
            self.run_replay(source_root=ROOT)
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(HarnessStop):
                self.run_replay(source_root=Path(temp))

    def test_tampered_original_source_identity_and_gate_source_hash_fail_closed(self):
        with patch("src.story_harness_p21.VALIDATOR_SHA", "0" * 64):
            with self.assertRaisesRegex(HarnessStop, "validator implementation"):
                self.run_replay()
        changed = copy.deepcopy(SOURCE["Q25-KITE01-CANDIDATES"])
        with patch.dict(SOURCE, {"Q25-KITE01-CANDIDATES": (
            changed[0], "0" * 64, changed[2],
        )}):
            with self.assertRaisesRegex(HarnessStop, "source request changed"):
                self.run_replay()

    def test_forged_model_result_or_swapped_ledger_rejected_before_gate_runs(self):
        m = _manifest()
        m["cases"][3]["files"][0]["sha256"] = "0" * 64
        with self.assertRaises(HarnessStop):
            self.run_replay(manifest=m)
        m = _manifest()
        m["cases"][3]["case_id"] = "Q25-KITE01-CANDIDATES"
        with self.assertRaises(HarnessStop):
            self.run_replay(manifest=m)

    def test_replay_receipt_matches_frozen_artifact_and_refuses_forged_history(self):
        archive = ROOT / "evidence/story_harness_p21/pinned-real-q25-offline-replay.json"
        frozen = json.loads(archive.read_text(encoding="utf8"))
        fresh = self.run_replay()
        self.assertEqual(frozen, fresh)
        self.assertTrue(verify_pinned_report(
            frozen, manifest=_manifest(), repo_root=ROOT,
            pinned_q25_root=_source_root(),
        ))
        for damage in ("rewrite_paid_reject", "fake_spine_gate",
                       "approve_semantics", "fake_provider_call",
                       "delete_source_order_fix", "promote_canonical_state"):
            with self.subTest(damage=damage):
                changed = copy.deepcopy(frozen)
                if damage == "rewrite_paid_reject":
                    changed["cases"][1]["original_paid_outcome_immutable"] = "SOURCE_BOUND_CANDIDATES_ONLY"
                elif damage == "fake_spine_gate":
                    changed["spineforge_gate_invocations"] = 1
                elif damage == "approve_semantics":
                    changed["semantic_support_certified"] = True
                elif damage == "fake_provider_call":
                    changed["provider_calls"] = 1
                elif damage == "delete_source_order_fix":
                    changed["cases"][1]["current_offline_source_order_adjustments"] = []
                elif damage == "promote_canonical_state":
                    changed["state_commit_authorized"] = True
                with self.assertRaises(HarnessStop):
                    verify_pinned_report(
                        changed, manifest=_manifest(), repo_root=ROOT,
                        pinned_q25_root=_source_root(),
                    )

    def test_real_validator_cli_is_pure_replay_no_provider_keys(self):
        cmd = [
            sys.executable, "-m", "src.story_harness_p21",
            "--repo-root", str(ROOT),
            "--pinned-q25-root", str(_source_root()),
        ]
        one = subprocess.check_output(cmd, cwd=ROOT, encoding="utf8", text=True)
        two = subprocess.check_output(cmd, cwd=ROOT, encoding="utf8", text=True)
        self.assertEqual(one, two)
        result = json.loads(one)
        self.assertEqual(result, self.run_replay())
        self.assertEqual(result["provider_calls"], 0)
        self.assertFalse(result["original_paid_gate_results_modified"])


if __name__ == "__main__":
    unittest.main()
