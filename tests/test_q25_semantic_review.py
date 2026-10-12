"""Q25 semantic review is read-only; self-attested judgments grant no authority."""
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.q25_semantic_review import (
    build_review_packet, record_review, review_packet_digest,
)

ROOT = Path("evidence/q25")
BASE = ROOT / "Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24"
RAW = ROOT / "Q25-STORY-STATE-CANDIDATES-20261012/raw-extractor-replay.json"
POLICY = ROOT / "Q25-ADMISSION-DRAFT-20261012/policy.json"


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def fixture():
    return dict(seed=read(BASE / "seed-input.json"),
                prose=read(BASE / "writer-2-text.json")["text"],
                raw_output=read(RAW), policy=read(POLICY))


def candidate_review(packet, support="SUPPORTED"):
    return {
        "schema_name": "q25.semantic-review-response.v1",
        "packet_sha256": review_packet_digest(packet),
        "reviewer_label": "external-reviewer-claim",
        "verdicts": [{
            "claim_id": item["claim_id"], "semantic_support": support,
            "temporal_scope": "TERMINAL", "epistemic_status": "OBSERVED",
            "note": "Independent semantic examination is claimed, not authenticated."
        } for item in packet["candidates"]],
    }


def test_packet_contains_every_source_bound_candidate_without_authority():
    args = fixture()
    before = copy.deepcopy(args)
    packet = build_review_packet(**args)
    assert packet["candidate_count"] == 15
    assert len({x["claim_id"] for x in packet["candidates"]}) == 15
    assert {x["group"] for x in packet["candidates"]} == {
        "objects", "terminal_relations", "character_claims",
        "goal_claims", "obligation_claims", "thread_claims",
        "property_claims",
    }
    assert packet["unresolved_terminal_fields"] == 70
    assert packet["coverage_counts"]["UNKNOWN"] == 2
    for item in packet["candidates"]:
        assert item["citations"] and item["status"] == "PENDING_INDEPENDENT_SEMANTIC_REVIEW"
        for span in item["citations"]:
            assert args["prose"][span["start"]:span["end"]] == span["text"]
        assert len(item["claim_sha256"]) == 64
    assert packet["review_status"] == "AWAITING_EXTERNAL_REVIEW"
    assert not packet["semantic_support_certified"]
    assert not packet["full_story_state_qualified"]
    assert not packet["state_commit_authorized"]
    assert packet["provider_calls"] == 0
    assert args == before
    assert packet == build_review_packet(**args)


def test_self_reported_all_supported_is_still_not_semantic_certification():
    packet = build_review_packet(**fixture())
    response = candidate_review(packet)
    before = copy.deepcopy((packet, response))
    result = record_review(packet=packet, response=response)
    assert result["support_counts"]["SUPPORTED"] == 15
    assert result["item_count"] == 15
    assert result["status"] == "SELF_REPORTED_REVIEW_LABELS_UNVERIFIED"
    assert result["independent_reviewer_authenticated"] is False
    assert result["semantic_support_certified"] is False
    assert result["state_commit_authorized"] is False
    assert result["full_story_state_qualified"] is False
    assert result["provider_calls"] == 0
    assert (packet, response) == before
    assert result == record_review(packet=packet, response=response)


@pytest.mark.parametrize("malformation", [
    "wrong_packet_hash", "missing_review", "duplicate_review",
    "unknown_claim", "bad_support", "bad_epistemic", "empty_explanation",
    "invented_authority", "no_reviewer",
])
def test_malformed_or_forged_review_rejected(malformation):
    packet = build_review_packet(**fixture())
    response = candidate_review(packet)
    if malformation == "wrong_packet_hash":
        response["packet_sha256"] = "0" * 64
    elif malformation == "missing_review":
        response["verdicts"].pop()
    elif malformation == "duplicate_review":
        response["verdicts"].append(response["verdicts"][0].copy())
    elif malformation == "unknown_claim":
        response["verdicts"][0]["claim_id"] = "invented:1:deadcafe0000"
    elif malformation == "bad_support":
        response["verdicts"][0]["semantic_support"] = "ACCEPTED"
    elif malformation == "bad_epistemic":
        response["verdicts"][0]["epistemic_status"] = "CERTIFIED_FACT"
    elif malformation == "empty_explanation":
        response["verdicts"][0]["note"] = ""
    elif malformation == "invented_authority":
        response["state_commit_authorized"] = True
    elif malformation == "no_reviewer":
        response["reviewer_label"] = ""
    with pytest.raises((ValueError, ValidationError)):
        record_review(packet=packet, response=response)


@pytest.mark.parametrize("tamper", ["source_hash", "invented_actor", "decisive_clue"])
def test_review_packet_rejects_untrusted_extractor_bypass(tamper):
    args = fixture()
    if tamper == "source_hash":
        args["raw_output"]["source_sha256"] = "0" * 64
    elif tamper == "invented_actor":
        args["raw_output"]["character_claims"][0]["actor"] = "NeverSeen"
    elif tamper == "decisive_clue":
        args["raw_output"]["objects"][0]["role"] = "DECISIVE_CLUE"
    with pytest.raises((ValueError, ValidationError)):
        build_review_packet(**args)


def test_cli_source_bound_packet_replay_unchanged_and_no_write():
    srcs = [BASE / "seed-input.json", BASE / "writer-2-text.json", RAW, POLICY]
    hashes = [hashlib.sha256(f.read_bytes()).hexdigest() for f in srcs]
    cmd = [sys.executable, "-m", "src.q25_semantic_review",
           "--seed", str(srcs[0]), "--prose-record", str(srcs[1]),
           "--raw-response", str(srcs[2]), "--policy", str(srcs[3])]
    payload = json.loads(subprocess.check_output(cmd, encoding="utf8"))
    assert payload == build_review_packet(**fixture())
    assert hashes == [hashlib.sha256(f.read_bytes()).hexdigest() for f in srcs]
