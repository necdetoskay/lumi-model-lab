"""Offline Q25 provisional meaning assessment of unresolved Q24 claims.

This is a recorded human/Codex *draft interpretation* only. Neither a
quote match nor full completion of this worksheet grants semantic truth,
independent adjudication, story acceptance, or canonical state authority.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Literal

from pydantic import Field

from src.q25_entity_candidates import fingerprint
from src.q25_offline_diagnostic import Strict
from src.q25_review_worklist import build_worklist


ASSESSMENT_CATEGORIES = (
    "DIRECT_EVENT_CANDIDATE",
    "CONTEXT_DEPENDENT",
    "NOT_ENTAILED",
    "UNDETERMINED",
    "PARTIAL_REPORT",
    "PARTIAL_OBSERVATION",
)


class ProvisionalFinding(Strict):
    issue_id: str = Field(min_length=3)
    assessment: Literal[
        "DIRECT_EVENT_CANDIDATE", "CONTEXT_DEPENDENT", "NOT_ENTAILED",
        "UNDETERMINED", "PARTIAL_REPORT", "PARTIAL_OBSERVATION",
    ]
    cited_support_indices: list[int] = Field(min_length=1)
    cited_competing_indices: list[int] = Field(default_factory=list)
    observed_event: str = Field(min_length=25, max_length=1000)
    why_not_final: str = Field(min_length=30, max_length=1400)


class ProvisionalAssessment(Strict):
    schema_name: Literal["q25.provisional-meaning-assessment.v1"]
    seed_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    annotations_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    findings: list[ProvisionalFinding] = Field(min_length=1)


def assess_worklist(*, seed, prose, entity_proposal, policy, story_proposal,
                    property_proposal, annotations, assessments):
    """Replay the entire source-bound audit, then bind non-authoritative notes."""
    originals = copy.deepcopy((
        seed, entity_proposal, policy, story_proposal,
        property_proposal, annotations, assessments,
    ))
    worklist = build_worklist(
        seed=seed, prose=prose, entity_proposal=entity_proposal,
        policy=policy, story_proposal=story_proposal,
        property_proposal=property_proposal, annotations=annotations,
    )
    parsed = ProvisionalAssessment.model_validate(assessments)
    for key in ("seed_sha256", "source_sha256", "annotations_sha256"):
        if getattr(parsed, key) != worklist[key]:
            raise ValueError("Stale or mismatched provisional review: " + key)

    registered = {issue["issue_id"]: issue for issue in worklist["issues"]}
    submitted = {item.issue_id: item for item in parsed.findings}
    if len(submitted) != len(parsed.findings) or set(submitted) != set(registered):
        raise ValueError("Missing, duplicate or invented provisional issue finding")

    def select_citations(indices, citations):
        if len(indices) != len(set(indices)) or indices != sorted(indices):
            raise ValueError("Duplicate or unordered cited evidence indices")
        if any(type(i) is not int or i < 0 or i >= len(citations) for i in indices):
            raise ValueError("Review references evidence outside its issue")
        return [citations[i] for i in indices]

    result = []
    for issue in worklist["issues"]:
        item = submitted[issue["issue_id"]]
        support = select_citations(
            item.cited_support_indices, issue["supporting_evidence"])
        competing = select_citations(
            item.cited_competing_indices, issue["competing_evidence"])
        result.append({
            "issue_id": item.issue_id,
            "target_path": issue["target_path"],
            "coverage_status": issue["coverage_status"],
            "provisional_category": item.assessment,
            "observed_event": item.observed_event,
            "why_not_final": item.why_not_final,
            "selected_supporting_evidence": support,
            "selected_competing_evidence": competing,
            "independent_review": "NOT_PERFORMED",
            "review_decision": "PENDING_INDEPENDENT_ADJUDICATION",
        })

    counts = {
        category: sum(x["provisional_category"] == category for x in result)
        for category in ASSESSMENT_CATEGORIES
    }
    assert originals == (
        seed, entity_proposal, policy, story_proposal,
        property_proposal, annotations, assessments,
    )
    return {
        "schema": "q25.provisional-meaning-review.v1",
        "seed_sha256": worklist["seed_sha256"],
        "source_sha256": worklist["source_sha256"],
        "annotations_sha256": worklist["annotations_sha256"],
        "assessment_sha256": fingerprint(parsed.model_dump(mode="json")),
        "worklist_scope": {
            "all_blocking_fields": worklist["blocking_field_count"],
            "provisionally_triaged_fields": len(result),
            "still_untriaged_fields": worklist["untriaged_field_count"],
            "coverage_counts": worklist["coverage_counts"],
        },
        "provisional_category_counts": counts,
        "findings": result,
        "untriaged_fields": worklist["untriaged_fields"],
        "initial_to_candidate_comparison":
            worklist["initial_to_candidate_comparison"],
        "proposed_closed_obligations":
            worklist["proposed_closed_obligations"],
        "independently_certified_closed_obligations": [],
        "contested_or_unverified_obligations":
            worklist["contested_or_unverified_obligations"],
        "meaning_assessment_status": "AUTHOR_DRAFT_NOT_INDEPENDENT_SEMANTIC_REVIEW",
        "independent_semantic_review_required": True,
        "semantic_support_certified": False,
        "full_story_state_qualified": False,
        "state_commit_authorized": False,
        "provider_calls": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "seed", "prose-record", "entity-proposal", "policy", "story-proposal",
        "property-proposal", "annotations", "assessments",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    load = lambda path: json.loads(path.read_text(encoding="utf8"))
    print(json.dumps(assess_worklist(
        seed=load(args.seed), prose=load(args.prose_record)["text"],
        entity_proposal=load(args.entity_proposal), policy=load(args.policy),
        story_proposal=load(args.story_proposal),
        property_proposal=load(args.property_proposal),
        annotations=load(args.annotations),
        assessments=load(args.assessments),
    ), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
