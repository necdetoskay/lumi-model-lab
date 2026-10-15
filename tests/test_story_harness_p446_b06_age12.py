"""P4.46 source-new B06 age12, existing 2-stage generator, mock only."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

import test_story_harness_p417_live_pilot as p417fake
from src.story_harness_p446_b06_age12 import (
    CASE_ID,SOURCE_SHA,source_case,sixth_story_once,status
)
from src.story_harness_v1 import HarnessStop

def fake_transport(pack, *, wrong_spine=False):
    model=p417fake.FakeProvider(pack)
    def send(body):
        legacy=deepcopy(body)
        legacy["response_format"]["json_schema"]["name"]=(
            legacy["response_format"]["json_schema"]["name"].replace("_flat_v2","_v1"))
        answer=model(legacy)
        content=json.loads(answer["choices"][0]["message"]["content"])
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
            filler=("Yasmin read the moonlit library shelves and remembered that the atlas "
                    "had no established owner or location without direct observation. ").split()
            while len(words)<1800:
                words.extend(filler)
            content={
                "source_pack_sha256":content["source_pack_sha256"],
                "spine_sha256":content["spine_sha256"],
                "story_text":" ".join(words[:1850]),
                "beat_ids_json":json.dumps(content["beat_ids"]),
            }
        answer["choices"][0]["message"]["content"]=json.dumps(content)
        return answer
    return send,model

class P446Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan,cls.pack=source_case(".")

    def test_exact_distinct_B06_age12_source(self):
        p=self.pack
        self.assertEqual(CASE_ID,"B06")
        self.assertEqual(p["pack_sha256"],SOURCE_SHA)
        self.assertEqual(p["reader_age"],12)
        self.assertEqual(p["topic"],"Ay ışığındaki kütüphane")
        self.assertEqual(p["word_targets"],{"min":1600,"max":2500})
        self.assertEqual(p["canonical_state"]["protagonist"]["name"],"Yasmin")
        self.assertEqual(p["canonical_state"]["locations"],["LIBRARY","TOWER"])
        self.assertEqual(p["open_obligations"],["Sözleşme kapanmamıştır","Atlasın sahibi bilinmemektedir"])
        self.assertEqual(p["forbidden_state_invention"],
                         "Atlasın sahibi veya konumu icat edilmez")

    def test_default_refuses_provider_and_canon_authority(self):
        d=status()
        self.assertEqual(d["generation_cost_cap_usd"],"0.35")
        self.assertEqual(d["prior_conservative_budget_reserved_usd"],"2.369558")
        self.assertEqual(d["provider_calls"],0)
        self.assertFalse(d["paid_execution_enabled"])
        self.assertFalse(d["quality_initial_accepted"])
        self.assertFalse(d["production_state_write_authorized"])

    def test_existing_unchanged_generator_works_for_new_age12_mock(self):
        with TemporaryDirectory() as td:
            mock,provider=fake_transport(self.pack)
            result=sixth_story_once(".",td,transport=mock)
            self.assertEqual(len(provider.calls),2)
            self.assertEqual(result["case_id"],"B06")
            self.assertTrue(1600<=result["english_word_count"]<=2500)
            self.assertEqual(result["initial_quality_verdict"],"NOT_YET_AUDITED")
            self.assertFalse(result["english_master_authorized"])
            self.assertFalse(result["q25_authorized"])
            self.assertFalse(result["production_state_write_authorized"])
            source=json.loads(next(Path(td).glob("b06-*-r06/story-draft.json")).read_bytes())
            spine=json.loads(next(Path(td).glob("b06-*-r06/spine-plan.json")).read_bytes())
            self.assertEqual(source["spine_sha256"],spine["spine_sha256"])

    def test_immutable_claim_denies_repeated_model_posts(self):
        with TemporaryDirectory() as td:
            fake,provider=fake_transport(self.pack)
            sixth_story_once(".",td,transport=fake)
            with self.assertRaises(FileExistsError):
                sixth_story_once(".",td,transport=fake)
            self.assertEqual(len(provider.calls),2)

    def test_bad_spine_and_timeout_fail_closed_no_retry(self):
        with TemporaryDirectory() as td:
            mock,provider=fake_transport(self.pack,wrong_spine=True)
            with self.assertRaises(HarnessStop):
                sixth_story_once(".",td,transport=mock)
            self.assertEqual(len(provider.calls),1)
        with TemporaryDirectory() as td:
            calls=[]
            def bad(_):
                calls.append(1)
                raise TimeoutError("provider charge unknown")
            with self.assertRaises(HarnessStop):
                sixth_story_once(".",td,transport=bad)
            self.assertEqual(calls,[1])
            self.assertTrue(list(Path(td).glob("b06-*-r06/01-spineforge-intent.json")))

if __name__=="__main__":
    unittest.main()
