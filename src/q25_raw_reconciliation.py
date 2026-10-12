"""Q25 generic raw-extractor -> reconciled terminal *candidate* bridge.

Unlike the Q24 annotated review, this input only requires a frozen seed,
complete prose and an untrusted model-shaped response. No provider request,
implicit semantic proof, canonical StoryState or production write.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from src.q25_entity_candidates import fingerprint
from src.q25_extractor_adapter import materialize_quotes, offline_replay
from src.q25_state_admission import build_draft
from src.q25_terminal_reconciler import _checked_graph


def project_raw(*, seed, prose, raw_output, policy):
    """Replay every Q25 gate then reconcile one source-bound hypothesis."""
    original = copy.deepcopy((seed, prose, raw_output, policy))
    replay = offline_replay(
        seed=seed, prose=prose, raw_output=raw_output, policy=policy,
    )
    if replay["status"] != "SOURCE_BOUND_CANDIDATES_ONLY":
        raise ValueError("Cannot project a structurally denied extractor response")
    materialized = materialize_quotes(
        seed=seed, prose=prose, raw_output=raw_output,
    )
    admitted = build_draft(
        seed=seed, prose=prose,
        proposal=materialized["entity_proposal"], policy=policy,
    )
    draft = admitted["draft_state"]
    if (draft is None or admitted["structural_admission"] != "ELIGIBLE_DRAFT"
            or admitted["state_commit_authorized"] is not False
            or draft["base_seed_sha256"] != replay["coverage"]["seed_sha256"]
            or draft["source_sha256"] != replay["coverage"]["source_sha256"]):
        raise ValueError("Raw reconciliation lineage or policy discrepancy")
    comparison = replay["coverage"]["initial_to_candidate_comparison"]
    property_changes = {
        x["path"]: x
        for x in comparison["object_changes"]
        if "/properties/" in x["path"]
    }
    objects = copy.deepcopy(draft["objects"])
    for name, obj in objects.items():
        obj["relation_authority"] = "STRUCTURAL_CANDIDATE_NOT_SEMANTICALLY_VERIFIED"
        obj["identity_authority"] = (
            "PENDING_NEW_ORDINARY_ENTITY_ADMISSION"
            if obj["identity_status"] == "PROPOSED"
            else "INITIAL_OBJECT_IDENTITY_REFERENCE"
        )
        current = obj["properties"]
        obj["properties"] = {}
        for key, initial in current.items():
            path = f"/objects/{name}/properties/{key}"
            change = property_changes.get(path)
            obj["properties"][key] = {
                "initial_reference": copy.deepcopy(initial),
                "terminal_proposal": (
                    copy.deepcopy(change["candidate_terminal_value"])
                    if change else None
                ),
                "value_status": (
                    "UNVERIFIED_SOURCE_BOUND_CHANGE"
                    if change else "UNASSESSED_SEED_REFERENCE_ONLY"
                ),
                "evidence": copy.deepcopy(change["evidence"]) if change else [],
            }

    approved_locations = set(seed["topology"]["locations"])
    established_owner_ids = {
        obj["owner"] for obj in seed["objects"].values()
        if obj.get("owner") is not None
        and obj["owner"] not in seed["characters"]
    }
    graph = _checked_graph(
        objects, approved_locations, seed["characters"],
        seed_external_owners=established_owner_ids,
    )
    for actor, char in draft["characters"].items():
        expected = {name: 1 for name in graph["directly_held_objects"][actor]}
        if char["inventory"] != expected:
            raise ValueError("Raw response inventory and graph do not agree")

    raw_characters = {}
    for actor, char in sorted(seed["characters"].items()):
        proposed = [
            x for x in comparison["character_changes"] if x["actor"] == actor
        ]
        goals = [
            x for x in comparison["goal_outcomes"] if x["actor"] == actor
        ]
        raw_characters[actor] = {
            "initial_reference": copy.deepcopy(char),
            "terminal_scalar_change_candidates": [
                x for x in proposed if x["field"] != "knowledge"
            ],
            "terminal_knowledge_addition_candidates": [
                x for x in proposed if x["field"] == "knowledge"
            ],
            "goal_outcome_candidate": goals[0] if goals else None,
            "structural_inventory_candidate": copy.deepcopy(
                draft["characters"][actor]["inventory"]
            ),
            "complete_knowledge_certified": False,
            "relationships_certified": False,
            "terminal_character_state_certified": False,
        }

    rows = copy.deepcopy(replay["coverage"]["fields"])
    if len(rows) != replay["coverage"]["blocking_field_count"]:
        raise ValueError("Incomplete generic terminal field coverage")
    for row in rows:
        row["terminal_accepted"] = False
        row["inherited_seed_is_proof"] = False

    result = {
        "schema": "q25.raw-terminal-hypothesis.v1",
        "seed_sha256": replay["coverage"]["seed_sha256"],
        "source_sha256": replay["coverage"]["source_sha256"],
        "raw_output_sha256": replay["raw_output_sha256"],
        "candidate_state": {
            "objects": objects,
            "characters": raw_characters,
            "world_initial_reference": copy.deepcopy(seed.get("world")),
            "proposed_world_time": None,
            "world_time_unassessed": True,
            "narrative_obligations": copy.deepcopy(
                comparison["narrative_obligations"]),
            "open_threads": copy.deepcopy(comparison["open_threads"]),
        },
        "structural_consistency": graph,
        "field_decisions": rows,
        "coverage_counts": replay["coverage"]["counts"],
        "blocking_field_count": len(rows),
        "proposed_obligation_closures": copy.deepcopy(
            comparison["proposed_closed_obligations"]),
        "approved_obligation_closures": [],
        "unverified_narrative_obligations": copy.deepcopy(
            comparison["contested_or_unverified_obligations"]),
        "raw_response_trust": "UNTRUSTED_SOURCE_QUOTED_CANDIDATES_ONLY",
        "unseen_story_model_accuracy_measured": False,
        "independent_semantic_review_required": True,
        "independent_semantic_review_completed": False,
        "terminal_state_complete": False,
        "semantic_support_certified": False,
        "full_story_state_qualified": False,
        "state_commit_authorized": False,
        "production_write_performed": False,
        "provider_calls": 0,
    }
    assert original == (seed, prose, raw_output, policy)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("seed", "prose-record", "raw-response", "policy"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    read = lambda path: json.loads(path.read_text(encoding="utf8"))
    print(json.dumps(project_raw(
        seed=read(args.seed), prose=read(args.prose_record)["text"],
        raw_output=read(args.raw_response), policy=read(args.policy),
    ), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
