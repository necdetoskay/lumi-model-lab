"""P4.31 age-10 third input via same P4.17 generation engine, mocks only."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json,unittest
from unittest.mock import patch

import test_story_harness_p417_live_pilot as p417fake
from src.story_harness_p431_b03_age10 import (
    CASE_ID,SOURCE_SHA,source_case,third_story_once,default_status
)
from src.story_harness_p417_live_pilot import MODEL
from src.story_harness_v1 import HarnessStop


def fake_transport(pack,*,wrong_spine=False):
    provider=p417fake.FakeProvider(pack)
    def send(body):
        updated=deepcopy(body)
        updated["response_format"]["json_schema"]["name"]=(
            updated["response_format"]["json_schema"]["name"].replace("_flat_v2","_v1"))
        response=provider(updated)
        content=json.loads(response["choices"][0]["message"]["content"])
        if "beats" in content:
            content={
                "source_pack_sha256":content["source_pack_sha256"],
                "spine_summary":content["spine_summary"],
                "beats_json":json.dumps(content["beats"]),
            }
            if wrong_spine: content["source_pack_sha256"]="0"*64
        else:
            words=content["story_text"].split()
            # This is ONLY a fake transport satisfying the AGE-10 word
            # contract. It never counts toward a real story quality target.
            filler=("Duru watched the river closely and decided not to cross "
                    "until the bridge was safe. ").split()
            while len(words)<930: words.extend(filler)
            words=words[:950]
            content={
                "source_pack_sha256":content["source_pack_sha256"],
                "spine_sha256":content["spine_sha256"],
                "story_text":" ".join(words),
                "beat_ids_json":json.dumps(content["beat_ids"]),
            }
        response["choices"][0]["message"]["content"]=json.dumps(content)
        return response
    return send,provider


class P431Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan,cls.pack=source_case(".")

    def test_B03_is_real_distinct_age10_source_not_B01_or_B02(self):
        self.assertEqual(self.pack["pack_sha256"],SOURCE_SHA)
        self.assertEqual(self.pack["reader_age"],10)
        self.assertEqual(self.pack["word_targets"],{"min":800,"max":1400})
        self.assertEqual(self.pack["canonical_state"]["protagonist"]["name"],"Duru")
        self.assertEqual(self.pack["canonical_state"]["protagonist"]["location"],"RIVERBANK")
        self.assertEqual(self.pack["canonical_state"]["locations"],["RIVERBANK","VILLAGE"])
        self.assertEqual(len(self.pack["open_obligations"]),2)

    def test_default_has_no_provider_calls_and_no_prior_acceptance(self):
        r=default_status()
        self.assertEqual(r["provider_calls"],0)
        self.assertFalse(r["paid_execution_default"])
        self.assertFalse(r["quality_accepted"])
        self.assertFalse(r["production_state_write_authorized"])
        self.assertEqual(r["cost_cap_usd"],"0.35")

    def test_same_existing_engine_emits_b03_spine_and_800_plus_words(self):
        with TemporaryDirectory() as td:
            wrapped,fake=fake_transport(self.pack)
            result=third_story_once(".",td,transport=wrapped)
            self.assertEqual(len(fake.calls),2)
            self.assertEqual(result["case_id"],"B03")
            self.assertEqual(result["reader_age"],10)
            self.assertEqual(result["source_pack_sha256"],SOURCE_SHA)
            self.assertTrue(800<=result["original_word_count"]<=1400)
            self.assertEqual(result["quality_initial_verdict"],"NOT_YET_AUDITED")
            self.assertFalse(result["english_master_authorized"])
            self.assertFalse(result["q25_authorized"])
            self.assertFalse(result["production_state_write_authorized"])
            manuscript=json.loads(next(Path(td).glob("b03-*-r06/story-draft.json")).read_text())
            spine=json.loads(next(Path(td).glob("b03-*-r06/spine-plan.json")).read_text())
            self.assertEqual(manuscript["spine_sha256"],spine["spine_sha256"])

    def test_consumed_b03_claim_cannot_run_second_time(self):
        with TemporaryDirectory() as td:
            wrapped,fake=fake_transport(self.pack)
            third_story_once(".",td,transport=wrapped)
            with self.assertRaises(FileExistsError):
                third_story_once(".",td,transport=wrapped)
            self.assertEqual(len(fake.calls),2)

    def test_mixed_canon_fails_before_writer_request(self):
        with TemporaryDirectory() as td:
            wrapped,fake=fake_transport(self.pack,wrong_spine=True)
            with self.assertRaises(HarnessStop):
                third_story_once(".",td,transport=wrapped)
            self.assertEqual(len(fake.calls),1)

    def test_timeout_consumes_new_attempt_with_no_retry(self):
        with TemporaryDirectory() as td:
            calls=[]
            def fail(body):
                calls.append(1)
                raise TimeoutError("unknown cost")
            with self.assertRaises(HarnessStop):
                third_story_once(".",td,transport=fail)
            self.assertEqual(calls,[1])
            self.assertTrue(bool(list(Path(td).glob("b03-*-r06/01-spineforge-intent.json"))))


if __name__=="__main__":
    unittest.main()
