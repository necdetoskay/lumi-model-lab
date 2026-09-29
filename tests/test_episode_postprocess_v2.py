from __future__ import annotations

import unittest

from src.episode_postprocess_v2 import _hard_constraints, _validate_source


class EpisodePostprocessV2Tests(unittest.TestCase):
    def approved(self):
        return {
            "source_run_id": 36520646579,
            "human_review": {"verdict": "APPROVE"},
            "gate": {"decision": "ACCEPT"},
            "episode_spine": {
                "writer_rules": ["keep bounded"],
                "reversal": {
                    "inference_ceiling": "do not prove recurrence",
                    "unresolved_after_reversal": "cause remains unknown",
                },
            },
        }

    def source(self):
        return {
            "schema_version": "episode-postprocess-source.v1",
            "source_spine_run_id": 36520646579,
            "english_story": "Title\nStory body.",
            "deterministic_checks": {"length_pass": True},
        }

    def test_source_requires_matching_accepted_spine(self):
        _validate_source(self.source(), self.approved())
        bad = self.source()
        bad["source_spine_run_id"] = 1
        with self.assertRaises(RuntimeError):
            _validate_source(bad, self.approved())

    def test_hard_constraints_include_epistemic_limits(self):
        rows = _hard_constraints(self.approved()["episode_spine"])
        joined = "\n".join(rows)
        self.assertIn("keep bounded", joined)
        self.assertIn("do not prove recurrence", joined)
        self.assertIn("cause remains unknown", joined)


if __name__ == "__main__":
    unittest.main()
