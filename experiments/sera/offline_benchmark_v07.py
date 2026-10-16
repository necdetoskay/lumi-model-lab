"""SERA v0.7 — offline classification metrics with explicit reference provenance.

A candidate worksheet is NOT gold. Therefore this module refuses to output
precision/recall for the real Mara worksheet until independently adjudicated
reference labels exist. Built-in metric self-tests use synthetic-only fixtures.
No LLM, network, canonical commit or trusted human-identity attestation.
"""
from __future__ import annotations

from experiments.sera.coverage import CoverageError

LABELS = frozenset({
    "STATE_EVENT", "KNOWLEDGE_EVENT", "CLAIM_ONLY",
    "NO_TRACKED_CHANGE", "TEXTURE", "AMBIGUOUS",
})
STATES = frozenset({"SYNTHETIC_TEST_ONLY", "EXTERNALLY_REVIEWED_UNATTESTED"})
SCHEMA = "sera.sentence-benchmark.v0.7"


def require(ok, code):
    if not ok:
        raise CoverageError(code)


def _fraction(a, b):
    return a / b if b else 1.0


def _prf(reference: set, predicted: set) -> dict:
    tp = len(reference & predicted)
    fp = len(predicted - reference)
    fn = len(reference - predicted)
    precision = _fraction(tp, tp + fp)
    recall = _fraction(tp, tp + fn)
    f1 = 2 * precision * recall / (precision + recall) if (
        precision + recall
    ) else 0.0
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
    }


def compare_reviewed_labels(*, reference: dict, prediction: dict) -> dict:
    """Measure exact sentence entity/label keys, never state correctness.

    A string claiming external human review is not an authenticated review.
    Outputs remain diagnostics, not an actual evidence/commit gate.
    """
    require(isinstance(reference, dict) and
            reference.get("schema") == SCHEMA and
            reference.get("reference_kind") in STATES,
            "BENCHMARK_REFERENCE_NOT_REVIEWED")
    require(isinstance(prediction, dict) and
            prediction.get("schema") == SCHEMA and
            prediction.get("prose_sha256") == reference.get("prose_sha256") and
            prediction.get("scene_key") == reference.get("scene_key"),
            "BENCHMARK_SOURCE_MISMATCH")
    gold = reference.get("rows")
    proposed = prediction.get("rows")
    require(isinstance(gold, list) and
            isinstance(proposed, list) and
            all(isinstance(x, dict) and set(x) ==
                {"sentence_id", "labels", "entity_refs"}
                for x in gold + proposed),
            "BENCHMARK_ROW_SCHEMA_INVALID")
    def indexed(rows):
        result = {}
        for row in rows:
            sid = row["sentence_id"]
            require(isinstance(sid, str) and sid and sid not in result and
                    isinstance(row["labels"], list) and
                    isinstance(row["entity_refs"], list) and
                    len(row["labels"]) == len(set(row["labels"])) and
                    len(row["entity_refs"]) == len(set(row["entity_refs"])) and
                    set(row["labels"]) <= LABELS and
                    all(isinstance(ref, str) and ref
                        for ref in row["entity_refs"]),
                    "BENCHMARK_ROW_VALUES_INVALID")
            result[sid] = row
        return result
    gold_map = indexed(gold)
    pred_map = indexed(proposed)
    require(gold_map and set(gold_map) == set(pred_map),
            "BENCHMARK_SENTENCE_SET_MISMATCH")
    label_truth = {
        (sid, v) for sid, row in gold_map.items() for v in row["labels"]
    }
    label_pred = {
        (sid, v) for sid, row in pred_map.items() for v in row["labels"]
    }
    entity_truth = {
        (sid, v) for sid, row in gold_map.items()
        for v in row["entity_refs"]
    }
    entity_pred = {
        (sid, v) for sid, row in pred_map.items()
        for v in row["entity_refs"]
    }
    return {
        "schema": "sera.sentence-benchmark-result.v0.7",
        "reference_kind": reference["reference_kind"],
        "reference_authenticity_verified": False,
        "source_prose_sha256": reference["prose_sha256"],
        "sentence_count": len(gold_map),
        "sentence_labels": _prf(label_truth, label_pred),
        "entity_mentions": _prf(entity_truth, entity_pred),
        "eligible_for_canonical_state_commit": False,
        "real_mara_gold_qualified": False,
        "assurance_status": "BENCHMARK_ONLY",
    }


def summarize_unreviewed_packet(packet: dict) -> dict:
    require(isinstance(packet, dict) and
            packet.get("schema") == "sera.sentence-review-packet.v0.7" and
            packet.get("source_type") == "CANDIDATE_WORKSHEET_NOT_GOLD" and
            packet.get("review_status") == "UNREVIEWED",
            "BENCHMARK_PACKET_NOT_UNREVIEWED")
    return {
        "schema": "sera.unreviewed-reference-status.v0.7",
        "source_prose_sha256": packet["prose_sha256"],
        "sentence_count": len(packet["sentences"]),
        "analyst_candidate_count": len(packet["event_suggestions"]),
        "entity_recall": None, "entity_precision": None,
        "event_recall": None, "event_precision": None,
        "reason": "NO_ADJUDICATED_GOLD_REFERENCE",
        "canonical_commit_authorized": False,
    }
