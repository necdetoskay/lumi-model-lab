"""P4.35: B03 Q25 strict river/village evidence remains OFF unless granted."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from src.story_harness_p432_b03_quality import (
    SOURCE_SHA, SPINE_SHA, STORY_SHA, FILES, EVIDENCE_DIR, get_original_B03,
)
from src.story_harness_p434_b03_master import AUDIT_PATH, QUALITY_CLAIM, seal_b03_once, load_b03_quality, MASTER_DIR
from src.story_harness_p435_b03_q25 import load_b03_bundle, b03_q25_wire, verify_b03_q25_response, q25_once, RUN_NAME
from src.story_harness_v1 import HarnessStop

def fixture(td):
    root=Path(td)
    claim=root/"producer"/("b03-"+SOURCE_SHA[:16]+"-r06")
    claim.mkdir(parents=True)
    q=root/"quality"/QUALITY_CLAIM
    q.mkdir(parents=True)
    master=root/"master"
    master.mkdir()
    for dest, src in FILES.items():
        (claim/dest).write_bytes((Path(EVIDENCE_DIR)/src).read_bytes())
    (q/"01-audit-outcome.json").write_bytes(Path(AUDIT_PATH).read_bytes())
    src=get_original_B03(".", root/"producer")
    audit=load_b03_quality(".", root/"quality")
    seal_b03_once(src, audit, master)
    return root, load_b03_bundle(".", root/"producer", root/"quality", master)

def proposed(bundle):
    text=bundle["english_master_text"]
    obs={
        "final_location":{"location_id":"VILLAGE","quote":"and she hugged Duru right there in the square."},
        "discovered_locations":[{"location_id":"VILLAGE","quote":"The path opened into a village of crooked rooftops"}],
        "object_observations":[],
        "open_obligation_outcomes":[
            {"obligation":"Nehir yalnızca tek geçişte aşılır","status":"SATISFIED",
             "quote":"She had crossed bravely, and she had crossed once."},
            {"obligation":"Kilit açılmadan sandık açılamaz","status":"SATISFIED",
             "quote":"The lock sprang open."},
        ],
        "unknown_facts_retained":bundle["source"]["pack"]["unknown_facts"],
        "world_time_delta":None,
    }
    for quote in [obs["final_location"]["quote"],obs["discovered_locations"][0]["quote"],
                  *[o["quote"] for o in obs["open_obligation_outcomes"]]]:
        assert quote in text, quote
    return obs

def mocked_response(bundle, evidence=None):
    evidence=evidence or proposed(bundle)
    payload={"source_pack_sha256":SOURCE_SHA,"spine_sha256":SPINE_SHA,"story_sha256":STORY_SHA,
             "evidence_json":json.dumps(evidence,ensure_ascii=False),
             "explanation":"Independent offline test of same-story quote matching only."}
    return {"model":"anthropic/claude-sonnet-5.5","id":"gen-B03MOCKQ25test",
            "usage":{"prompt_tokens":100,"completion_tokens":100,"cost":0.001},
            "choices":[{"finish_reason":"stop","message":{"content":json.dumps(payload,ensure_ascii=False)}}]}

class P435Tests(unittest.TestCase):
    def test_preflight_and_original_b03_river_grammar(self):
        with TemporaryDirectory() as td:
            _,bundle=fixture(td)
            wire=b03_q25_wire(bundle)
            self.assertEqual(json.loads(wire["messages"][1]["content"])["case_id"],"B03")
            self.assertEqual(wire["response_format"]["json_schema"]["name"],"lumi_b03_q25_evidence_proposal_v1")
            self.assertIn("AT_RIVERBANK",wire["messages"][0]["content"])
            self.assertIn("AT_VILLAGE",wire["messages"][0]["content"])
            self.assertNotIn("AT_MEADOW",wire["messages"][0]["content"])
            self.assertEqual(bundle["master"]["accepted_story_sha256"],STORY_SHA)

    def test_offline_mock_validation_is_not_a_real_q25(self):
        with TemporaryDirectory() as td:
            _,bundle=fixture(td)
            parsed=verify_b03_q25_response(bundle,mocked_response(bundle))
            self.assertEqual(parsed["schema"],"lumi.story-harness-p435-b03-evidence-proposal.v1")
            self.assertEqual(parsed["evidence_proposal"]["final_location"]["location_id"],"VILLAGE")
            self.assertFalse(parsed["semantic_state_fully_certified"])
            self.assertFalse(parsed["production_state_write_authorized"])

    def test_one_shot_consumes_claim_even_for_offline_mock(self):
        with TemporaryDirectory() as td:
            _,bundle=fixture(td)
            ledger=Path(td)/"q25";ledger.mkdir()
            q25_once(bundle,ledger,transport=lambda body:mocked_response(bundle))
            self.assertTrue((ledger/RUN_NAME/"00-intent.json").exists())
            self.assertTrue((ledger/RUN_NAME/"01-q25-evidence.json").exists())
            with self.assertRaises(FileExistsError):
                q25_once(bundle,ledger,transport=lambda body:mocked_response(bundle))

    def test_fabricated_last_location_and_cross_story_denied(self):
        with TemporaryDirectory() as td:
            _,bundle=fixture(td)
            evidence=proposed(bundle)
            evidence["final_location"]["quote"]="The river was wide and dark green"
            with self.assertRaises(HarnessStop):
                verify_b03_q25_response(bundle,mocked_response(bundle,evidence))
            altered=dict(bundle)
            altered["source"]=dict(bundle["source"])
            altered["source"]["case_id"]="B02"
            with self.assertRaises(HarnessStop):
                b03_q25_wire(altered)

    def test_mutated_master_or_audit_link_denied(self):
        with TemporaryDirectory() as td:
            root,_=fixture(td)
            prose=root/"master"/MASTER_DIR/"ENGLISH_MASTER.txt"
            prose.write_text(prose.read_text()+" invented")
            with self.assertRaises(HarnessStop):
                load_b03_bundle(".",root/"producer",root/"quality",root/"master")
            prose.write_bytes((Path(EVIDENCE_DIR)/FILES["story-draft.json"]).read_bytes())
            with self.assertRaises(HarnessStop):
                load_b03_bundle(".",root/"producer",root/"quality",root/"master")

if __name__=="__main__":
    unittest.main()
