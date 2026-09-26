import json
import unittest
from pathlib import Path

from src.story_defect_corpus import load_source_pool
from src.story_defect_detection import DEFECT_FAMILIES, segment_story


AUDIT = Path(
    "experiments/fixtures/story_defect_manual_gold_audit.tr-age4.v0.1.json"
)


class StoryDefectManualGoldAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = json.loads(AUDIT.read_text(encoding="utf-8"))
        pool = load_source_pool()
        cls.sources = {row["source_id"]: row for row in pool["sources"]}

    def test_manual_audit_is_not_misrepresented_as_api_benchmark(self):
        self.assertEqual(
            self.audit["status"],
            "MANUAL_GOLD_CANDIDATE_NOT_YET_FINAL_REFERENCE",
        )
        reviewer = self.audit["reviewer"]
        self.assertEqual(reviewer["surface"], "chatgpt_plus_interactive_session")
        self.assertEqual(reviewer["api_calls_used"], 0)

    def test_pilot_audits_five_real_frozen_sources(self):
        entries = self.audit["entries"]
        self.assertEqual(len(entries), 5)
        self.assertTrue(
            all(entry["source_id"] in self.sources for entry in entries)
        )

    def test_every_manual_finding_has_valid_family_and_exact_span(self):
        for entry in self.audit["entries"]:
            source = self.sources[entry["source_id"]]
            valid_ids = {row["id"] for row in segment_story(source["story"])}
            for finding in entry["findings"]:
                self.assertIn(finding["family"], DEFECT_FAMILIES)
                self.assertTrue(set(finding["span_ids"]).issubset(valid_ids))
                self.assertIn(
                    finding["repair_scope"],
                    {"NO_REPAIR", "LOCAL_REPAIR", "STRUCTURAL_REPAIR", "REPLAN"},
                )

    def test_manual_clean_candidate_never_contains_blocking_finding(self):
        for entry in self.audit["entries"]:
            blocking = [
                finding
                for finding in entry["findings"]
                if finding["severity"] in {"serious", "critical"}
            ]
            self.assertEqual(
                entry["admitted_as_manual_clean_candidate"],
                len(blocking) == 0,
            )

    def test_priority_busy_hands_causal_break_is_captured(self):
        entry = next(
            row
            for row in self.audit["entries"]
            if row["source_id"] == "src_cohort_a_03"
        )
        causal = [
            finding
            for finding in entry["findings"]
            if finding["family"] == "causal_logic"
            and finding["severity"] == "serious"
        ]
        self.assertEqual(len(causal), 1)
        self.assertIn("S017", causal[0]["span_ids"])

    def test_terminal_tail_is_captured(self):
        entry = next(
            row
            for row in self.audit["entries"]
            if row["source_id"] == "src_cohort_a_04"
        )
        closure = [
            finding
            for finding in entry["findings"]
            if finding["family"] == "closure_integrity"
            and finding["severity"] == "serious"
        ]
        self.assertEqual(len(closure), 1)
        self.assertIn("S051", closure[0]["span_ids"])


if __name__ == "__main__":
    unittest.main()
