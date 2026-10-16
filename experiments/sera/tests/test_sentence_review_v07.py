"""SERA v0.7 regression — frozen Mara worksheet, blind extraction and metrics."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from experiments.sera.coverage import (
    CoverageError, EXTRACTION_SCHEMA, prose_hash,
)
from experiments.sera.sentence_review_packet_v07 import (
    build_review_packet, generate_mara_packet, validate_review_packet,
)
from experiments.sera.independent_ledger_bridge_v07 import (
    bind_independent_to_ledger,
)
from experiments.sera.offline_benchmark_v07 import (
    compare_reviewed_labels, summarize_unreviewed_packet, SCHEMA as BENCH,
)
from experiments.sera.mara_s1_v04_audit import PATH, EXPECTED_SHA

LEXICON = {
    "candidate:bench": ["bench"],
    "candidate:pencil": ["pencil"],
}


def blind_report(prose, *, start=0, end=None, event_type="TELL_FACT"):
    if end is None:
        end = len(prose)
    return {
        "schema": EXTRACTION_SCHEMA,
        "source_role": "INDEPENDENT",
        "scene_key": "hook_empty_platform",
        "entry_revision": 0,
        "prose_sha256": prose_hash(prose),
        "mentions": [
            {"entity_ref": "vane", "role": "PRESENT",
             "start": 0, "end": 4}
        ],
        "events": [{
            "local_id": "vane_claim",
            "type": event_type,
            "arguments": {"from": "vane", "to": "mara",
                          "claim": "Vane reports no physical train"},
            "at": None, "modality": "REPORTED",
            "start": start, "end": end,
        }],
    }


class ReviewPacketV07Tests(unittest.TestCase):
    def test_frozen_mara_has_28_unreviewed_source_bound_rows_and_nine_suggestions(self):
        packet = generate_mara_packet()
        prose = json.loads(PATH.read_text(encoding="utf-8"))["prose"]
        summary = validate_review_packet(prose=prose, packet=packet)
        self.assertEqual(summary["sentence_count"], 28)
        self.assertEqual(summary["status"],
                         "PENDING_EXTERNAL_HUMAN_ADJUDICATION")
        self.assertEqual(packet["prose_sha256"], EXPECTED_SHA)
        self.assertEqual(len(packet["event_suggestions"]), 9)
        self.assertTrue(all(x["review"]["status"] == "UNREVIEWED"
                            for x in packet["sentences"]))
        self.assertTrue(all(x["review"]["labels"] == []
                            for x in packet["sentences"]))
        hints = {ref["ref"] for item in packet["sentences"]
                 for ref in item["entity_hints"]}
        self.assertIn("candidate:bench", hints)
        self.assertIn("candidate:pencil", hints)
        self.assertFalse(packet["adjudicated_gold"])
        self.assertFalse(packet["canonical_commit_authorized"])

    def test_reference_edit_or_source_change_fails_closed(self):
        original = generate_mara_packet()
        prose = json.loads(PATH.read_text(encoding="utf-8"))["prose"]
        edited = deepcopy(original)
        edited["sentences"][0]["review"]["labels"] = ["STATE_EVENT"]
        with self.assertRaisesRegex(CoverageError, "REVIEW_PACKET_DIGEST_MISMATCH"):
            validate_review_packet(prose=prose, packet=edited)
        with self.assertRaisesRegex(CoverageError,
                                    "REVIEW_PACKET_SOURCE_OR_AUTHORITY_INVALID"):
            validate_review_packet(prose=prose + " Modified", packet=original)

    def test_manually_forged_gold_status_does_not_pass(self):
        original = generate_mara_packet()
        prose = json.loads(PATH.read_text(encoding="utf-8"))["prose"]
        changed = deepcopy(original)
        changed["review_status"] = "HUMAN_VERIFIED"
        with self.assertRaisesRegex(CoverageError,
                                    "REVIEW_PACKET_SOURCE_OR_AUTHORITY_INVALID"):
            validate_review_packet(prose=prose, packet=changed)

    def test_tampered_analyst_evidence_quote_is_rejected(self):
        source = json.loads(PATH.read_text(encoding="utf-8"))
        candidates = deepcopy(source["candidates"])
        candidates[0]["evidence"]["quote"] = "not what story says"
        with self.assertRaisesRegex(CoverageError,
                                    "REVIEW_PACKET_EVENT_EVIDENCE_INVALID"):
            build_review_packet(
                prose=source["prose"], scene_key=source["scene_id"],
                registry={"mara": ["Mara"]},
                candidate_lexicon=LEXICON,
                analyst_candidates=candidates,
            )


class IndependentBindingV07Tests(unittest.TestCase):
    def test_one_extraction_event_can_link_to_multiple_sentence_ledger_rows(self):
        prose = "Vane said he waited. He saw no train beside the bench."
        result = bind_independent_to_ledger(
            prose=prose, scene_key="hook_empty_platform",
            entry_revision=0,
            registry={"vane": ["Vane"]},
            candidate_lexicon=LEXICON,
            report=blind_report(prose),
        )
        self.assertEqual(result["source_role"], "INDEPENDENT")
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(len(result["event_links"]), 1)
        self.assertEqual(result["event_links"][0]["sentence_ids"],
                         ["s001", "s002"])
        self.assertEqual(
            result["ledger_validation"]["distinct_narrative_events"], 1,
        )
        self.assertEqual(
            result["ledger_validation"]["event_evidence_count"], 2,
        )
        self.assertEqual(
            result["assurance"]["ledger_validation"]["accounted_sentences"], 2,
        )
        self.assertIn("INDEPENDENT_UNREPORTED_SCAN_HINT:s002:candidate:bench",
                      result["scan_findings"])
        self.assertIn("M2_SINGLE_SOURCE_UNRECONCILED",
                      result["assurance"]["findings"])
        self.assertNotIn("INDEPENDENT_EXTRACTION_NOT_PERFORMED",
                         result["assurance"]["findings"])
        self.assertEqual(result["model_calls_during_binding"], 0)
        self.assertEqual(result["world_db_writes"], 0)
        self.assertFalse(result["canonical_commit_authorized"])

    def test_fabricated_quote_offsets_cannot_be_linked(self):
        prose = "Vane said he waited. He saw no train beside the bench."
        report = blind_report(prose)
        report["events"][0]["end"] = len(prose)+5
        with self.assertRaisesRegex(CoverageError, "EVENT_OFFSET_INVALID"):
            bind_independent_to_ledger(
                prose=prose, scene_key="hook_empty_platform",
                entry_revision=0, registry={"vane":["Vane"]},
                candidate_lexicon=LEXICON, report=report,
            )

    def test_writer_pretending_to_be_independent_is_rejected(self):
        prose = "Vane said he waited. He saw no train beside the bench."
        report = blind_report(prose)
        report["source_role"] = "WRITER"
        with self.assertRaisesRegex(CoverageError,"SOURCE_ROLE_INVALID"):
            bind_independent_to_ledger(
                prose=prose, scene_key="hook_empty_platform",
                entry_revision=0, registry={"vane":["Vane"]},
                candidate_lexicon=LEXICON, report=report,
            )


class BenchmarkV07Tests(unittest.TestCase):
    def test_real_mara_review_packet_has_no_unearned_precision_or_recall(self):
        packet = generate_mara_packet()
        result = summarize_unreviewed_packet(packet)
        self.assertIsNone(result["event_recall"])
        self.assertIsNone(result["entity_precision"])
        self.assertEqual(result["reason"], "NO_ADJUDICATED_GOLD_REFERENCE")
        self.assertFalse(result["canonical_commit_authorized"])
        with self.assertRaisesRegex(CoverageError,
                                    "BENCHMARK_REFERENCE_NOT_REVIEWED"):
            compare_reviewed_labels(reference=packet, prediction=packet)

    def test_synthetic_fixture_measures_false_positive_and_false_negative(self):
        reference = {
            "schema": BENCH, "reference_kind": "SYNTHETIC_TEST_ONLY",
            "scene_key": "fixture", "prose_sha256": "synthetic",
            "rows": [
                {"sentence_id":"s001", "labels":["STATE_EVENT"],
                 "entity_refs":["mara","new:pencil"]},
                {"sentence_id":"s002", "labels":["CLAIM_ONLY"],
                 "entity_refs":["vane"]},
            ],
        }
        predicted = deepcopy(reference)
        predicted["rows"][0]["entity_refs"] = ["mara", "new:bench"]
        predicted["rows"][1]["labels"] = ["STATE_EVENT"]
        result = compare_reviewed_labels(
            reference=reference, prediction=predicted,
        )
        self.assertEqual(result["entity_mentions"]["tp"], 2)
        self.assertEqual(result["entity_mentions"]["fp"], 1)
        self.assertEqual(result["entity_mentions"]["fn"], 1)
        self.assertEqual(result["sentence_labels"]["recall"], 0.5)
        self.assertEqual(result["sentence_labels"]["precision"], 0.5)
        self.assertFalse(result["real_mara_gold_qualified"])
        self.assertFalse(result["eligible_for_canonical_state_commit"])

    def test_unreviewed_or_mismatched_source_not_scored(self):
        fixture = {
            "schema": BENCH, "reference_kind": "SYNTHETIC_TEST_ONLY",
            "scene_key": "fixture", "prose_sha256": "sha",
            "rows": [{"sentence_id":"s001", "labels": [],
                      "entity_refs": []}],
        }
        prediction = deepcopy(fixture)
        prediction["prose_sha256"] = "altered"
        with self.assertRaisesRegex(CoverageError,
                                    "BENCHMARK_SOURCE_MISMATCH"):
            compare_reviewed_labels(reference=fixture, prediction=prediction)


if __name__ == "__main__":
    unittest.main()
