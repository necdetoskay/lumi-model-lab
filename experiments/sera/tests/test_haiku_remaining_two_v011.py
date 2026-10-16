"""Offline-only Haiku tasks 002/003 continuation contract regression."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import ModuleType
from unittest.mock import patch
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.tests.test_mara_s1_haiku_probes_v011 import evidence
from experiments.sera.haiku_remaining_two_v011 import run,preflight,MODEL

def fake_source():
    return {"task_id":"task_001",
            "historical_provider_response_id":"synthetic-historical",
            "historical_provider_reported_cost":0.001252,
            "model_calls_during_recovery":0,
            "canonical_commit_authorized":False}

def fake_preflight_module():
    m=ModuleType("src.openrouter_preflight")
    m.fetch_key_status=lambda _:{"fake":True}
    m.enforce_key_access=lambda _,min_remaining:None
    return m

def reply(task_id,cost=0.001):
    quote="added" if task_id=="task_002" else "pocket watch open"
    raw={
        "verdict":"DOCUMENT_WRITE" if task_id=="task_002" else "STATE_OBSERVATION",
        "operation_kind":"WRITE" if task_id=="task_002" else "OBSERVE",
        "effect":"DOCUMENT" if task_id=="task_002" else "OBJECT",
        "evidence_quote":quote,
        "reason":"Synthetic source-backed proposed meaning, not gold",
    }
    wrapped=chr(96)*3+"json\n"+json.dumps(raw)+"\n"+chr(96)*3
    return {"error":None,"raw":{
        "id":"fake-"+task_id,"model":MODEL,
        "usage":{"cost":cost},
        "choices":[{"finish_reason":"stop","message":{"content":wrapped}}],
    }}

class HaikuTwoRemainingTests(unittest.TestCase):
    def test_does_not_repeat_paid_first_task_and_no_world_writes(self):
        with TemporaryDirectory() as td:
            with patch("experiments.sera.haiku_remaining_two_v011.preflight",
                       return_value=fake_source()),patch.dict(sys.modules,{
                           "src.openrouter_preflight":fake_preflight_module()
                       }),patch(
                "experiments.sera.haiku_remaining_two_v011.one_provider_call",
                side_effect=[reply("task_002"),reply("task_003")]
            ) as calls:
                out=run(audit=evidence(),original_task={},original_manifest={},
                        output_dir=Path(td)/"out",launch_id="synthetic",key="fake")
                self.assertEqual(calls.call_count,2)
                for call in calls.call_args_list:
                    self.assertEqual(call.kwargs["model"],MODEL)
                    req=call.kwargs["prepared"]["request"]
                    self.assertNotIn("max_tokens",json.dumps(req))
                    self.assertEqual(req["response_format"],{"type":"json_object"})
            self.assertEqual(out["status"],
                             "ALL_3_ADVISORY_TASKS_SOURCE_BOUND_SEMANTIC_HOLD")
            self.assertEqual(out["new_provider_calls"],2)
            self.assertEqual(out["completed_tasks"],
                             ["task_001","task_002","task_003"])
            self.assertEqual(out["pending_tasks"],[])
            self.assertEqual(out["new_provider_reported_cost_usd"],0.002)
            self.assertFalse(out["model_output_token_cap_configured"])
            self.assertFalse(out["canonical_commit_authorized"])
            self.assertEqual(out["world_db_writes"],0)
            self.assertEqual(json.loads(
                (Path(td)/"out"/"task_002.json").read_text()
            )["recovered_advisory"]["bound_advisory"]
                ["verdict_model_proposed"],"DOCUMENT_WRITE")

    def test_provider_invalid_output_fails_once_and_preserves_raw_response(self):
        invalid={"error":None,"raw":{
            "id":"fake","model":MODEL,"usage":{"cost":0.0009},
            "choices":[{"finish_reason":"stop",
                        "message":{"content":"freeform response"}}],
        }}
        with TemporaryDirectory() as td:
            root=Path(td)/"out"
            with patch("experiments.sera.haiku_remaining_two_v011.preflight",
                       return_value=fake_source()),patch.dict(sys.modules,{
                           "src.openrouter_preflight":fake_preflight_module()
                       }),patch(
                "experiments.sera.haiku_remaining_two_v011.one_provider_call",
                return_value=invalid
            ) as calls:
                out=run(audit=evidence(),original_task={},original_manifest={},
                        output_dir=root,launch_id="synthetic-error",key="fake")
                calls.assert_called_once()
            self.assertEqual(out["status"],"INCOMPLETE_TARGETED_REVIEW_HOLD")
            self.assertEqual(out["new_provider_calls"],1)
            self.assertIn("PROBE_UNSAFE_NONJSON_ENVELOPE",out["error_code"])
            self.assertEqual(out["pending_tasks"],["task_002","task_003"])
            recorded=json.loads((root/"task_002.json").read_text())
            self.assertEqual(recorded["raw_content"],"freeform response")

    def test_missing_key_no_external_call(self):
        with TemporaryDirectory() as td:
            with patch("experiments.sera.haiku_remaining_two_v011.preflight",
                       return_value=fake_source()):
                out=run(audit=evidence(),original_task={},original_manifest={},
                        output_dir=Path(td)/"out",launch_id="no-key",key="")
            self.assertEqual(out["new_provider_calls"],0)
            self.assertEqual(out["error_code"],"V0111_PROVIDER_KEY_MISSING")

    def test_existing_evidence_path_must_not_be_overwritten(self):
        with TemporaryDirectory() as td:
            path=Path(td)/"existing"
            path.mkdir()
            with patch("experiments.sera.haiku_remaining_two_v011.preflight",
                       return_value=fake_source()):
                with self.assertRaisesRegex(CoverageError,"V0111_OUTPUT_EXISTS"):
                    run(audit=evidence(),original_task={},original_manifest={},
                        output_dir=path,launch_id="existing",key="")

if __name__=="__main__":
    unittest.main()
