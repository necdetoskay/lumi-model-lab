"""Pilot English Master admission, original source and independent real gate."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import test_story_harness_p422_independent_audit as fixture
from src.story_harness_p422_independent_audit import verify_auditor_reply
from src.story_harness_p423_master import (
    qualify_master, seal_pilot_master, SCHEMA,
)
from src.story_harness_v1 import HarnessStop


class P423Tests(unittest.TestCase):
    def setUp(self):
        self.source=fixture.fake_source()
        self.source["story"]["word_count"]=len(
            self.source["story"]["story_text"].split())
        self.audit=verify_auditor_reply(
            self.source, fixture.fake_reply(self.source))

    def test_clean_source_and_quality_seal_exact_prose_without_mutation(self):
        result=qualify_master(self.source,self.audit)
        self.assertEqual(result["story_sha256"],self.source["story"]["story_sha256"])
        with TemporaryDirectory() as td:
            master=seal_pilot_master(self.source,self.audit,td)
            folder=Path(td)/("b01-"+master["source_story_sha256"][:16])
            text=(folder/"ENGLISH_MASTER.txt").read_text()
            self.assertEqual(text,self.source["story"]["story_text"])
            manifest=json.loads((folder/"master-manifest.json").read_text())
            self.assertEqual(manifest["schema"],SCHEMA)
            self.assertEqual(manifest["source_story_sha256"],manifest["accepted_story_sha256"])
            self.assertTrue(manifest["q25_read_only_extraction_allowed"])
            self.assertFalse(manifest["production_master_published"])
            self.assertFalse(manifest["production_state_write_authorized"])
            self.assertFalse(manifest["full_original_frozen_v21_4_production_quality_accepted"])
            with self.assertRaises(FileExistsError):
                seal_pilot_master(self.source,self.audit,td)

    def test_cross_story_sha_is_never_admitted(self):
        a=deepcopy(self.audit)
        a["story_sha256"]="e"*64
        with self.assertRaises(HarnessStop):
            qualify_master(self.source,a)

    def test_cross_spine_sha_is_never_admitted(self):
        a=deepcopy(self.audit)
        a["spine_sha256"]="e"*64
        with self.assertRaises(HarnessStop):
            qualify_master(self.source,a)

    def test_model_reject_blocks_master_seal(self):
        a=deepcopy(self.audit)
        a["quality_initial_verdict"]="REJECT"
        a["quality_initial_audit_accepted"]=False
        with self.assertRaises(HarnessStop):
            qualify_master(self.source,a)

    def test_reader_score_three_blocks_master(self):
        a=deepcopy(self.audit)
        a["reader_score"]=3
        with self.assertRaises(HarnessStop):
            qualify_master(self.source,a)

    def test_blocking_findings_blocks_master_despite_accept_flag(self):
        a=deepcopy(self.audit)
        a["blocking_findings"]=[{"family":"canon",
                               "quote":"Mira chose to help",
                               "reason":"Some material inconsistency."}]
        with self.assertRaises(HarnessStop):
            qualify_master(self.source,a)

    def test_unknown_or_over_cap_auditor_spend_blocks(self):
        for cost in (None,"NaN","0.0401","-0.01"):
            a=deepcopy(self.audit)
            a["auditor_reported_cost_usd"]=cost
            with self.subTest(cost=cost),self.assertRaises(HarnessStop):
                qualify_master(self.source,a)

    def test_story_modified_after_audit_is_denied(self):
        s=deepcopy(self.source)
        s["story"]["story_text"]+=" EDITED AFTER ACCEPT"
        with self.assertRaises(HarnessStop):
            qualify_master(s,self.audit)

    def test_untrusted_self_asserted_prod_authorization_denied(self):
        a=deepcopy(self.audit)
        a["state_write_authorized"]=True
        with self.assertRaises(HarnessStop):
            qualify_master(self.source,a)


if __name__=="__main__":
    unittest.main()
