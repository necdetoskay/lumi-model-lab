from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.episode_spine_v2_contract import EpisodeSpineV2
from src.sonnet55_spine_safe_normalize import normalize_reversal_support_refs


SOURCE = Path("data/specifications/story_lab/sonnet55_p25_recovery_source_36541988910.json")


class Sonnet55SafeNormalizeTests(unittest.TestCase):
    def test_p25_self_reference_is_removed_without_semantic_rewrite(self):
        source = json.loads(SOURCE.read_text())
        raw = source["architect_raw_payload"]
        normalized, repairs = normalize_reversal_support_refs(raw)

        self.assertEqual(len(repairs), 1)
        self.assertEqual(repairs[0]["removed_refs"], ["b7_reversal"])
        self.assertEqual(repairs[0]["kept_refs"], ["b4_first_series"])

        before = raw["reversal"]["evidence"][2]
        after = normalized["reversal"]["evidence"][2]
        self.assertEqual(before["claim"], after["claim"])
        self.assertEqual(before["certainty"], after["certainty"])

        EpisodeSpineV2.model_validate(normalized)

    def test_does_not_hide_missing_pre_reversal_evidence(self):
        raw = {
            "beats": [
                {"key": "b1", "phase": "HOOK"},
                {"key": "b2", "phase": "REVERSAL"},
            ],
            "reversal": {
                "evidence": [
                    {
                        "claim": "bad",
                        "certainty": "INFERRED",
                        "supporting_beat_keys": ["b2"],
                    }
                ]
            },
        }
        normalized, repairs = normalize_reversal_support_refs(raw)
        self.assertEqual(repairs, [])
        self.assertEqual(
            normalized["reversal"]["evidence"][0]["supporting_beat_keys"],
            ["b2"],
        )


if __name__ == "__main__":
    unittest.main()
