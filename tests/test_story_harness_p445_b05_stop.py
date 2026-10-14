"""P4.45: genuine B05 quality STOP is terminal, not a successful pilot.

Zero-provider regressions only. Never infer initial ACCEPT or Master
from a provider attempt whose receipt is UNKNOWN_OR_INVALID.
"""
import hashlib
import json
from pathlib import Path
import unittest

STOP = Path("evidence/story_harness_p444/b05-r06-original-quality-stop.json")
INTENT = Path("evidence/story_harness_p444/b05-r06-original-quality-intent.json")
SPINE = "9c5c1915680ac4d9b91e641527f2b69bb3e045413031973bdba8da8747ec9e24"
STORY = "342dff8084787c0f42f036ab34d973741aed55cecaef40a4e734ca242f9465c0"

class B05TerminalStop(unittest.TestCase):
    def test_original_stop_and_intent_are_immutable(self):
        self.assertEqual(hashlib.sha256(STOP.read_bytes()).hexdigest(),
                         "c1532871bdea9b114aa5c09c2d25a5014ff2f97d3e8f980683369213c6331309")
        self.assertEqual(hashlib.sha256(INTENT.read_bytes()).hexdigest(),
                         "4f4682615b0c72b2da262c64c751945837916794027ee3042222aebbae07dd60")
        s=json.loads(STOP.read_bytes())
        i=json.loads(INTENT.read_bytes())
        self.assertEqual(s["case_id"],"B05")
        self.assertEqual(s["source_story_sha256"],STORY)
        self.assertEqual(s["quality_initial_verdict"],"STOP_UNKNOWN_OR_INVALID")
        self.assertIsNone(s["auditor_reported_cost_usd"])
        self.assertFalse(s["english_master_authorized"])
        self.assertFalse(s["retry_allowed"])
        self.assertFalse(s["production_state_write_authorized"])
        self.assertEqual(i["case_id"],"B05")
        self.assertEqual(i["source_story_sha256"],STORY)
        self.assertEqual(i["spine_sha256"],SPINE)
        self.assertEqual(i["maximum_quality_model_posts"],1)
        self.assertEqual(i["stage_maximum_reported_usd"],"0.040")
        self.assertFalse(i["automatic_retry"])

    def test_stop_cannot_be_promoted_as_acceptance(self):
        from src.story_harness_p423_master import qualify_master
        from src.story_harness_p444_b05_quality import get_original_B05
        from src.story_harness_v1 import HarnessStop
        # The standalone STOP receipt is deliberately NOT an auditor ACCEPT.
        # The original provider source may be verified when the protected
        # producer files are mounted on CI, but no paid audit is attempted.
        import os
        root=os.getenv("RUNNER_WORKSPACE")
        if not root:
            self.skipTest("Original producer claims are only on secure runner")
        source=get_original_B05(".",Path(root)/"_lumi_p443_b05_story_claims")
        with self.assertRaises((HarnessStop,KeyError,TypeError,ValueError)):
            qualify_master(source,json.loads(STOP.read_bytes()))

    def test_no_fabricated_downstream_b05_artifacts(self):
        self.assertFalse(Path("evidence/story_harness_p445/b05-english-master-manifest.json").exists())
        self.assertFalse(Path("evidence/story_harness_p445/b05-q25-evidence.json").exists())
        self.assertFalse(Path("evidence/story_harness_p445/b05-final-state.json").exists())

if __name__=="__main__":
    unittest.main()
