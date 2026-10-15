"""P4.38 — age-10 B04 original market/studio pilot, mock-only safety tests."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

import test_story_harness_p417_live_pilot as p417fake
from src.story_harness_p438_b04_age10 import (
    CASE_ID, SOURCE_SHA, source_case, fourth_story_once, default_status,
)
from src.story_harness_v1 import HarnessStop

def fake_transport(pack, *, wrong_spine=False):
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
            if wrong_spine:
                content["source_pack_sha256"]="0"*64
        else:
            words=content["story_text"].split()
            # Pure fixture filler to satisfy the word-count check, NOT a
            # real quality verdict or payable model-generated B04 story.
            filler=("Emir stood in the market watching the missing colours "
                    "and carefully considered the route to the studio. ").split()
            while len(words)<930:
                words.extend(filler)
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

class P438Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan,cls.pack=source_case(".")

    def test_frozen_fourth_case_is_distinct_age10_canon(self):
        self.assertEqual(CASE_ID,"B04")
        self.assertEqual(self.pack["pack_sha256"],SOURCE_SHA)
        self.assertEqual(SOURCE_SHA,"f6edbf321afab965b1a0166ff0a4feb267935f6be556996c4168572477fa1c47")
        self.assertEqual(self.pack["reader_age"],10)
        self.assertEqual(self.pack["topic"],"Kayıp renklerin peşinde")
        self.assertEqual(self.pack["word_targets"],{"min":800,"max":1400})
        self.assertEqual(self.pack["canonical_state"]["protagonist"]["name"],"Emir")
        self.assertEqual(self.pack["canonical_state"]["protagonist"]["location"],"MARKET")
        self.assertEqual(self.pack["canonical_state"]["locations"],["MARKET","STUDIO"])
        self.assertEqual(len(self.pack["open_obligations"]),2)

    def test_zero_cost_default_does_not_claim_quality(self):
        result=default_status()
        self.assertEqual(result["provider_calls"],0)
        self.assertEqual(result["cost_cap_usd"],"0.35")
        self.assertEqual(result["previous_conservative_budget_usd"],"1.539558")
        self.assertFalse(result["paid_execution_default"])
        self.assertFalse(result["quality_accepted"])
        self.assertFalse(result["production_state_write_authorized"])

    def test_original_generator_accepts_new_b04_input_in_mock_only(self):
        with TemporaryDirectory() as td:
            wrapped,fake=fake_transport(self.pack)
            result=fourth_story_once(".",td,transport=wrapped)
            self.assertEqual(len(fake.calls),2)
            self.assertEqual(result["case_id"],"B04")
            self.assertEqual(result["reader_age"],10)
            self.assertEqual(result["source_pack_sha256"],SOURCE_SHA)
            self.assertTrue(800<=result["original_word_count"]<=1400)
            self.assertEqual(result["quality_initial_verdict"],"NOT_YET_AUDITED")
            self.assertFalse(result["english_master_authorized"])
            self.assertFalse(result["q25_authorized"])
            self.assertFalse(result["production_state_write_authorized"])
            manuscript=json.loads(next(Path(td).glob("b04-*-r06/story-draft.json")).read_text())
            spine=json.loads(next(Path(td).glob("b04-*-r06/spine-plan.json")).read_text())
            self.assertEqual(manuscript["spine_sha256"],spine["spine_sha256"])

    def test_second_b04_claim_rejected_without_provider_call(self):
        with TemporaryDirectory() as td:
            wrapped,fake=fake_transport(self.pack)
            fourth_story_once(".",td,transport=wrapped)
            with self.assertRaises(FileExistsError):
                fourth_story_once(".",td,transport=wrapped)
            self.assertEqual(len(fake.calls),2)

    def test_swapped_spine_and_unknown_transport_cost_fail_closed(self):
        with TemporaryDirectory() as td:
            wrapped,fake=fake_transport(self.pack,wrong_spine=True)
            with self.assertRaises(HarnessStop):
                fourth_story_once(".",td,transport=wrapped)
            self.assertEqual(len(fake.calls),1)
        with TemporaryDirectory() as td:
            calls=[]
            def transport_fails(_):
                calls.append(1)
                raise TimeoutError("charge not known")
            with self.assertRaises(HarnessStop):
                fourth_story_once(".",td,transport=transport_fails)
            self.assertEqual(calls,[1])
            self.assertTrue(list(Path(td).glob("b04-*-r06/01-spineforge-intent.json")))

if __name__=="__main__":
    unittest.main()
