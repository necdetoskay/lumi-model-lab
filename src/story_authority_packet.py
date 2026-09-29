from __future__ import annotations

import re
from typing import Any


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _entity_specific_world_facts(projection: dict[str, Any]) -> dict[str, list[str]]:
    world = projection["world"]
    facts = [str(x) for x in world.get("known_world_facts") or []]
    result: dict[str, list[str]] = {}

    for loc in world.get("location_access") or []:
        key = str(loc["key"])
        name = str(loc["name"])
        nname = _norm(name)
        nkey = _norm(key.replace("_", " "))
        matched: list[str] = []
        for fact in facts:
            nf = _norm(fact)
            if nname and nname in nf:
                matched.append(fact)
            elif nkey and nkey in nf:
                matched.append(fact)
        result[key] = matched

    return result


def build_story_authority_packet(approved: dict[str, Any]) -> dict[str, Any]:
    projection = approved["projection"]
    spine = approved["episode_spine"]
    character = projection["character"]
    world = projection["world"]

    known_proper_names = {str(character["name"])}
    for loc in world.get("location_access") or []:
        known_proper_names.add(str(loc["name"]))

    # Public Saga titles are durable names too.
    main_saga = projection.get("main_saga_public") or {}
    if main_saga.get("title"):
        known_proper_names.add(str(main_saga["title"]))

    entity_facts = _entity_specific_world_facts(projection)

    branch_record_contracts: dict[str, dict[str, Any]] = {}
    for branch in (spine.get("decision_point") or {}).get("branches") or []:
        branch_record_contracts[str(branch["key"])] = {
            "evidence_state_after_choice": branch.get("evidence_state_after_choice"),
            "cost_or_risk": branch.get("cost_or_risk"),
            "local_payoff_if_earned": branch.get("local_payoff_if_earned"),
        }

    return {
        "schema_version": "story-authority-packet.v1",
        "authority_rules": [
            "Ambient world summary is setting-level context, not entity-specific authority.",
            "A class-level or world-level fact MUST NOT be transferred to a named location, object, person, group, or historical event unless an entity-specific fact or the approved spine explicitly authorizes that transfer.",
            "Do not invent durable history for named entities. Age, origin, builders, prior incidents, prior owners, institutional history, or old causal knowledge require explicit authority.",
            "Do not invent durable proper names for recurring NPCs or institutions. If a required role has no supplied proper name, use the role descriptor.",
            "Character speculation and hypotheses are allowed only when clearly framed as speculation; narration must not silently promote them into world fact.",
            "Raw readings, field notes, sketches, and measurements are not the same state as a reviewed formal entry. Never describe all records as absent when raw observations already exist.",
            "Future rumors, reports, social spread, access changes, or institutional actions remain conditional unless they occur in the episode or are explicitly committed by the chosen branch.",
        ],
        "known_durable_proper_names": sorted(known_proper_names),
        "new_durable_proper_names_allowed": False,
        "entity_specific_world_facts": entity_facts,
        "world_level_known_facts": list(world.get("known_world_facts") or []),
        "ambient_world_summary": world.get("summary"),
        "ambient_summary_is_not_entity_binding": True,
        "record_state_rules": {
            "raw_observations_are_distinct_from_formal_reviewed_entry": True,
            "chosen_branch_controls_formal_entry_state": True,
            "branch_contracts": branch_record_contracts,
        },
        "must_remain_unresolved": {
            "inference_ceiling": (spine.get("reversal") or {}).get("inference_ceiling"),
            "unresolved_after_reversal": (spine.get("reversal") or {}).get("unresolved_after_reversal"),
        },
        "writer_rules": list(spine.get("writer_rules") or []),
    }
