"""One shared generic producer reader for ages 4, 10, 12, 25, 40."""
from pathlib import Path
import json
import shutil
import tempfile
import unittest

from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p416_input_bridge import (
    compile_case, build_spine_request,
)
from src.story_harness_p417_live_pilot import wire
from src.story_harness_p422_independent_audit import audit_wire
from src.story_harness_p458_b07_quality import (
    PROVIDER_FILE_DIGESTS, SOURCE_SHA, SPINE_SHA, STORY_SHA,
)
from src.story_harness_cohort_source_v1 import load_original_case
from src.story_harness_v1 import HarnessStop

SAVED = Path("evidence/story_harness_p457")
FILES = {
    "spine-plan.json": "b07-r06-original-spine-plan.json",
    "story-draft.json": "b07-r06-original-writer-draft.json",
    "01-spineforge-receipt.json": "b07-r06-original-spineforge-receipt.json",
    "02-writer-receipt.json": "b07-r06-original-writer-receipt.json",
}


def original_claim(folder):
    pack = compile_case(next(c for c in load_plan()["cases"] if c["id"] == "B07"))
    claim = Path(folder) / ("b07-" + pack["pack_sha256"][:16] + "-r06")
    claim.mkdir()
    for name, archived in FILES.items():
        shutil.copyfile(SAVED / archived, claim / name)
    return claim


class GenericCohortSourceTests(unittest.TestCase):
    def test_all_ten_inputs_compile_with_same_shared_spine_model_contract(self):
        plan = load_plan()
        self.assertEqual(len(plan["cases"]), 10)
        profiles = set()
        for case in plan["cases"]:
            pack = compile_case(case)
            self.assertEqual(pack["reader_age"], case["input"]["reader_age"])
            self.assertEqual(pack["topic"], case["input"]["topic"])
            request = build_spine_request(pack)
            model_wire = wire("SPINEFORGE", request, simple_envelope=True)
            self.assertTrue(model_wire.get("messages"))
            profiles.add(model_wire["model"])
        self.assertEqual(len(profiles), 1)

    def test_b07_real_historical_artifacts_fit_common_initial_audit_reader(self):
        with tempfile.TemporaryDirectory() as td:
            original_claim(td)
            source = load_original_case(".", td, case_id="B07",
                                        trusted_file_sha256=PROVIDER_FILE_DIGESTS)
            self.assertEqual(source["story"]["story_sha256"], STORY_SHA)
            self.assertEqual(source["spine"]["spine_sha256"], SPINE_SHA)
            self.assertEqual(source["pack"]["pack_sha256"], SOURCE_SHA)
            self.assertEqual(source["generation_cost_usd"], "0.093066")
            self.assertFalse(source["quality_accepted"])
            request = audit_wire(source, max_request_bytes=22000)
            self.assertFalse(request["provider"]["allow_fallbacks"])

    def test_original_source_byte_tamper_detected_before_quality(self):
        with tempfile.TemporaryDirectory() as td:
            claim = original_claim(td)
            for filename in FILES:
                file = claim / filename
                previous = file.read_bytes()
                file.write_bytes(previous + b" ")
                with self.subTest(filename=filename), self.assertRaises(HarnessStop):
                    load_original_case(".", td, case_id="B07",
                                       trusted_file_sha256=PROVIDER_FILE_DIGESTS)
                file.write_bytes(previous)

    def test_unknown_case_and_untrusted_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            original_claim(td)
            with self.assertRaises(HarnessStop):
                load_original_case(".", td, case_id="B08",
                                   trusted_file_sha256=PROVIDER_FILE_DIGESTS)
            with self.assertRaises(HarnessStop):
                load_original_case(".", td, case_id="B07",
                                   trusted_file_sha256={})
            hashes = dict(PROVIDER_FILE_DIGESTS)
            hashes["story-draft.json"] = "f" * 64
            with self.assertRaises(HarnessStop):
                load_original_case(".", td, case_id="B07",
                                   trusted_file_sha256=hashes)


if __name__ == "__main__":
    unittest.main()
