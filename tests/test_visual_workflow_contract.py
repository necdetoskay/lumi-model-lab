from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / ".github" / "workflows" / "visual-qualification-live.yml"
PROMOTION = ROOT / ".github" / "workflows" / "visual-qualification-promotion.yml"


class VisualWorkflowContractTests(unittest.TestCase):
    def test_screen_builds_promotion_artifacts_but_does_not_run_promotion(self) -> None:
        text = SCREEN.read_text(encoding="utf-8")
        self.assertIn("Build no-cost promotion shortlist", text)
        self.assertIn("promotion_shortlist.json", text)
        self.assertIn("promotion_config.yaml", text)
        self.assertNotIn("Run paid promotion qualification", text)

    def test_promotion_is_manual_and_requires_explicit_paid_confirmation(self) -> None:
        text = PROMOTION.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("pull_request:", text)
        self.assertNotIn("push:", text)
        self.assertIn("screen_run_id:", text)
        self.assertIn("I_UNDERSTAND_THIS_RUN_IS_PAID", text)
        self.assertIn("actions/download-artifact@v4", text)
        self.assertIn("--plan-only", text)
        self.assertIn("--authorize-paid", text)

    def test_promotion_reuses_screen_evidence_and_has_no_automatic_spend_path(self) -> None:
        text = PROMOTION.read_text(encoding="utf-8")
        self.assertIn("qualification_report.json", text)
        self.assertIn("promotion_config.yaml", text)
        self.assertIn("OPENROUTER_API_KEY", text)
        self.assertIn("steps.authorize.outputs.authorized == 'true'", text)


if __name__ == "__main__":
    unittest.main()
