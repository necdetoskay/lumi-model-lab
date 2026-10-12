"""Q25 review worklist: unresolved claims stay unresolved, with cited questions."""
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.q25_review_worklist import build_worklist

ROOT = Path("evidence/q25")
Q24 = ROOT / "Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24"
CAND = ROOT / "Q25-STORY-STATE-CANDIDATES-20261012"
ENTITY = ROOT / "Q25-ENTITY-CANDIDATE-20261012/proposal.json"
POLICY = ROOT / "Q25-ADMISSION-DRAFT-20261012/policy.json"
STORY = CAND / "story-proposal-knowledge-extension.json"
PROPERTY = CAND / "property-proposal.json"
ISSUES = CAND / "review-gap-annotations.json"


def load(path):
    return json.loads(path.read_text(encoding="utf8"))


def frozen():
    return dict(
        seed=load(Q24 / "seed-input.json"),
        prose=load(Q24 / "writer-2-text.json")["text"],
        entity_proposal=load(ENTITY),
        policy=load(POLICY),
        story_proposal=load(STORY),
        property_proposal=load(PROPERTY),
        annotations=load(ISSUES),
    )


def test_q24_worklist_preserves_explicit_ambiguity_and_every_other_gap():
    inputs = frozen()
    before = copy.deepcopy(inputs)
    result = build_worklist(**inputs)
    assert result["blocking_field_count"] == 70
    assert result["coverage_counts"] == {
        "CANDIDATE": 12, "PARTIAL_CANDIDATES": 3,
        "STRUCTURAL_ONLY": 23, "UNASSESSED": 30, "UNKNOWN": 2,
    }
    assert result["triaged_issue_count"] == 11
    assert result["untriaged_field_count"] == 59
    assert result["triaged_issue_count"] + result["untriaged_field_count"] == 70
    issues = {x["issue_id"]: x for x in result["issues"]}
    bookmark = issues["bookmark_return_semantics"]
    assert bookmark["target_path"] == "/objects/red_bookmark/properties/returned_to_owner"
    assert bookmark["coverage_status"] == "UNASSESSED"
    assert len(bookmark["supporting_evidence"]) == 2
    apology = issues["apology_without_instant_intimacy"]
    assert apology["coverage_status"] == "CANDIDATE"
    assert len(apology["supporting_evidence"]) == 2
    assert len(apology["competing_evidence"]) == 2
    assert issues["reading_book_owner"]["coverage_status"] == "UNKNOWN"
    assert issues["reading_book_location"]["coverage_status"] == "UNKNOWN"
    assert issues["nisa_knowledge_completeness"]["coverage_status"] == "PARTIAL_CANDIDATES"
    assert issues["suspicion_thread_scope"]["coverage_status"] == "CANDIDATE"
    assert all(x["review_decision"] == "PENDING_INDEPENDENT_ADJUDICATION"
               for x in result["issues"])
    assert result["independently_certified_closed_obligations"] == []
    assert set(result["proposed_closed_obligations"]) == {
        "investigate_evidence", "recover_bookmark", "correct_and_apologize",
    }
    assert set(result["contested_or_unverified_obligations"]) == set(
        result["proposed_closed_obligations"])
    assert result["review_status"] == "REVIEW_WORKLIST_ONLY_NO_SEMANTIC_CERTIFICATION"
    assert not result["state_commit_authorized"]
    assert not result["semantic_support_certified"]
    assert not result["full_story_state_qualified"]
    assert result["provider_calls"] == 0
    assert result == build_worklist(**inputs)
    assert inputs == before


@pytest.mark.parametrize("damage", [
    "seed_hash", "source_hash", "story_hash", "property_hash",
    "invented_path", "duplicate_issue_id", "duplicate_target",
    "invalid_support_quote", "invalid_competing_quote",
    "reverse_support", "no_quotes", "unsupported_issue_type",
    "add_commit_authority", "fake_approval", "new_decisive_clue",
    "modified_seed",
])
def test_untrusted_or_stale_triage_cannot_bypass_coverage_gates(damage):
    kw = frozen()
    issues = kw["annotations"]["issues"]
    if damage.endswith("_hash"):
        kw["annotations"][damage.replace("_hash", "") + "_proposal_sha256"
                          if damage in ("story_hash", "property_hash")
                          else damage.replace("_hash", "") + "_sha256"] = "0" * 64
    elif damage == "invented_path":
        issues[0]["target_path"] = "/objects/invented/owner"
    elif damage == "duplicate_issue_id":
        issues[1]["issue_id"] = issues[0]["issue_id"]
    elif damage == "duplicate_target":
        issues[1]["target_path"] = issues[0]["target_path"]
    elif damage == "invalid_support_quote":
        issues[0]["supporting_evidence"][0]["text"] = "Invented terminal action"
    elif damage == "invalid_competing_quote":
        issues[1]["competing_evidence"][0]["end"] += 1
    elif damage == "reverse_support":
        issues[0]["supporting_evidence"].reverse()
    elif damage == "no_quotes":
        issues[0]["supporting_evidence"] = []
    elif damage == "unsupported_issue_type":
        issues[0]["issue_type"] = "AUTOMATICALLY_APPROVED"
    elif damage == "add_commit_authority":
        kw["annotations"]["state_commit_authorized"] = True
    elif damage == "fake_approval":
        issues[0]["review_decision"] = "CERTIFIED"
    elif damage == "new_decisive_clue":
        kw["entity_proposal"]["objects"][0]["role"] = "DECISIVE_CLUE"
    elif damage == "modified_seed":
        kw["seed"]["characters"]["Nisa"]["location"] = "invented_place"
    with pytest.raises((ValueError, ValidationError)):
        build_worklist(**kw)


def test_read_only_cli_matches_function_and_preserves_immutable_evidence():
    paths = [
        Q24 / "seed-input.json", Q24 / "writer-2-text.json",
        ENTITY, POLICY, STORY, PROPERTY, ISSUES,
    ]
    digests = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
    cmd = [
        sys.executable, "-X", "utf8", "-m", "src.q25_review_worklist",
        "--seed", str(paths[0]), "--prose-record", str(paths[1]),
        "--entity-proposal", str(ENTITY), "--policy", str(POLICY),
        "--story-proposal", str(STORY),
        "--property-proposal", str(PROPERTY), "--annotations", str(ISSUES),
    ]
    cli_result = json.loads(subprocess.check_output(
        cmd, encoding="utf8", text=True))
    assert cli_result == build_worklist(**frozen())
    assert digests == [
        hashlib.sha256(path.read_bytes()).hexdigest() for path in paths
    ]
