"""Offline SERA v0.8 annotation and adjudication guard regressions."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.sentence_review_packet_v07 import (
    build_review_packet, generate_mara_packet,
)
from experiments.sera.review_adjudication_v08 import (
    blank_annotation, validate_annotation, compare_annotations,
)
from experiments.sera.review_forms_cli_v08 import emit_forms, compare_files, validate_file

PROSE = "Vane closed the watch case. Mara wrote in her notebook by the bench."
REGISTRY = {
    "vane": ["Vane"], "mara": ["Mara"],
    "vane_watch": ["watch"], "mara_notebook": ["notebook"],
}
CANDIDATES = {"candidate:bench": ["bench"]}


def fixture():
    return build_review_packet(
        prose=PROSE, scene_key="synthetic_fixture",
        registry=REGISTRY, candidate_lexicon=CANDIDATES,
    )


def reviewed(alias="reviewer_A"):
    packet = fixture()
    form = blank_annotation(packet, reviewer_alias=alias)
    for i, row in enumerate(form["rows"]):
        row["disposition"] = "STATE_EVENT"
        row["notes"] = "Synthetic reviewer example; not actual human decision"
        for hint in row["entity_decisions"]:
            hint["decision"] = "PHYSICALLY_PRESENT"
            hint["reason"] = "Explicit noun phrase for synthetic fixture"
        snippet = "closed the watch case" if i == 0 else "wrote in her notebook"
        start = PROSE.index(snippet)
        row["events"] = [{
            "event_id": "event_close" if i == 0 else "event_write",
            "event_type": "CLOSE" if i == 0 else "WRITE",
            "start": start, "end": start + len(snippet),
            "quote": snippet,
            "epistemic": "OBSERVED_ACTION",
            "effect": "OBJECT" if i == 0 else "DOCUMENT",
            "entity_refs": ["vane_watch"] if i == 0 else
                           ["mara_notebook"],
            "reason": "Synthetic annotated operation",
        }]
    return packet, form


class BlindAnnotationV08Tests(unittest.TestCase):
    def test_blind_mara_form_has_28_source_rows_and_no_prior_analyst_suggestions(self):
        packet = generate_mara_packet()
        form = blank_annotation(packet, reviewer_alias="blind_A")
        self.assertEqual(len(form["rows"]), 28)
        self.assertEqual(form["status"], "IN_PROGRESS")
        self.assertNotIn("event_suggestions", form)
        self.assertNotIn("suggested_event_ids", form["rows"][0])
        self.assertNotIn("evt_s1_01", str(form))
        self.assertFalse(form["canonical_commit_authorized"])
        status = validate_annotation(packet=packet, annotation=form)
        self.assertEqual(status["reviewed_sentence_count"], 0)
        self.assertEqual(len(status["unreviewed_sentence_ids"]), 28)
        self.assertFalse(status["gold_qualified"])
        with self.assertRaisesRegex(CoverageError,
                                    "ANNOTATION_NOT_COMPLETE"):
            validate_annotation(packet=packet, annotation=form,
                                require_complete=True)

    def test_reviewed_synthetic_fixture_complete_but_not_gold(self):
        packet, form = reviewed()
        result = validate_annotation(
            packet=packet, annotation=form, require_complete=True,
        )
        self.assertEqual(result["reviewed_sentence_count"], 2)
        self.assertEqual(result["distinct_event_ids"], 2)
        self.assertTrue(result["fully_reviewed_claimed"])
        self.assertFalse(result["reviewer_identity_authenticated"])
        self.assertFalse(result["gold_qualified"])
        self.assertFalse(result["canonical_commit_authorized"])

    def test_partial_review_is_valid_progress_not_complete(self):
        packet, form = reviewed()
        form["rows"][1]["disposition"] = "UNREVIEWED"
        form["rows"][1]["events"] = []
        for hint in form["rows"][1]["entity_decisions"]:
            hint["decision"] = "UNREVIEWED"
            hint["reason"] = ""
        progress = validate_annotation(packet=packet, annotation=form)
        self.assertEqual(progress["status"], "PARTIAL_REVIEW_HOLD")
        self.assertEqual(progress["unreviewed_sentence_ids"], ["s002"])
        with self.assertRaisesRegex(CoverageError,
                                    "ANNOTATION_NOT_COMPLETE"):
            validate_annotation(packet=packet, annotation=form,
                                require_complete=True)

    def test_sentence_cannot_be_removed_or_duplicated(self):
        packet, form = reviewed()
        form["rows"].pop()
        with self.assertRaisesRegex(CoverageError,
                                    "ANNOTATION_SENTENCE_COUNT_INVALID"):
            validate_annotation(packet=packet, annotation=form)
        packet, form = reviewed()
        form["rows"][1] = deepcopy(form["rows"][0])
        with self.assertRaisesRegex(CoverageError,
                                    "ANNOTATION_SENTENCE_SOURCE_MISMATCH"):
            validate_annotation(packet=packet, annotation=form)

    def test_cannot_insert_fake_evidence_or_change_event_location(self):
        packet, form = reviewed()
        form["rows"][0]["events"][0]["quote"] = "Vane broke the clock"
        with self.assertRaisesRegex(CoverageError, "ANNOTATION_EVENT_INVALID"):
            validate_annotation(packet=packet, annotation=form)
        packet, form = reviewed()
        form["rows"][0]["events"][0]["start"] = form["rows"][1]["start"]
        with self.assertRaisesRegex(CoverageError, "ANNOTATION_EVENT_INVALID"):
            validate_annotation(packet=packet, annotation=form)

    def test_cannot_forge_gold_status_or_claim_authenticated_identity(self):
        packet, form = reviewed()
        form["gold_status"] = "GOLD"
        with self.assertRaisesRegex(
                CoverageError, "ANNOTATION_SOURCE_OR_AUTHORITY_INVALID"):
            validate_annotation(packet=packet, annotation=form)
        packet, form = reviewed()
        form["review_source"] = "SIGNED_HUMAN"
        with self.assertRaisesRegex(
                CoverageError, "ANNOTATION_SOURCE_OR_AUTHORITY_INVALID"):
            validate_annotation(packet=packet, annotation=form)

    def test_event_missing_from_state_change_sentence_rejected(self):
        packet, form = reviewed()
        form["rows"][0]["events"] = []
        with self.assertRaisesRegex(CoverageError, "ANNOTATION_EVENT_EXPECTED"):
            validate_annotation(packet=packet, annotation=form)

    def test_event_mislabeled_texture_does_not_silently_pass(self):
        packet, form = reviewed()
        form["rows"][0]["disposition"] = "TEXTURE"
        form["rows"][0]["events"] = []
        check = validate_annotation(packet=packet, annotation=form)
        self.assertIn("ANNOTATION_POSSIBLE_MISSED_EVENT:s001",
                      check["risk_findings"])
        self.assertFalse(check["gold_qualified"])

    def test_entity_hints_must_be_reviewed_with_reason(self):
        packet, form = reviewed()
        form["rows"][1]["entity_decisions"][0]["decision"] = "UNREVIEWED"
        form["rows"][1]["entity_decisions"][0]["reason"] = ""
        progress = validate_annotation(packet=packet, annotation=form)
        self.assertIn("HINT_UNREVIEWED:s002:",
                      " ".join(progress["risk_findings"]))
        with self.assertRaisesRegex(CoverageError, "ANNOTATION_NOT_COMPLETE"):
            validate_annotation(packet=packet, annotation=form,
                                require_complete=True)
        packet, form = reviewed()
        form["rows"][1]["entity_decisions"][0]["reason"] = ""
        with self.assertRaisesRegex(
                CoverageError, "ANNOTATION_ENTITY_REASON_REQUIRED"):
            validate_annotation(packet=packet, annotation=form)

    def test_reported_only_bench_from_physical_prose_requires_review(self):
        packet, form = reviewed()
        item = next(x for x in form["rows"][1]["entity_decisions"]
                    if x["ref"] == "candidate:bench")
        item["decision"] = "MENTIONED_ONLY"
        item["reason"] = "Synthetic disputed sighting"
        status = validate_annotation(packet=packet, annotation=form)
        self.assertIn("ANNOTATION_T2_DOWNGRADED:s002:candidate:bench",
                      status["risk_findings"])

    def test_review_event_can_have_multiple_evidence_spans(self):
        packet, form = reviewed()
        form["rows"][1]["events"][0]["event_id"] = "event_close"
        # Must be consistent for a cross-sentence event.
        form["rows"][1]["events"][0]["event_type"] = "CLOSE"
        form["rows"][1]["events"][0]["effect"] = "OBJECT"
        form["rows"][1]["events"][0]["entity_refs"] = ["vane_watch"]
        valid = validate_annotation(packet=packet, annotation=form)
        self.assertEqual(valid["reviewed_event_span_count"], 2)
        self.assertEqual(valid["distinct_event_ids"], 1)
        form["rows"][1]["events"][0]["effect"] = "DOCUMENT"
        with self.assertRaisesRegex(
                CoverageError,"ANNOTATION_CROSS_SENTENCE_EVENT_CONFLICT"):
            validate_annotation(packet=packet, annotation=form)

    def test_unscanned_entity_in_event_is_flagged_not_canonized(self):
        packet, form = reviewed()
        form["rows"][0]["events"][0]["entity_refs"].append("new:imaginary_watch")
        result = validate_annotation(packet=packet, annotation=form)
        self.assertIn(
            "ANNOTATION_UNGROUNDED_ENTITY_REF:s001:new:imaginary_watch",
            result["risk_findings"],
        )
        self.assertFalse(result["gold_qualified"])
        self.assertFalse(result["canonical_commit_authorized"])

    def test_evidence_reference_fingerprint_prevents_source_drift(self):
        packet, form = reviewed()
        form["source_packet_sha256"] = "a" * 64
        with self.assertRaisesRegex(
                CoverageError,"ANNOTATION_SOURCE_OR_AUTHORITY_INVALID"):
            validate_annotation(packet=packet, annotation=form)


class ComparisonV08Tests(unittest.TestCase):
    def test_agreeing_synthetic_reviewers_still_not_gold(self):
        packet, a = reviewed("independent_A")
        _, b = reviewed("independent_B")
        compared = compare_annotations(packet=packet, reviewer_a=a,
                                       reviewer_b=b)
        self.assertEqual(compared["agreed_sentence_ids"], ["s001", "s002"])
        self.assertEqual(compared["disagreements"], [])
        self.assertFalse(compared["reviewer_identities_authenticated"])
        self.assertTrue(compared["human_adjudication_required_for_gold"])
        self.assertFalse(compared["canonical_commit_authorized"])
        self.assertEqual(compared["production_db_writes"], 0)

    def test_disagreement_on_event_and_entity_is_explicit(self):
        packet, a = reviewed("independent_A")
        _, b = reviewed("independent_B")
        b["rows"][0]["events"][0]["event_type"] = "OPEN"
        b["rows"][1]["entity_decisions"][0]["decision"] = "REPORTED_ONLY"
        out = compare_annotations(packet=packet, reviewer_a=a,
                                  reviewer_b=b)
        self.assertEqual(len(out["disagreements"]), 2)
        self.assertIn("EVENT_EVIDENCE_OR_SEMANTICS",
                      out["disagreements"][0]["components"])
        self.assertIn("ENTITY_PRESENCE",
                      out["disagreements"][1]["components"])
        self.assertEqual(out["priority_sentence_ids"], ["s001", "s002"])

    def test_unfinished_review_and_downgraded_candidate_are_escalated(self):
        packet, a = reviewed("independent_A")
        _, b = reviewed("independent_B")
        b["rows"][0]["disposition"] = "UNREVIEWED"
        b["rows"][0]["events"] = []
        for entity in b["rows"][0]["entity_decisions"]:
            entity["decision"] = "UNREVIEWED"
            entity["reason"] = ""
        for entity in b["rows"][1]["entity_decisions"]:
            if entity["ref"] == "candidate:bench":
                entity["decision"] = "MENTIONED_ONLY"
                entity["reason"] = "Uncertain fixture example"
        out = compare_annotations(packet=packet, reviewer_a=a,
                                  reviewer_b=b)
        self.assertIn("s001", out["priority_sentence_ids"])
        self.assertIn("s002", out["priority_sentence_ids"])
        self.assertEqual(out["disagreements"][0]["category"], "INCOMPLETE")

    def test_same_reviewer_alias_cannot_pretend_independent(self):
        packet, a = reviewed("same")
        _, b = reviewed("same")
        with self.assertRaisesRegex(CoverageError,
                                    "ADJUDICATION_DUPLICATE_ALIAS"):
            compare_annotations(packet=packet, reviewer_a=a, reviewer_b=b)

class ExportedMaraReviewFormsV08Tests(unittest.TestCase):
    def test_two_blind_json_forms_are_exported_and_never_gold(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)
            summary = emit_forms(path)
            self.assertEqual(summary["sentence_count"], 28)
            self.assertFalse(summary["gold_qualified"])
            self.assertEqual(summary["model_calls"], 0)
            self.assertFalse(summary["canonical_commit_authorized"])
            files = [path / name for name in summary["exported"]]
            self.assertTrue(all(file.exists() for file in files))
            a = json.loads(files[0].read_text(encoding="utf-8"))
            b = json.loads(files[1].read_text(encoding="utf-8"))
            self.assertNotEqual(a["reviewer_alias"], b["reviewer_alias"])
            self.assertNotIn("evt_s1_01", files[0].read_text())
            self.assertEqual(len(a["rows"]), 28)
            self.assertTrue(all(r["disposition"] == "UNREVIEWED"
                                for r in b["rows"]))
            queue = compare_files(review_a=files[0], review_b=files[1])
            self.assertEqual(len(queue["disagreements"]), 28)
            self.assertEqual(queue["agreed_sentence_ids"], [])
            self.assertFalse(queue["canonical_commit_authorized"])
            self.assertEqual(queue["status"],
                             "NOT_GOLD_HUMAN_ADJUDICATION_REQUIRED")

    def test_downloaded_browser_form_can_be_validated_offline(self):
        with TemporaryDirectory() as folder:
            directory = Path(folder)
            files = emit_forms(directory)["exported"]
            sample = directory / files[0]
            incomplete = validate_file(review=sample)
            self.assertEqual(incomplete["reviewed_sentence_count"], 0)
            self.assertFalse(incomplete["gold_qualified"])
            self.assertFalse(incomplete["canonical_commit_authorized"])
            with self.assertRaisesRegex(CoverageError, "ANNOTATION_NOT_COMPLETE"):
                validate_file(review=sample, require_complete=True)

    def test_comparison_rejects_changed_source_form(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)
            summary = emit_forms(path)
            a = path / summary["exported"][0]
            b = path / summary["exported"][1]
            content = json.loads(a.read_text())
            content["rows"][0]["quote"] = "tampered"
            a.write_text(json.dumps(content))
            with self.assertRaisesRegex(
                CoverageError, "ANNOTATION_SENTENCE_SOURCE_MISMATCH"
            ):
                compare_files(review_a=a, review_b=b)



if __name__ == "__main__":
    unittest.main()
