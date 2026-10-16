"""One-call Haiku final task runner tests; synthetic and offline."""
from __future__ import annotations

from pathlib import Path
import json
import sys
from tempfile import TemporaryDirectory
from types import ModuleType
from unittest.mock import patch
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.haiku_last_probe_v011 import run,MODEL
from experiments.sera.tests.test_mara_s1_haiku_probes_v011 import evidence

def histories():
    return [
        {"task_id":"task_001","canonical_commit_authorized":False,
         "model_calls_during_recovery":0,
         "historical_provider_response_id":"fake1"},
        {"task_id":"task_002","canonical_commit_authorized":False,
         "model_calls_during_recovery":0,
         "historical_provider_response_id":"fake2"},
    ]

def fake_preflight():
    m=ModuleType("src.openrouter_preflight")
    m.fetch_key_status=lambda key:{"synthetic":True}
    m.enforce_key_access=lambda status,min_remaining:None
    return m

class LastHaikuProbeTests(unittest.TestCase):
    def test_only_task3_called_and_previous_two_reused(self):
        output={
            "verdict":"STATE_OBSERVATION",
            "operation_kind":"OBSERVE","effect":"OBJECT",
            "evidence_quote":"pocket watch open",
            "reason":"A watch described as open prior to later closure",
        }
        response={"error":None,"raw":{
            "id":"fake-last","model":MODEL,
            "usage":{"cost":0.0011},
            "choices":[{"finish_reason":"stop",
                        "message":{"content":json.dumps(output)}}]
        }}
        with TemporaryDirectory() as td:
            target=Path(td)/"last"
            with patch(
                "experiments.sera.haiku_last_probe_v011.prepare",
                return_value=histories(),
            ),patch.dict(sys.modules,{
                "src.openrouter_preflight":fake_preflight()
            }),patch(
                "experiments.sera.haiku_last_probe_v011.one_provider_call",
                return_value=response,
            ) as caller:
                result=run(
                    audit=evidence(),first={},first_manifest={},
                    second={},second_manifest={},output_dir=target,
                    launch_id="synthetic",key="fake")
                caller.assert_called_once()
                self.assertEqual(caller.call_args.kwargs["model"],MODEL)
                self.assertNotIn("max_tokens",str(caller.call_args))
            self.assertEqual(result["status"],
                             "THREE_INDEPENDENT_OPINIONS_RECORDED_SEMANTIC_HOLD")
            self.assertEqual(result["completed_tasks"],[
                "task_001","task_002","task_003"
            ])
            self.assertEqual(result["new_provider_calls"],1)
            self.assertEqual(result["new_provider_reported_cost_usd"],0.0011)
            self.assertEqual(result["pending_tasks"],[])
            self.assertFalse(result["canonical_commit_authorized"])
            self.assertEqual(result["world_db_writes"],0)
            proof=json.loads((target/"task_003.json").read_text())
            self.assertEqual(proof["recovered_advisory"]["bound_advisory"]
                             ["verdict_model_proposed"],"STATE_OBSERVATION")

    def test_incomplete_provider_does_not_repeat_or_approve(self):
        response={"error":None,"raw":{
            "id":"fake-incomplete","model":MODEL,
            "usage":{"cost":0.0010},
            "choices":[{"finish_reason":"length",
                        "message":{"content":'{"unfinished":true'}}]
        }}
        with TemporaryDirectory() as td:
            with patch("experiments.sera.haiku_last_probe_v011.prepare",
                       return_value=histories()),patch.dict(sys.modules,{
                "src.openrouter_preflight":fake_preflight()
            }),patch(
                "experiments.sera.haiku_last_probe_v011.one_provider_call",
                return_value=response,
            ) as caller:
                result=run(
                    audit=evidence(),first={},first_manifest={},
                    second={},second_manifest={},output_dir=Path(td)/"last",
                    launch_id="synthetic-bad",key="fake")
                caller.assert_called_once()
            self.assertEqual(result["status"],"LAST_PROBE_INCOMPLETE_HOLD")
            self.assertEqual(result["error_code"],"HAIKU_LAST_INCOMPLETE")
            self.assertEqual(result["pending_tasks"],["task_003"])
            self.assertFalse(result["canonical_commit_authorized"])

    def test_key_absent_makes_no_model_call(self):
        with TemporaryDirectory() as td:
            with patch("experiments.sera.haiku_last_probe_v011.prepare",
                       return_value=histories()):
                result=run(audit=evidence(),first={},first_manifest={},
                           second={},second_manifest={},output_dir=Path(td)/"last",
                           launch_id="missing-key",key="")
            self.assertEqual(result["new_provider_calls"],0)
            self.assertEqual(result["error_code"],"HAIKU_LAST_KEY_MISSING")

    def test_refuses_reusing_existing_evidence_path(self):
        with TemporaryDirectory() as td:
            path=Path(td)/"exists";path.mkdir()
            with patch("experiments.sera.haiku_last_probe_v011.prepare",
                       return_value=histories()):
                with self.assertRaisesRegex(CoverageError,
                                            "HAIKU_LAST_OUTPUT_EXISTS"):
                    run(audit=evidence(),first={},first_manifest={},
                        second={},second_manifest={},output_dir=path,
                        launch_id="repeat",key="fake")

if __name__=="__main__":
    unittest.main()
