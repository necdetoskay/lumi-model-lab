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



def test_all_seventy_fields_have_a_seed_snapshot_and_no_fake_final_values():
    case = saved_case()
    report = assess_worklist(**case)
    matrix = report["full_field_matrix"]
    summary = report["full_field_matrix_summary"]
    rows = {r["path"]: r for r in matrix}
    assert len(matrix) == len(rows) == summary["field_count"] == 70
    assert summary == {
        "field_count": 70,
        "author_draft_review_count": 11,
        "not_individually_triaged_count": 59,
        "independently_certified_count": 0,
        "terminal_values_committable_count": 0,
    }
    assert all(r["independently_certified"] is False and
               r["terminal_value_committable"] is False for r in matrix)
    assert {r["individual_review"]["status"] for r in matrix} == {
        "AUTHOR_DRAFT_ONLY", "NOT_INDIVIDUALLY_SEMANTICALLY_TRIAGED",
    }
    def row(path):
        return rows[path]
    bookmark = row("/objects/red_bookmark/properties/found")
    assert bookmark["seed_snapshot"] == {"status": "PRESENT", "value": False}
    assert bookmark["terminal_hypothesis"]["value"] is True
    assert bookmark["terminal_hypothesis"]["status"] == "SOURCE_BOUND_DELTA_CANDIDATE"
    returned = row("/objects/red_bookmark/properties/returned_to_owner")
    assert returned["seed_snapshot"]["value"] is False
    assert returned["terminal_hypothesis"]["value"] is True
    assert returned["individual_review"]["provisional_category"] == "CONTEXT_DEPENDENT"
    contained = row("/objects/blue_atlas/contains")
    assert contained["seed_snapshot"]["value"] == ["red_bookmark"]
    assert contained["terminal_hypothesis"]["value"] == []
    book_owner = next(r for r in matrix
                      if r["path"].startswith("/objects/new_")
                      and r["path"].endswith("/owner"))
    assert book_owner["seed_snapshot"] == {"status": "NOT_IN_INITIAL_SEED"}
    assert book_owner["terminal_hypothesis"]["status"] == "EXPLICIT_UNKNOWN_NEW_ENTITY_FIELD"
    assert book_owner["required_next_action"].startswith("RETAIN_UNKNOWN")
    unchanged_seed = row("/objects/blue_atlas/owner")
    assert unchanged_seed["seed_snapshot"] == {"status": "PRESENT", "value": "library"}
    assert unchanged_seed["terminal_hypothesis"] == {"status": "NO_TERMINAL_VALUE_PROPOSED"}
    assert unchanged_seed["coverage_status"] == "STRUCTURAL_ONLY"
    trust = row("/characters/Cem/relationships/Nisa/trust")
    assert trust["seed_snapshot"] == {"status": "PRESENT", "value": "good"}
    assert trust["terminal_hypothesis"]["status"] == "NO_TERMINAL_VALUE_PROPOSED"
    assert trust["individual_review"]["provisional_category"] == "UNDETERMINED"
    nisa = row("/characters/Nisa/knowledge")
    assert len(nisa["seed_snapshot"]["value"]) == 5
    assert nisa["terminal_hypothesis"]["status"] == "PARTIAL_EPISTEMIC_ADDITIONS"
    assert nisa["coverage_status"] == "PARTIAL_CANDIDATES"
    goal = row("/characters/Cem/condition/goal")
    assert goal["seed_snapshot"]["value"] == "join_reading_activity"
    assert goal["terminal_hypothesis"]["status"] == "GOAL_OUTCOME_ONLY_NOT_A_NEW_GOAL"
    assert goal["terminal_hypothesis"]["outcome"] == "ACHIEVED"
    obligation = row("/narrative_obligations/correct_and_apologize/status")
    assert obligation["seed_snapshot"]["value"] == "OPEN"
    assert obligation["terminal_hypothesis"]["outcome"] == "SATISFIED"
    assert obligation["individual_review"]["provisional_category"] == "CONTEXT_DEPENDENT"
    clock = row("/world/time")
    assert clock["seed_snapshot"]["value"]["minutes_until_reading_activity"] == 30
    assert clock["terminal_hypothesis"] == {"status": "NO_TERMINAL_VALUE_PROPOSED"}


def test_matrix_does_not_mutate_or_complete_missing_terminal_fields():
    case = saved_case()
    before = copy.deepcopy(case)
    result = assess_worklist(**case)
    assert sum(x["terminal_hypothesis"]["status"] == "NO_TERMINAL_VALUE_PROPOSED"
               for x in result["full_field_matrix"]) > 20
    assert len(result["untriaged_fields"]) == 59
    assert case == before
    assert result == assess_worklist(**case)


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
        key = {
            "wrong_seed_hash": "seed_sha256",
            "wrong_source_hash": "source_sha256",
            "wrong_annotations_hash": "annotations_sha256",
        }[damage]
        case["assessments"][key] = "0" * 64
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
