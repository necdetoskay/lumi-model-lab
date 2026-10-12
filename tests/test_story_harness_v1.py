"""Story Harness V1: deterministic, fail-closed offline control-plane tests.

These tests validate *orchestration mechanics only*, never story quality.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.story_harness_v1 import (
    HarnessStop, archive_once, canonical_bytes, digest,
    load_json, replay, secure_artifact,
)

REPO = Path(__file__).resolve().parents[1]
PLAN_FILE = REPO / "configs/story_harness_v1_fixture.json"
FIXTURE_DIR = REPO / "tests/fixtures/story_harness_v1"


def base_plan():
    return json.loads(PLAN_FILE.read_text(encoding="utf-8"))


class StoryHarnessV1Tests(unittest.TestCase):
    def test_all_four_stage_artifacts_are_pinned_to_real_bytes(self):
        plan = base_plan()
        self.assertEqual([s["stage_id"] for s in plan["stages"]],
                         ["context", "spine", "writer", "q25"])
        self.assertEqual(plan["budget"],
                         {"max_provider_calls": 0, "max_cost_usd": "0"})
        for stage in plan["stages"]:
            src = REPO / stage["artifact"]
            self.assertEqual(stage["sha256"],
                             hashlib.sha256(src.read_bytes()).hexdigest())
            doc = json.loads(src.read_text(encoding="utf-8"))
            self.assertTrue(doc["demo_only"])
            self.assertFalse(doc.get("production_canonical_state", False))
            self.assertFalse(doc.get("actual_model_story", False))

    def test_replay_is_stable_and_never_promotes_referenced_reported_pass(self):
        plan = base_plan()
        plan_before = copy.deepcopy(plan)
        result = replay(plan, repo_root=REPO)
        self.assertEqual(result, replay(plan, repo_root=REPO))
        self.assertEqual(plan, plan_before)
        self.assertEqual(result["stage_count_planned"], 4)
        self.assertEqual(result["stage_count_inspected"], 4)
        self.assertEqual(result["status"], "REPLAYED_REPORTED_CHAIN_ONLY")
        self.assertFalse(result["gate_decision_authoritatively_verified"])
        self.assertFalse(result["semantic_support_certified"])
        self.assertFalse(result["state_commit_authorized"])
        self.assertFalse(result["full_story_state_qualified"])
        self.assertFalse(result["production_write_performed"])
        self.assertFalse(result["model_execution_performed"])
        self.assertEqual(result["provider_calls"], 0)
        self.assertEqual(result["provider_cost_usd"], "0")
        self.assertTrue(all(
            s["reported_gate"] == "REPORTED_PASS" and
            s["gate_decision_authoritatively_verified"] is False and
            s["actual_stage_invoked"] is False and
            s["provider_calls"] == 0
            for s in result["stages"]
        ))

    def test_cli_is_read_only_and_deterministic(self):
        command = [
            sys.executable, "-m", "src.story_harness_v1",
            "--plan", "configs/story_harness_v1_fixture.json",
            "--repo-root", str(REPO),
        ]
        one = subprocess.check_output(command, text=True, encoding="utf-8", cwd=REPO)
        two = subprocess.check_output(command, text=True, encoding="utf-8", cwd=REPO)
        self.assertEqual(one, two)
        result = json.loads(one)
        self.assertEqual(result, replay(base_plan(), repo_root=REPO))
        self.assertEqual(result["provider_calls"], 0)

    def test_reported_rejection_blocks_downstream_without_inspecting_files(self):
        plan = base_plan()
        plan["stages"][1]["reported_gate"] = "REPORTED_REJECT"
        plan["stages"][2]["artifact"] = "tests/fixtures/story_harness_v1/not-present.json"
        result = replay(plan, repo_root=REPO)
        self.assertEqual(result["status"], "STOPPED_ON_REPORTED_REJECT")
        self.assertEqual(result["stage_count_inspected"], 2)
        self.assertTrue(result["downstream_blocked"])
        self.assertFalse(result["state_commit_authorized"])

    def test_reported_review_stops_and_does_not_claim_approved_review(self):
        plan = base_plan()
        plan["stages"][2]["reported_gate"] = "REPORTED_REVIEW"
        result = replay(plan, repo_root=REPO)
        self.assertEqual(result["status"], "STOPPED_ON_REPORTED_REVIEW")
        self.assertEqual(result["stage_count_inspected"], 3)
        self.assertFalse(result["gate_decision_authoritatively_verified"])

    def test_stage_chain_dependency_is_hash_exact(self):
        plan = base_plan()
        plan["stages"][2]["consumed_sha256"] = "0" * 64
        with self.assertRaisesRegex(HarnessStop, "input SHA"):
            replay(plan, repo_root=REPO)
        plan = base_plan()
        plan["stages"][2]["depends_on"] = "context"
        with self.assertRaisesRegex(HarnessStop, "dependency"):
            replay(plan, repo_root=REPO)

    def test_stage_hash_must_match_artifact(self):
        plan = base_plan()
        plan["stages"][3]["sha256"] = "0" * 64
        with self.assertRaises(HarnessStop):
            replay(plan, repo_root=REPO)
        plan = base_plan()
        plan["stages"][0]["sha256"] = "X" * 64
        with self.assertRaises(HarnessStop):
            replay(plan, repo_root=REPO)

    def test_no_forged_model_cost_retry_or_extra_stage_field(self):
        for mutation in ["calls", "cost", "mode", "unknown_plan", "unknown_stage",
                         "extra_stage", "duplicate_stage", "bad_gate",
                         "bad_run_id", "first_has_parent"]:
            with self.subTest(mutation=mutation):
                plan = base_plan()
                if mutation == "calls":
                    plan["budget"]["max_provider_calls"] = 1
                elif mutation == "cost":
                    plan["budget"]["max_cost_usd"] = "0.20"
                elif mutation == "mode":
                    plan["mode"] = "LIVE_PAID"
                elif mutation == "unknown_plan":
                    plan["auto_retry"] = True
                elif mutation == "unknown_stage":
                    plan["stages"][0]["command"] = "run-a-model"
                elif mutation == "extra_stage":
                    plan["stages"].append(copy.deepcopy(plan["stages"][-1]))
                elif mutation == "duplicate_stage":
                    plan["stages"][1]["stage_id"] = "context"
                elif mutation == "bad_gate":
                    plan["stages"][0]["reported_gate"] = "GATE_ACCEPTED"
                elif mutation == "bad_run_id":
                    plan["run_id"] = "../production"
                elif mutation == "first_has_parent":
                    plan["stages"][0]["depends_on"] = "spine"
                with self.assertRaises(HarnessStop):
                    replay(plan, repo_root=REPO)

    def test_stage_paths_cannot_escape_or_cross_symlinks(self):
        for attack in [
            "../secrets.json", "/etc/passwd", "configs/../../etc/passwd",
            "tests/fixtures/story_harness_v1/context.txt",
            "https://elsewhere/file.json",
        ]:
            with self.subTest(path=attack):
                with self.assertRaises(HarnessStop):
                    secure_artifact(REPO, attack)
        with tempfile.TemporaryDirectory() as location:
            root = Path(location)
            (root / "data").mkdir()
            (root / "private.json").write_text('{"valid": true}', encoding="utf-8")
            (root / "data" / "link.json").symlink_to(root / "private.json")
            with self.assertRaises(HarnessStop):
                secure_artifact(root, "data/link.json")

    def test_duplicate_json_keys_and_nan_fail_closed(self):
        for payload in (
            b'{"status": "PASS", "status": "REJECT"}',
            b'{"cost": NaN}',
            b'{bad json',
            b"\xff",
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(HarnessStop):
                    load_json(payload)
        with tempfile.TemporaryDirectory() as location:
            root = Path(location)
            (root / "data").mkdir()
            (root / "data" / "corrupt.json").write_text(
                '{"reported_gate":"REPORTED_PASS","reported_gate":"REPORTED_REJECT"}',
                encoding="utf-8",
            )
            with self.assertRaises(HarnessStop):
                secure_artifact(root, "data/corrupt.json")

    def test_once_only_manifest_archive_is_explicit_and_not_overwritten(self):
        result = replay(base_plan(), repo_root=REPO)
        with tempfile.TemporaryDirectory() as location:
            root = Path(location)
            file = archive_once(result, repo_root=root)
            self.assertTrue(file.is_relative_to(root / "runs/story_harness_v1"))
            archived = json.loads(file.read_text(encoding="utf-8"))
            self.assertEqual(result, archived)
            original_hash = hashlib.sha256(file.read_bytes()).hexdigest()
            with self.assertRaises(FileExistsError):
                archive_once(result, repo_root=root)
            self.assertEqual(original_hash,
                             hashlib.sha256(file.read_bytes()).hexdigest())

    def test_archive_rejects_fake_promotion_and_directory_symlink(self):
        result = replay(base_plan(), repo_root=REPO)
        with tempfile.TemporaryDirectory() as location:
            root = Path(location)
            attack = copy.deepcopy(result)
            attack["state_commit_authorized"] = True
            with self.assertRaises(HarnessStop):
                archive_once(attack, repo_root=root)
            (root / "runs").symlink_to(Path(location).parent)
            with self.assertRaises(HarnessStop):
                archive_once(result, repo_root=root)

    def test_canonical_digest_and_stage_byte_hash_are_distinct(self):
        p = base_plan()
        self.assertEqual(digest(canonical_bytes(p)),
                         replay(p, repo_root=REPO)["plan_sha256"])
        source = secure_artifact(REPO, "tests/fixtures/story_harness_v1/context.json")
        self.assertEqual(digest(source), p["stages"][0]["sha256"])
        self.assertNotEqual(digest(canonical_bytes(load_json(source))), digest(source))


if __name__ == "__main__":
    unittest.main()
