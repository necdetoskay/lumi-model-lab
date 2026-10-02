from __future__ import annotations

import json
from pathlib import Path

from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v20 import run
from src.spineforge_v20_obligations import load_qualification_cases


PACK = Path("data/specifications/story_lab/age12_island_not_on_any_map_spine_context_pack_v20.json")


def _architect_response(pack: SpineContextPackV1) -> dict:
    locs = pack.approved_premise["location_refs"]
    return {
        "schema": "narrative-spine.v1",
        "title": "The Island That Wasn't on Any Map",
        "episode_concept": {
            "story_promise": "Arda and Nisa reach an uncharted island before it vanishes.",
            "story_family": "ADVENTURE_EXPLORATION",
            "tone": "adventurous, tense, wonder-filled",
            "target_reader_effect": "curiosity, momentum, and earned mystery",
        },
        "protagonist": {
            "role": "young explorer",
            "immediate_goal": "reach the island and learn whether someone was there before",
            "pressure": "the route home is closing",
        },
        "central_question": "Who reached the island before them, and how far should Arda go before turning back?",
        "stakes": "They can lose their route home or lose the discovery.",
        "world_specific_elements": [
            {"context_ref": locs[1], "narrative_use": "first landing"},
            {"context_ref": locs[2], "narrative_use": "active exploration"},
            {"context_ref": locs[3], "narrative_use": "prior expedition discovery"},
        ],
        "beats": [
            {
                "key": "land",
                "location_ref": locs[1],
                "character_action": "Arda commits to the landing with Nisa.",
                "external_change": "The island starts drifting faster.",
                "new_information": "Their route home is already shrinking.",
                "consequence": "They move inland instead of lingering.",
                "escalation": "The cloud wall closes in.",
            },
            {
                "key": "trace",
                "location_ref": locs[2],
                "character_action": "They follow a human-made trail marker through unfamiliar terrain.",
                "external_change": "The trail leads away from their return point.",
                "new_information": "Someone else definitely explored this island.",
                "consequence": "Arda pushes toward the abandoned site.",
                "escalation": "Nisa argues that they are going too far.",
            },
            {
                "key": "site",
                "location_ref": locs[3],
                "character_action": "Arda searches the abandoned site and finds one concrete expedition trace.",
                "external_change": "The return corridor begins collapsing.",
                "new_information": "The earlier explorers expected the island to move again.",
                "consequence": "Arda chooses to take the trace and turn back now.",
                "escalation": "They must race the closing route.",
            },
            {
                "key": "escape",
                "location_ref": locs[1],
                "character_action": "Arda and Nisa launch together and escape with the discovered trace.",
                "external_change": "The island disappears into the cloud wall.",
                "new_information": "They were not first, but they are the first current scouts to return with proof of its history.",
                "consequence": "The island becomes a real unresolved discovery.",
                "escalation": "The clue points toward a larger mystery.",
            },
        ],
        "decision": {
            "required": True,
            "pressure": "The return corridor is almost gone.",
            "options": [
                {
                    "option": "follow the final clue deeper",
                    "immediate_cost": "risk losing the route home",
                    "possible_consequence": "learn more but become stranded",
                },
                {
                    "option": "turn back with the expedition trace",
                    "immediate_cost": "leave the deepest clue unresolved",
                    "possible_consequence": "return safely with a bounded discovery",
                },
            ],
        },
        "climax": "Arda chooses to turn back with the expedition trace and races Nisa to the gliders as the route closes.",
        "local_payoff": "They escape with proof that the island has a prior expedition history while its origin remains unknown.",
        "unresolved_hooks": ["Who left the expedition trace?", "Where does the island go?"],
        "reveal_limits": ["Do not explain the island's ultimate origin or destination."],
        "persistent_outcome_candidates": [
            {
                "type": "KNOWLEDGE",
                "description": "The uncharted island has evidence of prior explorers.",
                "commit_condition": "Delivered prose shows the trace being found and brought back.",
            }
        ],
        "writer_rules": [
            "Keep exploration and movement foregrounded.",
            "Do not turn the episode into a measurement or reporting sequence.",
        ],
    }


def _architect_call(**kwargs):
    raw = _architect_response(
        SpineContextPackV1.model_validate(
            json.loads(kwargs["user_prompt"])["spine_context_pack"]
        )
    )
    return raw, {"usage": {}}, {"response_format": {"type": "json_object"}}, []


def _gate_call(**kwargs):
    raw = {
        "schema": "spineforge-v19-product-gate.v1",
        "decision": "ACCEPT",
        "blocking_findings": [],
        "summary": "Ready for human review.",
    }
    return raw, {"usage": {}}, {"response_format": {"type": "json_schema"}}, []


def test_v20_runtime_uses_story_first_prompt_and_stops_for_human_review():
    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    case = load_qualification_cases().cases[0]
    result = run(
        context_pack=pack,
        obligations=case.obligations,
        api_key="not-used",
        architect_call_fn=_architect_call,
        gate_call_fn=_gate_call,
    )
    assert result["schema"] == "spineforge-v20-evidence.v1"
    assert result["status"] == "awaiting_human_review"
    assert result["writer_authorized"] is False
    assert result["generation_topology"][0] == "SONNET_STORY_FIRST_NARRATIVE_SPINE_ARCHITECT"
    assert result["deterministic_validation"]["authority_valid"] is True
    assert result["deterministic_validation"]["reveal_safe"] is True
    assert result["deterministic_validation"]["obligations_valid"] is True
