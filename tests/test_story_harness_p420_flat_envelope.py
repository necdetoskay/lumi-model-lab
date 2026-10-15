"""P4.20: flat provider-compatible envelope retains immutable local acceptance."""
from __future__ import annotations
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p416_input_bridge import (
    compile_case, build_spine_request, approve_spine_for_writer,
    build_writer_request, sha)
from src.story_harness_p417_live_pilot import (
    BoundedOncePilot, MODEL, wire)
from src.story_harness_v1 import HarnessStop

ROOT=Path(__file__).resolve().parents[1]

def valid_beats(pack):
    return [{
        "id":f"BEAT_{i+1:02d}",
        "location":pack["canonical_state"]["locations"][0 if i<2 else 1],
        "goal":f"The character seeks the truth during event number {i}.",
        "choice":f"The character makes an independent moral decision at step {i}.",
        "consequence":f"The world visibly changes as a consequence of step {i}.",
        "obligation_reference":pack["open_obligations"][0] if i==3 else None,
    } for i in range(4)]

def fake_story():
    return "Mira studied the little glowing stone and chose to ask her friend for help. "*25

class P420Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=load_plan(ROOT)
        cls.pack=compile_case(cls.plan["cases"][0])

    def test_flat_spine_has_no_nested_union_enum_or_array(self):
        req=wire("SPINEFORGE",build_spine_request(self.pack),
                 simple_envelope=True)
        schema=req["response_format"]["json_schema"]["schema"]
        self.assertEqual(set(schema["properties"]),{
            "source_pack_sha256","spine_summary","beats_json"})
        self.assertTrue(all(v["type"]=="string" for v in schema["properties"].values()))
        self.assertIn("flat_v2",req["response_format"]["json_schema"]["name"])
        self.assertNotIn("minItems",json.dumps(schema))
        self.assertNotIn("enum",json.dumps(schema))
        self.assertEqual(req["provider"]["only"],["Anthropic"])
        self.assertFalse(req["provider"]["allow_fallbacks"])
        self.assertIn("beats_json",req["messages"][0]["content"])

    def test_flat_writer_has_no_nested_arrays_and_contains_exact_source(self):
        prepared=approve_spine_for_writer(self.pack,{
            "source_pack_sha256":self.pack["pack_sha256"],
            "beats":valid_beats(self.pack),
            "spine_summary":"A young heroine makes a personal choice.",
        })
        req=wire("WRITER",build_writer_request(self.pack,prepared),
                 simple_envelope=True)
        schema=req["response_format"]["json_schema"]["schema"]
        self.assertEqual(set(schema["properties"]),{
            "source_pack_sha256","spine_sha256","story_text","beat_ids_json"})
        self.assertTrue(all(x["type"]=="string" for x in schema["properties"].values()))
        self.assertIn("beat_ids_json",req["messages"][0]["content"])
        self.assertEqual(req["model"],MODEL)

    def test_real_engine_accepts_fake_envelopes_but_marks_quality_false(self):
        with TemporaryDirectory() as td:
            runner=BoundedOncePilot(td,case_id="B01",plan=self.plan,
                                    run_variant="r04")
            beats=valid_beats(self.pack)
            spine={
                "source_pack_sha256":self.pack["pack_sha256"],
                "beats":beats,
                "spine_summary":"A young heroine makes a personal choice.",
            }
            calls=[]
            def response(body):
                calls.append(body)
                stage=body["response_format"]["json_schema"]["name"]
                if "spineforge" in stage:
                    value={
                        "source_pack_sha256":self.pack["pack_sha256"],
                        "spine_summary":spine["spine_summary"],
                        "beats_json":json.dumps(beats,ensure_ascii=False),
                    }
                else:
                    value={
                        "source_pack_sha256":self.pack["pack_sha256"],
                        "spine_sha256":sha(spine),
                        "story_text":fake_story(),
                        "beat_ids_json":json.dumps([b["id"] for b in beats]),
                    }
                return {
                    "model":MODEL,"id":"gen-FAKEUNITPROBE1234",
                    "usage":{"prompt_tokens":1000,"completion_tokens":400,
                             "cost":0.005},
                    "choices":[{"finish_reason":"stop",
                                "message":{"content":json.dumps(value)}}],
                }
            out=runner.execute(transport=response)
            self.assertEqual(len(calls),2)
            self.assertEqual(out["two_stage_cost_usd"],"0.010")
            self.assertTrue((runner.dir/"story-draft.json").exists())
            self.assertFalse(out["quality_accepted"])
            self.assertFalse(out["english_master_authorized"])
            self.assertFalse(out["q25_authorized"])

    def test_bad_flat_spine_beats_still_rejected_and_consumed(self):
        with TemporaryDirectory() as td:
            runner=BoundedOncePilot(td,case_id="B01",plan=self.plan,
                                    run_variant="r04")
            calls=[]
            def response(body):
                calls.append(1)
                return {
                    "model":MODEL,
                    "usage":{"prompt_tokens":1000,"completion_tokens":400,
                             "cost":0.004},
                    "choices":[{"finish_reason":"stop","message":{
                        "content":json.dumps({
                            "source_pack_sha256":self.pack["pack_sha256"],
                            "spine_summary":"Correct structure but bad world.",
                            "beats_json":json.dumps(valid_beats(self.pack)[:3]),
                        })}}],
                }
            with self.assertRaises(HarnessStop):
                runner.execute(transport=response)
            self.assertEqual(len(calls),1)
            self.assertFalse((runner.dir/"story-draft.json").exists())
            self.assertEqual(
                json.loads((runner.dir/"01-spineforge-receipt.json").read_text())
                    ["provider_reported_cost_usd"],"0.004")

    def test_cross_source_writer_envelope_never_accepted(self):
        with TemporaryDirectory() as td:
            runner=BoundedOncePilot(td,case_id="B01",plan=self.plan,
                                    run_variant="r04")
            beats=valid_beats(self.pack)
            calls=[]
            def response(body):
                calls.append(1)
                if len(calls)==1:
                    data={"source_pack_sha256":self.pack["pack_sha256"],
                          "spine_summary":"A real story from a heroine.",
                          "beats_json":json.dumps(beats)}
                else:
                    data={"source_pack_sha256":"f"*64,
                          "spine_sha256":"c"*64,
                          "story_text":fake_story(),
                          "beat_ids_json":json.dumps([b["id"] for b in beats])}
                return {"model":MODEL,
                        "usage":{"prompt_tokens":900,"completion_tokens":350,
                                 "cost":0.003},
                        "choices":[{"finish_reason":"stop",
                                    "message":{"content":json.dumps(data)}}]}
            with self.assertRaises(HarnessStop):
                runner.execute(transport=response)
            self.assertEqual(len(calls),2)
            self.assertFalse((runner.dir/"story-draft.json").exists())
            self.assertEqual(json.loads(
                (runner.dir/"02-writer-receipt.json").read_text())
                ["provider_reported_cost_usd"],"0.003")

if __name__=="__main__":
    unittest.main()
