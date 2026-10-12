"""Q24 provisional readings are evidence-bound but never acceptance decisions."""
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.q25_provisional_review import assess_worklist

ROOT = Path("evidence/q25")
Q24 = ROOT / "Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24"
CASE = ROOT / "Q25-STORY-STATE-CANDIDATES-20261012"
ENTITY = ROOT / "Q25-ENTITY-CANDIDATE-20261012/proposal.json"
POLICY = ROOT / "Q25-ADMISSION-DRAFT-20261012/policy.json"
STORY = CASE / "story-proposal-knowledge-extension.json"
PROPERTY = CASE / "property-proposal-return-candidate.json"
ANNOTATIONS = CASE / "review-gap-annotations.json"
ASSESSMENTS = CASE / "provisional-meaning-assessment.json"


def load(path):
    return json.loads(path.read_text(encoding="utf8"))


def saved_case():
    return {
        "seed": load(Q24 / "seed-input.json"),
        "prose": load(Q24 / "writer-2-text.json")["text"],
        "entity_proposal": load(ENTITY),
        "policy": load(POLICY),
        "story_proposal": load(STORY),
        "property_proposal": load(PROPERTY),
        "annotations": load(ANNOTATIONS),
        "assessments": load(ASSESSMENTS),
    }


def test_all_eleven_provisional_interpretations_are_explicitly_non_authoritative():
    source = saved_case()
    before = copy.deepcopy(source)
    result = assess_worklist(**source)
    counts = result["provisional_category_counts"]
    assert counts == {
        "DIRECT_EVENT_CANDIDATE": 1,
        "CONTEXT_DEPENDENT": 3,
        "NOT_ENTAILED": 1,
        "UNDETERMINED": 4,
        "PARTIAL_REPORT": 1,
        "PARTIAL_OBSERVATION": 1,
    }
    assert sum(counts.values()) == 11
    assert result["worklist_scope"]["all_blocking_fields"] == 70
    assert result["worklist_scope"]["provisionally_triaged_fields"] == 11
    assert result["worklist_scope"]["still_untriaged_fields"] == 59
    assert len(result["untriaged_fields"]) == 59
    assert set(result["proposed_closed_obligations"]) == {
        "investigate_evidence", "recover_bookmark", "correct_and_apologize"}
    assert result["independently_certified_closed_obligations"] == []
    assert set(result["contested_or_unverified_obligations"]) == set(
        result["proposed_closed_obligations"])
    assert result["meaning_assessment_status"] == "AUTHOR_DRAFT_NOT_INDEPENDENT_SEMANTIC_REVIEW"
    assert result["independent_semantic_review_required"] is True
    assert result["semantic_support_certified"] is False
    assert result["full_story_state_qualified"] is False
    assert result["state_commit_authorized"] is False
    assert result["provider_calls"] == 0
    changes = {x["path"]: x for x in result[
        "initial_to_candidate_comparison"]["object_changes"]}
    assert changes["/objects/red_bookmark/properties/returned_to_owner"][
        "candidate_terminal_value"] is True
    outcomes = {x["issue_id"]: x for x in result["findings"]}
    assert outcomes["bookmark_return_semantics"]["provisional_category"] == "CONTEXT_DEPENDENT"
    assert outcomes["nisa_relief_from_smile"]["provisional_category"] == "NOT_ENTAILED"
    assert outcomes["cem_reported_knowledge"]["provisional_category"] == "PARTIAL_REPORT"
    assert outcomes["reading_book_owner"]["provisional_category"] == "UNDETERMINED"
    assert outcomes["apology_without_instant_intimacy"][
        "selected_competing_evidence"]
    for item in result["findings"]:
        assert item["review_decision"] == "PENDING_INDEPENDENT_ADJUDICATION"
        assert item["independent_review"] == "NOT_PERFORMED"
        for quote in item["selected_supporting_evidence"] + item["selected_competing_evidence"]:
            assert source["prose"][quote["start"]:quote["end"]] == quote["text"]
    assert source == before
    assert assess_worklist(**source) == result


@pytest.mark.parametrize("damage", [
    "wrong_seed_hash", "wrong_source_hash", "wrong_annotations_hash",
    "missing", "duplicate", "unknown_issue", "unsupported_status",
    "empty_event", "empty_reason", "invalid_support_index",
    "invalid_competing_index", "duplicate_support_index",
    "unordered_support_index", "boolean_index", "approval_in_input",
    "approval_in_finding", "invented_knowledge", "altered_quote",
    "denied_new_object", "modified_seed",
])
def test_untrusted_interpretations_fail_closed(damage):
    case = saved_case()
    findings = case["assessments"]["findings"]
    if damage in ("wrong_seed_hash", "wrong_source_hash", "wrong_annotations_hash"):
        case["assessments"][damage[6:] + "_sha256"] = "0" * 64
    elif damage == "missing":
        findings.pop()
    elif damage == "duplicate":
        findings.append(copy.deepcopy(findings[0]))
    elif damage == "unknown_issue":
        findings[0]["issue_id"] = "invented_issue"
    elif damage == "unsupported_status":
        findings[0]["assessment"] = "CERTIFIED"
    elif damage == "empty_event":
        findings[0]["observed_event"] = "n/a"
    elif damage == "empty_reason":
        findings[0]["why_not_final"] = ""
    elif damage == "invalid_support_index":
        findings[0]["cited_support_indices"] = [999]
    elif damage == "invalid_competing_index":
        findings[1]["cited_competing_indices"] = [999]
    elif damage == "duplicate_support_index":
        findings[0]["cited_support_indices"] = [0, 0]
    elif damage == "unordered_support_index":
        findings[0]["cited_support_indices"] = [1, 0]
    elif damage == "boolean_index":
        findings[0]["cited_support_indices"] = [True]
    elif damage == "approval_in_input":
        case["assessments"]["state_commit_authorized"] = True
    elif damage == "approval_in_finding":
        findings[0]["review_decision"] = "CERTIFIED"
    elif damage == "invented_knowledge":
        case["story_proposal"]["character_claims"][0]["value"] = "secret_magical_clue"
    elif damage == "altered_quote":
        case["annotations"]["issues"][0]["supporting_evidence"][0]["text"] = "fabricated story event"
    elif damage == "denied_new_object":
        case["policy"]["allow_new_ordinary_objects"] = False
    elif damage == "modified_seed":
        case["seed"]["characters"]["Nisa"]["location"] = "invented_location"
    with pytest.raises((ValueError, ValidationError)):
        assess_worklist(**case)


def test_full_cli_is_read_only_matches_function_and_preserves_frozen_inputs():
    paths = [
        Q24 / "seed-input.json", Q24 / "writer-2-text.json",
        ENTITY, POLICY, STORY, PROPERTY, ANNOTATIONS, ASSESSMENTS,
    ]
    hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
    cmd = [
        sys.executable, "-X", "utf8", "-m", "src.q25_provisional_review",
        "--seed", str(paths[0]), "--prose-record", str(paths[1]),
        "--entity-proposal", str(ENTITY), "--policy", str(POLICY),
        "--story-proposal", str(STORY), "--property-proposal", str(PROPERTY),
        "--annotations", str(ANNOTATIONS), "--assessments", str(ASSESSMENTS),
    ]
    output = json.loads(subprocess.check_output(cmd, encoding="utf8", text=True))
    assert output == assess_worklist(**saved_case())
    assert hashes == [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
