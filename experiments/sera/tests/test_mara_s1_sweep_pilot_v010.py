"""SERA v0.10 pilot entrypoint: no billable calls during tests."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType
from unittest.mock import patch
import json
import sys
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_sweep_pilot_v010 import (
    TARGET_QUOTE, prepare, run,
)


def fake_raw(batch):
    return {"rows": [{
        "sentence_id": sid, "disposition": "AMBIGUOUS",
        "reason": "Synthetic model: review pending",
        "mentions": [], "events": [],
    } for sid in batch["sentence_ids"]]}


def preflight_stub():
    module=ModuleType("src.openrouter_preflight")
    module.fetch_key_status=lambda key: {"fake_key":True}
    module.enforce_key_access=lambda x, min_remaining: None
    return module


class MaraSweepPilotV010Tests(unittest.TestCase):
    def test_frozen_mara_one_batch_and_no_output_token_cap(self):
        prepared=prepare()
        self.assertEqual(prepared["plan"]["sentence_count"],28)
        self.assertEqual(len(prepared["plan"]["batches"]),7)
        self.assertEqual(len(prepared["batch"]["sentence_ids"]),4)
        self.assertTrue(any(TARGET_QUOTE in s["quote"]
                            for s in prepared["plan"]["source_sentences"]
                            if s["id"] in prepared["batch"]["sentence_ids"]))
        self.assertEqual(prepared["batch"]["response_format"],
                         {"type":"json_object"})
        self.assertNotIn("max_tokens",str(prepared["batch"]))
        self.assertNotIn("max_completion_tokens",str(prepared["batch"]))
        self.assertFalse(prepared["plan"]["canonical_commit_authorized"])

    def test_no_secret_fails_closed_without_model_attempt(self):
        with TemporaryDirectory() as td:
            result=run(output=Path(td)/"result.json",launch_id="unit-missing",
                       key="")
            self.assertEqual(result["provider_attempts"],0)
            self.assertEqual(result["status"],"DIAGNOSTIC_INCOMPLETE_HOLD")
            self.assertEqual(result["error_code"],"V010_PROVIDER_KEY_MISSING")
            self.assertFalse(result["canonical_commit_authorized"])
            self.assertEqual(result["world_db_writes"],0)

    def test_successful_simulated_provider_is_one_batch_not_scene_approval(self):
        prepared=prepare()
        response={
            "raw":{
                "id":"fake-pilot", "model":"synthetic-model",
                "usage":{"cost":0.003,"completion_tokens":650},
                "choices":[{
                    "finish_reason":"stop",
                    "message":{"content":json.dumps(fake_raw(prepared["batch"]))},
                }],
            },
            "error":None,
        }
        with TemporaryDirectory() as td:
            file=Path(td)/"out.json"
            with patch.dict(sys.modules, {
                "src.openrouter_preflight":preflight_stub(),
            }),patch(
                "experiments.sera.mara_s1_sweep_pilot_v010.one_provider_call",
                return_value=response,
            ) as call:
                result=run(output=file,launch_id="synthetic-only",key="fake")
                call.assert_called_once()
            self.assertEqual(result["provider_attempts"],1)
            self.assertEqual(result["status"],
                             "ONE_BATCH_EXTRACTED_REMAINING_SOURCE_HOLD")
            self.assertEqual(result["provider_reported_cost"],0.003)
            self.assertEqual(len(result["bound_batch"]["rows"]),4)
            self.assertEqual(len(result["recovery_queue"]["pending_batch_ids"]),6)
            self.assertFalse(result["canonical_commit_authorized"])
            self.assertEqual(result["world_db_writes"],0)
            self.assertEqual(json.loads(file.read_text())["status"],
                             result["status"])

    def test_model_non_stop_stays_diagnostic_hold_and_records_cost(self):
        response={
            "raw":{
                "id":"mock-truncated", "model":"synthetic",
                "usage":{"cost":0.004},
                "choices":[{
                    "finish_reason":"length",
                    "message":{"content":'{"rows":['},
                }],
            },
            "error":None,
        }
        with TemporaryDirectory() as td:
            with patch.dict(sys.modules, {
                "src.openrouter_preflight":preflight_stub(),
            }),patch(
                "experiments.sera.mara_s1_sweep_pilot_v010.one_provider_call",
                return_value=response,
            ) as call:
                result=run(output=Path(td)/"out.json",
                           launch_id="synthetic-truncated",key="fake")
                call.assert_called_once()
            self.assertEqual(result["status"],"DIAGNOSTIC_INCOMPLETE_HOLD")
            self.assertEqual(result["error_code"],"V010_PROVIDER_INCOMPLETE")
            self.assertEqual(result["provider_reported_cost"],0.004)
            self.assertFalse(result["max_model_output_tokens_configured"])
            self.assertIsNone(result["bound_batch"])

    def test_http_400_records_error_and_provider_detail_without_retries(self):
        with TemporaryDirectory() as td:
            with patch.dict(sys.modules, {
                "src.openrouter_preflight":preflight_stub(),
            }),patch(
                "experiments.sera.mara_s1_sweep_pilot_v010.one_provider_call",
                return_value={
                    "raw":None, "error":"HTTP_400",
                    "provider_detail":"provider rejected response format",
                },
            ) as call:
                result=run(output=Path(td)/"err.json",
                           launch_id="synthetic-http400",key="fake")
                call.assert_called_once()
            self.assertEqual(result["status"],"PROVIDER_ERROR_HOLD")
            self.assertEqual(result["error_code"],"HTTP_400")
            self.assertIn("response format",result["provider_detail"])
            self.assertEqual(result["provider_attempts"],1)
            self.assertFalse(result["canonical_commit_authorized"])

    def test_evidence_path_cannot_be_overwritten(self):
        with TemporaryDirectory() as td:
            path=Path(td)/"existing.json"
            path.write_text('{"original":true}')
            with self.assertRaisesRegex(CoverageError,
                                        "V010_EVIDENCE_PATH_EXISTS"):
                run(output=path,launch_id="repeat",key="")
            self.assertEqual(path.read_text(),'{"original":true}')


if __name__ == "__main__":
    unittest.main()
