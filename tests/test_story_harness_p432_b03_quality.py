"""P4.32 B03 age10 independent audit contract; mocked quality isn't success."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json,unittest

from src.story_harness_p431_b03_age10 import SOURCE_SHA
from src.story_harness_p432_b03_quality import (
    SPINE_SHA,STORY_SHA,FILES,EVIDENCE_DIR,
    get_original_B03,inspect_B03_audit,audit_B03_once,status
)
from src.story_harness_p417_live_pilot import MODEL
from src.story_harness_p422_independent_audit import verify_auditor_reply
from src.story_harness_v1 import HarnessStop


def source_copy(root):
    f=Path(root)/("b03-"+SOURCE_SHA[:16]+"-r06")
    f.mkdir(parents=True)
    for src,dest in FILES.items():
        (f/src).write_bytes((Path(".")/EVIDENCE_DIR/dest).read_bytes())


def mock_audit(source, verdict="ACCEPT", score=4, blockers=()):
    data={
       "story_sha256":source["story"]["story_sha256"],
       "spine_sha256":source["spine"]["spine_sha256"],
       "verdict":verdict,"reader_score":score,
       "blocking_findings_json":json.dumps(list(blockers)),
       "advisories_json":"[]",
       "rationale":"Separate critical literary and continuity review for age ten.",
    }
    return {"id":"gen-MOCKB03QUALITY123456","model":MODEL,
            "usage":{"cost":"0.028","prompt_tokens":4500,"completion_tokens":1250},
            "choices":[{"finish_reason":"stop","message":{"content":json.dumps(data)}}]}


class P432Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=TemporaryDirectory()
        source_copy(cls.t.name)
        cls.source=get_original_B03(".",cls.t.name)

    @classmethod
    def tearDownClass(cls):
        cls.t.cleanup()

    def test_original_real_age10_still_source_byte_sealed(self):
        s=self.source
        self.assertEqual(s["case_id"],"B03")
        self.assertEqual(s["story"]["story_sha256"],STORY_SHA)
        self.assertEqual(s["spine"]["spine_sha256"],SPINE_SHA)
        self.assertEqual(s["story"]["word_count"],1300)
        self.assertEqual(s["pack"]["reader_age"],10)
        self.assertEqual(s["generation_cost_usd"],"0.067720")
        self.assertEqual(len(s["spine"]["spine"]["beats"]),6)

    def test_wire_is_age10_and_checks_all_original_Canon_and_spine(self):
        w=inspect_B03_audit(self.source)
        body=json.loads(w["messages"][1]["content"])
        self.assertEqual(body["case_id"],"B03")
        self.assertEqual(body["reader_age"],10)
        self.assertEqual(body["canonical_state"]["protagonist"]["name"],"Duru")
        self.assertEqual(body["story_sha256"],STORY_SHA)
        self.assertEqual(len(body["approved_spine_beats"]),6)
        self.assertIn("10 years old",w["messages"][0]["content"])
        self.assertEqual(w["response_format"]["json_schema"]["name"],
                         "lumi_b03_independent_initial_audit_v1")

    def test_b03_model_fake_accept_never_promotes_story_state(self):
        with TemporaryDirectory() as td:
            calls=[]
            def reply(body):
                calls.append(1)
                return mock_audit(self.source)
            result=audit_B03_once(self.source,td,transport=reply)
            self.assertEqual(len(calls),1)
            self.assertEqual(result["case_id"],"B03")
            self.assertTrue(result["quality_initial_audit_accepted"])
            self.assertFalse(result["english_master_authorized"])
            self.assertFalse(result["q25_authorized"])
            self.assertFalse(result["state_write_authorized"])
            self.assertFalse(result["full_original_v21_final_audit_completed"])
            with self.assertRaises(FileExistsError):
                audit_B03_once(self.source,td,transport=reply)

    def test_actual_story_quote_may_be_rejected_on_single_river_crossing(self):
        item={"family":"canon",
              "quote":"Going home can wait for another day.",
              "reason":"Could imply another crossing despite the original one-crossing river rule."}
        q=verify_auditor_reply(self.source,mock_audit(
            self.source,verdict="REJECT",score=3,blockers=[item]))
        self.assertEqual(q["quality_initial_verdict"],"REJECT")
        self.assertEqual(q["blocking_findings"][0]["family"],"canon")
        bogus=deepcopy(item)
        bogus["quote"]="Never said in the original story"
        with self.assertRaises(HarnessStop):
            verify_auditor_reply(self.source,mock_audit(
                self.source,verdict="REJECT",score=3,blockers=[bogus]))

    def test_wrong_case_or_provenance_cannot_enter_b03_audit(self):
        for k,val in (("case_id","B02"),("case_id","B01")):
            x=deepcopy(self.source)
            x[k]=val
            with self.assertRaises(HarnessStop):
                inspect_B03_audit(x)
        with TemporaryDirectory() as td:
            source_copy(td)
            f=next(Path(td).glob("b03-*-r06/story-draft.json"))
            p=json.loads(f.read_text())
            p["word_count"]=1301
            f.write_text(json.dumps(p))
            with self.assertRaises(HarnessStop):
                get_original_B03(".",td)

    def test_unknown_timeout_consumes_only_one_quality_attempt(self):
        with TemporaryDirectory() as td:
            calls=[]
            def fail(body):
                calls.append(1)
                raise TimeoutError("unknown charge")
            with self.assertRaises(HarnessStop):
                audit_B03_once(self.source,td,transport=fail)
            self.assertEqual(calls,[1])
            with self.assertRaises(FileExistsError):
                audit_B03_once(self.source,td,transport=fail)

    def test_default_budget_and_quality_not_inherited(self):
        s=status()
        self.assertEqual(s["case_id"],"B03")
        self.assertEqual(s["model_calls"],0)
        self.assertEqual(s["prior_budget_reserved_usd"],"1.449558")
        self.assertEqual(s["max_new_quality_stage_usd"],"0.040")
        self.assertFalse(s["initial_quality_accepted"])


if __name__=="__main__":
    unittest.main()
