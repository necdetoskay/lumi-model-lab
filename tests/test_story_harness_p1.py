"""P1 real historical archived evidence replay, not model or semantic approval."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.story_harness_p1 import (
    FROZEN_CASES, PINNED_SOURCE_COMMIT, inspect_historical,
)
from src.story_harness_v1 import HarnessStop

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "configs/story_harness_p1_frozen_import.json"
SOURCE = ROOT / MANIFEST


def source():
    return json.loads(SOURCE.read_text(encoding="utf8"))


class FrozenHistoricalAdapterTests(unittest.TestCase):
    def test_four_real_separate_historical_cases_are_reproducible_and_untrusted(self):
        manifest = source()
        before = copy.deepcopy(manifest)
        report = inspect_historical(manifest, repo_root=ROOT)
        self.assertEqual(report, inspect_historical(manifest, repo_root=ROOT))
        self.assertEqual(before, manifest)
        self.assertEqual(report["schema"], "lumi.story-harness-historical-evidence.v1")
        self.assertEqual(report["source_commit"], PINNED_SOURCE_COMMIT)
        self.assertEqual(report["case_count"], 4)
        self.assertEqual(len(report["historical_cases"]), 4)
        self.assertEqual(report["sum_historical_provider_reported_cost_usd_for_q25_subset"], "0.085152")
        self.assertEqual(report["new_provider_calls"], 0)
        self.assertEqual(report["new_provider_cost_usd"], "0")
        self.assertEqual(report["real_gate_invocations"], 0)
        self.assertFalse(report["historical_verdicts_rewritten"])
        self.assertFalse(report["spine_and_q25_story_chain_claimed"])
        self.assertFalse(report["historical_gate_authenticated_by_harness"])
        self.assertFalse(report["semantic_support_certified"])
        self.assertFalse(report["full_story_state_qualified"])
        self.assertFalse(report["state_commit_authorized"])
        self.assertFalse(report["production_write_performed"])
        for case in report["historical_cases"]:
            self.assertFalse(case["shared_story_dependency_inferred"])
            self.assertFalse(case["historical_gate_authenticated_by_harness"])
            self.assertFalse(case["downstream_execution_permitted_by_harness"])
            for item in case["artifact_inventory"]:
                self.assertFalse(item["source_bytes_rechecked_against_remote_this_run"])
                self.assertEqual(item["source_commit"], PINNED_SOURCE_COMMIT)
                self.assertEqual(item["verified_sha256"],
                    hashlib.sha256((ROOT / item["archive_path"]).read_bytes()).hexdigest())

    def test_v20_human_approved_spine_retains_handoff_not_paid_authorization(self):
        report = inspect_historical(source(), repo_root=ROOT)
        case = report["historical_cases"][0]
        assert case["case_id"] == "SPINE-V20-HUMAN-APPROVED"
        decision = case["inspection"]
        self.assertEqual(decision["historical_original_outcome"], "ACCEPT")
        self.assertEqual(decision["historical_outcome_class"],
                         "HUMAN_SPINE_APPROVAL_RECORDED_HARNESS_NOT_AUTHORITY")
        self.assertFalse(decision["historical_stop_required"])
        self.assertFalse(decision["reviewer_authenticated_by_harness"])
        self.assertFalse(decision["original_gate_reexecuted"])
        self.assertFalse(decision["model_call_authorized"])
        self.assertFalse(case["downstream_execution_permitted_by_harness"])

    def test_v20_failed_story_audit_stays_rejected_even_if_other_spine_was_approved(self):
        report = inspect_historical(source(), repo_root=ROOT)
        case = report["historical_cases"][1]
        self.assertEqual(case["case_id"], "SPINE-V20-AUDIT-REJECTED")
        self.assertEqual(case["inspection"]["historical_original_outcome"],
                         "FAIL_KNOWN_DEFECT_MISSED")
        self.assertEqual(case["inspection"]["historical_outcome_class"],
                         "SPINE_AUDIT_FAILED_HARNESS_MUST_BLOCK")
        self.assertTrue(case["inspection"]["historical_stop_required"])

    def test_kite_is_not_terminal_state_and_greenhouse_paid_reject_remains_reject(self):
        report = inspect_historical(source(), repo_root=ROOT)
        kite, greenhouse = report["historical_cases"][2:4]
        self.assertEqual(kite["case_id"], "Q25-KITE01-CANDIDATES")
        self.assertEqual(kite["inspection"]["historical_original_outcome"],
                         "SOURCE_BOUND_CANDIDATES_ONLY")
        self.assertEqual(kite["inspection"]["historical_outcome_class"],
                         "SOURCE_BOUND_CANDIDATES_ONLY_NOT_FINAL_STATE")
        self.assertEqual(kite["inspection"]["raw_claim_count"], 16)
        self.assertEqual(kite["inspection"]["historical_provider_cost_usd"], "0.042406")
        self.assertFalse(kite["inspection"]["canonical_state_admitted"])
        self.assertTrue(kite["inspection"]["historical_stop_required"])
        self.assertEqual(greenhouse["case_id"], "Q25-GREENHOUSE01-REJECTED")
        self.assertEqual(greenhouse["inspection"]["historical_original_outcome"],
                         "REJECTED_BY_OFFLINE_GATE")
        self.assertEqual(greenhouse["inspection"]["historical_outcome_class"],
                         "PAID_RUN_REJECTED_DO_NOT_RETROACTIVELY_PASS")
        self.assertEqual(greenhouse["inspection"]["historical_provider_cost_usd"], "0.042746")
        self.assertTrue(greenhouse["inspection"]["historical_stop_required"])
        self.assertFalse(greenhouse["inspection"]["canonical_state_admitted"])
        for row in (kite,greenhouse):
            self.assertEqual(row["inspection"]["historical_provider_calls_reported"], 1)
            self.assertEqual(row["inspection"]["new_provider_calls"], 0)

    def test_real_exported_bytes_match_explicit_pinned_hashes(self):
        manifest = source()
        self.assertEqual(set(x["case_id"] for x in manifest["cases"]), set(FROZEN_CASES))
        for case in manifest["cases"]:
            pinned = FROZEN_CASES[case["case_id"]]
            self.assertEqual(case["adapter"], pinned["adapter"])
            for file in case["files"]:
                short, path, sha = pinned["files"][file["kind"]]
                self.assertEqual(file["archive"],
                    "evidence/story_harness_p1/snapshots/" + short)
                self.assertEqual(file["source_path"], path)
                self.assertEqual(file["sha256"], sha)
                self.assertEqual(hashlib.sha256(
                    (ROOT / file["archive"]).read_bytes()).hexdigest(),sha)

    def test_cli_is_deterministic_and_network_free(self):
        cmd=[sys.executable,"-m","src.story_harness_p1",
            "--manifest",MANIFEST,"--repo-root",str(ROOT)]
        a=subprocess.check_output(cmd,cwd=ROOT,text=True,encoding="utf8")
        b=subprocess.check_output(cmd,cwd=ROOT,text=True,encoding="utf8")
        self.assertEqual(a,b)
        self.assertEqual(json.loads(a),inspect_historical(source(),repo_root=ROOT))

    def test_tampered_source_label_or_commit_is_blocked(self):
        for damage in [
            "new_origin", "different_commit", "renamed_case", "swapped_case_id",
            "changed_adapter", "source_path", "wrong_sha", "same_archive_reused",
            "missing_ledger", "duplicate_role", "paid_mode", "unknown_case",
            "source_snapshot_path", "wrong_source_kind",
        ]:
            with self.subTest(damage=damage):
                m=source()
                if damage=="new_origin":m["source_repository"]="attacker/fake"
                elif damage=="different_commit":m["source_commit"]="0"*40
                elif damage=="renamed_case":m["cases"][2]["case_id"]="Q25-FAKE-SUCCESS"
                elif damage=="swapped_case_id":m["cases"][2]["case_id"],m["cases"][3]["case_id"]=m["cases"][3]["case_id"],m["cases"][2]["case_id"]
                elif damage=="changed_adapter":m["cases"][3]["adapter"]="spine_human_review"
                elif damage=="source_path":m["cases"][3]["files"][1]["source_path"]="evidence/q25/Q25-WITHHELD-TRIAL-20261012/paid-attempt-03-raw-extraction.json"
                elif damage=="wrong_sha":m["cases"][3]["files"][0]["sha256"]="0"*64
                elif damage=="same_archive_reused":m["cases"][3]["files"][0]["archive"]=m["cases"][2]["files"][0]["archive"]
                elif damage=="missing_ledger":m["cases"][3]["files"].pop(0)
                elif damage=="duplicate_role":m["cases"][2]["files"][0]["kind"]="raw"
                elif damage=="paid_mode":m["mode"]="EXECUTE_PAID"
                elif damage=="unknown_case":m["cases"][0]["case_id"]="PROD-WRITER-APPROVED"
                elif damage=="source_snapshot_path":m["cases"][0]["files"][0]["archive"]="../private.json"
                elif damage=="wrong_source_kind":m["cases"][0]["files"][0]["source_path"]="evidence/q25/other.json"
                with self.assertRaises(HarnessStop):
                    inspect_historical(m,repo_root=ROOT)

    def test_modifying_a_real_archived_artifact_byte_prevents_consumption(self):
        m=source()
        with tempfile.TemporaryDirectory() as location:
            root=Path(location)
            for case in m["cases"]:
                for file in case["files"]:
                    dst=root / file["archive"]
                    dst.parent.mkdir(parents=True,exist_ok=True)
                    dst.write_bytes((ROOT / file["archive"]).read_bytes())
            selected=root/m["cases"][3]["files"][0]["archive"]
            payload=json.loads(selected.read_text(encoding="utf8"))
            payload["outcome"]="SOURCE_BOUND_CANDIDATES_ONLY"
            selected.write_text(json.dumps(payload,ensure_ascii=False)+"\n",encoding="utf8")
            with self.assertRaisesRegex(HarnessStop,"integrity|differs|hash"):
                inspect_historical(m,repo_root=root)

    def test_historical_provider_usage_is_never_new_harness_spending(self):
        report=inspect_historical(source(),repo_root=ROOT)
        self.assertGreater(float(report["sum_historical_provider_reported_cost_usd_for_q25_subset"]),0)
        self.assertEqual(report["new_provider_calls"],0)
        self.assertEqual(report["new_provider_cost_usd"],"0")
        self.assertEqual(report["real_gate_invocations"],0)


if __name__=="__main__":
    unittest.main()
