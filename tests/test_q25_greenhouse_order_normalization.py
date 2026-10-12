"""Reproduce genuine greenhouse rejection and safe source-order-only replay.

Historical paid outcome stays REJECTED, despite later upgraded read-only adapter.
There are no API calls, semantic repairs or canonical state writes.
"""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from src.q25_extractor_adapter import materialize_quotes, offline_replay
from src.q25_entity_candidates import fingerprint
from src.q25_semantic_gap_queue import make_queue
from src.q25_raw_reconciliation import project_raw
from src.q25_withheld_trial import evaluate

BASE = Path("evidence/q25/Q25-GREENHOUSE-COLD-TRIAL-20261012")


def load(name):
    return json.loads((BASE / name).read_text(encoding="utf8"))


def args():
    request = load("request.json")
    return dict(
        seed=request["seed"], prose=request["prose_record"]["text"],
        policy=request["policy"],
        raw_output=load("paid-attempt-01-raw-extraction.json"),
    )


def test_original_failed_paid_run_and_new_offline_replay_are_distinct():
    ledger = load("paid-attempt-01-public-ledger.json")
    assert ledger["outcome"] == "REJECTED_BY_OFFLINE_GATE"
    assert ledger["gate_failure_type"] == "ValueError"
    assert ledger["attempted_calls"] == ledger["provider_calls"] == 1
    assert ledger["usage"]["actual_cost_usd"] == 0.042746
    assert ledger["usage"]["prompt_tokens"] == 6903
    assert ledger["usage"]["completion_tokens"] == 2894
    assert ledger["model_schema_profile"] == "ANTHROPIC_STRICT_V1"
    raw_args = args()
    original = copy.deepcopy(raw_args)
    old_hash = fingerprint(raw_args["raw_output"])
    upgraded = offline_replay(**raw_args)
    assert upgraded["status"] == "SOURCE_BOUND_CANDIDATES_ONLY"
    assert upgraded["evidence_order_adjustments"] == [{
        "group": "obligation_claims", "ordinal": 2,
        "original_offsets": [1373, 1190],
        "canonical_offsets": [1190, 1373],
        "reason": "SOURCE_POSITION_SORT_ONLY_NOT_SEMANTIC_REPAIR",
    }]
    assert upgraded["coverage"]["counts"] == {
        "CANDIDATE": 14, "PARTIAL_CANDIDATES": 1,
        "STRUCTURAL_ONLY": 23, "UNASSESSED": 14, "UNKNOWN": 2,
    }
    assert upgraded["state_commit_authorized"] is False
    assert upgraded["full_story_state_qualified"] is False
    assert old_hash == fingerprint(raw_args["raw_output"])
    assert raw_args == original
    assert load("paid-attempt-01-public-ledger.json")["outcome"] == (
        "REJECTED_BY_OFFLINE_GATE")


def test_model_quote_citations_are_ordered_only_after_exact_verification():
    d = args()
    original = copy.deepcopy(d["raw_output"])
    projection = materialize_quotes(seed=d["seed"], prose=d["prose"],
                                    raw_output=d["raw_output"])
    actual = projection["story_proposal"]["obligation_claims"][1]["evidence"]
    assert [span["start"] for span in actual] == [1190, 1373]
    assert all(d["prose"][span["start"]:span["end"]] == span["text"]
               for span in actual)
    assert projection["raw_output_sha256"] == fingerprint(d["raw_output"])
    assert d["raw_output"] == original


@pytest.mark.parametrize("damage", [
    "same_span_repeated", "fabricated_quote", "broken_source_hash",
    "unqualified_subject", "invalid_actor", "changed_truth_value",
    "fake_state_commit",
])
def test_chronology_normalizer_never_masks_fabrication_or_danger(damage):
    kw = args()
    raw = kw["raw_output"]
    if damage == "same_span_repeated":
        raw["obligation_claims"][1]["evidence"][1] = copy.deepcopy(
            raw["obligation_claims"][1]["evidence"][0])
    elif damage == "fabricated_quote":
        raw["obligation_claims"][1]["evidence"][1]["quote"] = "Suddenly the greenhouse flew away."
    elif damage == "broken_source_hash":
        raw["source_sha256"] = "0" * 64
    elif damage == "unqualified_subject":
        raw["terminal_relations"][0]["subject"] = "blue_tarp"
    elif damage == "invalid_actor":
        raw["character_claims"][0]["actor"] = "Invented"
    elif damage == "changed_truth_value":
        raw["property_claims"][0]["proposed_terminal_value"] = "false"
    elif damage == "fake_state_commit":
        raw["state_commit_authorized"] = True
    with pytest.raises(ValueError):
        offline_replay(**kw)


def test_generic_reconciliation_remains_unverified_even_with_sorted_quotes():
    kw = args()
    report = project_raw(**kw)
    assert report["schema"] == "q25.raw-terminal-hypothesis.v1"
    assert report["blocking_field_count"] == 54
    assert report["state_commit_authorized"] is False
    assert report["production_write_performed"] is False
    assert report["independent_semantic_review_completed"] is False
    assert report["candidate_state"]["proposed_world_time"] is None
    assert report["candidate_state"]["world_time_unassessed"] is True
    assert report["candidate_state"]["objects"]["roof_vent"]["properties"]["open"][
        "terminal_proposal"] is False
    assert report["candidate_state"]["objects"]["blue_tarp"]["location"]["ref"] == (
        "greenhouse")
    assert report["approved_obligation_closures"] == []


def test_provisional_identity_score_not_semantic_accuracy_or_human_review():
    d = args()
    request = load("request.json")
    reference = load("provisional-reference.json")
    measured = evaluate(
        request_package=request, reference_package=reference,
        raw_response=d["raw_output"], origin="ARCHIVED_REJECTED_PAID_RUN_REPLAYED_OFFLINE")
    assert measured["overall"]["true_positive"] == 13
    assert measured["overall"]["false_positive"] == 4
    assert measured["overall"]["false_negative"] == 3
    assert measured["overall"]["precision"] == pytest.approx(13/17)
    assert measured["overall"]["recall"] == pytest.approx(13/16)
    assert measured["overall"]["f1"] == pytest.approx(26/33)
    assert measured["reference_labels_independently_adjudicated"] is False
    assert measured["real_model_success_measured"] is False
    gaps = make_queue(
        request_package=request, reference_package=reference,
        raw_response=d["raw_output"])
    assert gaps["raw_identity_overlap"] == 13
    assert gaps["independently_authenticated_reviewer"] is False
    assert gaps["semantic_equivalence_certified"] is False
    assert gaps["provider_calls"] == 0


def test_evidence_immutable_before_and_after_replay():
    paths = [BASE / name for name in [
        "request.json", "provisional-reference.json",
        "paid-attempt-01-raw-extraction.json",
        "paid-attempt-01-public-ledger.json",
    ]]
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    assert offline_replay(**args())["status"] == "SOURCE_BOUND_CANDIDATES_ONLY"
    assert before == [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
