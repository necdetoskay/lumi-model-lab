"""General semantic-gap queue: exact string mismatch never auto-accepts meaning."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.q25_semantic_gap_queue import make_queue

KITE = Path("evidence/q25/Q25-WITHHELD-TRIAL-20261012")
GREENHOUSE = Path("evidence/q25/Q25-GREENHOUSE-COLD-TRIAL-20261012")


def data(directory, response):
    read = lambda name: json.loads((directory / name).read_text(encoding="utf8"))
    return dict(
        request_package=read("request.json"),
        reference_package=read("provisional-reference.json"),
        raw_response=read(response),
    )


def test_real_kite_semantic_pairs_are_not_automatically_accepted():
    kw = data(KITE, "paid-attempt-03-raw-extraction.json")
    before = copy.deepcopy(kw)
    report = make_queue(**kw)
    assert report["request_id"] == "KITE-01"
    assert report["raw_identity_overlap"] == 14
    assert report["meaning_pairs_not_decided"] == 2
    assert len(report["paired_meaning_review"]) == 2
    assert report["unpaired_extra_claims"] == []
    assert report["unpaired_missing_claims"] == []
    assert {tuple(x["semantic_slot"][:3]) for x in report["paired_meaning_review"]} == {
        ("character_claims", "Bora", "knowledge"),
        ("character_claims", "Defne", "knowledge"),
    }
    assert len(report["matching_identity_different_excerpt"]) == 11
    assert all(x["independent_decision"] is None for x in report["paired_meaning_review"])
    assert all(x["disposition"] == "REVIEW_MEANING_EQUIVALENCE_NOT_AUTO_MATCHED"
               for x in report["paired_meaning_review"])
    assert report["independently_authenticated_reviewer"] is False
    assert report["semantic_equivalence_certified"] is False
    assert report["complete_state_certified"] is False
    assert report["state_commit_authorized"] is False
    assert report["provider_calls"] == 0
    assert kw == before
    assert make_queue(**kw) == report


def test_distinct_greenhouse_reference_self_score_means_no_model_success():
    kw = data(GREENHOUSE, "provisional-reference.json")
    kw["raw_response"] = kw["reference_package"]["raw_reference"]
    report = make_queue(**kw)
    assert report["request_id"] == "GREENHOUSE-01"
    assert report["raw_identity_overlap"] == 16
    assert report["meaning_pairs_not_decided"] == 0
    assert report["paired_meaning_review"] == []
    assert report["matching_identity_different_excerpt"] == []
    assert report["complete_state_certified"] is False
    assert report["provider_calls"] == 0


def test_one_sided_missing_claim_is_not_conjured_from_a_other_actor():
    kw = data(KITE, "paid-attempt-03-raw-extraction.json")
    kw["raw_response"]["character_claims"] = [
        c for c in kw["raw_response"]["character_claims"]
        if c["actor"] != "Defne"]
    report = make_queue(**kw)
    assert report["meaning_pairs_not_decided"] == 1
    assert len(report["unpaired_missing_claims"]) == 1
    assert report["unpaired_missing_claims"][0]["identity"][0] == "Defne"
    assert report["semantic_equivalence_certified"] is False


@pytest.mark.parametrize("damage", [
    "seed_change", "prose_change", "forged_label", "fabricated_quote",
    "bad_relation", "label_identity_change",
])
def test_rejected_or_unbound_candidates_cannot_reach_review_queue(damage):
    kw = data(KITE, "paid-attempt-03-raw-extraction.json")
    if damage == "seed_change":
        kw["request_package"]["seed"]["objects"]["red_kite"]["state"]["ready"] = True
    elif damage == "prose_change":
        kw["request_package"]["prose_record"]["text"] += " FALSE."
    elif damage == "forged_label":
        kw["reference_package"]["review_status"] = "ACCEPTED"
    elif damage == "fabricated_quote":
        kw["raw_response"]["objects"][0]["mention"]["quote"] = "not in story"
    elif damage == "bad_relation":
        kw["raw_response"]["terminal_relations"][0]["subject"] = "blue_string"
    elif damage == "label_identity_change":
        kw["reference_package"]["request_id"] = "NOPE"
    with pytest.raises(ValueError):
        make_queue(**kw)


def test_cli_echoes_queue_read_only():
    cmd = [
        sys.executable, "-X", "utf8", "-m", "src.q25_semantic_gap_queue",
        "--request-package", str(KITE / "request.json"),
        "--reference-package", str(KITE / "provisional-reference.json"),
        "--raw-response", str(KITE / "paid-attempt-03-raw-extraction.json"),
    ]
    report = json.loads(subprocess.check_output(cmd, text=True, encoding="utf8"))
    assert report == make_queue(**data(KITE, "paid-attempt-03-raw-extraction.json"))
    assert report["semantic_equivalence_certified"] is False
