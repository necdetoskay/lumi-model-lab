from __future__ import annotations

from typing import Any

from src.story_authority_packet import _entity_specific_world_facts


def build_story_authority_packet_v2(approved: dict[str, Any]) -> dict[str, Any]:
    projection = approved["projection"]
    spine = approved["episode_spine"]
    premise = (approved.get("approved_premise") or {}).get("premise") or {}
    character = projection["character"]
    world = projection["world"]

    known_names = {str(character["name"])}
    for loc in world.get("location_access") or []:
        known_names.add(str(loc["name"]))
    main_saga = projection.get("main_saga_public") or {}
    if main_saga.get("title"):
        known_names.add(str(main_saga["title"]))

    premise_fields = [
        "protagonist_role",
        "immediate_objective",
        "inciting_event",
        "central_problem",
        "wonder_or_discovery",
        "stakes",
        "meaningful_choice_pressure",
        "mystery_or_forward_question",
        "local_payoff",
    ]
    premise_facts = [str(premise.get(k) or "").strip() for k in premise_fields]
    premise_facts.extend(str(x).strip() for x in premise.get("constraints") or [])
    premise_facts.extend(str(x).strip() for x in premise.get("persistent_outcomes_possible") or [])
    premise_facts.extend(str(x).strip() for x in premise.get("world_specific_elements") or [])
    premise_facts = [x for x in premise_facts if x]

    beat_authority = []
    for beat in spine.get("beats") or []:
        beat_authority.append({
            "key": beat.get("key"),
            "phase": beat.get("phase"),
            "location_ref": beat.get("location_ref"),
            "character_action": beat.get("character_action"),
            "external_event": beat.get("external_event"),
            "new_information": beat.get("new_information"),
            "state_change": beat.get("state_change"),
        })

    branch_contracts = {}
    for branch in (spine.get("decision_point") or {}).get("branches") or []:
        branch_contracts[str(branch["key"])] = {
            "option": branch.get("option"),
            "immediate_action": branch.get("immediate_action"),
            "evidence_state_after_choice": branch.get("evidence_state_after_choice"),
            "cost_or_risk": branch.get("cost_or_risk"),
            "relationship_or_access_effect": branch.get("relationship_or_access_effect"),
            "climax_requirement": branch.get("climax_requirement"),
            "local_payoff_if_earned": branch.get("local_payoff_if_earned"),
        }

    return {
        "schema_version": "story-authority-packet.v2",
        "character_authority": {
            "name": character.get("name"),
            "exact_age": character.get("age"),
            "archetype": character.get("archetype"),
            "current_role": character.get("current_role"),
            "origin_summary": character.get("origin_summary"),
            "traits": character.get("traits") or [],
            "interests": character.get("interests") or [],
            "identity_anchors": character.get("identity_anchors") or [],
            "core_drives": character.get("core_drives") or [],
            "immediate_desires": character.get("immediate_desires") or [],
            "immediate_avoidances": character.get("immediate_avoidances") or [],
        },
        "premise_authorized_facts": premise_facts,
        "spine_authorized_events": beat_authority,
        "writer_rules": list(spine.get("writer_rules") or []),
        "known_durable_proper_names": sorted(known_names),
        "new_durable_proper_names_allowed": False,
        "entity_specific_world_facts": _entity_specific_world_facts(projection),
        "world_level_known_facts": list(world.get("known_world_facts") or []),
        "ambient_world_summary": world.get("summary"),
        "ambient_summary_is_not_entity_binding": True,
        "record_state_rules": {
            "raw_observations_are_distinct_from_formal_reviewed_entry": True,
            "chosen_branch_controls_formal_entry_state": True,
            "branch_contracts": branch_contracts,
        },
        "must_remain_unresolved": {
            "inference_ceiling": (spine.get("reversal") or {}).get("inference_ceiling"),
            "unresolved_after_reversal": (spine.get("reversal") or {}).get("unresolved_after_reversal"),
        },
        "operational_instantiation_policy": {
            "allow_transient_role_participants": True,
            "allow_scene_mechanics_implied_by_authorized_beats": True,
            "allow_non_durable_sensory_description": True,
            "allow_non_decisive_numeric_instantiation_when_consistent_with_constraints": True,
            "do_not_treat_reasonable_scene_instantiation_as_durable_canon": True,
            "still_forbid": [
                "new durable history not authorized",
                "new durable proper names",
                "branch state committed before earned",
                "unresolved cause/recurrence/scope promoted to fact",
                "numeric detail that changes evidence class or state beyond the spine",
            ],
        },
        "global_local_payoff": spine.get("local_payoff"),
        "decision_unknowns": (spine.get("decision_point") or {}).get("what_is_unknown"),
    }
