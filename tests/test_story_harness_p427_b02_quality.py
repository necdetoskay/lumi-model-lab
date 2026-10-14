"""P4.27 B02 real-file source contract and negative independent initial quality tests.

Synthetic quality replies in this test are not proof that the real B02 story
passed; only a separately billed, source-bound model call can provide that.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from src.story_harness_p427_b02_quality import (
    SCHEMA, SOURCE_SHA, SPINE_SHA, STORY_SHA, COPY_FILES, EVIDENCE_DIR,
    get_b02_original, inspect_b02_initial, audit_b02_once, default_status,
)
from src.story_harness_p422_independent_audit import (
    audit_wire, verify_auditor_reply, load_source,
)
from src.story_harness_p417_live_pilot import MODEL
from src.story_harness_v1 import HarnessStop


def copy_original(tmp):
    folder=Path(tmp)/("b02-"+SOURCE_SHA[:16]+"-r06")
    folder.mkdir()
    for source,name in COPY_FILES.items():
        (folder/source).write_bytes((Path(".")/EVIDENCE_DIR/name).read_bytes())
    return folder


def fake_quality_response(source, verdict="ACCEPT", score=4, problems=()):
    return {
        "model":MODEL,"id":"gen-TEST_B02AUDIT123456",
        "usage":{"prompt_tokens":3400,"completion_tokens":800,"cost":"0.023"},
        "choices":[{"finish_reason":"stop","message":{"content":json.dumps({
            "story_sha256":source["story"]["story_sha256"],
            "spine_sha256":source["spine"]["spine_sha256"],
            "verdict":verdict,
            "reader_score":score,
            "blocking_findings_json":json.dumps(list(problems)),
            "advisories_json":"[]",
            "rationale":"Independent source-grounded literary and continuity assessment.",
        })}}],
    }


class P427Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.originals=TemporaryDirectory()
        cls.original_path=copy_original(cls.originals.name)
        cls.original=get_b02_original(".",cls.originals.name)

    @classmethod
    def tearDownClass(cls):
        cls.originals.cleanup()

    def test_real_provider_artifacts_are_b02_and_not_b01(self):
        original=self.original
        self.assertEqual(original["case_id"],"B02")
        self.assertEqual(original["pack"]["pack_sha256"],SOURCE_SHA)
        self.assertEqual(original["spine"]["spine_sha256"],SPINE_SHA)
        self.assertEqual(original["story"]["story_sha256"],STORY_SHA)
        self.assertEqual(original["story"]["word_count"],561)
        self.assertEqual(original["generation_cost_usd"],"0.04503")
        self.assertEqual(original["pack"]["canonical_state"]["protagonist"]["name"],"Aren")
        self.assertIn("Commons",original["story"]["story_text"])
        self.assertNotIn("Mira",original["story"]["story_text"])

    def test_audit_wire_uses_actual_b02_age_topic_and_story(self):
        w=inspect_b02_initial(self.original)
        packet=json.loads(w["messages"][1]["content"])
        self.assertEqual(packet["case_id"],"B02")
        self.assertEqual(packet["source_pack_sha256"],SOURCE_SHA)
        self.assertEqual(packet["topic"],"Şarkı söylemeyi unutan bulut")
        self.assertEqual(packet["approved_spine_sha256"],SPINE_SHA)
        self.assertEqual(packet["story_sha256"],STORY_SHA)
        self.assertEqual(packet["complete_story_text"],
                         self.original["story"]["story_text"])
        self.assertEqual(len(packet["approved_spine_beats"]),5)
        self.assertEqual(w["provider"]["only"],["Anthropic"])
        self.assertEqual(w["max_tokens"],3200)
        self.assertTrue(w["response_format"]["json_schema"]["strict"])
        self.assertNotIn("Mira",w["messages"][1]["content"])

    def test_independent_accept_mock_does_not_promote_to_master_or_production(self):
        with TemporaryDirectory() as tmp:
            calls=[]
            def reply(body):
                calls.append(body)
                return fake_quality_response(self.original)
            verdict=audit_b02_once(self.original,tmp,transport=reply)
            self.assertEqual(len(calls),1)
            self.assertEqual(verdict["case_id"],"B02")
            self.assertEqual(verdict["quality_initial_verdict"],"ACCEPT")
            self.assertEqual(verdict["reader_score"],4)
            self.assertFalse(verdict["english_master_authorized"])
            self.assertFalse(verdict["q25_authorized"])
            self.assertFalse(verdict["state_write_authorized"])
            self.assertFalse(verdict["full_original_v21_final_audit_completed"])
            self.assertTrue((Path(tmp)/("p427-b02-r06-"+STORY_SHA[:12])/"01-audit-outcome.json").exists())
            with self.assertRaises(FileExistsError):
                audit_b02_once(self.original,tmp,transport=reply)
            self.assertEqual(len(calls),1)

    def test_blocking_finding_must_use_real_quote_and_canonical_family(self):
        defect={"family":"spatial","quote":"The Commons was full of soft sounds.",
                "reason":"A supposed teleport from the Commons contradicts the prior location."}
        parsed=verify_auditor_reply(
            self.original,fake_quality_response(self.original,verdict="REJECT",
                                                score=3,problems=[defect]))
        self.assertEqual(parsed["case_id"],"B02")
        self.assertEqual(parsed["blocking_findings"][0]["family"],"spatial")
        fake=deepcopy(defect)
        fake["quote"]="NOT ACTUALLY IN B02"
        with self.assertRaises(HarnessStop):
            verify_auditor_reply(
                self.original,fake_quality_response(self.original,
                              verdict="REJECT",score=3,problems=[fake]))
        with self.assertRaises(HarnessStop):
            verify_auditor_reply(
                self.original,fake_quality_response(self.original,
                              verdict="ACCEPT",score=4,problems=[defect]))

    def test_B01_cannot_be_passed_as_B02(self):
        other=deepcopy(self.original)
        other["case_id"]="B01"
        with self.assertRaises(HarnessStop):
            inspect_b02_initial(other)
        with TemporaryDirectory() as tmp:
            with self.assertRaises(HarnessStop):
                audit_b02_once(other,tmp,transport=lambda wire:None)
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_changed_spine_and_story_hash_are_denied(self):
        for name,marker in (
            ("spine-plan.json",b"NON_CANON_EDIT"),
            ("story-draft.json",b"MODIFICATION")):
            with TemporaryDirectory() as tmp:
                root=copy_original(tmp)
                p=root/name
                changed=json.loads(p.read_text())
                changed["unexpected_tamper_marker"]=marker.decode()
                p.write_text(json.dumps(changed))
                with self.subTest(name=name),self.assertRaises(HarnessStop):
                    get_b02_original(".",tmp)

    def test_missing_or_unsettled_stage_receipt_denied_before_paid_audit(self):
        with TemporaryDirectory() as tmp:
            root=copy_original(tmp)
            p=root/"02-writer-receipt.json"
            obj=json.loads(p.read_text())
            obj["outcome"]="STOP_UNKNOWN"
            p.write_text(json.dumps(obj))
            with self.assertRaises(HarnessStop):
                get_b02_original(".",tmp)

    def test_synthetic_replay_and_expired_claim_cannot_call_provider_twice(self):
        with TemporaryDirectory() as tmp:
            def failing(body):
                raise TimeoutError("uncertain billing")
            with self.assertRaises(HarnessStop):
                audit_b02_once(self.original,tmp,transport=failing)
            path=Path(tmp)/("p427-b02-r06-"+STORY_SHA[:12])/"01-audit-outcome.json"
            result=json.loads(path.read_text())
            self.assertEqual(result["quality_initial_verdict"],"STOP_UNKNOWN_OR_INVALID")
            self.assertFalse(result["retry_allowed"])
            with self.assertRaises(FileExistsError):
                audit_b02_once(self.original,tmp,transport=failing)

    def test_default_does_not_spend_or_inherit_old_quality(self):
        s=default_status()
        self.assertEqual(s["provider_calls"],0)
        self.assertEqual(s["maximum_new_quality_usd"],"0.040")
        self.assertEqual(s["previous_budget_reserved_usd"],"1.339402")
        self.assertEqual(s["total_user_budget_usd"],"10.00")
        self.assertFalse(s["quality_accepted"])
        self.assertFalse(s["english_master_authorized"])
        self.assertFalse(s["q25_authorized"])


if __name__=="__main__":
    unittest.main()
