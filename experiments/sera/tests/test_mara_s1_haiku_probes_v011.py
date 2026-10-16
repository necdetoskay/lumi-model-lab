"""SERA v0.11 Haiku second-opinion runner contract tests; synthetic only."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType
from unittest.mock import patch
import json
import sys
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_v04_audit import EXPECTED_SHA
from experiments.sera.mara_s1_haiku_probes_v011 import (
    run,qualify_source,MODEL,MAX_PROVIDER_ATTEMPTS,
)


def evidence():
    kinds=[
        ("MOVE_KIND_EFFECT_MISMATCH:s014","Mara turned to the clock.",
         "Was this relocation or attention?"),
        ("DOCUMENT_APPEND_MISREAD_AS_SPEECH:s021",
         "She paused then added, “Discrepancy unknown.”",
         "Was this writing or speaking?"),
        ("OPENABLE_BEFORE_CLOSE_NEEDS_TYPED_ASPECT:s004",
         "Vane held his pocket watch open. Vane closed the case.",
         "Was the watch case open before closing?"),
    ]
    return {
        "schema":"sera.semantic-risk-audit.v0.11",
        "source_prose_sha256":EXPECTED_SHA,
        "candidate_event_count":25,
        "targeted_task_count":3,
        "automatic_state_writes":0,
        "canonical_commit_authorized":False,
        "targeted_tasks":[{
            "task_id":f"task_{i+1:03d}",
            "finding_code":name,
            "independent_review_question":question,
            "exact_source_context":[{
                "sentence_id":f"s{i+1:03d}",
                "start":0,"end":len(text),"quote":text
            }],
        } for i,(name,text,question) in enumerate(kinds)],
    }


def stub():
    m=ModuleType("src.openrouter_preflight")
    m.fetch_key_status=lambda k:{"synthetic":True}
    m.enforce_key_access=lambda x,min_remaining:None
    return m


def provider_result(i):
    text=evidence()["targeted_tasks"][i]["exact_source_context"][0]["quote"]
    quote="turned" if i==0 else "added" if i==1 else "pocket watch open"
    assert quote in text
    raw={
        "verdict":"UNCERTAIN" if i!=1 else "DOCUMENT_WRITE",
        "operation_kind":"UNMAPPED" if i!=1 else "WRITE",
        "effect":"UNKNOWN" if i!=1 else "DOCUMENT",
        "evidence_quote":quote,
        "reason":"Synthetic provisional Haiku candidate",
    }
    return {"error":None,"raw":{
        "id":f"synthetic-haiku-{i}",
        "model":MODEL,
        "usage":{"cost":0.0015},
        "choices":[{
            "finish_reason":"stop",
            "message":{"content":json.dumps(raw)},
        }],
    }}


class HaikuProbeV011Tests(unittest.TestCase):
    def test_source_requires_specific_three_disagreements_not_gold(self):
        s=qualify_source(evidence())
        self.assertEqual(s["targeted_task_count"],3)
        s["candidate_event_count"]=24
        with self.assertRaisesRegex(CoverageError,"V011_PROBE_SOURCE_NOT_PINNED"):
            qualify_source(s)

    def test_three_independent_probes_bind_without_truth_approval(self):
        with TemporaryDirectory() as d:
            root=Path(d)/"new"
            with patch.dict(sys.modules,{
                "src.openrouter_preflight":stub(),
            }),patch(
                "experiments.sera.mara_s1_haiku_probes_v011.one_provider_call",
                side_effect=[provider_result(i) for i in range(3)],
            ) as caller:
                out=run(evidence=evidence(),output_dir=root,
                        launch_id="synthetic-three",key="synthetic")
                self.assertEqual(caller.call_count,3)
                for call in caller.call_args_list:
                    self.assertEqual(call.kwargs["model"],MODEL)
                    self.assertEqual(call.kwargs["prepared"]["request"]
                                     ["response_format"],{"type":"json_object"})
                    self.assertNotIn("max_tokens",str(call.kwargs["prepared"]))
            self.assertEqual(out["provider_attempts"],3)
            self.assertEqual(out["provider_reported_cost_usd"],0.0045)
            self.assertEqual(out["status"],
                             "ALL_TARGETED_PROBES_RETURNED_SEMANTIC_HOLD")
            self.assertEqual(out["pending_task_ids"],[])
            self.assertFalse(out["canonical_commit_authorized"])
            self.assertEqual(out["world_db_writes"],0)
            saved=json.loads((root/"task_002.json").read_text())
            self.assertEqual(saved["bound_advisory_result"]
                             ["verdict_model_proposed"],"DOCUMENT_WRITE")
            self.assertEqual(saved["bound_advisory_result"]
                             ["status"],"HOLD_MODEL_RESPONSE_NOT_AUTHORITY")

    def test_http_400_stops_and_keeps_first_request_diagnostics(self):
        with TemporaryDirectory() as d:
            root=Path(d)/"bad"
            with patch.dict(sys.modules,{
                "src.openrouter_preflight":stub(),
            }),patch(
                "experiments.sera.mara_s1_haiku_probes_v011.one_provider_call",
                return_value={
                    "error":"HTTP_400","raw":None,
                    "provider_detail":"invalid request",
                },
            ) as caller:
                out=run(evidence=evidence(),output_dir=root,
                        launch_id="synthetic-400",key="fake")
                caller.assert_called_once()
            self.assertEqual(out["provider_attempts"],1)
            self.assertEqual(out["status"],"PROBE_ERROR_OR_INCOMPLETE_HOLD")
            self.assertEqual(len(out["pending_task_ids"]),3)
            self.assertIn("HTTP_400",out["error_code"])
            first=json.loads((root/"task_001.json").read_text())
            self.assertEqual(first["status"],"PROVIDER_ERROR_HOLD")

    def test_key_not_configured_does_not_call_provider(self):
        with TemporaryDirectory() as d:
            out=run(evidence=evidence(),output_dir=Path(d)/"run",
                    launch_id="no-key",key="")
            self.assertEqual(out["provider_attempts"],0)
            self.assertEqual(out["error_code"],"V011_KEY_MISSING")
            self.assertFalse(out["canonical_commit_authorized"])

    def test_existing_output_dir_refused(self):
        with TemporaryDirectory() as d:
            root=Path(d)/"exists"
            root.mkdir()
            with self.assertRaisesRegex(CoverageError,"V011_OUTPUT_EXISTS"):
                run(evidence=evidence(),output_dir=root,
                    launch_id="duplicate",key="fake")


if __name__=="__main__":
    unittest.main()
