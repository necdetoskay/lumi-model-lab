"""P4.57 paid-gate safety is tested with no model calls."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from src.story_harness_p457_b07_gate import (
    EXPECTED_GRANT, LABEL, OLD_CLAIM_ROOTS, check_claims,
    check_grant, preflight,
)
from src.story_harness_p454_b07_age25 import status
from src.story_harness_v1 import HarnessStop

REPO = Path(__file__).resolve().parents[1]

class P457GateTests(unittest.TestCase):
    def test_exact_budget_grant_and_no_model_post(self):
        self.assertTrue(check_grant(deepcopy(EXPECTED_GRANT)))
        state = status(".")
        self.assertEqual(state["provider_calls"], 0)
        self.assertEqual(state["generation_cost_cap_usd"], "0.35")
        self.assertEqual(state["prior_conservative_budget_reserved_usd"], "2.859558")
        self.assertFalse(state["paid_execution_enabled"])

    def test_mutated_grants_are_denied(self):
        for key, value in (
            ("maximum_new_cost_usd", "0.36"),
            ("previous_conservative_budget_reserved_usd", "0"),
            ("automatic_retries", True),
            ("max_model_posts", 3),
            ("production_write", True),
            ("case_id", "B06"),
            ("previous_p455_model_posts", 1),
        ):
            with self.subTest(key=key):
                changed = deepcopy(EXPECTED_GRANT)
                changed[key] = value
                with self.assertRaises(HarnessStop):
                    check_grant(changed)

    def test_claims_deny_both_old_runner_roots(self):
        with TemporaryDirectory() as td:
            self.assertTrue(check_claims(td))
            for root_name in OLD_CLAIM_ROOTS:
                folder = Path(td) / root_name / LABEL
                folder.mkdir(parents=True)
                with self.assertRaises(HarnessStop):
                    check_claims(td)
                folder.rmdir()
                folder.parent.rmdir()

    def test_claim_root_symlink_does_not_bypass(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / OLD_CLAIM_ROOTS[0]).symlink_to(root, target_is_directory=True)
            with self.assertRaises(HarnessStop):
                check_claims(td)

    def test_real_source_stop_and_grant_offline(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "only-grant.json"
            path.write_text(json.dumps(EXPECTED_GRANT), encoding="utf-8")
            receipt = preflight(".", td, path)
            self.assertEqual(receipt["provider_calls"], 0)
            self.assertEqual(receipt["offline_preflight"], "READY_NO_MODEL_POST")
            self.assertEqual(receipt["maximum_new_spend_usd"], "0.35")

    def test_workflow_is_one_grant_commit_only(self):
        path = REPO / ".github/workflows/story-harness-p457-b07-paid-gate.yml"
        data = path.read_text(encoding="utf-8")
        self.assertIn("configs/story_harness_p457_b07_trigger.json", data)
        self.assertNotIn("github.run_attempt == 1", data)
        self.assertNotIn("github.event.action == 'synchronize'", data)
        self.assertIn("git", data)
        self.assertIn("--paid-once", data)
        self.assertIn("if-no-files-found: warn", data)
        self.assertIn("on:\n  workflow_dispatch:", data)
        self.assertIn("if: ${{ false }}", data)
        self.assertNotIn("\n  pull_request:", data)
        self.assertNotIn("cancel-in-progress: true", data)
        self.assertIn("P457_B07_READY_NO_POST", data)

if __name__ == "__main__":
    unittest.main()
