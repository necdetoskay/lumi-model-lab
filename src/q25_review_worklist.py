"""Q25 offline semantic gap worklist from immutable Q24 state candidates.

Annotations are untrusted, manually prepared triage questions, never a
semantic judge, a state-delta approval, or an authority to close obligations.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Literal

from pydantic import Field

from src.q25_entity_candidates import fingerprint
from src.q25_offline_diagnostic import Strict, Span, digest, valid_span
from src.q25_state_coverage import coverage_report


class GapIssue(Strict):
    issue_id: str = Field(min_length=3, pattern=r"^[a-z][a-z0-9_]*$")
    target_path: str = Field(min_length=2, pattern=r"^/")
    issue_type: Literal[
        "SEMANTIC_AMBIGUITY", "INSUFFICIENT_SUPPORT", "INCOMPLETE_COVERAGE",
        "MISSING_TERMINAL_EVIDENCE", "POSSIBLE_COUNTEREVIDENCE",
    ]
    reviewer_question: str = Field(min_length=20, max_length=1000)
    rationale: str = Field(min_length=20, max_length=1500)
    supporting_evidence: list[Span] = Field(default_factory=list)
    competing_evidence: list[Span] = Field(default_factory=list)


class GapAnnotations(Strict):
    schema_name: Literal["q25.review-gap-annotations.v1"]
    seed_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    story_proposal_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    property_proposal_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    issues: list[GapIssue] = Field(min_length=1)


def build_worklist(*, seed, prose, entity_proposal, policy,
                   story_proposal, property_proposal, annotations):
    """Recompute every upstream gate before binding human-review questions."""
    originals = copy.deepcopy((
        seed, entity_proposal, policy, story_proposal, property_proposal, annotations,
    ))
    audit = coverage_report(
        seed=seed, prose=prose, entity_proposal=entity_proposal, policy=policy,
        story_proposal=story_proposal, property_proposal=property_proposal,
    )
    parsed = GapAnnotations.model_validate(annotations)
    for key, actual in (
        ("seed_sha256", fingerprint(seed)),
        ("source_sha256", digest(prose)),
        ("story_proposal_sha256", audit["story_proposal_sha256"]),
        ("property_proposal_sha256", audit["property_proposal_sha256"]),
    ):
        if getattr(parsed, key) != actual:
            raise ValueError("Worklist annotation is stale or has mismatched " + key)

    paths = {item["path"]: item for item in audit["fields"]}
    issue_ids, targets, validated = set(), set(), []

    def check_spans(spans):
        last_end = -1
        for span in spans:
            if not valid_span(prose, parsed.source_sha256, span):
                raise ValueError("Worklist contains non-source or invalid quote")
            if span.start < last_end:
                raise ValueError("Overlapping or unordered worklist evidence")
            last_end = span.end

    for issue in parsed.issues:
        if issue.issue_id in issue_ids or issue.target_path in targets:
            raise ValueError("Duplicate issue identifier or target field")
        if issue.target_path not in paths:
            raise ValueError("Worklist target is not an unresolved coverage field")
        if not (issue.supporting_evidence or issue.competing_evidence):
            raise ValueError("A review question needs at least one source quotation")
        check_spans(issue.supporting_evidence)
        check_spans(issue.competing_evidence)
        issue_ids.add(issue.issue_id)
        targets.add(issue.target_path)
        validated.append({
            **issue.model_dump(mode="json"),
            "coverage_status": paths[issue.target_path]["status"],
            "coverage_note": paths[issue.target_path]["note"],
            "review_decision": "PENDING_INDEPENDENT_ADJUDICATION",
        })

    compared = audit["initial_to_candidate_comparison"]
    unannotated = [
        {"path": row["path"], "status": row["status"]}
        for row in audit["fields"] if row["path"] not in targets
    ]
    assert originals == (
        seed, entity_proposal, policy, story_proposal, property_proposal, annotations,
    )
    return {
        "schema": "q25.review-gap-worklist.v1",
        "seed_sha256": audit["seed_sha256"],
        "source_sha256": audit["source_sha256"],
        "story_proposal_sha256": audit["story_proposal_sha256"],
        "property_proposal_sha256": audit["property_proposal_sha256"],
        "annotations_sha256": fingerprint(parsed.model_dump(mode="json")),
        "coverage_counts": audit["counts"],
        "initial_to_candidate_comparison": compared,
        "coverage_fields": copy.deepcopy(audit["fields"]),
        "blocking_field_count": audit["blocking_field_count"],
        "triaged_issue_count": len(validated),
        "issues": validated,
        "untriaged_fields": unannotated,
        "untriaged_field_count": len(unannotated),
        "proposed_closed_obligations": compared["proposed_closed_obligations"],
        "independently_certified_closed_obligations": [],
        "contested_or_unverified_obligations": compared[
            "contested_or_unverified_obligations"
        ],
        "review_status": "REVIEW_WORKLIST_ONLY_NO_SEMANTIC_CERTIFICATION",
        "semantic_support_certified": False,
        "full_story_state_qualified": False,
        "state_commit_authorized": False,
        "provider_calls": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "seed", "prose-record", "entity-proposal", "policy",
        "story-proposal", "property-proposal", "annotations",
    ):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    load = lambda path: json.loads(path.read_text(encoding="utf8"))
    result = build_worklist(
        seed=load(args.seed),
        prose=load(args.prose_record)["text"],
        entity_proposal=load(args.entity_proposal),
        policy=load(args.policy),
        story_proposal=load(args.story_proposal),
        property_proposal=load(args.property_proposal),
        annotations=load(args.annotations),
    )
    print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
