"""P4.58: audit B07 original immutable Sonnet story using mock-only QA.

The protected source tests run on the dedicated q25-offline runner. No
OpenRouter secret, no paid model calls and no production promotion.
"""
import json
import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.story_harness_p458_b07_quality import (
    AUDIT_DIR, CLAIM_NAME, SOURCE_SHA, SPINE_SHA, STORY_SHA, SPINE_ID,
    GEN_COST, PROVIDER_FILE_DIGESTS, get_original_B07, inspect_B07_audit,
    audit_B07_once, status,
)
from src.story_harness_p417_live_pilot import MODEL
from src.story_harness_v1 import HarnessStop

def fake_qa(source, *, verdict="ACCEPT", score=4, blockers=None):
    outcome = {
        "story_sha256": source["story"]["story_sha256"],
        "spine_sha256": source["spine"]["spine_sha256"],
        "verdict": verdict,
        "reader_score": score,
        "blocking_findings_json": json.dumps(blockers or []),
        "advisories_json": json.dumps([]),
        "rationale": "Bounded mock: used only to check admission and call accounting, never real quality.",
    }
    return {
        "id": "gen-OfflineMockB07Audit", "model": MODEL,
        "usage": {"prompt_tokens": 100, "completion_tokens": 100, "cost": 0.001},
        "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(outcome)}}],
    }

class P458OfflineTests(unittest.TestCase):
    def test_status_only_is_unapproved_and_cost_bounded(self):
        result = status()
        self.assertEqual(result["case_id"], "B07")
        self.assertEqual(result["story_sha256"], STORY_SHA)
        self.assertEqual(result["spine_sha256"], SPINE_SHA)
        self.assertEqual(result["real_generation_cost_usd"], "0.093066")
        self.assertEqual(result["prior_conservative_budget_reserved_usd"], "3.209558")
        self.assertEqual(result["new_quality_maximum_usd"], "0.040")
        self.assertEqual(result["maximum_new_model_posts"], 1)
        self.assertEqual(result["provider_calls"], 0)
        self.assertFalse(result["initial_quality_accepted"])
        self.assertFalse(result["production_state_write_authorized"])

    def test_original_artifact_hash_manifest_is_pinned(self):
        self.assertEqual(len(PROVIDER_FILE_DIGESTS), 4)
        self.assertTrue(all(len(v) == 64 for v in PROVIDER_FILE_DIGESTS.values()))
        self.assertEqual(CLAIM_NAME, "b07-" + SOURCE_SHA[:16] + "-r06")

@unittest.skipUnless(os.getenv("RUNNER_WORKSPACE"), "Needs original protected self-hosted provider claims")
class P458ProtectedOriginalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(os.environ["RUNNER_WORKSPACE"]) / "_lumi_p455_b07_story_claims"
        cls.source=get_original_B07(".", cls.root)

    def test_true_original_b07_provenance_and_age_sensitive_audit_wire(self):
        src=self.source
        self.assertEqual(src["story"]["word_count"],2708)
        self.assertEqual(src["story"]["story_sha256"],STORY_SHA)
        self.assertEqual(src["spine"]["spine_sha256"],SPINE_SHA)
        self.assertEqual(src["spine"]["provider_generation_id"],SPINE_ID)
        self.assertEqual(src["generation_cost_usd"],"0.093066")
        self.assertEqual(len(src["spine"]["spine"]["beats"]),5)
        wire=inspect_B07_audit(src)
        self.assertEqual(wire["response_format"]["json_schema"]["name"],
                         "lumi_b07_independent_initial_audit_v1")
        self.assertFalse(wire["provider"]["allow_fallbacks"])
        self.assertEqual(wire["model"],MODEL)

    def test_tampered_writer_or_provider_receipt_denied(self):
        with TemporaryDirectory() as td:
            folder=Path(td) / CLAIM_NAME
            folder.mkdir()
            original=self.root / CLAIM_NAME
            for name in PROVIDER_FILE_DIGESTS:
                shutil.copyfile(original/name,folder/name)
            get_original_B07(".",td)
            for name in ("story-draft.json","01-spineforge-receipt.json"):
                p=folder/name
                prior=p.read_bytes()
                p.write_bytes(prior+b" ")
                with self.subTest(name=name),self.assertRaises(HarnessStop):
                    get_original_B07(".",td)
                p.write_bytes(prior)

    def test_one_shot_mock_transport_cannot_dispatch_twice(self):
        with TemporaryDirectory() as td:
            calls=[]
            def transport(body):
                calls.append(body)
                return fake_qa(self.source)
            result=audit_B07_once(self.source,td,transport=transport)
            self.assertEqual(len(calls),1)
            self.assertEqual(result["case_id"],"B07")
            self.assertEqual(result["quality_initial_verdict"],"ACCEPT")
            self.assertEqual(result["auditor_generation_id"],"gen-OfflineMockB07Audit")
            self.assertFalse(result["english_master_authorized"])
            self.assertFalse(result["q25_authorized"])
            self.assertFalse(result["state_write_authorized"])
            self.assertTrue((Path(td)/AUDIT_DIR/"00-intent.json").exists())
            with self.assertRaises(FileExistsError):
                audit_B07_once(self.source,td,transport=transport)
            self.assertEqual(len(calls),1)

    def test_invalid_reply_consumes_one_attempt_with_fail_closed_stop(self):
        with TemporaryDirectory() as td:
            calls=[]
            def invalid(body):
                calls.append(1)
                response=fake_qa(self.source)
                response["usage"]["cost"]=0.5
                return response
            with self.assertRaises(HarnessStop):
                audit_B07_once(self.source,td,transport=invalid)
            self.assertEqual(calls,[1])
            stop=json.loads((Path(td)/AUDIT_DIR/"01-audit-outcome.json").read_bytes())
            self.assertEqual(stop["quality_initial_verdict"],"STOP_UNKNOWN_OR_INVALID")
            self.assertFalse(stop["retry_allowed"])
            self.assertFalse(stop["english_master_authorized"])

    def test_cross_story_and_tampered_master_never_enter_audit(self):
        source=dict(self.source)
        source["case_id"]="B03"
        with self.assertRaises(HarnessStop):
            inspect_B07_audit(source)
        source=dict(self.source)
        source["story"]=dict(source["story"])
        source["story"]["story_sha256"]="0"*64
        with self.assertRaises(HarnessStop):
            inspect_B07_audit(source)

if __name__=="__main__":
    unittest.main()
