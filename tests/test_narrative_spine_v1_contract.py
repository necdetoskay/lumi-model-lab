from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from src.narrative_spine_v1_contract import NarrativeSpineV1, SpineProductGateV19


def _spine() -> dict:
    return {
        "schema": "narrative-spine.v1",
        "title": "The Returning Road",
        "episode_concept": {
            "story_promise": "Leyra tests why a vanished road has returned.",
            "story_family": "FANTASY_MYSTERY",
            "tone": "tense exploratory wonder",
            "target_reader_effect": "curiosity, agency, and earned uncertainty",
        },
        "protagonist": {
            "role": "forbidden cartographer",
            "immediate_goal": "verify the road without exposing her source",
            "pressure": "the road may vanish again before dusk",
        },
        "central_question": "What changed enough for the road to reappear?",
        "stakes": "Leyra can gain access and evidence, or lose credibility and safe passage.",
        "world_specific_elements": [
            {"context_ref": "greyfen", "narrative_use": "field evidence"},
            {"context_ref": "ashen_gate", "narrative_use": "boundary pressure"},
        ],
        "beats": [
            {
                "key": "trace_marks",
                "location_ref": "greyfen",
                "character_action": "Leyra measures the new track against old survey marks.",
                "external_change": "A second line of stones becomes visible.",
                "new_information": "The new road follows a route older than the current map.",
                "consequence": "She must choose whether to follow before she can verify the source.",
                "escalation": "Time pressure begins.",
            },
            {
                "key": "test_gate",
                "location_ref": "ashen_gate",
                "character_action": "Leyra tests the gate response with a harmless marker.",
                "external_change": "The gate reacts only to one route alignment.",
                "new_information": "The road and gate are causally linked.",
                "consequence": "Returning safely now requires preserving the alignment.",
                "escalation": "Access becomes conditional.",
            },
            {
                "key": "choose_record",
                "location_ref": "greyfen",
                "character_action": "Leyra decides what evidence to preserve and what to leave untouched.",
                "external_change": "The visible path starts fading.",
                "new_information": "Only one observation can be completed before the route disappears.",
                "consequence": "Her choice determines what can be proved later.",
                "escalation": "Evidence and access cannot both be maximized.",
            },
        ],
        "decision": {
            "required": True,
            "pressure": "Only one observation can be completed before the road fades.",
            "options": [
                {
                    "option": "record the gate response",
                    "immediate_cost": "lose the chance to map the deeper route",
                    "possible_consequence": "strong proof but less exploration",
                },
                {
                    "option": "follow the deeper route",
                    "immediate_cost": "return with weaker proof",
                    "possible_consequence": "more discovery but credibility risk",
                },
            ],
        },
        "climax": "Leyra commits to one evidence path and acts before the road closes.",
        "local_payoff": "She returns with an earned, limited finding and a new open question.",
        "unresolved_hooks": ["Why did the route return now?"],
        "reveal_limits": ["Do not answer the long-horizon hidden cause."],
        "persistent_outcome_candidates": [
            {
                "type": "KNOWLEDGE",
                "description": "Leyra may retain evidence that the gate responds to route alignment.",
                "commit_condition": "the chosen evidence is actually observed in the story",
            }
        ],
        "writer_rules": ["Do not turn candidate outcomes into facts before they are earned."],
    }


def test_contract_does_not_require_legacy_phase_taxonomy():
    value = NarrativeSpineV1.model_validate(_spine())
    assert len(value.beats) == 3
    assert not hasattr(value.beats[0], "phase")


def test_application_owned_fields_are_rejected_from_model_product():
    raw = _spine()
    raw["exact_age"] = 18
    with pytest.raises(ValidationError):
        NarrativeSpineV1.model_validate(raw)


def test_required_decision_needs_two_real_options():
    raw = copy.deepcopy(_spine())
    raw["decision"]["options"] = raw["decision"]["options"][:1]
    with pytest.raises(ValidationError):
        NarrativeSpineV1.model_validate(raw)


def test_gate_accept_is_compact_and_finding_free():
    gate = SpineProductGateV19.model_validate({
        "schema": "spineforge-v19-product-gate.v1",
        "decision": "ACCEPT",
        "blocking_findings": [],
        "summary": "No blocking product defect remains.",
    })
    assert gate.decision == "ACCEPT"


def test_gate_repair_cannot_hide_structural_replan():
    with pytest.raises(ValidationError):
        SpineProductGateV19.model_validate({
            "schema": "spineforge-v19-product-gate.v1",
            "decision": "REPAIR",
            "blocking_findings": [{
                "dimension": "AGE_FIT",
                "severity": "BLOCKER",
                "repairability": "PREMISE",
                "target_path": "episode_concept",
                "reason": "Premise is too young.",
                "evidence": "Core activity is preschool pretend play.",
            }],
            "summary": "This needs a new premise.",
        })
