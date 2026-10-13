"""P4.24 evidence-only Q25 provider contract tests. Zero real model requests."""
import json
import hashlib
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.story_harness_p424_q25_evidence import (
    SCHEMA, COST_CAP, extraction_wire, verify_candidate,
    verify_model_response, extract_once,
)
from src.story_harness_p417_live_pilot import MODEL
from src.story_harness_v1 import HarnessStop
from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p416_input_bridge import compile_case, sha


def example_bundle():
    case=next(c for c in load_plan(".")["cases"] if c["id"]=="B01")
    pack=compile_case(case)
    prose=(
       "Little Mira sat by the window in her cozy HOME. "
       "She saw a shining stone but she did not know its owner. "
       "Mira walked carefully into the MEADOW for the first time. "
       "The stone did not wake by itself. She warmed the stone with her hands. "
       "Then the stone glowed because Mira hummed. "
       "Mira brought a little star back to the window. "
       "Then Mira went inside her cozy HOME. The star stayed at the window."
    )
    beats=[{
        "id":f"BEAT_{i+1:02d}",
        "location":("HOME" if i in (0,3) else "MEADOW"),
        "goal":f"Mira's established objective with the stone at beat {i}.",
        "choice":f"Mira chooses a kind concrete action at beat {i}.",
        "consequence":f"Consequence persists after her choice at beat {i}.",
        "obligation_reference":pack["open_obligations"][i] if i<2 else None,
    } for i in range(4)]
    spine={"source_pack_sha256":pack["pack_sha256"],
           "spine_summary":"A little star gets help finding its window.",
           "beats":beats}
    storyhash=hashlib.sha256(prose.encode()).hexdigest()
    return {
        "source":{
           "pack":pack,
           "spine":{"spine":spine,"spine_sha256":sha(spine)},
           "story":{"story_text":prose,"story_sha256":storyhash},
        },
        "english_master_text":prose,
    }


def candidate(bundle):
    pack=bundle["source"]["pack"]
    return {
        "source_pack_sha256":pack["pack_sha256"],
        "spine_sha256":bundle["source"]["spine"]["spine_sha256"],
        "story_sha256":bundle["source"]["story"]["story_sha256"],
        "evidence_json":json.dumps({
            "final_location":{"location_id":"HOME",
                              "quote":"Then Mira went inside her cozy HOME."},
            "discovered_locations":[{"location_id":"MEADOW",
                   "quote":"Mira walked carefully into the MEADOW for the first time."}],
            "object_observations":[{"object_name":"stone",
                    "last_seen_relation":"HELD_BY_PROTAGONIST",
                    "ownership":"UNKNOWN",
                    "quote":"She warmed the stone with her hands."}],
            "open_obligation_outcomes":[
                {"obligation":pack["open_obligations"][0],
                 "status":"SATISFIED",
                 "quote":"Little Mira sat by the window in her cozy HOME."},
                {"obligation":pack["open_obligations"][1],
                 "status":"SATISFIED",
                 "quote":"The stone did not wake by itself."},
            ],
            "unknown_facts_retained":pack["unknown_facts"],
            "world_time_delta":None,
        }),
        "explanation":"Source-anchored observational proposal with unknown ownership.",
    }


def response(bundle):
    return {
        "id":"gen-P424MOCK12345","model":MODEL,
        "usage":{"prompt_tokens":2500,"completion_tokens":1100,"cost":0.019},
        "choices":[{"finish_reason":"stop","message":{
            "content":json.dumps(candidate(bundle))}}],
    }


class P424Tests(unittest.TestCase):
    def setUp(self):
        self.bundle=example_bundle()

    def test_provider_wire_makes_separate_source_bound_q25_evidence_only(self):
        body=extraction_wire(self.bundle)
        self.assertEqual(body["model"],MODEL)
        self.assertEqual(body["provider"]["only"],["Anthropic"])
        self.assertFalse(body["provider"]["allow_fallbacks"])
        self.assertEqual(body["usage"],{"include":True})
        self.assertTrue(body["response_format"]["json_schema"]["strict"])
        self.assertEqual(set(body["response_format"]["json_schema"]["schema"]["properties"]),
             {"source_pack_sha256","story_sha256","spine_sha256",
              "evidence_json","explanation"})
        self.assertNotIn("temperature",body)
        payload=json.loads(body["messages"][1]["content"])
        self.assertEqual(payload["English_Master_Text"],
                         self.bundle["english_master_text"])
        self.assertEqual(payload["original_canonical_state"],
                         self.bundle["source"]["pack"]["canonical_state"])

    def test_valid_candidate_only_proposal_not_committed(self):
        obs=verify_candidate(self.bundle,candidate(self.bundle))
        self.assertEqual(obs["final_location"]["location_id"],"HOME")
        self.assertEqual(obs["object_observations"][0]["ownership"],"UNKNOWN")
        result=verify_model_response(self.bundle,response(self.bundle))
        self.assertTrue(result["quote_matching_verified"])
        self.assertFalse(result["semantic_state_fully_certified"])
        self.assertFalse(result["production_state_write_authorized"])
        self.assertFalse(result["final_story_state_committed"])
        self.assertEqual(result["provider_reported_cost_usd"],"0.019")

    def test_cross_story_or_spine_hash_denied(self):
        for field in ("source_pack_sha256","story_sha256","spine_sha256"):
            ans=candidate(self.bundle)
            ans[field]="0"*64
            with self.subTest(field=field),self.assertRaises(HarnessStop):
                verify_candidate(self.bundle,ans)

    def test_hallucinated_final_location_or_quote_denied(self):
        for location,quote in (
            ("UNKNOWN_PLACE","Then Mira went inside her cozy HOME."),
            ("HOME","Never occurred in this story."),
            ("HOME","Little Mira sat by the window in her cozy HOME."),
        ):
            c=candidate(self.bundle)
            x=json.loads(c["evidence_json"])
            x["final_location"]={"location_id":location,"quote":quote}
            c["evidence_json"]=json.dumps(x)
            with self.subTest(location=location,quote=quote),self.assertRaises(HarnessStop):
                verify_candidate(self.bundle,c)

    def test_canon_unknown_owner_must_remain_unknown(self):
        c=candidate(self.bundle)
        x=json.loads(c["evidence_json"])
        x["object_observations"][0]["ownership"]="Mira"
        c["evidence_json"]=json.dumps(x)
        with self.assertRaises(HarnessStop):
            verify_candidate(self.bundle,c)

    def test_unknown_facts_and_unmeasured_world_time_preserved(self):
        for changed in (lambda x:x.update(unknown_facts_retained=[]),
                        lambda x:x.update(world_time_delta=3)):
            c=candidate(self.bundle)
            x=json.loads(c["evidence_json"])
            changed(x)
            c["evidence_json"]=json.dumps(x)
            with self.assertRaises(HarnessStop):
                verify_candidate(self.bundle,c)

    def test_obligation_duplicate_or_missing_not_admitted(self):
        for alter in ("missing","duplicate","invented"):
            c=candidate(self.bundle)
            x=json.loads(c["evidence_json"])
            q=x["open_obligation_outcomes"]
            if alter=="missing":q.pop()
            elif alter=="duplicate":q[1]["obligation"]=q[0]["obligation"]
            else:q[0]["obligation"]="Unexpected canonical obligation"
            c["evidence_json"]=json.dumps(x)
            with self.subTest(alter=alter),self.assertRaises(HarnessStop):
                verify_candidate(self.bundle,c)

    def test_unproven_is_allowed_but_does_not_invent_fulfilled(self):
        c=candidate(self.bundle)
        x=json.loads(c["evidence_json"])
        x["open_obligation_outcomes"][1]["status"]="UNPROVEN"
        c["evidence_json"]=json.dumps(x)
        self.assertEqual(verify_candidate(self.bundle,c)
                         ["open_obligation_outcomes"][1]["status"],"UNPROVEN")

    def test_new_location_must_be_canonical_and_explicitly_discovered(self):
        for bad in ("HOME","SECRET_CAVE"):
            c=candidate(self.bundle)
            x=json.loads(c["evidence_json"])
            x["discovered_locations"][0]["location_id"]=bad
            c["evidence_json"]=json.dumps(x)
            with self.subTest(bad=bad),self.assertRaises(HarnessStop):
                verify_candidate(self.bundle,c)

    def test_named_objects_must_appear_in_quote(self):
        c=candidate(self.bundle)
        x=json.loads(c["evidence_json"])
        x["object_observations"][0]["object_name"]="phantom atlas"
        c["evidence_json"]=json.dumps(x)
        with self.assertRaises(HarnessStop):
            verify_candidate(self.bundle,c)

    def test_invalid_usage_model_and_truncation_fail_closed(self):
        for change in ("over","missing","wrong_model","length"):
            r=response(self.bundle)
            if change=="over":r["usage"]["cost"]="0.051"
            elif change=="missing":r["usage"].pop("cost")
            elif change=="wrong_model":r["model"]="wrong"
            else:r["choices"][0]["finish_reason"]="length"
            with self.subTest(change=change),self.assertRaises(HarnessStop):
                verify_model_response(self.bundle,r)

    def test_one_shot_persists_exact_source_and_no_replay(self):
        with TemporaryDirectory() as td:
            calls=[]
            def fn(body):
                calls.append(1)
                return response(self.bundle)
            out=extract_once(self.bundle,td,transport=fn)
            self.assertEqual(out["story_sha256"],
                             self.bundle["source"]["story"]["story_sha256"])
            self.assertEqual(len(calls),1)
            with self.assertRaises(FileExistsError):
                extract_once(self.bundle,td,transport=fn)
            self.assertEqual(len(calls),1)
            receipt=json.loads(next(Path(td).glob("*/01-q25-proposal.json")).read_text())
            self.assertFalse(receipt["final_story_state_committed"])

    def test_unknown_provider_execution_consumes_without_retry(self):
        with TemporaryDirectory() as td:
            calls=[]
            def transport(body):
                calls.append(1)
                raise TimeoutError("Ambiguous provider billing")
            with self.assertRaises(HarnessStop):
                extract_once(self.bundle,td,transport=transport)
            self.assertEqual(calls,[1])
            result=json.loads(next(Path(td).glob("*/01-q25-proposal.json")).read_text())
            self.assertEqual(result["status"],"STOP_UNKNOWN_OR_INVALID")
            self.assertIsNone(result["billed_cost_usd"])

if __name__=="__main__":
    unittest.main()
