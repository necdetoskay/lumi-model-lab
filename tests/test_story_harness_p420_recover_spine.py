"""Read-only r05 original Spine recovery; synthetic fixtures cannot prove provider stored content."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.story_harness_p420_recover_spine import (
    exact_source, verify_original_completion, recover_once, ROOT_NAME,
    SOURCE_PACK, ENDPOINT,
)
from src.story_harness_p416_input_bridge import sha
from src.story_harness_v1 import HarnessStop


def source_spine(pack):
    sites=pack["canonical_state"]["locations"]
    return {
        "source_pack_sha256":pack["pack_sha256"],
        "spine_summary":"A small brave girl seeks the missing star and brings a gentle light home.",
        "beats":[{
            "id":f"BEAT_{i+1:02d}",
            "location":sites[0] if i==0 or i==3 else sites[1],
            "goal":f"Mira's real story goal at moment {i}, not an outline.",
            "choice":f"Mira decides how to help the small star at step {i}.",
            "consequence":f"The choice causes a visible gentle consequence at step {i}.",
            "obligation_reference":pack["open_obligations"][0] if i==3 else None,
        } for i in range(4)]
    }


class P420Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack=exact_source(".")

    def test_pinned_case_source_sha_and_url(self):
        self.assertEqual(self.pack["pack_sha256"],SOURCE_PACK)
        self.assertIn("generation/content?id=gen-",ENDPOINT)

    def test_flat_output_with_real_lineage_in_fake_fixture(self):
        spine=source_spine(self.pack)
        saved={"source_pack_sha256":spine["source_pack_sha256"],
               "spine_summary":spine["spine_summary"],
               "beats_json":json.dumps(spine["beats"])}
        result=verify_original_completion(
            self.pack,{"output":{"completion":json.dumps(saved)}},
            expected_spine_sha256=sha(spine))
        self.assertEqual(result["spine_sha256"],sha(spine))
        self.assertFalse(result["independent_spine_validation_accepted"])

    def test_mismatched_original_sha_fails_even_valid_synthetic_spine(self):
        spine=source_spine(self.pack)
        with self.assertRaises(HarnessStop):
            verify_original_completion(
                self.pack,{"output":{"completion":json.dumps(spine)}})

    def test_200_mock_recovery_records_immutable_spine_without_accepting_quality(self):
        spine=source_spine(self.pack)
        with TemporaryDirectory() as td:
            result=recover_once(".",td,"fake",
                 transport=lambda k:{"http_status":200,"data":{
                        "output":{"completion":json.dumps(spine)}}},
                 expected_spine_sha256=sha(spine))
            self.assertTrue(result["spine_recovered"])
            self.assertFalse(result["quality_accepted"])
            self.assertEqual(result["new_model_spend_usd"],"0")
            saved=json.loads((Path(td)/ROOT_NAME/"original-spine.json").read_text())
            self.assertEqual(saved["spine_sha256"],sha(spine))
            with self.assertRaises(FileExistsError):
                recover_once(".",td,"fake",transport=lambda k:None)

    def test_provider_not_stored_404_is_not_fabricated_spine(self):
        with TemporaryDirectory() as td:
            calls=[]
            def unavailable(k):
                calls.append(k)
                return {"http_status":404,"data":None}
            r=recover_once(".",td,"fake",transport=unavailable)
            self.assertFalse(r["spine_recovered"])
            self.assertEqual(r["status"],"CONTENT_UNAVAILABLE")
            self.assertEqual(calls,["fake"])
            self.assertFalse((Path(td)/ROOT_NAME/"original-spine.json").exists())

    def test_no_stored_completion_is_a_stop_not_an_imagined_spine(self):
        with TemporaryDirectory() as td:
            with self.assertRaises(HarnessStop):
                recover_once(".",td,"fake",
                 transport=lambda k:{"http_status":200,"data":{"output":{}}})
            receipt=json.loads((Path(td)/ROOT_NAME/"01-receipt.json").read_text())
            self.assertFalse(receipt["spine_recovered"])
            self.assertEqual(receipt["model_posts"],0)

    def test_story_substitution_or_unknown_location_is_denied(self):
        spine=source_spine(self.pack)
        spine["beats"][1]["location"]="TELEPORT"
        with self.assertRaises(HarnessStop):
            verify_original_completion(self.pack,{"output":{"completion":json.dumps(spine)}},
                                       expected_spine_sha256=sha(spine))


if __name__=="__main__":
    unittest.main()
