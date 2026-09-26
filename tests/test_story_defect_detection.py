import json
import unittest
from pathlib import Path

from src.story_defect_benchmark import score_defect_predictions
from src.story_defect_detection import (
    DEFECT_FAMILIES,
    build_jev_defect_questions,
    build_jev_state,
    build_repair_context,
    segment_story,
    suspected_families,
    validate_defect_finding,
)


FIXTURE = Path("experiments/fixtures/story_defect_corpus_v1.seed.json")


class StoryDefectDetectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.cases = cls.corpus["cases"]

    def test_seed_corpus_is_explicitly_non_qualification_evidence(self):
        self.assertEqual(
            self.corpus["status"], "SEED_ONLY_NOT_QUALIFICATION_EVIDENCE"
        )
        self.assertGreaterEqual(len(self.cases), 20)

    def test_sentence_segmentation_is_stable_and_addressable(self):
        rows = segment_story("Birinci cümle. İkinci cümle! Üçüncü cümle?")
        self.assertEqual([row["id"] for row in rows], ["S001", "S002", "S003"])
        self.assertEqual(rows[1]["text"], "İkinci cümle!")

    def test_jev_questions_are_atomic_per_defect_family(self):
        questions = build_jev_defect_questions()
        self.assertEqual(set(questions), set(DEFECT_FAMILIES))
        self.assertTrue(all(question["type"] == "noul" for question in questions.values()))

    def test_jev_state_keeps_sentence_ids_and_constraints_separate(self):
        state = build_jev_state(
            story_id="story-1",
            story_text="Ada topu gördü. Topu aldı.",
            authoritative_constraints={"character": "Ada"},
        )
        self.assertEqual(state["segments"][0]["id"], "S001")
        self.assertEqual(state["authoritative_constraints"]["character"], "Ada")

    def test_suspicion_threshold_is_explicit_not_hidden_global_policy(self):
        scores = {
            "physical_feasibility": 0.72,
            "causal_logic": 0.31,
        }
        result = suspected_families(scores, threshold=0.50)
        self.assertEqual(result, [("physical_feasibility", 0.72)])
        with self.assertRaises(ValueError):
            suspected_families(scores, threshold=1.1)

    def test_typed_defect_finding_requires_location_reason_and_scope(self):
        finding = {
            "family": "state_continuity",
            "severity": "serious",
            "span_ids": ["S003"],
            "reason": "Taş açıklamasız biçimde önceki konumuna dönüyor.",
            "repair_scope": "LOCAL_REPAIR",
        }
        self.assertEqual(validate_defect_finding(finding), [])
        broken = dict(finding)
        broken["span_ids"] = []
        self.assertIn("span_ids_missing", validate_defect_finding(broken))

    def test_repair_context_is_bounded_around_confirmed_span(self):
        segments = segment_story("Bir. İki. Üç. Dört. Beş.")
        context = build_repair_context(segments, ["S003"], window=1)
        self.assertEqual([row["id"] for row in context], ["S002", "S003", "S004"])

    def test_every_corrupt_seed_has_valid_family_and_addressable_gold_span(self):
        corrupt = [case for case in self.cases if case["variant"] == "corrupt"]
        self.assertGreaterEqual(len(corrupt), 10)
        for case in corrupt:
            gold = case["gold"]
            self.assertIn(gold["family"], DEFECT_FAMILIES)
            ids = {row["id"] for row in segment_story(case["text"])}
            self.assertTrue(set(gold["span_ids"]).issubset(ids))

    def test_perfect_predictions_score_full_recall(self):
        predictions = []
        for case in self.cases:
            findings = []
            if case["gold"]["defect_present"]:
                findings.append(
                    {
                        "family": case["gold"]["family"],
                        "severity": case["gold"]["severity"],
                        "span_ids": case["gold"]["span_ids"],
                    }
                )
            predictions.append({"case_id": case["case_id"], "findings": findings})

        score = score_defect_predictions(self.cases, predictions)
        self.assertEqual(score["false_negative_cases"], 0)
        self.assertEqual(score["false_positive_findings"], 0)
        self.assertEqual(score["recall"], 1.0)
        self.assertEqual(score["serious_critical_recall"], 1.0)
        self.assertEqual(score["critical_recall"], 1.0)
        self.assertEqual(score["span_locator_recall"], 1.0)

    def test_missing_one_serious_defect_is_visible_as_false_negative(self):
        predictions = []
        skipped = False
        for case in self.cases:
            findings = []
            if case["gold"]["defect_present"] and not skipped:
                skipped = True
            elif case["gold"]["defect_present"]:
                findings.append(
                    {
                        "family": case["gold"]["family"],
                        "severity": case["gold"]["severity"],
                        "span_ids": case["gold"]["span_ids"],
                    }
                )
            predictions.append({"case_id": case["case_id"], "findings": findings})

        score = score_defect_predictions(self.cases, predictions)
        self.assertEqual(score["false_negative_cases"], 1)
        self.assertLess(score["serious_critical_recall"], 1.0)
        self.assertEqual(len(score["missed"]), 1)


if __name__ == "__main__":
    unittest.main()
