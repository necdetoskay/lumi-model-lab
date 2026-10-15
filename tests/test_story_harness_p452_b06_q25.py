"""P4.51: genuine B06 accepted Master to once-only source-bound Q25, offline mock."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from src.story_harness_p449_b06_quality import CLAIM_NAME,AUDIT_DIR,STORY_SHA,SPINE_SHA,SOURCE_SHA
from src.story_harness_p450_b06_master import (
    AUDIT_PATH,SOURCE_FILES,seal_or_verify,load_b06_quality,original_b06,MASTER_DIR
)
from src.story_harness_p452_b06_q25 import (
    RUN_NAME,load_b06_bundle,b06_q25_wire,check_b06_response,q25_v02_once
)
from src.story_harness_v1 import HarnessStop

def fixture(tmp):
    root=Path(tmp)
    pr=root/"producer";claim=pr/CLAIM_NAME;claim.mkdir(parents=True)
    qr=root/"quality";aq=qr/AUDIT_DIR;aq.mkdir(parents=True)
    mr=root/"master";mr.mkdir()
    for name,saved in SOURCE_FILES.items():
        (claim/name).write_bytes((Path("evidence/story_harness_p448")/saved).read_bytes())
    (aq/"01-audit-outcome.json").write_bytes(Path(AUDIT_PATH).read_bytes())
    source=original_b06(".",pr)
    audit=load_b06_quality(".",qr)
    seal_or_verify(source,audit,mr)
    return root,load_b06_bundle(".",pr,qr,mr)

def valid_observations(bundle):
    story=bundle["english_master_text"]
    end_quote="the library seemed to breathe out around her."
    tower_quote="The tower rose from a patch of rough ground"
    obligations_quote="The Agreement was open. The atlas's owner was unknown."
    assert end_quote in story and story.rfind(end_quote) >= int(len(story)*.60)
    assert tower_quote in story and obligations_quote in story
    return {
        "final_location":{"location_id":"LIBRARY","quote":end_quote},
        "discovered_locations":[{"location_id":"TOWER","quote":tower_quote}],
        "object_observations":[],
        "open_obligation_outcomes":[{"obligation":o,"status":"OPEN","quote":obligations_quote}
                                    for o in bundle["source"]["pack"]["open_obligations"]],
        "unknown_facts_retained":bundle["source"]["pack"]["unknown_facts"],
        "world_time_delta":None,
    }

def fake_reply(bundle, obs=None):
    j={"source_pack_sha256":SOURCE_SHA,"spine_sha256":SPINE_SHA,
       "story_sha256":STORY_SHA,
       "evidence_json":json.dumps(obs if obs is not None else valid_observations(bundle)),
       "explanation":"An immutable quote-grounded source-only observation, no Canon changes."}
    return {"id":"gen-B06Q25Mock456789","model":"anthropic/claude-sonnet-5.5",
            "usage":{"prompt_tokens":100,"completion_tokens":100,"cost":"0.001"},
            "choices":[{"finish_reason":"stop","message":{"content":json.dumps(j)}}]}

class B06Q25Offline(unittest.TestCase):
    def test_identity_and_original_spatial_grammar(self):
        with TemporaryDirectory() as td:
            _,b=fixture(td)
            wire=b06_q25_wire(b)
            self.assertEqual(wire["response_format"]["json_schema"]["name"],
                             "lumi_b06_q25_evidence_proposal_v02")
            self.assertIn("AT_LIBRARY",wire["messages"][0]["content"])
            self.assertIn("AT_TOWER",wire["messages"][0]["content"])
            self.assertEqual(b["master"]["english_master_word_count"],2285)
            self.assertEqual(b["master"]["accepted_story_sha256"],STORY_SHA)
    def test_original_v01_stop_pinned(self):
        from src.story_harness_p452_b06_q25 import verify_original_v01_stop
        verify_original_v01_stop(".")

    def test_three_same_method_improvements_are_source_bound(self):
        with TemporaryDirectory() as td:
            _,b=fixture(td)
            system=b06_q25_wire(b)["messages"][0]["content"]
            for phrase in ("the library seemed to breathe out around her.",
                           "The tower rose from a patch of rough ground",
                           "The Agreement was open. The atlas's owner was unknown.",
                           "JSON-encoded STRING", "world_time_delta JSON null"):
                self.assertIn(phrase,system)

    def test_b06_spatial_contract_failure_safe_category_preserves_cost(self):
        with TemporaryDirectory() as td:
            root,b=fixture(td);q=root/"q25";q.mkdir()
            def invalid(_):
                item=valid_observations(b)
                item["final_location"]["location_id"]="TOWER"
                return fake_reply(b,item)
            with self.assertRaises(HarnessStop):
                q25_v02_once(b,q,transport=invalid)
            report=json.loads((q/RUN_NAME/"01-q25-evidence.json").read_bytes())
            self.assertEqual(report["safe_failure_code"],"B06_SPATIAL_SOURCE_QUOTE_INVALID")
            self.assertEqual(report["provider_reported_cost_usd"],"0.001")
            self.assertFalse(report["automatic_retry"])
            self.assertFalse(report["production_state_write_authorized"])
            self.assertNotIn("English_Master_Text",str(report))

    def test_v01_stop_tampering_rejected(self):
        from src.story_harness_p452_b06_q25 import verify_original_v01_stop
        with TemporaryDirectory() as td:
            home=Path(td)
            for s in ("evidence/story_harness_p451/b06-r06-original-q25-stop.json",
                      "evidence/story_harness_p451/b06-r06-original-q25-intent.json"):
                p=home/s;p.parent.mkdir(parents=True,exist_ok=True)
                p.write_bytes(Path(s).read_bytes())
            p=home/"evidence/story_harness_p451/b06-r06-original-q25-stop.json"
            p.write_bytes(p.read_bytes()+b" ")
            with self.assertRaises(HarnessStop):verify_original_v01_stop(home)

    def test_mock_state_is_read_only_and_obligations_remain_open(self):
        with TemporaryDirectory() as td:
            _,b=fixture(td)
            p=check_b06_response(b,fake_reply(b))
            self.assertEqual(p["evidence_proposal"]["final_location"]["location_id"],"LIBRARY")
            self.assertEqual([x["location_id"] for x in p["evidence_proposal"]["discovered_locations"]],["TOWER"])
            self.assertEqual([x["status"] for x in p["evidence_proposal"]["open_obligation_outcomes"]],["OPEN","OPEN"])
            self.assertFalse(p["production_state_write_authorized"])
            self.assertFalse(p["semantic_state_fully_certified"])
    def test_unknown_or_hallucinated_facts_stop(self):
        with TemporaryDirectory() as td:
            _,b=fixture(td)
            for defect in ("closed","invented","time","quote","discovery"):
                p=valid_observations(b)
                if defect=="closed":p["open_obligation_outcomes"][1]["status"]="SATISFIED"
                elif defect=="invented":p["final_location"]["location_id"]="STUDIO"
                elif defect=="time":p["world_time_delta"]=1
                elif defect=="quote":p["final_location"]["quote"]="The imaginary library was a fake"
                elif defect=="discovery":p["discovered_locations"][0]["location_id"]="LIBRARY"
                with self.subTest(defect=defect),self.assertRaises(HarnessStop):
                    check_b06_response(b,fake_reply(b,p))
    def test_claim_is_consumed_after_one_fake_post(self):
        with TemporaryDirectory() as td:
            root,b=fixture(td); q=root/"q25";q.mkdir()
            calls=[]
            def fake(req):
                calls.append(1);return fake_reply(b)
            o=q25_v02_once(b,q,transport=fake)
            self.assertEqual(o["case_id"],"B06")
            self.assertEqual(calls,[1])
            with self.assertRaises(FileExistsError):
                q25_v02_once(b,q,transport=fake)
            self.assertEqual(calls,[1])
    def test_transport_fault_consumes_and_does_not_retry(self):
        with TemporaryDirectory() as td:
            root,b=fixture(td); q=root/"q25";q.mkdir()
            calls=[]
            def failed(_):
                calls.append(1);raise TimeoutError("unknown provider cost")
            with self.assertRaises(HarnessStop):q25_v02_once(b,q,transport=failed)
            self.assertEqual(calls,[1])
            record=json.loads((q/RUN_NAME/"01-q25-evidence.json").read_bytes())
            self.assertEqual(record["status"],"STOP_UNKNOWN_OR_INVALID")
            self.assertFalse(record["automatic_retry"])
    def test_tampered_master_fails_before_audit(self):
        with TemporaryDirectory() as td:
            root,_=fixture(td)
            p=root/"master"/MASTER_DIR/"ENGLISH_MASTER.txt"
            p.write_bytes(p.read_bytes()+b" forged")
            with self.assertRaises(HarnessStop):
                load_b06_bundle(".",root/"producer",root/"quality",root/"master")

if __name__=="__main__":
    unittest.main()
