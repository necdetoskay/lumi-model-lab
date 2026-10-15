"""P4.29: B02 English Master → Q25 evidence, preserving Canon without writes.

All 'model' responses here are mocks; success requires a separate real Sonnet
generation and exact B02 file hashes. These tests never count toward 90%.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.story_harness_p428_b02_master import seal_b02_once,load_b02_quality
from src.story_harness_p427_b02_quality import get_b02_original
from src.story_harness_p429_b02_q25 import (
    SCHEMA,RUN_NAME,load_b02_bundle,b02_q25_wire,one_b02_q25,
    PREVIOUS_RESERVED_USD,COST_CAP,
)
from src.story_harness_p424_q25_evidence import verify_model_response
from src.story_harness_p417_live_pilot import MODEL
from src.story_harness_v1 import HarnessStop
from test_story_harness_p428_b02_master import make_sources


def fake_b02_observations(bundle):
    canon=bundle["source"]["pack"]["canonical_state"]
    return {
        "final_location":{
            "location_id":"GARDEN",
            "quote":"They walked back along the crooked path to the garden he knew."},
        "discovered_locations":[{"location_id":"COMMONS",
            "quote":"The Commons was full of soft sounds."}],
        "object_observations":[{
            "object_name":"Cloud","last_seen_relation":"AT_GARDEN",
            "ownership":"UNKNOWN","quote":"Then Cloud sang."}],
        "open_obligation_outcomes":[
            {"obligation":canon["open_obligations"][0],"status":"SATISFIED",
             "quote":"Aren knew his garden very well."},
            {"obligation":canon["open_obligations"][1],"status":"SATISFIED",
             "quote":"Aren did not guess."},
        ],
        "unknown_facts_retained":canon["unknown_facts"],
        "world_time_delta":None,
    }


def fake_reply(bundle, *, observation=None):
    observation=observation or fake_b02_observations(bundle)
    source=bundle["source"]
    answer={
        "source_pack_sha256":source["pack"]["pack_sha256"],
        "story_sha256":source["story"]["story_sha256"],
        "spine_sha256":source["spine"]["spine_sha256"],
        "evidence_json":json.dumps(observation),
        "explanation":"Quoted B02 Canon and material evidence, no inferred clock time.",
    }
    return {
        "model":MODEL,"id":"gen-MOCKB02Q25ABCDE",
        "usage":{"prompt_tokens":2200,"completion_tokens":1200,"cost":0.021},
        "choices":[{"finish_reason":"stop","message":{"content":json.dumps(answer)}}],
    }


class P429Tests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        producer,quality,master=make_sources(self.temp.name)
        source=get_b02_original(".",producer)
        audit=load_b02_quality(".",quality)
        seal_b02_once(source,audit,master)
        self.bundle=load_b02_bundle(".",producer,quality,master)

    def test_real_b02_source_and_master_qualify_without_B01(self):
        self.assertEqual(self.bundle["source"]["case_id"],"B02")
        self.assertEqual(self.bundle["master"]["case_id"],"B02")
        self.assertEqual(self.bundle["master"]["reader_score"],5)
        self.assertEqual(self.bundle["master"]["english_master_word_count"],561)
        self.assertFalse(self.bundle["master"]["production_master_published"])
        self.assertEqual(PREVIOUS_RESERVED_USD.__str__(),"1.360092")
        self.assertEqual(str(COST_CAP),"0.050")

    def test_real_Q25_wire_uses_only_B02_known_locations_and_exact_master(self):
        w=b02_q25_wire(self.bundle)
        system=w["messages"][0]["content"]
        payload=json.loads(w["messages"][1]["content"])
        self.assertEqual(payload["case_id"],"B02")
        self.assertEqual(payload["English_Master_Text"],self.bundle["english_master_text"])
        self.assertIn("AT_COMMONS",system)
        self.assertIn("AT_GARDEN",system)
        self.assertNotIn("AT_HOME",system)
        self.assertNotIn("AT_MEADOW",system)
        self.assertIn("ownership field ALWAYS",system)
        self.assertTrue(w["response_format"]["json_schema"]["strict"])
        self.assertEqual(w["response_format"]["json_schema"]["name"],
                         "lumi_b02_q25_evidence_proposal_v1")

    def test_anchored_canon_ownership_unknown_candidate_passes_parser(self):
        result=verify_model_response(self.bundle,fake_reply(self.bundle))
        self.assertEqual(result["case_id"],"B02")
        self.assertEqual(result["evidence_proposal"]["final_location"]["location_id"],"GARDEN")
        self.assertEqual(result["evidence_proposal"]["discovered_locations"][0]["location_id"],"COMMONS")
        self.assertEqual(result["evidence_proposal"]["object_observations"][0]["ownership"],"UNKNOWN")
        self.assertFalse(result["production_state_write_authorized"])
        self.assertFalse(result["semantic_state_fully_certified"])

    def test_one_distinct_B02_Q25_request_produces_only_evidence_proposal(self):
        with TemporaryDirectory() as td:
            calls=[]
            def mock(wire):
                calls.append(wire)
                return fake_reply(self.bundle)
            result=one_b02_q25(self.bundle,td,transport=mock)
            self.assertEqual(result["schema"],SCHEMA)
            self.assertEqual(len(calls),1)
            self.assertFalse(result["final_story_state_committed"])
            original=json.loads((Path(td)/RUN_NAME/"01-b02-q25-evidence.json").read_text())
            self.assertEqual(original["story_sha256"],result["story_sha256"])
            with self.assertRaises(FileExistsError):
                one_b02_q25(self.bundle,td,transport=mock)
            self.assertEqual(len(calls),1)

    def test_false_object_owner_denied_and_known_model_bill_preserved(self):
        broken=fake_b02_observations(self.bundle)
        broken["object_observations"][0]["ownership"]="Aren"
        with TemporaryDirectory() as td:
            with self.assertRaises(HarnessStop):
                one_b02_q25(self.bundle,td,transport=lambda wire:fake_reply(
                    self.bundle,observation=broken))
            output=json.loads((Path(td)/RUN_NAME/"01-b02-q25-evidence.json").read_text())
            self.assertEqual(output["status"],"STOP_UNKNOWN_OR_INVALID")
            self.assertEqual(output["provider_reported_cost_usd"],"0.021")
            self.assertFalse(output["automatic_retry"])
            self.assertNotIn("Aren",json.dumps(output.get("error","")))

    def test_unproven_final_position_and_invented_worldtime_fail(self):
        cases=[
           ("location","GARDEN","The garden was quiet. It was too quiet."),
           ("time",3,None),
        ]
        for item,change,quote in cases:
            o=fake_b02_observations(self.bundle)
            if item=="time":
                o["world_time_delta"]=change
            else:
                o["final_location"]["quote"]=quote
            with self.subTest(item=item),self.assertRaises(HarnessStop):
                verify_model_response(self.bundle,fake_reply(
                    self.bundle,observation=o))

    def test_B01_bundle_cannot_enter_B02_Q25(self):
        b=deepcopy(self.bundle)
        b["source"]["case_id"]="B01"
        with self.assertRaises(HarnessStop):
            b02_q25_wire(b)

    def test_provider_exception_is_consumed_without_retry_or_prose_logging(self):
        with TemporaryDirectory() as td:
            with self.assertRaises(HarnessStop):
                one_b02_q25(self.bundle,td,transport=lambda wire:(
                    (_ for _ in ()).throw(TimeoutError("Bearer sk-or-SENSITIVE"))))
            receipt=(Path(td)/RUN_NAME/"01-b02-q25-evidence.json").read_text()
            self.assertNotIn("sk-or-",receipt)
            self.assertEqual(json.loads(receipt)["status"],"STOP_UNKNOWN_OR_INVALID")
            with self.assertRaises(FileExistsError):
                one_b02_q25(self.bundle,td,transport=lambda wire:fake_reply(self.bundle))


if __name__=="__main__":
    unittest.main()
