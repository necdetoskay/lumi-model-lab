"""Pre-freeze readiness must not silently grant provider access."""
import unittest
from src.story_harness_readiness_v1 import offline_readiness

class StoryHarnessReadinessTests(unittest.TestCase):
    def test_every_harness_component_and_all_ten_memories_checked(self):
        result = offline_readiness(".")
        self.assertEqual(result["input_count"], 10)
        self.assertEqual(len(result["inputs"]), 10)
        self.assertEqual(len(result["harness_sections"]), 9)
        self.assertEqual(len(result["model_stage_names"]), 4)
        self.assertEqual(len(result["tool_names"]), 9)
        self.assertEqual(result["budget_cap_usd"], "20.00")
        self.assertEqual(result["provider_calls_performed"], 0)
        self.assertEqual(result["paid_calls_authorized"], 0)
        self.assertFalse(result["full_real_cohort_started"])
        self.assertEqual(result["harness_configuration_status"],
                         "PREPARED_NOT_FROZEN")
        self.assertEqual(result["real_paid_cohort_status"],
                         "BLOCKED_NOT_SEALED")
        self.assertGreater(len(result["missing_live_gates"]), 0)
        ages = sorted(v["age"] for v in result["inputs"].values())
        self.assertEqual(ages,[4,4,10,10,12,12,25,25,40,40])
        self.assertEqual(len(set(v["input_sha256"] for v in result["inputs"].values())),10)
        self.assertEqual(len(set(v["memory_snapshot_sha256"]
                                 for v in result["inputs"].values())),10)

    def test_component_freeze_is_actual_file_content_not_name_and_commit(self):
        from src.story_harness_frozen_round_v1 import (
            simulate_seal, _actual_component_sha256, COMPONENT_FILES
        )
        import hashlib
        result = offline_readiness(".")
        seal = simulate_seal(".")
        self.assertEqual(seal["component_sha256"],
                         _actual_component_sha256(seal["files_sha256"]))
        self.assertEqual(set(COMPONENT_FILES), set(seal["component_sha256"]))
        self.assertNotEqual(
            seal["component_sha256"]["model_runtime_profile"],
            hashlib.sha256(("model_runtime_profile:" +
                            result["run_commit"]).encode()).hexdigest())
