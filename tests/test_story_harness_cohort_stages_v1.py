"""All common stage entrypoints exercise real B07 producer bytes offline.

Quality/Q25 responses are MOCK PROVIDER envelopes in these tests and cannot
establish a genuine accepted story.
"""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p416_input_bridge import compile_case
from src.story_harness_cohort_source_v1 import load_original_case
from src.story_harness_p458_b07_quality import PROVIDER_FILE_DIGESTS
from src.story_harness_p417_live_pilot import MODEL
from src.story_harness_p422_independent_audit import verify_auditor_reply
from src.story_harness_cohort_stages_v1 import (
    prepare_quality_request, make_pilot_bundle, prepare_real_q25_request,
    validate_real_q25_response, read_only_state_projection
)
from src.story_harness_v1 import HarnessStop

SAVED = Path("evidence/story_harness_p457")
FILES = {
    "spine-plan.json": "b07-r06-original-spine-plan.json",
    "story-draft.json": "b07-r06-original-writer-draft.json",
    "01-spineforge-receipt.json": "b07-r06-original-spineforge-receipt.json",
    "02-writer-receipt.json": "b07-r06-original-writer-receipt.json",
}

def source_b07(folder):
    pack = compile_case(next(c for c in load_plan()["cases"] if c["id"] == "B07"))
    claim = Path(folder) / ("b07-" + pack["pack_sha256"][:16] + "-r06")
    claim.mkdir()
    for file, frozen in FILES.items():
        shutil.copyfile(SAVED / frozen, claim / file)
    return load_original_case(".", folder, case_id="B07",
                              trusted_file_sha256=PROVIDER_FILE_DIGESTS)

def mock_response(content, cost="0.010"):
    return {"model": MODEL, "id": "gen-OfflineTestOnlyB07",
            "usage": {"prompt_tokens": 100, "completion_tokens": 150,
                      "cost": float(cost)},
            "choices": [{"finish_reason": "stop",
                         "message": {"content": json.dumps(content)}}]}

def mock_accepted_audit(source):
    data = {"story_sha256": source["story"]["story_sha256"],
            "spine_sha256": source["spine"]["spine_sha256"],
            "verdict": "ACCEPT", "reader_score": 5,
            "blocking_findings_json": "[]", "advisories_json": "[]",
            "rationale": "Synthetic offline fixture checks versioned structure only."}
    return verify_auditor_reply(source, mock_response(data))

def offline_q25_reply(bundle):
    text = bundle["english_master_text"]
    quote_end = text[int(len(text) * .85):][:50]
    quote_any = text[:50]
    canon = bundle["source"]["pack"]["canonical_state"]
    obs = {
        "final_location": {
            "location_id": canon["protagonist"]["location"],
            "quote": quote_end
        },
        "discovered_locations": [],
        "object_observations": [],
        "open_obligation_outcomes": [
            {"obligation": x, "status": "UNPROVEN", "quote": quote_any}
            for x in canon["open_obligations"]
        ],
        "unknown_facts_retained": canon["unknown_facts"],
        "world_time_delta": None,
    }
    return mock_response({
        "source_pack_sha256": bundle["source"]["pack"]["pack_sha256"],
        "spine_sha256": bundle["source"]["spine"]["spine_sha256"],
        "story_sha256": bundle["source"]["story"]["story_sha256"],
        "evidence_json": json.dumps(obs), "explanation":
            "Untrusted mock test of source anchored Q25 proposal, not Canon."
    })

class CommonStagesTests(unittest.TestCase):
    def test_original_b07_source_prepares_same_audit_and_q25(self):
        with tempfile.TemporaryDirectory() as td:
            source = source_b07(td)
            audit = prepare_quality_request(source)
            self.assertEqual(audit["response_format"]["json_schema"]["name"],
                             "lumi_b07_independent_initial_audit_v1")
            fake = mock_accepted_audit(source)
            bundle = make_pilot_bundle(source, fake)
            self.assertEqual(bundle["master"]["case_id"], "B07")
            self.assertFalse(bundle["master"]["provider_evidence_externally_attested"])
            self.assertEqual(hashlib.sha256(bundle["english_master_text"].encode()).hexdigest(),
                             source["story"]["story_sha256"])
            q25_request = prepare_real_q25_request(bundle)
            self.assertEqual(q25_request["response_format"]["json_schema"]["name"],
                             "lumi_b07_q25_evidence_proposal_v1")
            receipt = validate_real_q25_response(bundle, offline_q25_reply(bundle))
            final = read_only_state_projection(bundle, receipt)
            self.assertEqual(final["case_id"], "B07")
            self.assertFalse(final["production_state_write_authorized"])
            self.assertIsNone(final["final_world_time"])
            self.assertEqual(final["unknown_facts_retained"],
                             bundle["source"]["pack"]["unknown_facts"])
            self.assertFalse(final["independent_state_semantics_certified"])


    def test_long_age_25_and_age_40_stories_use_uniform_complete_40k_bound(self):
        from src.story_harness_p422_independent_audit import audit_wire
        from src.story_harness_p424_q25_evidence import extraction_wire
        from src.story_harness_p410 import canonical_json
        for age, case_id in ((25, "B08"), (40, "B09")):
            case = next(c for c in load_plan()["cases"] if c["id"] == case_id)
            pack = compile_case(case)
            long_story = "A decision has consequences. " * 2500
            long_story = " ".join(long_story.split()[:2650])
            fake_source = {
                "case_id": case_id, "pack": pack,
                "spine": {"spine_sha256": "a" * 64,
                          "spine": {"spine_summary": "Original frozen plan",
                                    "beats": []}},
                "story": {"story_sha256": hashlib.sha256(long_story.encode()).hexdigest(),
                          "word_count": 2650, "story_text": long_story}
            }
            self.assertTrue(1800 <= len(long_story.split()) <= 2800)
            with self.assertRaises(HarnessStop):
                audit_wire(fake_source)
            expanded = prepare_quality_request(fake_source)
            self.assertIn(long_story, expanded["messages"][1]["content"])
            self.assertLess(len(canonical_json(expanded)), 40000)
            with self.assertRaises(HarnessStop):
                audit_wire(fake_source, max_request_bytes=40000)
            mock_bundle = {
                "schema": "lumi.story-harness-cohort-common-stages.v1",
                "source": fake_source, "english_master_text": long_story,
                "master": {"source_story_sha256": fake_source["story"]["story_sha256"],
                           "manual_text_edits": 0}
            }
            request = prepare_real_q25_request(mock_bundle)
            self.assertIn(long_story, request["messages"][1]["content"])
            self.assertLess(len(canonical_json(request)), 40000)
            with self.assertRaises(HarnessStop):
                extraction_wire(mock_bundle, max_request_bytes=40000)

    def test_rejection_never_creates_master_and_state_lineage_cannot_swap(self):
        with tempfile.TemporaryDirectory() as td:
            source = source_b07(td)
            fake = mock_accepted_audit(source)
            fake["quality_initial_verdict"] = "REJECT"
            with self.assertRaises(HarnessStop):
                make_pilot_bundle(source, fake)
            accepted = make_pilot_bundle(source, mock_accepted_audit(source))
            receipt = validate_real_q25_response(accepted, offline_q25_reply(accepted))
            receipt["story_sha256"] = "f" * 64
            with self.assertRaises(HarnessStop):
                read_only_state_projection(accepted, receipt)

    def test_missing_q25_quote_or_changed_world_time_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            source = source_b07(td)
            bundle = make_pilot_bundle(source, mock_accepted_audit(source))
            reply = offline_q25_reply(bundle)
            envelope = json.loads(reply["choices"][0]["message"]["content"])
            observations = json.loads(envelope["evidence_json"])
            observations["world_time_delta"] = 100
            envelope["evidence_json"] = json.dumps(observations)
            reply["choices"][0]["message"]["content"] = json.dumps(envelope)
            with self.assertRaises(HarnessStop):
                validate_real_q25_response(bundle, reply)
