"""Mock-only full Story Harness pipeline, all ten registered ages/cases.

Mocks deliberately do not establish real story quality or provider billing.
"""
import json
from pathlib import Path
import tempfile
import unittest

from src.story_harness_runtime_v1 import create_harness
from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p416_input_bridge import compile_case, sha
from src.story_harness_p417_live_pilot import MODEL
from src.story_harness_cohort_pipeline_v1 import (
    run_one_case_with_injected_transport, ProviderCostUnknown
)

class MockProvider:
    def __init__(self, case_id, *, reject=False):
        self.case = next(c for c in load_plan()["cases"] if c["id"] == case_id)
        self.pack = compile_case(self.case)
        self.beats = []
        self.spine = {}
        self.rejected = reject
        self.calls = []
    def __call__(self, body):
        self.calls.append(body["response_format"]["json_schema"]["name"])
        kind = self.calls[-1]
        if "spineforge_flat" in kind:
            locs = self.pack["canonical_state"]["locations"]
            beats = [
                {"id": f"BEAT_{i+1:02d}",
                 "location": locs[0] if i < 2 else locs[1],
                 "goal": f"The protagonist advances the quest at moment {i}.",
                 "choice": f"The protagonist makes a courageous new choice {i}.",
                 "consequence": f"That choice produces a significant consequence {i}.",
                 "obligation_reference": self.pack["open_obligations"][0] if i == 3 else None}
                for i in range(4)
            ]
            self.spine = {
                "source_pack_sha256": self.pack["pack_sha256"],
                "spine_summary": "An original story with emotional growth and choices.",
                "beats": beats
            }
            content = {"source_pack_sha256": self.pack["pack_sha256"],
                       "spine_summary": self.spine["spine_summary"],
                       "beats_json": json.dumps(beats)}
        elif "writer_flat" in kind:
            n = self.pack["word_targets"]["min"] + 8
            story = " ".join(["The"] * n)
            self.story = story
            content = {"source_pack_sha256": self.pack["pack_sha256"],
                       "spine_sha256": sha(self.spine),
                       "story_text": story,
                       "beat_ids_json": json.dumps([b["id"] for b in self.spine["beats"]])}
        elif "initial_audit" in kind:
            payload = json.loads(body["messages"][1]["content"])
            content = {
                "story_sha256": payload["story_sha256"],
                "spine_sha256": payload["approved_spine_sha256"],
                "verdict": "REJECT" if self.rejected else "ACCEPT",
                "reader_score": 3 if self.rejected else 5,
                "blocking_findings_json": json.dumps([{
                    "family": "narrative", "quote": "The The",
                    "reason": "Mock prose does not contain real literary scenes."
                }] if self.rejected else []),
                "advisories_json": "[]",
                "rationale": "Synthetic shape test only, not independent literary evaluation."
            }
        elif "q25_evidence" in kind:
            payload = json.loads(body["messages"][1]["content"])
            canon = self.pack["canonical_state"]
            story = payload["English_Master_Text"]
            observations = {
                "final_location": {
                    "location_id": canon["protagonist"]["location"],
                    "quote": story[-50:]
                },
                "discovered_locations": [],
                "object_observations": [],
                "open_obligation_outcomes": [
                    {"obligation": x, "status": "UNPROVEN",
                     "quote": story[:50]} for x in canon["open_obligations"]
                ],
                "unknown_facts_retained": canon["unknown_facts"],
                "world_time_delta": None
            }
            content = {
                "source_pack_sha256": payload["source_pack_sha256"],
                "spine_sha256": payload["spine_sha256"],
                "story_sha256": payload["story_sha256"],
                "evidence_json": json.dumps(observations),
                "explanation": "Synthetic read-only evidence, not a real model result."
            }
        else:
            raise AssertionError("Unexpected mock model stage " + kind)
        return {
            "id": "gen-MockOnlyNoProvider123",
            "model": MODEL, "usage": {
                "prompt_tokens": 100, "completion_tokens": 100, "cost": 0.01},
            "choices": [{"finish_reason": "stop", "message": {
                "content": json.dumps(content)}}]
        }

class UnifiedPipelineTests(unittest.TestCase):
    def test_all_ten_use_one_common_adapter_without_real_provider(self):
        with tempfile.TemporaryDirectory() as td:
            for i in range(1, 11):
                case = f"B{i:02d}"
                mock = MockProvider(case)
                r = run_one_case_with_injected_transport(".", case, td,
                                                         transport=mock, harness=create_harness(".", case))
                self.assertEqual(r["case_id"], case)
                self.assertEqual(r["status"], "ACCEPT_CLAIMED",
                                 "Mock only; no certified acceptance")
                self.assertEqual(r["model_call_envelopes_observed"], 4)
                self.assertFalse(r["independent_quality_certified_for_release"])
                self.assertFalse(r["transport_origin_independently_attested"])
                self.assertFalse(r["production_change"])
                folder = Path(td)/case
                self.assertTrue((folder/"ENGLISH_MASTER.txt").exists())
                self.assertTrue((folder/"07-final-state-draft.json").exists())
                with self.assertRaises(FileExistsError):
                    run_one_case_with_injected_transport(".", case, td,
                                                         transport=mock,
                                                         harness=create_harness(".", case))
                self.assertEqual(len(mock.calls), 4)

    def test_reject_does_not_call_q25_and_does_not_retry(self):
        with tempfile.TemporaryDirectory() as td:
            mock = MockProvider("B01", reject=True)
            r = run_one_case_with_injected_transport(".", "B01", td,
                                                     transport=mock,
                                                     harness=create_harness(".", "B01"))
            self.assertEqual(r["status"], "REJECT")
            self.assertEqual(len(mock.calls), 3)
            self.assertFalse((Path(td)/"B01"/"05-q25-intent.json").exists())

    def test_provider_unknown_billing_is_global_stop(self):
        with tempfile.TemporaryDirectory() as td:
            def fail(body):
                raise TimeoutError("Transport may already be billed")
            with self.assertRaises(ProviderCostUnknown):
                run_one_case_with_injected_transport(".", "B02", td,
                                                     transport=fail, harness=create_harness(".", "B02"))

    def test_bad_writer_is_recorded_without_a_second_attempt(self):
        with tempfile.TemporaryDirectory() as td:
            mock = MockProvider("B01")
            def broken_writer(body):
                reply = mock(body)
                if "writer_flat" in mock.calls[-1]:
                    reply["choices"][0]["message"]["content"] = "{}"
                return reply
            r = run_one_case_with_injected_transport(".", "B01", td,
                                                     transport=broken_writer, harness=create_harness(".", "B01"))
            self.assertEqual(r["status"], "OPERATIONAL_STOP")
            self.assertEqual(len(mock.calls), 2)
            self.assertEqual(r["automatic_retries"], 0)
