"""P4.56 offline-only CI contract."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
UNIQUE = "$" + "{{ github.job }}-" + "$" + "{{ github.run_id }}-" + "$" + "{{ github.run_attempt }}"

class StoryHarnessCIContract(unittest.TestCase):
    def test_archived_one_shots_cannot_run_on_pr_or_manual_dispatch(self):
        retired = sorted(p for p in WORKFLOWS.glob("story-harness-*.yml")
                         if p.name.endswith(("-once.yml", "-one-shot.yml")))
        self.assertGreaterEqual(len(retired), 23)
        for path in retired:
            with self.subTest(path=path.name):
                data = path.read_text(encoding="utf-8")
                self.assertIn("on:\n  workflow_dispatch:", data)
                self.assertNotRegex(data, r"(?m)^  pull_request:")
                self.assertNotRegex(data, r"(?m)^  push:")
                self.assertIn("jobs:\n", data)
                jobs = data.partition("\njobs:\n")[2]
                all_jobs = re.findall(r"(?m)^  [A-Za-z0-9_-]+:\n", jobs)
                disabled = re.findall(r"(?m)^    if: \$\{\{ false \}\}$", jobs)
                self.assertTrue(all_jobs)
                self.assertEqual(len(all_jobs), len(disabled))

    def test_active_offline_jobs_use_unique_checkout_and_workdir(self):
        active = [p for p in WORKFLOWS.glob("story-harness-*.yml")
                  if not p.name.endswith(("-once.yml", "-one-shot.yml"))]
        self.assertGreaterEqual(len(active), 16)
        for path in active:
            with self.subTest(path=path.name):
                data = path.read_text(encoding="utf-8")
                checkouts = re.findall(
                    r"(?m)^      - uses: actions/checkout@v4\n"
                    r"        with:\n((?:          .*\n)+)", data)
                self.assertTrue(checkouts, "Missing checkout action")
                for checkout in checkouts:
                    self.assertIn("path: " + UNIQUE, checkout)
                    self.assertIn("persist-credentials: false", checkout)
                self.assertIn("working-directory: " + UNIQUE, data)
                if path.name != "story-harness-p456-ci-guard.yml":
                    self.assertNotIn("      - .github/workflows/" + path.name,
                                     data.partition("\npermissions:")[0])

    def test_p456_guard_stays_zero_provider(self):
        path = WORKFLOWS / "story-harness-p456-ci-guard.yml"
        data = path.read_text(encoding="utf-8")
        for name in ("test_story_harness_p456_ci_contract.py",
                     "test_story_harness_p445_b05_stop.py",
                     "test_story_harness_p453_b06_final_state.py",
                     "test_story_harness_p454_b07_age25.py"):
            self.assertIn(name, data)
        self.assertNotIn("OPENROUTER_API_KEY", data)
        self.assertNotIn("--paid-once", data)
        self.assertIn("path: " + UNIQUE, data)


    def test_historical_offline_checks_run_only_on_changed_push_files(self):
        old = [p for p in WORKFLOWS.glob("story-harness-*.yml")
               if not p.name.endswith(("-once.yml", "-one-shot.yml"))
               and p.name not in ("story-harness-p456-ci-guard.yml",
                                  "story-harness-p457-b07-paid-gate.yml")]
        self.assertEqual(len(old), 16)
        for path in old:
            with self.subTest(workflow=path.name):
                data = path.read_text(encoding="utf-8")
                self.assertIn("on:\n  push:\n    branches:\n      - experiment/story-harness-control-plane-v1\n", data)
                self.assertNotRegex(data, r"(?m)^  pull_request:")
                self.assertIn("github.sha", data if "ref:" in data else data + "github.sha")

if __name__ == "__main__":
    unittest.main()
