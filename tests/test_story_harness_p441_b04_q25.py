"""P4.41 B04 genuine Master -> Q25 quote/obligation gates; offline mock only."""
import json
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.story_harness_p439_b04_quality import (
    CLAIM_NAME,AUDIT_DIR,STORY_SHA,SPINE_SHA,SOURCE_SHA
)
from src.story_harness_p440_b04_master import (
    AUDIT_PATH,SOURCE_FILES,seal_or_verify,load_b04_quality,original_b04,MASTER_DIR
)
from src.story_harness_p441_b04_q25 import (
    RUN_NAME,load_b04_bundle,b04_q25_wire,check_b04_response,q25_once
)
from src.story_harness_v1 import HarnessStop

def fixture(tmp):
    root=Path(tmp)
    p=root/"producer"; claim=p/CLAIM_NAME;claim.mkdir(parents=True)
    q=root/"quality";folder=q/AUDIT_DIR;folder.mkdir(parents=True)
    m=root/"master";m.mkdir()
    for original,saved in SOURCE_FILES.items():
        (claim/original).write_bytes((Path("evidence/story_harness_p438")/saved).read_bytes())
    (folder/"01-audit-outcome.json").write_bytes(Path(AUDIT_PATH).read_bytes())
    src=original_b04(".",p)
    audit=load_b04_quality(".",q)
    seal_or_verify(src,audit,m)
    return root,load_b04_bundle(".",p,q,m)

def valid_observations(bundle):
    quote="The studio was quiet when he arrived."
    assert quote in bundle["english_master_text"]
    obligations=bundle["source"]["pack"]["open_obligations"]
    missing="The paint was still gone. The map was still missing."
    assert missing in bundle["english_master_text"]
    return {
        "final_location":{"location_id":"STUDIO","quote":quote},
        "discovered_locations":[{"location_id":"STUDIO","quote":quote}],
        "object_observations":[],
        "open_obligation_outcomes":[{"obligation":s,"status":"OPEN","quote":missing} for s in obligations],
        "unknown_facts_retained":bundle["source"]["pack"]["unknown_facts"],
        "world_time_delta":None,
    }

def mock_response(bundle, observations=None):
    data={
        "source_pack_sha256":SOURCE_SHA,
        "spine_sha256":SPINE_SHA,
        "story_sha256":STORY_SHA,
        "evidence_json":json.dumps(observations or valid_observations(bundle)),
        "explanation":"Evidence only: actual original studio and two still unresolved obligations.",
    }
    return {
        "id":"gen-OfflineMockB04Q25", "model":"anthropic/claude-sonnet-5.5",
        "usage":{"prompt_tokens":100,"completion_tokens":200,"cost":0.001},
        "choices":[{"finish_reason":"stop","message":{"content":json.dumps(data)}}],
    }

class P441Tests(unittest.TestCase):
    def test_true_master_and_exact_market_studio_vocabulary(self):
        with TemporaryDirectory() as td:
            _,b=fixture(td)
            request=b04_q25_wire(b)
            self.assertEqual(request["response_format"]["json_schema"]["name"],
                             "lumi_b04_q25_evidence_proposal_v1")
            sys=request["messages"][0]["content"]
            self.assertIn("AT_MARKET",sys)
            self.assertIn("AT_STUDIO",sys)
            self.assertNotIn("AT_VILLAGE",sys)
            self.assertEqual(b["master"]["accepted_story_sha256"],STORY_SHA)
            self.assertEqual(b["master"]["english_master_word_count"],1277)

    def test_mock_only_proposal_does_not_certify_state(self):
        with TemporaryDirectory() as td:
            _,b=fixture(td)
            out=check_b04_response(b,mock_response(b))
            self.assertEqual(out["evidence_proposal"]["final_location"]["location_id"],"STUDIO")
            self.assertEqual([a["status"] for a in out["evidence_proposal"]["open_obligation_outcomes"]],
                             ["OPEN","OPEN"])
            self.assertFalse(out["semantic_state_fully_certified"])
            self.assertFalse(out["production_state_write_authorized"])

    def test_both_obligations_open_and_source_ownership_guard(self):
        with TemporaryDirectory() as td:
            _,b=fixture(td)
            for defect in ["closed_map","invented_location","invented_time","fake_quote"]:
                obs=valid_observations(b)
                if defect=="closed_map":
                    obs["open_obligation_outcomes"][1]["status"]="SATISFIED"
                elif defect=="invented_location":
                    obs["final_location"]["location_id"]="MARKET"
                elif defect=="invented_time":
                    obs["world_time_delta"]=3
                else:
                    obs["final_location"]["quote"]="Invented studio that is not in story"
                with self.subTest(defect=defect),self.assertRaises(HarnessStop):
                    check_b04_response(b,mock_response(b,obs))

    def test_mock_consumes_ledger_once_no_retry(self):
        with TemporaryDirectory() as td:
            root,b=fixture(td)
            q=root/"q25";q.mkdir()
            calls=[]
            def transport(req):
                calls.append(1)
                return mock_response(b)
            result=q25_once(b,q,transport=transport)
            self.assertEqual(result["case_id"],"B04")
            self.assertEqual(calls,[1])
            self.assertTrue((q/RUN_NAME/"01-q25-evidence.json").is_file())
            with self.assertRaises(FileExistsError):
                q25_once(b,q,transport=transport)
            self.assertEqual(calls,[1])

    def test_transport_failure_consumes_and_stops(self):
        with TemporaryDirectory() as td:
            root,b=fixture(td)
            q=root/"q25";q.mkdir()
            calls=[]
            def transport(req):
                calls.append(1)
                raise TimeoutError("unresolved provider charge")
            with self.assertRaises(HarnessStop):
                q25_once(b,q,transport=transport)
            status=json.loads((q/RUN_NAME/"01-q25-evidence.json").read_bytes())
            self.assertEqual(status["status"],"STOP_UNKNOWN_OR_INVALID")
            self.assertFalse(status["automatic_retry"])
            self.assertEqual(calls,[1])

    def test_corrupt_original_master_byte_denied(self):
        with TemporaryDirectory() as td:
            root,_=fixture(td)
            (root/"master"/MASTER_DIR/"ENGLISH_MASTER.txt").write_text("fabricated")
            with self.assertRaises(HarnessStop):
                load_b04_bundle(".",root/"producer",root/"quality",root/"master")

if __name__=="__main__":
    unittest.main()
