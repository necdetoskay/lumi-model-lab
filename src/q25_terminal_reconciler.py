"""Q25 read-only terminal-state reconciliation on validated source candidates.

A structurally coherent projection is not a semantically accepted StoryState.
Every value carries its authority; copied seed facts remain assumptions.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from src.q25_entity_candidates import fingerprint
from src.q25_provisional_review import assess_worklist
from src.q25_state_admission import build_draft


HISTORICAL_OR_DESCRIPTIVE_PROPERTIES = frozenset({
    "color", "author", "entry_day", "entry_text", "placed_by", "returned_by",
})


def classify_field(row):
    """A missing edit never becomes proof of an unchanged terminal value."""
    hypothesis = row["terminal_hypothesis"]
    state = hypothesis["status"]
    if state == "EXPLICIT_UNKNOWN_NEW_ENTITY_FIELD":
        return "UNKNOWN_REQUIRES_EVIDENCE"
    if state == "PARTIAL_EPISTEMIC_ADDITIONS":
        return "PARTIAL_KNOWLEDGE_CANDIDATE"
    if state in ("SOURCE_BOUND_DELTA_CANDIDATE",
                 "SOURCE_BOUND_CHARACTER_CANDIDATE",
                 "GOAL_OUTCOME_ONLY_NOT_A_NEW_GOAL",
                 "PROPOSED_OBLIGATION_OUTCOME_ONLY",
                 "PROPOSED_THREAD_OUTCOME_ONLY"):
        return "UNVERIFIED_TERMINAL_CANDIDATE"
    if state == "PROPOSED_OBJECT_IDENTITY_ONLY":
        return "UNADMITTED_OBJECT_IDENTITY"
    if row["coverage_status"] == "STRUCTURAL_ONLY":
        return "STRUCTURAL_SEED_OR_PROPOSED_RELATION_ONLY"
    if state == "NO_TERMINAL_VALUE_PROPOSED":
        # These are prior *facts*, not proof they stayed unchanged.
        if (row["category"] == "OBJECT_PROPERTY"
                and row["path"].rsplit("/", 1)[-1]
                in HISTORICAL_OR_DESCRIPTIVE_PROPERTIES):
            return "HISTORICAL_SEED_FACT_UNVERIFIED_AT_TERMINAL"
        return "UNASSESSED_DO_NOT_INFER_UNCHANGED"
    raise ValueError("Cannot classify a terminal field")


def _checked_graph(objects, allowed_locations, characters):
    """Independent reciprocal relation checks on the candidate projection."""
    ids = set(objects)
    occupants = {key: set() for key in objects}
    held = {key: set() for key in characters}
    for key, obj in objects.items():
        for field in ("owner", "location", "container", "held_by"):
            slot = obj[field]
            if slot["status"] not in ("KNOWN", "NONE", "UNKNOWN"):
                raise ValueError("Unknown relation state")
            if slot["status"] == "KNOWN" and slot["ref"] is None:
                raise ValueError("Known relation cannot have null target")
            if slot["status"] != "KNOWN" and slot["ref"] is not None:
                raise ValueError("Non-known relation cannot have a target")
        container = obj["container"]
        holder = obj["held_by"]
        if container["status"] == "KNOWN":
            if holder["status"] == "KNOWN":
                raise ValueError("Inside a container and held simultaneously")
            if container["ref"] not in ids or container["ref"] == key:
                raise ValueError("Invalid terminal container")
            occupants[container["ref"]].add(key)
        if holder["status"] == "KNOWN":
            if holder["ref"] not in held:
                raise ValueError("Unknown direct holder")
            held[holder["ref"]].add(key)
        location = obj["location"]
        if location["status"] == "KNOWN" and location["ref"] not in allowed_locations:
            raise ValueError("Location outside approved topology")
    for key, obj in objects.items():
        if len(obj["contains"]) != len(set(obj["contains"])):
            raise ValueError("Duplicate candidate contents")
        if set(obj["contains"]) != occupants[key]:
            raise ValueError("Nonreciprocal terminal containment")
    for key, obj in objects.items():
        seen = set()
        target = key
        while objects[target]["container"]["status"] == "KNOWN":
            if target in seen:
                raise ValueError("Candidate containment cycle")
            seen.add(target)
            target = objects[target]["container"]["ref"]
    return {
        "status": "STRUCTURALLY_COHERENT_CANDIDATES_ONLY",
        "reciprocal_container_pairs": sum(len(x) for x in occupants.values()),
        "directly_held_objects": {k: sorted(v) for k, v in sorted(held.items())},
        "semantic_truth_checked": False,
    }


def reconcile(*, seed, prose, entity_proposal, policy, story_proposal,
              property_proposal, annotations, assessments):
    """Render a deterministic terminal hypothesis without any canonical write."""
    before = copy.deepcopy((seed, entity_proposal, policy,
                            story_proposal, property_proposal,
                            annotations, assessments))
    review = assess_worklist(
        seed=seed, prose=prose, entity_proposal=entity_proposal,
        policy=policy, story_proposal=story_proposal,
        property_proposal=property_proposal, annotations=annotations,
        assessments=assessments,
    )
    admission = build_draft(
        seed=seed, prose=prose, proposal=entity_proposal, policy=policy)
    if admission["structural_admission"] != "ELIGIBLE_DRAFT":
        raise ValueError("Entity admission not eligible")
    draft = admission["draft_state"]
    if draft["base_seed_sha256"] != review["seed_sha256"] or (
            draft["source_sha256"] != review["source_sha256"]):
        raise ValueError("Reconciler draft lineage mismatch")
    if admission["state_commit_authorized"] is not False:
        raise ValueError("Unexpected upstream write authority")
    field_matrix = copy.deepcopy(review["full_field_matrix"])
    field_lookup = {r["path"]: r for r in field_matrix}
    if len(field_lookup) != len(field_matrix):
        raise ValueError("Duplicate terminal field")
    for row in field_matrix:
        row["reconciliation_policy"] = classify_field(row)
        row["initial_is_terminal_proof"] = False
        row["accepted_as_final"] = False

    objects = copy.deepcopy(draft["objects"])
    for name, obj in objects.items():
        for field in ("owner", "location", "container", "held_by"):
            path = f"/objects/{name}/{field}"
            if path not in field_lookup:
                raise ValueError("Incomplete relation field audit")
            obj[field]["authority"] = (
                "PROVISIONAL_STRUCTURE_NOT_SEMANTICALLY_ACCEPTED")
        obj["contains_authority"] = "PROVISIONAL_STRUCTURE_NOT_SEMANTICALLY_ACCEPTED"
        obj["identity_authority"] = (
            "NEW_UNADMITTED_IDENTITY" if obj["identity_status"] == "PROPOSED"
            else "INITIAL_OBJECT_IDENTITY")
        props = obj["properties"]
        obj["properties"] = {}
        for field, seed_value in props.items():
            path = f"/objects/{name}/properties/{field}"
            if path not in field_lookup:
                raise ValueError("Property absent from exhaustive matrix")
            row = field_lookup[path]
            hypothesis = row["terminal_hypothesis"]
            has_candidate = hypothesis["status"] == "SOURCE_BOUND_DELTA_CANDIDATE"
            obj["properties"][field] = {
                "initial_value": copy.deepcopy(seed_value),
                "proposed_terminal_value": (
                    copy.deepcopy(hypothesis["value"]) if has_candidate else None),
                "terminal_value_assessed": has_candidate,
                "value_origin": (
                    "SOURCE_QUOTED_UNVERIFIED_CHANGE" if has_candidate
                    else "SEED_REFERENCE_ONLY"),
                "provisional_review_category": (
                    row["individual_review"].get("provisional_category")),
                "semantic_support_certified": False,
            }

    graph = _checked_graph(
        objects, set(seed["topology"]["locations"]), seed["characters"])
    for actor, inventory in draft["characters"].items():
        observed = {name: count for name, count in inventory["inventory"].items()}
        computed = {name: 1 for name in graph["directly_held_objects"][actor]}
        if observed != computed:
            raise ValueError("Direct holder and inventory disagree")

    changes = review["initial_to_candidate_comparison"]
    character_state = {}
    for name, initial in sorted(seed["characters"].items()):
        claims = [x for x in changes["character_changes"] if x["actor"] == name]
        knowledge = [x for x in claims if x["field"] == "knowledge"]
        scalar = [x for x in claims if x["field"] != "knowledge"]
        outcomes = [x for x in changes["goal_outcomes"] if x["actor"] == name]
        character_state[name] = {
            "initial_condition": copy.deepcopy(initial["condition"]),
            "initial_location": initial["location"],
            "initial_relationships": copy.deepcopy(initial["relationships"]),
            "initial_knowledge": copy.deepcopy(initial["knowledge"]),
            "initial_inventory": copy.deepcopy(initial["inventory"]),
            "proposed_knowledge_additions": knowledge,
            "proposed_scalar_changes": scalar,
            "proposed_goal_outcome": outcomes[0] if outcomes else None,
            "structural_inventory_candidate": copy.deepcopy(
                draft["characters"][name]["inventory"]),
            "terminal_emotion_certified": False,
            "relationship_trust_certified": False,
            "knowledge_completeness_certified": False,
        }
    proposal_status = {
        "schema": "q25.terminal-reconciliation-candidate.v1",
        "seed_sha256": review["seed_sha256"],
        "source_sha256": review["source_sha256"],
        "review_worklist_sha256": review["annotations_sha256"],
        "provisional_assessment_sha256": review["assessment_sha256"],
        "object_identity_map": copy.deepcopy(draft["identity_map"]),
        "candidate_state": {
            "objects": objects,
            "characters": character_state,
            "world": {
                "seed_reference": copy.deepcopy(seed["world"]),
                "proposed_terminal_time": None,
                "time_unassessed": True,
                "terminal_world_certified": False,
            },
            "narrative_obligations": copy.deepcopy(changes["narrative_obligations"]),
            "open_threads": copy.deepcopy(changes["open_threads"]),
            "topology_reference_sha256": fingerprint(seed["topology"]),
        },
        "field_decisions": field_matrix,
        "field_count": len(field_matrix),
        "field_policy_counts": {
            key: sum(r["reconciliation_policy"] == key for r in field_matrix)
            for key in sorted({r["reconciliation_policy"] for r in field_matrix})
        },
        "structural_consistency": graph,
        "pending_review_count": len(field_matrix),
        "independently_certified_field_count": 0,
        "approved_narrative_obligation_closures": [],
        "projection_status": "COHERENT_UNVERIFIED_TERMINAL_HYPOTHESIS",
        "review_status": "UNTRUSTED_ANNOTATIONS_WITH_AUTHOR_PROVISIONAL_READINGS",
        "semantic_support_certified": False,
        "full_story_state_qualified": False,
        "state_commit_authorized": False,
        "production_write_performed": False,
        "provider_calls": 0,
    }
    assert before == (seed, entity_proposal, policy,
                      story_proposal, property_proposal,
                      annotations, assessments)
    return proposal_status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "seed", "prose-record", "entity-proposal", "policy", "story-proposal",
        "property-proposal", "annotations", "assessments",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    load = lambda p: json.loads(p.read_text(encoding="utf8"))
    print(json.dumps(reconcile(
        seed=load(args.seed), prose=load(args.prose_record)["text"],
        entity_proposal=load(args.entity_proposal), policy=load(args.policy),
        story_proposal=load(args.story_proposal),
        property_proposal=load(args.property_proposal),
        annotations=load(args.annotations), assessments=load(args.assessments),
    ), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
