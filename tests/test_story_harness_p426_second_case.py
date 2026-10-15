"""P4.26 second genuinely different state/topic story can use the original transport.

All model responses in this suite are synthetic; tests never prove literary quality.
"""
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import test_story_harness_p417_live_pilot as p417fake

from src.story_harness_p426_second_case import (
    SCHEMA, CASE, VARIANT, get_case, status, execute_second_story,
    PRIOR_CONSERVATIVE_RESERVED_USD, MAX_NEW_USD,
)
from src.story_harness_p417_live_pilot import USD_CAP, GLOBAL_USER_CAP
from src.story_harness_p416_input_bridge import compile_case
from src.story_harness_p415_benchmark import load_plan
from src.story_harness_v1 import HarnessStop


class P426Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan,cls.row,cls.pack=get_case(".")

    @staticmethod
    def mock_transport(pack, *, use_wrong_state=False):
        fake=p417fake.FakeProvider(pack)
        def called(body):
            copied=deepcopy(body)
            copied["response_format"]["json_schema"]["name"]=(
                copied["response_format"]["json_schema"]["name"]
                .replace("_flat_v2","_v1"))
            response=fake(copied)
            obj=json.loads(response["choices"][0]["message"]["content"])
            if "beats" in obj:
                obj={"source_pack_sha256":obj["source_pack_sha256"],
                     "spine_summary":obj["spine_summary"],
                     "beats_json":json.dumps(obj["beats"])}
                if use_wrong_state:obj["source_pack_sha256"]="0"*64
            else:
                obj={"source_pack_sha256":obj["source_pack_sha256"],
                     "spine_sha256":obj["spine_sha256"],
                     "story_text":obj["story_text"],
                     "beat_ids_json":json.dumps(obj["beat_ids"])}
            response["choices"][0]["message"]["content"]=json.dumps(obj)
            return response
        return called,fake

    def test_new_case_is_not_the_original_story(self):
        b01=compile_case(next(x for x in self.plan["cases"] if x["id"]=="B01"))
        self.assertEqual(self.row["id"],CASE)
        self.assertEqual(self.pack["reader_age"],4)
        self.assertNotEqual(b01["pack_sha256"],self.pack["pack_sha256"])
        self.assertNotEqual(b01["topic_sha256"],self.pack["topic_sha256"])
        self.assertNotEqual(b01["canonical_state_sha256"],
                            self.pack["canonical_state_sha256"])
        self.assertEqual(self.pack["canonical_state"]["protagonist"]["location"],
                         "GARDEN")

    def test_default_status_does_not_dispatch_paid_provider(self):
        r=status(".")
        self.assertEqual(r["provider_calls"],0)
        self.assertFalse(r["default_paid_dispatch_enabled"])
        self.assertFalse(r["quality_accepted"])
        self.assertEqual(r["one_story_exposure_cap_usd"],"0.35")
        self.assertLessEqual(PRIOR_CONSERVATIVE_RESERVED_USD+MAX_NEW_USD,
                             GLOBAL_USER_CAP)

    def test_second_distinct_story_reuses_original_spine_writer_with_lineage(self):
        with TemporaryDirectory() as td:
            called,provider=self.mock_transport(self.pack)
            result=execute_second_story(".",td,transport=called)
            self.assertEqual(result["schema"],SCHEMA)
            self.assertEqual(len(provider.calls),2)
            self.assertEqual(result["case_id"],"B02")
            self.assertEqual(result["reader_age"],4)
            self.assertEqual(result["source_pack_sha256"],self.pack["pack_sha256"])
            self.assertEqual(result["provider_reported_spine_writer_cost_usd"],"0.024")
            self.assertEqual(result["manual_story_edits"],0)
            self.assertFalse(result["independent_quality_accepted"])
            self.assertFalse(result["english_master_authorized"])
            self.assertFalse(result["q25_evidence_accepted"])
            self.assertFalse(result["final_story_state_certified"])
            self.assertFalse(result["production_state_write_authorized"])
            artifact=next(Path(td).glob("b02-*-r06/story-draft.json"))
            spine=next(Path(td).glob("b02-*-r06/spine-plan.json"))
            obj=json.loads(artifact.read_text())
            self.assertEqual(obj["spine_artifact_path"],"spine-plan.json")
            self.assertEqual(obj["spine_sha256"],
                json.loads(spine.read_text())["spine_sha256"])

    def test_duplicate_second_case_claim_refuses_replay(self):
        with TemporaryDirectory() as td:
            call,fake=self.mock_transport(self.pack)
            execute_second_story(".",td,transport=call)
            with self.assertRaises(FileExistsError):
                execute_second_story(".",td,transport=call)
            self.assertEqual(len(fake.calls),2)

    def test_wrong_original_case_spine_cannot_be_promoted_to_b02(self):
        with TemporaryDirectory() as td:
            call,fake=self.mock_transport(self.pack,use_wrong_state=True)
            with self.assertRaises(HarnessStop):
                execute_second_story(".",td,transport=call)
            self.assertEqual(len(fake.calls),1)
            self.assertFalse(bool(list(Path(td).glob("b02-*-r06/story-draft.json"))))

    def test_provider_timeout_consumes_one_new_attempt_without_retry(self):
        with TemporaryDirectory() as td:
            called=[]
            def transport(body):
                called.append(1)
                raise TimeoutError("unknown model charge")
            with self.assertRaises(HarnessStop):
                execute_second_story(".",td,transport=transport)
            self.assertEqual(called,[1])
            self.assertTrue(bool(list(Path(td).glob("b02-*-r06/01-spineforge-intent.json"))))

    def test_inconsistent_b02_canon_case_fails_without_provider(self):
        original=deepcopy(self.plan)
        for case in original["cases"]:
            if case["id"]=="B02":
                case["input"]["canonical_state"]["protagonist"]["location"]="SECRET"
        with patch("src.story_harness_p426_second_case.load_plan",return_value=original):
            with self.assertRaises(HarnessStop):
                get_case(".")

    def test_b02_has_unchanged_spine_writer_stage_cost_limits(self):
        from src.story_harness_p417_live_pilot import STAGE_MAX_USD
        self.assertEqual(MAX_NEW_USD,USD_CAP)
        self.assertLessEqual(sum(STAGE_MAX_USD.values()),MAX_NEW_USD)
        self.assertLessEqual(PRIOR_CONSERVATIVE_RESERVED_USD+MAX_NEW_USD,
                             GLOBAL_USER_CAP)


if __name__=="__main__":
    unittest.main()
