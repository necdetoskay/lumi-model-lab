"""v0.47 unattended v0.22 fallback and v0.20 scene rewrite — offline."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from experiments.sera.coverage import CoverageError
from experiments.sera.scene_trace_full_fallback_v047 import (
    EXTRACT,FALLBACK,SOURCE_1,SOURCE_2,
    one_synthetic_trial,verify_durable_replay,
    initial_failure_then_fallback,
)
from experiments.sera.coverage import prose_hash


class SceneTraceFullFallbackV047Tests(TestCase):
    def test_successful_fallback_on_first_invalid_receipted_extraction(self):
        with TemporaryDirectory() as tmp:
            a=one_synthetic_trial(Path(tmp)/"good",rewrite=False)
        self.assertEqual(a["status"],"SCENE_CANDIDATE_READY_NONCANONICAL")
        self.assertEqual(a["first_model_bad_sweep_receipts"],1)
        self.assertEqual(a["independent_fallback_sweep_responses"],1)
        self.assertEqual(a["scripted_writer_calls_current_run"],0)
        self.assertEqual(a["trace_sentence_counts"],[2])
        self.assertEqual(a["source_after_sha256"],prose_hash(SOURCE_2))
        self.assertEqual(a["real_external_model_calls"],0)
        self.assertEqual(a["actual_spend_usd"],"0")
        self.assertFalse(a["canonical_commit_authorized"])
        self.assertFalse(a["real_model_causal_validation"])
        self.assertEqual(a["production_db_writes"],0)

    def test_invalid_original_auto_rewrite_then_fallback_recheck_real_checker(self):
        with TemporaryDirectory() as tmp:
            a=one_synthetic_trial(Path(tmp)/"rewrite",rewrite=True)
            original=(Path(tmp)/"rewrite"/"evidence"/
                      (prose_hash(SOURCE_1)+".json"))
            revised=(Path(tmp)/"rewrite"/"evidence"/
                     (prose_hash(SOURCE_2)+".json"))
            self.assertTrue(original.exists())
            self.assertTrue(revised.exists())
        self.assertEqual(a["status"],"SCENE_CANDIDATE_READY_NONCANONICAL")
        self.assertEqual(a["controller_result"]["rewrite_count"],1)
        self.assertEqual(a["scripted_writer_calls_current_run"],1)
        self.assertEqual(a["source_before_sha256"],prose_hash(SOURCE_1))
        self.assertEqual(a["source_after_sha256"],prose_hash(SOURCE_2))
        self.assertEqual(a["first_model_bad_sweep_receipts"],2)
        self.assertEqual(a["independent_fallback_sweep_responses"],2)
        self.assertEqual(a["trace_sentence_counts"],[2,2])
        self.assertEqual(a["canonical_commit_authorized"],False)

    def test_full_provider_and_writer_durable_success_replay_is_zero_dispatch(self):
        with TemporaryDirectory() as tmp:
            proof=verify_durable_replay(Path(tmp)/"replay",rewrite=True)
        self.assertTrue(proof["stable_replay_without_new_model_or_writer"])
        self.assertEqual(proof["initial"]["status"],
                         "SCENE_CANDIDATE_READY_NONCANONICAL")
        self.assertEqual(
            proof["replay"]["total_scripted_provider_calls_current_run"],0)
        self.assertEqual(
            proof["replay"]["scripted_writer_calls_current_run"],0)
        self.assertEqual(proof["initial"]["controller_result"],
                         proof["replay"]["controller_result"])

    def test_all_receipted_models_invalid_is_failed_safe_terminal(self):
        with TemporaryDirectory() as tmp:
            a=one_synthetic_trial(Path(tmp)/"both_bad",mode="both_bad",
                                  rewrite=False)
        self.assertEqual(a["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(a["first_model_bad_sweep_receipts"],1)
        self.assertEqual(a["independent_fallback_sweep_responses"],1)
        self.assertEqual(a["scripted_writer_calls_current_run"],0)
        self.assertIsNone(a["source_after_sha256"])
        self.assertEqual(a["real_external_model_calls"],0)
        self.assertFalse(a["canonical_commit_authorized"])

    def test_unknown_inflight_disallows_fallback_and_no_second_dispatch(self):
        with TemporaryDirectory() as tmp:
            proof=verify_durable_replay(
                Path(tmp)/"lost",mode="unreceipted",rewrite=False,
            )
        a=proof["initial"]
        self.assertEqual(a["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(a["first_model_bad_sweep_receipts"],1)
        self.assertEqual(a["independent_fallback_sweep_responses"],0)
        self.assertEqual(
            proof["replay"]["total_scripted_provider_calls_current_run"],0)
        self.assertEqual(a["real_external_model_calls"],0)
        self.assertEqual(a["production_db_writes"],0)

    def test_unknown_scenario_not_permitted(self):
        with self.assertRaisesRegex(CoverageError,
                                    "V047_INVALID_LAB_MODE"):
            initial_failure_then_fallback([],mode="silent-pass")


if __name__=="__main__":
    import unittest
    unittest.main()
