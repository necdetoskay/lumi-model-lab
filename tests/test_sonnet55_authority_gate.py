from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.episode_spine_v2_contract import EpisodeSpineV2
from src.sonnet55_spine_p27_authority_gate import build_gate_input
from src.sonnet55_spine_safe_normalize import normalize_reversal_support_refs


SOURCE = Path("data/specifications/story_lab/sonnet55_p25_recovery_source_36541988910.json")
AUTHORITY = Path("data/specifications/story_lab/sonnet55_revision05_qualification_authority.json")
QUAL_PROMPT = Path("prompts/episode_spine_gate_sonnet55_qualification.md")
BASE_PROMPT = Path("prompts/episode_spine_gate_v2.md")


class Sonnet55AuthorityGateTests(unittest.TestCase):
    def _fixture(self):
        source = json.loads(SOURCE.read_text())
        authority = json.loads(AUTHORITY.read_text())
        normalized, repairs = normalize_reversal_support_refs(source["architect_raw_payload"])
        self.assertEqual(len(repairs), 1)
        spine = EpisodeSpineV2.model_validate(normalized)
        return source, authority, spine

    def test_authority_is_frozen_human_approved_revision05(self):
        authority = json.loads(AUTHORITY.read_text())
        self.assertEqual(authority["source_run_id"], 36520646579)
        self.assertEqual(authority["human_review"]["verdict"], "APPROVE")
        fresh = authority["frozen_mechanics"]["decision_point"]["fresh_setup_retest"]
        self.assertIn("may legitimately end", fresh["log_rule"])
        self.assertTrue(authority["frozen_mechanics"]["saga_progression"]["commit_only_if_earned"])

    def test_gate_input_contains_human_authority_and_candidate(self):
        source, authority, spine = self._fixture()
        payload = build_gate_input(source=source, authority=authority, episode_spine=spine)
        self.assertEqual(
            payload["task"],
            "evaluate_episode_spine_with_frozen_human_authority",
        )
        self.assertEqual(payload["qualification_authority"]["source_run_id"], 36520646579)
        self.assertEqual(payload["qualification_authority"]["human_review"]["verdict"], "APPROVE")
        self.assertEqual(payload["episode_spine"]["episode_role"], "MAIN_SAGA_ENTRY")

    def test_qualification_prompt_resolves_old_premise_payoff_conflict(self):
        text = QUAL_PROMPT.read_text()
        self.assertIn("Revision-05 controls", text)
        self.assertIn("NO completed reviewed log", text)
        self.assertIn("simply does not earn that milestone", text)

    def test_base_gate_remains_generic_and_unmodified_by_qualification_authority(self):
        text = BASE_PROMPT.read_text()
        self.assertNotIn("qualification_authority", text)
        self.assertNotIn("Revision-05 controls", text)


if __name__ == "__main__":
    unittest.main()
