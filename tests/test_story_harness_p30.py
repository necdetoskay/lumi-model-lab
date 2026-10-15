"""P3.0 same-story frozen SpineForge -> Writer manifest; missing-Q25 fail-closed."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from src.story_harness_p30 import (
    APPROVAL_PATH, AUDIT_FILE, EXPECTED_ARTIFACT_ID, EXCLUDED_Q25_CASES,
    PINS, Q25_MISSING, SCHEMA, STORY_SHA, _pin_source,
    _run_original_writer_checker, _validate_chain, qualify, verify_report,
)
from src.story_harness_v1 import HarnessStop, digest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "configs/story_harness_p1_frozen_import.json"


def source():
    raw = os.environ.get("STORY_HARNESS_PINNED_P3_ROOT")
    return Path(raw).resolve(strict=True) if raw else None


def frozen_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def source_record():
    return json.loads((source() / APPROVAL_PATH).read_text(encoding="utf-8"))


def original_writer():
    return _run_original_writer_checker(
        pinned_root=source(), python_executable=__import__("sys").executable,
    )


def original_audit():
    return json.loads((source() / AUDIT_FILE).read_text(encoding="utf-8"))


@unittest.skipUnless(os.environ.get("STORY_HARNESS_PINNED_P3_ROOT"),
                     "Actual P3 frozen source checkout required")
class P30SameStoryArtifactTests(unittest.TestCase):
    def full(self, manifest=None, original_source=None):
        return qualify(
            manifest=frozen_manifest() if manifest is None else manifest,
            repo_root=ROOT,
            pinned_source_root=source() if original_source is None else original_source,
        )

    def test_verified_pinned_spine_writer_story_and_missing_q25(self):
        report = self.full()
        self.assertEqual(report, self.full())
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["source_commit"],
                         "2eb3d825b5baf8f0f16ccb23805f619d433c7236")
        self.assertTrue(report["writer_original_validator_executed"])
        self.assertTrue(report["same_story_spine_to_writer_confirmed"])
        self.assertEqual(report["writer_story_sha256"], STORY_SHA)
        self.assertEqual(report["writer_manifest_artifact_id"], EXPECTED_ARTIFACT_ID)
        self.assertEqual(report["writer_word_count"], 2324)
        self.assertEqual(report["original_story_audit_qualification"],
                         "FAIL_KNOWN_DEFECT_MISSED")
        self.assertFalse(report["original_story_audit_qualification_pass"])
        self.assertFalse(report["original_story_audit_reexecuted"])
        self.assertEqual(report["q25_considered_but_unrelated_frozen_cases"],
                         EXCLUDED_Q25_CASES)
        self.assertEqual(report["stop_reason"], Q25_MISSING)
        self.assertEqual(report["state"], "STOPPED_MISSING_SAME_STORY_Q25")
        self.assertEqual(report["provider_calls"], 0)
        self.assertEqual(report["provider_cost_usd"], "0")
        for key in (
            "same_story_q25_evidence_present", "same_story_q25_handoff_verified",
            "historical_human_approval_authenticated",
            "model_story_quality_certified", "writer_execution_authorized",
            "q25_execution_authorized", "downstream_execution_authorized",
            "state_commit_authorized", "production_write_performed",
        ):
            self.assertIs(report[key], False, key)

    def test_original_writer_verifier_actually_runs_and_files_pinned(self):
        _pin_source(source())
        writer = original_writer()
        self.assertTrue(writer["validated_original_writer_artifact"])
        self.assertEqual(writer["writer_result_status"], "writer_generated")
        self.assertEqual(writer["writer_envelope_status"], "writer_generated")
        self.assertEqual(writer["writer_manifest"]["artifact_id"], EXPECTED_ARTIFACT_ID)
        for path, sha in PINS.items():
            self.assertEqual(digest((source() / path).read_bytes()), sha)

    def test_changed_checkout_and_altered_manifest_fail_closed(self):
        with self.assertRaises(HarnessStop):
            self.full(original_source=ROOT)
        broken = frozen_manifest()
        broken["cases"][0]["files"][0]["sha256"] = "a" * 64
        with self.assertRaises(HarnessStop):
            self.full(manifest=broken)
        broken = frozen_manifest()
        broken["cases"][2]["case_id"] = "SPINE-V20-WRITER3-SAME-STORY"
        with self.assertRaises(HarnessStop):
            self.full(manifest=broken)

    def test_hash_changed_even_if_source_code_would_still_execute(self):
        # Simulates different source module/config/artifact hash, no source mutations.
        with patch.dict(PINS, {AUDIT_FILE: "0" * 64}):
            with self.assertRaisesRegex(HarnessStop, "not version-pinned"):
                _pin_source(source())
        with patch.dict(PINS, {APPROVAL_PATH: "0" * 64}):
            with self.assertRaisesRegex(HarnessStop, "not version-pinned"):
                _pin_source(source())

    def test_bad_context_approval_and_spine_lineage_rejected(self):
        approved, writer, audit = source_record(), original_writer(), original_audit()
        self.assertEqual(
            _validate_chain(spine_record=approved, writer=writer, audit=audit)["spine_hash"],
            approved["spine_hash"],
        )
        for key in ("spine_hash", "approval_id", "context_fingerprint", "context_pack_id"):
            altered = copy.deepcopy(writer)
            altered["writer_result_lineage"][key] = "forged"
            with self.subTest(field=key), self.assertRaisesRegex(HarnessStop, "NOT the same story"):
                _validate_chain(spine_record=approved, writer=altered, audit=audit)
            altered = copy.deepcopy(writer)
            altered["writer_manifest"][key] = "forged"
            with self.subTest(manifest_key=key), self.assertRaises(HarnessStop):
                _validate_chain(spine_record=approved, writer=altered, audit=audit)

    def test_writer_run_swap_story_tamper_and_forged_success_rejected(self):
        approved, writer, audit = source_record(), original_writer(), original_audit()
        for field, value in (
            ("source_run_id", 36955873689),
            ("story_path", "evidence/spineforge-v20-paid-writer/36955873689/fake.txt"),
            ("story_sha256", "0" * 64),
            ("artifact_id", "writer-story:fake"),
            ("immutable", False),
            ("attempt_index", 4),
        ):
            altered = copy.deepcopy(writer)
            altered["writer_manifest"][field] = value
            with self.subTest(field=field), self.assertRaises(HarnessStop):
                _validate_chain(spine_record=approved, writer=altered, audit=audit)
        altered = copy.deepcopy(writer)
        altered["writer_result_status"] = "writer_provider_failure"
        with self.assertRaises(HarnessStop):
            _validate_chain(spine_record=approved, writer=altered, audit=audit)
        altered = copy.deepcopy(writer)
        altered["validated_original_writer_artifact"] = False
        with self.assertRaises(HarnessStop):
            _validate_chain(spine_record=approved, writer=altered, audit=audit)

    def test_failed_qualified_audit_can_never_become_accept(self):
        approved, writer, audit = source_record(), original_writer(), original_audit()
        for key, value in (
            ("qualification_pass", True),
            ("status", "ACCEPT"),
            ("source_story_sha256", "0" * 64),
            ("source_artifact_id", "writer-story:other"),
            ("matched_target_count", 1),
        ):
            fake = copy.deepcopy(audit)
            fake[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(HarnessStop, "failed audit"):
                _validate_chain(spine_record=approved, writer=writer, audit=fake)

    def test_forged_receipt_and_fake_q25_authority_rejected(self):
        expected = self.full()
        self.assertTrue(verify_report(
            expected, manifest=frozen_manifest(), repo_root=ROOT,
            pinned_source_root=source(),
        ))
        for key, value in (
            ("state_commit_authorized", True),
            ("q25_execution_authorized", True),
            ("same_story_q25_evidence_present", True),
            ("same_story_q25_handoff_verified", True),
            ("stop_reason", "ACCEPT"),
            ("original_story_audit_qualification_pass", True),
        ):
            forged = copy.deepcopy(expected)
            forged[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(HarnessStop, "receipt differs"):
                verify_report(forged, manifest=frozen_manifest(),
                              repo_root=ROOT, pinned_source_root=source())

    def test_never_forward_provider_environment(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "fake", "OPENAI_API_KEY": "fake",
                                     "ANTHROPIC_API_KEY": "fake", "PYTHONPATH": "/tmp/fake"}):
            report = self.full()
        self.assertEqual(report["provider_calls"], 0)
        self.assertEqual(report["stop_reason"], Q25_MISSING)


if __name__ == "__main__":
    unittest.main()

