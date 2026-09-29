from __future__ import annotations

import unittest

from src.episode_writer_v2_generate import _combined_rollup, _validate_source


class EpisodeWriterV2Tests(unittest.TestCase):
    def approved(self):
        return {
            "schema_version": "episode-spine-v2-human-approved.v1",
            "source_run_id": 1,
            "human_review": {"verdict": "APPROVE"},
            "gate": {"decision": "ACCEPT"},
            "episode_spine": {"target_words_min": 1600, "target_words_max": 2500},
            "source_usage_rollup": {
                "calls": [
                    {
                        "stage": "episode_spine_architect",
                        "model": "m1",
                        "provider": "p",
                        "status": "completed",
                        "attempt": 1,
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "reasoning_tokens": 1,
                        "cached_tokens": 0,
                        "cache_write_tokens": 0,
                        "total_tokens": 15,
                        "cost_usd": 0.1,
                        "latency_seconds": 2.0,
                    }
                ]
            },
        }

    def test_source_requires_human_approve_and_gate_accept(self):
        value = self.approved()
        _validate_source(value)
        value["human_review"]["verdict"] = "REVISE"
        with self.assertRaises(RuntimeError):
            _validate_source(value)

    def test_combined_rollup_adds_writer_without_reinference(self):
        source = self.approved()
        writer = {
            "stage": "episode_writer",
            "model": "aion-labs/aion-3.5-mini",
            "provider": "openrouter",
            "status": "completed",
            "attempt": 1,
            "input_tokens": 20,
            "output_tokens": 10,
            "reasoning_tokens": 2,
            "cached_tokens": 0,
            "cache_write_tokens": 0,
            "total_tokens": 30,
            "cost_usd": 0.2,
            "latency_seconds": 3.0,
        }
        rollup = _combined_rollup(source, writer)
        self.assertEqual(rollup["totals"]["api_calls"], 2)
        self.assertEqual(rollup["totals"]["total_tokens"], 45)
        self.assertAlmostEqual(rollup["totals"]["cost_usd"], 0.3)


if __name__ == "__main__":
    unittest.main()
