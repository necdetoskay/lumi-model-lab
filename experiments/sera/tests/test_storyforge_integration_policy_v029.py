"""v0.29 offline SERA gate: StoryForge integration must not regress output policy.

These source checks intentionally need no third-party packages; the separate
StoryForge CI job executes the actual normalized outbound HTTP mock tests.
"""
import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
STORYFORGE = ROOT / "src" / "storyforge" / "runtime.py"
GENERATE = ROOT / "src" / "generate.py"
STRUCTURED = ROOT / "src" / "english_story_pipeline.py"


class StoryForgeIntegrationCapfreeV029Tests(unittest.TestCase):
    def test_no_numbered_output_token_limit_in_storyforge_runtime_calls(self):
        code=STORYFORGE.read_text(encoding="utf-8")
        tree=ast.parse(code)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for kw in node.keywords:
                if kw.arg in {
                    "max_tokens", "max_output_tokens",
                    "max_completion_tokens", "max_generation_tokens",
                    "max_new_tokens", "num_predict", "n_predict",
                }:
                    self.assertIsInstance(kw.value, ast.Constant)
                    self.assertIsNone(kw.value.value)
        self.assertIn("_preflight_storyforge_output_policy(models)",code)
        self.assertIn("forbid_output_token_limit=True",code)
        self.assertIn("forbid_ambiguous_paid_retry=True",code)

    def test_final_normalized_provider_payload_has_enforced_guard(self):
        code=GENERATE.read_text(encoding="utf-8")
        self.assertIn("forbid_output_token_limit: bool = False",code)
        self.assertIn("enforce_no_output_token_limit(payload)",code)
        self.assertLess(
            code.index("enforce_no_output_token_limit(payload)"),
            code.index("requests.post("),
        )
        self.assertIn("OPENROUTER_UNKNOWN_CHARGE_NO_RESEND",code)
        self.assertIn("needs_provider_idempotent_reconciliation",code)

    def test_structured_retry_forwards_cap_and_billing_safety(self):
        code=STRUCTURED.read_text(encoding="utf-8")
        self.assertIn("forbid_output_token_limit=forbid_output_token_limit",code)
        self.assertIn("forbid_ambiguous_paid_retry=forbid_ambiguous_paid_retry",code)


if __name__=="__main__":
    unittest.main()
