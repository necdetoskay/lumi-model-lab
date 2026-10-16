"""Offline v0.10 six-batch resume tests: synthetic provider, never charge."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import ModuleType
from unittest.mock import patch
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.sentence_sweep_v010 import bind_batch
from experiments.sera.mara_s1_sweep_pilot_v010 import prepare
from experiments.sera.mara_s1_remaining_sweep_v010 import (
    run, OBSERVED_SPEND_STOP_USD, MAX_NEW_PROVIDER_ATTEMPTS,
)


def blank(batch):
    return {"rows":[{
        "sentence_id":sid, "disposition":"AMBIGUOUS",
        "reason":"Synthetic uncertainty, not human adjudication",
        "mentions":[],"events":[],
    } for sid in batch["sentence_ids"]]}


def staged():
    p=prepare()
    history=next(b for b in p["plan"]["batches"] if b["batch_id"]=="batch_003")
    bound=bind_batch(plan=p["plan"],batch_id="batch_003",
                     raw=blank(history),prose=p["prose"])
    return {
        "preflight":p, "historic_bound":bound,
        "remaining":[b["batch_id"] for b in p["plan"]["batches"]
                     if b["batch_id"]!="batch_003"],
    }


def fixture_provider_response(batch, cost=0.001):
    return {
        "error":None,
        "raw":{
            "id":"synthetic-"+batch["batch_id"],
            "model":"synthetic",
            "usage":{"cost":cost},
            "choices":[{
                "finish_reason":"stop",
                "message":{"content":json.dumps(blank(batch))},
            }],
        },
    }


def fake_preflight():
    m=ModuleType("src.openrouter_preflight")
    m.fetch_key_status=lambda _:{"mock":True}
    m.enforce_key_access=lambda _,min_remaining:None
    return m


class ResumeSixV010Tests(unittest.TestCase):
    def test_synthetic_six_batch_completion_still_semantic_hold(self):
        test=staged()
        batches=[b for b in test["preflight"]["plan"]["batches"]
                 if b["batch_id"]!="batch_003"]
        seq=[fixture_provider_response(b) for b in batches]
        with TemporaryDirectory() as td:
            root=Path(td)/"out"
            with patch(
                "experiments.sera.mara_s1_remaining_sweep_v010.make_resume_plan",
                return_value=test,
            ),patch.dict(sys.modules,{
                "src.openrouter_preflight":fake_preflight(),
            }),patch(
                "experiments.sera.mara_s1_remaining_sweep_v010.one_provider_call",
                side_effect=seq,
            ) as caller:
                result=run(output_dir=root,launch_id="synthetic-six",
                           key="fake",pilot_evidence={})
                self.assertEqual(caller.call_count,6)
            self.assertEqual(result["new_provider_attempts"],6)
            self.assertEqual(result["status"],
                             "ALL_28_SENTENCES_EXTRACTED_SEMANTIC_HOLD")
            self.assertEqual(result["all_sentences_accounted_for"],28)
            self.assertEqual(result["pending_batch_ids"],[])
            self.assertEqual(result["new_provider_cost_usd"],0.006)
            self.assertGreater(result["targeted_probe_count"],0)
            self.assertFalse(result["model_output_token_cap_configured"])
            self.assertFalse(result["canonical_commit_authorized"])
            self.assertEqual(result["world_db_writes"],0)
            proof=json.loads(
                (root/"full_scene_assurance.json").read_text(encoding="utf-8")
            )
            self.assertEqual(proof["status"],
                             "HOLD_MODEL_SEMANTICS_UNVERIFIED")
            self.assertFalse(proof["semantic_recall_proven"])
            self.assertEqual(len(list(root.glob("batch_*.json"))),6)

    def test_first_provider_http_error_stops_without_six_retries(self):
        test=staged()
        with TemporaryDirectory() as td:
            root=Path(td)/"error"
            with patch(
                "experiments.sera.mara_s1_remaining_sweep_v010.make_resume_plan",
                return_value=test,
            ),patch.dict(sys.modules,{
                "src.openrouter_preflight":fake_preflight(),
            }),patch(
                "experiments.sera.mara_s1_remaining_sweep_v010.one_provider_call",
                return_value={"error":"HTTP_400","provider_detail":"schema mismatch",
                              "raw":None},
            ) as caller:
                result=run(output_dir=root,launch_id="synthetic-fail",
                           key="fake",pilot_evidence={})
                caller.assert_called_once()
            self.assertEqual(result["new_provider_attempts"],1)
            self.assertEqual(result["status"],
                             "INCOMPLETE_SOURCE_DIAGNOSTIC_HOLD")
            self.assertIn("HTTP_400",result["error_code"])
            self.assertEqual(len(result["pending_batch_ids"]),6)
            self.assertFalse(result["canonical_commit_authorized"])
            self.assertEqual(result["world_db_writes"],0)
            record=json.loads((root/"batch_001.json").read_text())
            self.assertEqual(record["status"],"PROVIDER_ERROR_HOLD")

    def test_missing_provider_cost_stops_before_next_call(self):
        test=staged()
        b=test["preflight"]["plan"]["batches"][0]
        response=fixture_provider_response(b,cost=None)
        with TemporaryDirectory() as td:
            with patch(
                "experiments.sera.mara_s1_remaining_sweep_v010.make_resume_plan",
                return_value=test,
            ),patch.dict(sys.modules,{
                "src.openrouter_preflight":fake_preflight(),
            }),patch(
                "experiments.sera.mara_s1_remaining_sweep_v010.one_provider_call",
                return_value=response,
            ) as caller:
                result=run(output_dir=Path(td)/"run",
                           launch_id="missing-cost",key="fake",
                           pilot_evidence={})
                caller.assert_called_once()
            self.assertEqual(result["status"],
                             "INCOMPLETE_SOURCE_DIAGNOSTIC_HOLD")
            self.assertFalse(result["reported_usage_complete"])
            self.assertIn("COST_UNKNOWN",result["error_code"])

    def test_single_high_reported_cost_stops_next_provider_call(self):
        test=staged()
        b=test["preflight"]["plan"]["batches"][0]
        response=fixture_provider_response(
            b,cost=float(OBSERVED_SPEND_STOP_USD),
        )
        with TemporaryDirectory() as td:
            with patch(
                "experiments.sera.mara_s1_remaining_sweep_v010.make_resume_plan",
                return_value=test,
            ),patch.dict(sys.modules,{
                "src.openrouter_preflight":fake_preflight(),
            }),patch(
                "experiments.sera.mara_s1_remaining_sweep_v010.one_provider_call",
                return_value=response,
            ) as caller:
                result=run(output_dir=Path(td)/"run",
                           launch_id="price-stop",key="fake",
                           pilot_evidence={})
                caller.assert_called_once()
            self.assertEqual(result["new_provider_attempts"],1)
            self.assertIn("SPEND_STOP",result["error_code"])
            self.assertEqual(result["pending_batch_ids"][0],"batch_002")

    def test_existing_evidence_dir_cannot_be_overwritten(self):
        with TemporaryDirectory() as td:
            root=Path(td)/"exists"
            root.mkdir()
            with self.assertRaisesRegex(
                CoverageError,"SWEEP_OUTPUT_DIRECTORY_EXISTS"
            ):
                run(output_dir=root,launch_id="duplicate",key="",
                    pilot_evidence={})
            self.assertEqual(list(root.iterdir()),[])


if __name__=="__main__":
    unittest.main()
