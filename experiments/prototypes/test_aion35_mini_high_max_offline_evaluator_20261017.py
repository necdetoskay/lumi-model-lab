"""Offline audit tests: true pair receipt provenance, no semantic false-pass."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

from experiments.prototypes import aion35_mini_reasoning_high_max_once_20261017 as ab
from experiments.prototypes import aion35_mini_high_max_offline_evaluator_20261017 as audit
from experiments.prototypes.test_aion35_mini_reasoning_high_max_once_20261017 import fake_provider


def fixture(root,provider=fake_provider):
    with patch.object(ab,"validate_one_use_launch",
                      return_value=ab.verify_equal_experiment()), \
         patch.object(ab,"real_stream_call",side_effect=provider):
        return ab.run_live(output_root=root/"run",claim_root=root/"claims",
                           api_key="sk-test-not-a-real-api-key",
                           grant={"launch_id":"aion35mini-deniz-high-max-20261017-once"})


def mutate(path,change):
    d=json.loads(path.read_text(encoding="utf-8"))
    change(d)
    path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",
                    encoding="utf-8")


class AionPairedOfflineEvidenceTests(unittest.TestCase):
    def test_complete_pair_has_metrics_but_no_unearned_quality_winner(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            response=fixture(root)
            self.assertTrue(response["both_provider_generations_distinct_and_complete"])
            v=audit.evaluate(root/"run")
        self.assertEqual(v["status"],
                         "PAIRED_RECEIPTS_VERIFIED_QUALITY_UNDETERMINED")
        self.assertTrue(v["comparison_authorized"])
        self.assertEqual(v["winner"],
                         "UNDETERMINED_NOT_SEMANTICALLY_JUDGED")
        self.assertEqual(v["high"]["reasoning_tokens"],1700)
        self.assertEqual(v["max"]["reasoning_tokens"],2200)
        self.assertEqual(v["max_minus_high"]["reasoning_tokens_max_minus_high"],
                         500)
        self.assertEqual(v["high"]["reported_cost_usd"],"0.004")
        self.assertGreater(v["high"]["repetition_indicator"]["repeated_fivegrams"],0)
        self.assertFalse(v["high"]["story_validated_against_physical_truth"])
        self.assertTrue(v["lexical_cues_do_not_establish_causality"])
        self.assertEqual(v["new_provider_calls"],0)
        self.assertEqual(v["canonical_world_writes"],0)

    def test_changed_text_rejected_even_if_summary_still_says_pass(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root)
            story=root/"run"/"high.txt"
            story.write_text("An editor changed the story.\n",encoding="utf-8")
            with self.assertRaisesRegex(
                RuntimeError,"PAIR_STORY_CHANGED_FROM_ORIGINAL_RECEIPT"
            ):
                audit.evaluate(root/"run")

    def test_forged_received_model_and_lexical_summary_rejected(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root)
            f=root/"run"/"max.summary.json"
            mutate(f,lambda d: d.update({"model":"fake/other-model"}))
            with self.assertRaisesRegex(
                RuntimeError,"PAIR_RECEIPT_SUMMARY_PROVENANCE_DRIFT"
            ):
                audit.evaluate(root/"run")

    def test_wrong_input_hash_rejected(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root)
            f=root/"run"/"inputs.json"
            mutate(f,lambda d:d.update({
                "common_request_sha256":"unauthorized-changed-spine"
            }))
            with self.assertRaisesRegex(
                RuntimeError,"PAIR_INPUT_SOURCE_OR_SCOPE_DRIFT"
            ):
                audit.evaluate(root/"run")

    def test_stopped_first_writer_is_hold_no_second_dispatch(self):
        calls=[]
        def abnormal(req,key):
            calls.append(req["reasoning"]["effort"])
            reply=fake_provider(req,key)
            reply["finish_reason"]="length"
            return reply
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            out=fixture(root,abnormal)
            audit_result=audit.evaluate(root/"run")
        self.assertEqual(calls,["high"])
        self.assertEqual(out["status"],
                         "PARTIAL_OR_FAILED_SAFE_NO_PROVIDER_RESEND")
        self.assertEqual(audit_result["status"],
                         "HOLD_INCOMPLETE_PROVIDER_PAIR")
        self.assertFalse(audit_result["comparison_authorized"])
        self.assertEqual(audit_result["new_provider_calls"],0)

    def test_second_provider_truncated_is_not_a_comparable_pair(self):
        calls=[]
        def second_length(req,key):
            effort=req["reasoning"]["effort"]
            calls.append(effort)
            reply=fake_provider(req,key)
            if effort=="max":
                reply["finish_reason"]="length"
            return reply
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            out=fixture(root,second_length)
            report=audit.evaluate(root/"run")
        self.assertEqual(calls,["high","max"])
        self.assertFalse(out["both_provider_generations_distinct_and_complete"])
        self.assertEqual(out["status"],
                         "PARTIAL_OR_FAILED_SAFE_NO_PROVIDER_RESEND")
        self.assertEqual(report["winner"],"UNDETERMINED")

    def test_duplicate_generation_ids_hold_and_do_not_pretend_independent(self):
        def repeated(req,key):
            reply=fake_provider(req,key)
            reply["generation_id"]="same-generation-id"
            return reply
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            out=fixture(root,repeated)
            with self.assertRaisesRegex(RuntimeError,
                                        "PAIR_DUPLICATE_PROVIDER_GENERATION"):
                # The run result truthfully says not comparable. Tampering
                # the final status into a PASS cannot override receipt guard.
                mutate(root/"run"/"result.json",
                       lambda d:d.update({
                           "status":"TWO_GENUINE_PROVIDER_ANSWERS_COMPARABLE",
                           "both_provider_generations_distinct_and_complete":True
                       }))
                audit.evaluate(root/"run")
        self.assertEqual(out["status"],
                         "PARTIAL_OR_FAILED_SAFE_NO_PROVIDER_RESEND")

    def test_model_swap_after_first_reply_stops_second(self):
        calls=[]
        def fake_switch(req,key):
            calls.append(req["reasoning"]["effort"])
            reply=fake_provider(req,key)
            reply["returned_model"]="unwanted/fallback"
            return reply
        with TemporaryDirectory() as tmp:
            out=fixture(Path(tmp),fake_switch)
        self.assertEqual(calls,["high"])
        self.assertEqual(out["status"],
                         "PARTIAL_OR_FAILED_SAFE_NO_PROVIDER_RESEND")

    def test_cost_missing_is_unknown_not_zero(self):
        def no_cost(req,key):
            reply=deepcopy(fake_provider(req,key))
            reply["usage"].pop("cost")
            reply["usage"]["completion_tokens_details"].pop("reasoning_tokens")
            return reply
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root,no_cost)
            v=audit.evaluate(root/"run")
        self.assertIsNone(v["high"]["reported_cost_usd"])
        self.assertIsNone(v["max_minus_high"]
                          ["reported_cost_usd_max_minus_high"])
        self.assertIsNone(v["high"]["reasoning_tokens"])
        self.assertEqual(v["winner"],
                         "UNDETERMINED_NOT_SEMANTICALLY_JUDGED")


if __name__=="__main__":
    unittest.main()
