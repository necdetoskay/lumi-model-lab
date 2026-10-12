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



def _initial_snapshot(seed, path):
    """Look up the exact seed field; absent is NOT the value None/False."""
    tokens = [x.replace("~1", "/").replace("~0", "~")
              for x in path.lstrip("/").split("/")]
    if not path.startswith("/") or not all(tokens):
        raise ValueError("Invalid coverage pointer")
    data = None
    if tokens[0] == "objects" and len(tokens) >= 3:
        obj = seed["objects"].get(tokens[1])
        if obj is None:
            return {"status": "NOT_IN_INITIAL_SEED"}
        if tokens[2] in ("owner", "location") and len(tokens) == 3:
            data = obj
            tokens = tokens[2:]
        elif tokens[2] in ("container", "contains", "held_by") and len(tokens) == 3:
            data = obj.get("state", {})
            tokens = tokens[2:]
        elif tokens[2] == "properties" and len(tokens) == 4:
            data = obj.get("state", {})
            tokens = tokens[3:]
        elif tokens[2] == "identity_status" and len(tokens) == 3:
            return {"status": "NOT_IN_INITIAL_SEED"}
        else:
            raise ValueError("Unsupported object coverage field")
    elif tokens[0] == "characters" and len(tokens) >= 3:
        data = seed["characters"].get(tokens[1])
        if data is None:
            raise ValueError("Unknown seed character in coverage")
        tokens = tokens[2:]
    elif tokens[0] == "narrative_obligations" and len(tokens) == 3 and tokens[2] == "status":
        hits = [o for o in seed["narrative_obligations"] if o["id"] == tokens[1]]
        if len(hits) != 1:
            raise ValueError("Ambiguous seed obligation")
        return {"status": "PRESENT", "value": hits[0]["status"]}
    elif tokens[0] == "open_threads" and len(tokens) == 2:
        if tokens[1] not in seed["open_threads"]:
            raise ValueError("Unknown initial open thread")
        return {"status": "PRESENT", "value": "OPEN"}
    elif tokens == ["world", "time"]:
        return {"status": "PRESENT", "value": copy.deepcopy(seed["world"]["time"])}
    else:
        raise ValueError("Unsupported coverage pointer")

    for part in tokens:
        if not isinstance(data, dict) or part not in data:
            return {"status": "NOT_IN_INITIAL_SEED"}
        data = data[part]
    return {"status": "PRESENT", "value": copy.deepcopy(data)}


def _field_action(row):
    """Mechanical dispatch only, no source-semantic judgment."""
    category, status = row["category"], row["status"]
    if status == "UNKNOWN":
        return "RETAIN_UNKNOWN_OR_REQUIRE_EXPLICIT_IDENTITY_EVIDENCE"
    if status == "PARTIAL_CANDIDATES":
        return "REVIEW_EPISTEMIC_CLAIMS_AND_EXHAUSTIVE_KNOWLEDGE"
    if status == "CANDIDATE":
        return ("REVIEW_GOAL_OR_NARRATIVE_COMPLETENESS"
                if category in ("GOAL", "NARRATIVE_OBLIGATION", "OPEN_THREAD")
                else "REVIEW_CITED_PROPOSED_TERMINAL_CHANGE")
    if status == "STRUCTURAL_ONLY":
        return "VERIFY_END_OF_STORY_RELATION_NOT_JUST_STRUCTURE"
    if status == "UNASSESSED":
        return ("REVIEW_TERMINAL_CHARACTER_OR_RELATIONSHIP"
                if category in ("CHARACTER", "RELATIONSHIP", "CHARACTER_KNOWLEDGE")
                else "ESTABLISH_TERMINAL_VALUE_OR_MARK_EXPLICITLY_UNDETERMINED")
    raise ValueError("Unrecognized source coverage status")


def _field_matrix(seed, worklist, findings):
    """One row per blocked field, preserving seed vs hypothesis vs no evidence."""
    comparison = worklist["initial_to_candidate_comparison"]
    objects = {x["path"]: x for x in comparison["object_changes"]}
    characters = {}
    for claim in comparison["character_changes"]:
        actor, field = claim["actor"], claim["field"]
        if field in ("health", "emotion"):
            path = f"/characters/{actor}/condition/{field}"
        elif field == "relationship_trust":
            path = f"/characters/{actor}/relationships/{claim['other_actor']}/trust"
        else:
            path = f"/characters/{actor}/{field}"
        characters.setdefault(path, []).append(claim)
    goals = {f"/characters/{x['actor']}/condition/goal": x
             for x in comparison["goal_outcomes"]}
    obligations = {f"/narrative_obligations/{x['obligation_id']}/status": x
                   for x in comparison["narrative_obligations"]}
    threads = {f"/open_threads/{x['thread_id']}": x
               for x in comparison["open_threads"]}
    new_objects = {
        f"/objects/{x['object_id']}": x
        for x in comparison["new_object_candidates"]
    }
    reviews = {x["target_path"]: x for x in findings}
    all_rows = worklist["coverage_fields"]
    field_paths = [x["path"] for x in all_rows]
    if len(field_paths) != len(set(field_paths)):
        raise ValueError("Duplicate source coverage field in full-field matrix")
    if set(reviews) - set(field_paths):
        raise ValueError("Review result references an unknown field")

    rows = []
    for field in all_rows:
        path = field["path"]
        hypothesis = {"status": "NO_TERMINAL_VALUE_PROPOSED"}
        if path in objects:
            d = objects[path]
            hypothesis = {
                "status": "SOURCE_BOUND_DELTA_CANDIDATE",
                "value": copy.deepcopy(d["candidate_terminal_value"]),
                "evidence": copy.deepcopy(d["evidence"]),
            }
        elif path in characters:
            claims = characters[path]
            hypothesis = {
                "status": "PARTIAL_EPISTEMIC_ADDITIONS" if
                          field["category"] == "CHARACTER_KNOWLEDGE" else
                          "SOURCE_BOUND_CHARACTER_CANDIDATE",
                "proposals": copy.deepcopy(claims),
            }
        elif path in goals:
            d = goals[path]
            hypothesis = {
                "status": "GOAL_OUTCOME_ONLY_NOT_A_NEW_GOAL",
                "outcome": d["proposed_outcome"],
                "evidence": copy.deepcopy(d["evidence"]),
            }
        elif path in obligations and obligations[path]["proposed_outcome"] is not None:
            d = obligations[path]
            hypothesis = {
                "status": "PROPOSED_OBLIGATION_OUTCOME_ONLY",
                "outcome": d["proposed_outcome"],
                "evidence": copy.deepcopy(d["evidence"]),
            }
        elif path in threads and threads[path]["proposed_outcome"] is not None:
            d = threads[path]
            hypothesis = {
                "status": "PROPOSED_THREAD_OUTCOME_ONLY",
                "outcome": d["proposed_outcome"],
                "evidence": copy.deepcopy(d["evidence"]),
            }
        else:
            for prefix, item in new_objects.items():
                if path == prefix + "/identity_status":
                    hypothesis = {"status": "PROPOSED_OBJECT_IDENTITY_ONLY"}
                elif path == prefix + "/owner" or path == prefix + "/location":
                    hypothesis = {"status": "EXPLICIT_UNKNOWN_NEW_ENTITY_FIELD"}
        review = reviews.get(path)
        rows.append({
            "path": path,
            "category": field["category"],
            "coverage_status": field["status"],
            "seed_snapshot": _initial_snapshot(seed, path),
            "terminal_hypothesis": hypothesis,
            "coverage_note": field["note"],
            "source_proposal_evidence": copy.deepcopy(field["evidence"]),
            "individual_review": (
                {"status": "AUTHOR_DRAFT_ONLY",
                 "issue_id": review["issue_id"],
                 "provisional_category": review["provisional_category"],
                 "why_not_final": review["why_not_final"]}
                if review else
                {"status": "NOT_INDIVIDUALLY_SEMANTICALLY_TRIAGED"}
            ),
            "required_next_action": _field_action(field),
            "independently_certified": False,
            "terminal_value_committable": False,
        })
    if len(rows) != worklist["blocking_field_count"] or set(field_paths) != {x["path"] for x in rows}:
        raise ValueError("Full-field matrix does not exhaust source coverage")
    return rows


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

    matrix = _field_matrix(seed, worklist, result)
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
        "full_field_matrix": matrix,
        "full_field_matrix_summary": {
            "field_count": len(matrix),
            "author_draft_review_count": sum(
                r["individual_review"]["status"] == "AUTHOR_DRAFT_ONLY"
                for r in matrix),
            "not_individually_triaged_count": sum(
                r["individual_review"]["status"] ==
                "NOT_INDIVIDUALLY_SEMANTICALLY_TRIAGED" for r in matrix),
            "independently_certified_count": 0,
            "terminal_values_committable_count": 0,
        },
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
