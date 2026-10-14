"""The shared-key probe may ONLY be triggered manually and cannot call a model."""
from pathlib import Path
import unittest

FILE=Path(__file__).resolve().parents[1]/".github/workflows/model-qualification.yml"
class ManualExistingKeyWorkflow(unittest.TestCase):
    def test_secret_probe_is_manual_default_registered_workflow_only(self):
        y=FILE.read_text()
        self.assertIn("workflow_dispatch:",y)
        self.assertNotIn("pull_request:",y)
        self.assertNotIn("push:",y)
        self.assertIn("inputs.qualification_config != 'LUMI_EXISTING_KEY_READONLY_V1'",y)
        self.assertIn("inputs.qualification_config == 'LUMI_EXISTING_KEY_READONLY_V1'",y)
        self.assertIn("github.ref == 'refs/heads/experiment/story-harness-control-plane-v1'",y)
        self.assertIn("github.sha == inputs.model",y)

    def test_secret_job_never_executes_pr_source_or_provider_post(self):
        y=FILE.read_text().split("  lumi-cohort-existing-key-readonly:",1)[1]
        self.assertNotIn("actions/checkout@",y)
        self.assertNotIn("pip install",y)
        self.assertNotIn("src.",y)
        self.assertNotIn('method="POST"',y)
        self.assertNotIn("chat/completions",y)
        self.assertIn('method="GET"',y)
        self.assertIn("COHORT_DISPATCH_AUTHORIZED=FALSE",y)
        self.assertIn("MODEL_POSTS=0",y)
        self.assertIn("NoRedirect",y)
        self.assertIn("KEY_RAW_SECRET_OR_PROVIDER_LABEL_RECORDED=FALSE",y)
