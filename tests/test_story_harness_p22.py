"""P2.2 real historical SpineForge deterministic validator, offline only."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from src.story_harness_p22 import (
    CASE_ID, CONTEXT_PATH, CASES_PATH, SCHEMA, SOURCE_SHA256,
    _pinned_inputs, _run_spine_validator, rerun_spine,
    verify_pinned_report,
)
from src.story_harness_v1 import HarnessStop, digest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "configs/story_harness_p1_frozen_import.json"
APPROVED = ROOT / "evidence/story_harness_p1/snapshots/spine-v20-approved.json"


def pinned_root():
    value = os.environ.get("STORY_HARNESS_PINNED_SPINE_ROOT")
    return Path(value).resolve(strict=True) if value else None


def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@unittest.skipUnless(os.environ.get("STORY_HARNESS_PINNED_SPINE_ROOT"),
                     "Requires exact frozen SpineForge checkout, no substitute fixture")
class P22RealSpineForgeTests(unittest.TestCase):
    def run_replay(self, source=None, manifest_override=None):
        return rerun_spine(
            manifest=manifest() if manifest_override is None else manifest_override,
            repo_root=ROOT,
            pinned_spine_root=pinned_root() if source is None else source,
        )

    def test_real_deterministic_validator_executes_and_is_reproducible(self):
        before = manifest()
        report = self.run_replay(manifest_override=before)
        self.assertEqual(report, self.run_replay())
        self.assertEqual(before, manifest())
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["case_id"], CASE_ID)
        self.assertEqual(report["original_historical_gate_claim_immutable"], "ACCEPT")
        self.assertEqual(report["actual_spine_deterministic_validator_invocations"], 1)
        self.assertEqual(report["result_scope"], "STRUCTURAL_CONTEXT_AUTHORITY_OBLIGATIONS_ONLY")
        validated = report["real_validator_report"]
        self.assertEqual(validated["schema"], "spineforge-v19-validation.v1")
        self.assertEqual(validated["discovery_turns"], 8)
        self.assertEqual(validated["real_choice_count"], 2)
        self.assertEqual(len(validated["location_sequence"]), 6)
        self.assertTrue(validated["authority_valid"])
        self.assertTrue(validated["reveal_safe"])
        self.assertTrue(validated["obligations_valid"])
        for key in ("original_human_review_authenticated", "original_model_product_gate_reexecuted",
                    "story_semantic_quality_certified", "spine_writer_q25_same_story_handoff_verified",
                    "downstream_execution_authorized", "state_commit_authorized",
                    "production_write_performed"):
            self.assertIs(report[key], False)
        self.assertEqual(report["provider_calls"], 0)
        self.assertEqual(report["provider_cost_usd"], "0")

    def test_source_modules_and_fixtures_pinned_by_sha(self):
        source = pinned_root()
        context, cases = _pinned_inputs(source)
        self.assertEqual(context, source / CONTEXT_PATH)
        self.assertEqual(cases, source / CASES_PATH)
        for path, wanted in SOURCE_SHA256.items():
            self.assertEqual(digest((source / path).read_bytes()), wanted)

    def test_changed_checkout_or_manifest_fail_closed(self):
        with self.assertRaises(HarnessStop):
            self.run_replay(source=ROOT)
        altered = copy.deepcopy(manifest())
        altered["cases"][0]["files"][0]["sha256"] = "0" * 64
        with self.assertRaises(HarnessStop):
            self.run_replay(manifest_override=altered)
        altered = copy.deepcopy(manifest())
        altered["cases"][0]["case_id"] = "FAKE-SPINE"
        with self.assertRaises(HarnessStop):
            self.run_replay(manifest_override=altered)

    def test_altered_spine_and_mismatched_context_fail_closed(self):
        source = pinned_root()
        context, cases = _pinned_inputs(source)
        approval = json.loads(APPROVED.read_text(encoding="utf-8"))
        approval["approved_spine"]["title"] += " altered without approval"
        with self.assertRaisesRegex(HarnessStop, "rejected"):
            _run_spine_validator(
                approval_bytes=json.dumps(approval).encode(),
                pinned_root=source,
                context_path=context, cases_path=cases,
                python_executable=__import__("sys").executable,
            )
        approval = json.loads(APPROVED.read_text(encoding="utf-8"))
        approval["context_fingerprint"] = "f" * 64
        with self.assertRaisesRegex(HarnessStop, "rejected"):
            _run_spine_validator(
                approval_bytes=json.dumps(approval).encode(),
                pinned_root=source,
                context_path=context, cases_path=cases,
                python_executable=__import__("sys").executable,
            )

    def test_forged_receipt_or_downstream_authorization_rejected(self):
        good = self.run_replay()
        self.assertTrue(verify_pinned_report(
            good, manifest=manifest(), repo_root=ROOT, pinned_spine_root=pinned_root(),
        ))
        forged = copy.deepcopy(good)
        forged["downstream_execution_authorized"] = True
        with self.assertRaises(HarnessStop):
            verify_pinned_report(
                forged, manifest=manifest(), repo_root=ROOT, pinned_spine_root=pinned_root(),
            )
        forged = copy.deepcopy(good)
        forged["real_validator_report"]["discovery_turns"] = 100
        with self.assertRaises(HarnessStop):
            verify_pinned_report(
                forged, manifest=manifest(), repo_root=ROOT, pinned_spine_root=pinned_root(),
            )

    def test_provider_credentials_not_inherited(self):
        with patch.dict(os.environ, {
            "OPENROUTER_API_KEY": "not-forwarded",
            "OPENAI_API_KEY": "not-forwarded",
            "ANTHROPIC_API_KEY": "not-forwarded",
        }):
            self.assertEqual(self.run_replay()["provider_calls"], 0)


if __name__ == "__main__":
    unittest.main()

