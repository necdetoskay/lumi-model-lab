"""P4.54 source-new B07 age25, existing 2-stage generator, mock only."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from pathlib import Path
import json
import unittest

import test_story_harness_p417_live_pilot as p417fake
from src.story_harness_p454_b07_age25 import (
    CASE_ID,SOURCE_SHA,source_case,seventh_story_once,status,
    PAID_GRANT_ENV,PAID_GRANT_VALUE,main
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
            filler=( "Eren watched the storm crossing the harbor and refused to pretend "
                    "the unopened letter had been read before he reached the lighthouse. ").split()
            while len(words)<2100:
                words.extend(filler)
            content={
                "source_pack_sha256":content["source_pack_sha256"],
                "spine_sha256":content["spine_sha256"],
                "story_text":" ".join(words[:2150]),
                "beat_ids_json":json.dumps(content["beat_ids"]),
            }
        answer["choices"][0]["message"]["content"]=json.dumps(content)
        return answer
    return send,model

class P454Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan,cls.pack=source_case(".")

    def test_exact_distinct_B07_age25_source(self):
        p=self.pack
        self.assertEqual(CASE_ID,"B07")
        self.assertEqual(p["pack_sha256"],SOURCE_SHA)
        self.assertEqual(p["reader_age"],25)
        self.assertEqual(p["topic"],"Fenerdeki eski mektup")
        self.assertEqual(p["word_targets"],{"min":1800,"max":2800})
        self.assertEqual(p["canonical_state"]["protagonist"]["name"],"Eren")
        self.assertEqual(p["canonical_state"]["locations"],["HARBOR","LIGHTHOUSE"])
        self.assertEqual(p["open_obligations"],["Mektup henüz okunmamıştır","Fırtına başlamıştır"])
        self.assertEqual(p["forbidden_state_invention"],
                         "İmkânsız zaman sıçraması yapılmaz")

    def test_old_prepost_grant_cannot_authorize_paid_inference(self):
        self.assertEqual(PAID_GRANT_ENV,"LUMI_P455_B07")
        self.assertEqual(PAID_GRANT_VALUE,"ONE_ORIGINAL_B07_AGE25_GENERATION")
        with TemporaryDirectory() as td:
            with patch.dict("os.environ",{
                "LUMI_P446_B07":"ONE_ORIGINAL_B07_AGE25_GENERATION",
                "LUMI_P454_B07":"ONE_ORIGINAL_B07_AGE25_GENERATION",
                "LUMI_P455_B07":"",
            },clear=True):
                with patch("sys.argv",["b07","--paid-once","--claim-root",td]):
                    with self.assertRaises(HarnessStop):
                        main()
            self.assertEqual(list(Path(td).iterdir()),[])

    def test_default_refuses_provider_and_canon_authority(self):
        d=status()
        self.assertEqual(d["generation_cost_cap_usd"],"0.35")
        self.assertEqual(d["prior_conservative_budget_reserved_usd"],"2.859558")
        self.assertEqual(d["provider_calls"],0)
        self.assertFalse(d["paid_execution_enabled"])
        self.assertFalse(d["quality_initial_accepted"])
        self.assertFalse(d["production_state_write_authorized"])

    def test_existing_unchanged_generator_works_for_new_age25_mock(self):
        with TemporaryDirectory() as td:
            mock,provider=fake_transport(self.pack)
            result=seventh_story_once(".",td,transport=mock)
            self.assertEqual(len(provider.calls),2)
            self.assertEqual(result["case_id"],"B07")
            self.assertTrue(1800<=result["english_word_count"]<=2800)
            self.assertEqual(result["initial_quality_verdict"],"NOT_YET_AUDITED")
            self.assertFalse(result["english_master_authorized"])
            self.assertFalse(result["q25_authorized"])
            self.assertFalse(result["production_state_write_authorized"])
            source=json.loads(next(Path(td).glob("b07-*-r06/story-draft.json")).read_bytes())
            spine=json.loads(next(Path(td).glob("b07-*-r06/spine-plan.json")).read_bytes())
            self.assertEqual(source["spine_sha256"],spine["spine_sha256"])

    def test_immutable_claim_denies_repeated_model_posts(self):
        with TemporaryDirectory() as td:
            fake,provider=fake_transport(self.pack)
            seventh_story_once(".",td,transport=fake)
            with self.assertRaises(FileExistsError):
                seventh_story_once(".",td,transport=fake)
            self.assertEqual(len(provider.calls),2)

    def test_bad_spine_and_timeout_fail_closed_no_retry(self):
        with TemporaryDirectory() as td:
            mock,provider=fake_transport(self.pack,wrong_spine=True)
            with self.assertRaises(HarnessStop):
                seventh_story_once(".",td,transport=mock)
            self.assertEqual(len(provider.calls),1)
        with TemporaryDirectory() as td:
            calls=[]
            def bad(_):
                calls.append(1)
                raise TimeoutError("provider charge unknown")
            with self.assertRaises(HarnessStop):
                seventh_story_once(".",td,transport=bad)
            self.assertEqual(calls,[1])
            self.assertTrue(list(Path(td).glob("b07-*-r06/01-spineforge-intent.json")))

if __name__=="__main__":
    unittest.main()
