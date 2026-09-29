from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.model_registry import normalize_openrouter_request, require_qualification_runtime_profile
from src.sonnet55_audit_ab import _anchor_segment_ids, _score


class Sonnet55QualificationTests(unittest.TestCase):
    def test_runtime_profile_is_exact_and_audit_is_low_effort(self):
        profile = require_qualification_runtime_profile("anthropic/claude-sonnet-5.5")
        self.assertEqual(profile["match"]["type"], "exact")
        self.assertTrue(profile["qualification"]["ready"])
        self.assertEqual(profile["metadata"]["context_tokens"], 1000000)
        self.assertEqual(profile["metadata"]["max_output_tokens"], 128000)
        self.assertEqual(profile["metadata"]["pricing_usd_per_million_tokens"]["input"], 2.00)
        self.assertEqual(profile["metadata"]["pricing_usd_per_million_tokens"]["output"], 10.00)
        payload = normalize_openrouter_request(
            "anthropic/claude-sonnet-5.5",
            {"temperature": 0.0, "max_tokens": 2800, "seed": 7},
            request_class="editorial_audit",
            structured_output=True,
        )
        self.assertNotIn("temperature", payload)
        self.assertNotIn("seed", payload)
        self.assertEqual(payload["max_tokens"], 2800)
        self.assertEqual(payload["reasoning"], {"effort": "low", "exclude": True})
        self.assertEqual(payload["response_format"], {"type": "json_object"})

    def test_gold_anchors_exist_in_frozen_raw_story(self):
        source = json.loads(Path(
            "data/specifications/story_lab/age12_episode1_writer_run_36526379349.json"
        ).read_text())
        gold = json.loads(Path(
            "data/specifications/story_lab/sonnet55_audit_gold_age12.json"
        ).read_text())
        mapping = _anchor_segment_ids(source["english_story"], gold["roots"])
        self.assertEqual(len(mapping), 6)
        self.assertTrue(all(mapping.values()))

    def test_score_matches_by_segment_overlap(self):
        roots = [
            {"id": "a", "anchors": ["x"]},
            {"id": "b", "anchors": ["y"]}
        ]
        findings = [
            {"span_ids": ["S1"]},
            {"span_ids": ["S9"]}
        ]
        score = _score(findings, roots, {"a": ["S1"], "b": ["S2"]})
        self.assertEqual(score["matched_root_count"], 1)
        self.assertEqual(score["missed_roots"], ["b"])
        self.assertEqual(score["unmapped_finding_count"], 1)


if __name__ == "__main__":
    unittest.main()
