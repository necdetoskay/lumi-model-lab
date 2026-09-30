from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.spineforge_v5_contract import (
    SpineCreativeBlueprintV2,
    SpineStructuralAssemblyV1,
)


def _signature() -> dict:
    return {
        "dramatic_engine": "A legal map denies a road that instruments can witness.",
        "protagonist_desire": "Document the anomaly honestly.",
        "protagonist_pressure": "Dusk and professional risk.",
        "central_wonder_or_intrigue": "A boundary seems to seek a witness.",
        "signature_scene_promises": ["A living map discrepancy", "A dangerous second reading"],
        "roleplay_opportunities": ["Calibrate tools", "Interpret evidence", "Choose what to record"],
        "emotional_turns": ["Curiosity to dread", "Dread to resolve"],
        "world_specific_story_uses": ["Witnessed cartographic magic", "Legally binding maps"],
        "freshness_claim": "The map conflict is epistemic rather than a generic portal.",
        "why_reader_wants_next_beat": "The road may be real, unstable, or both.",
    }


def _blueprint() -> dict:
    return {
        "schema": "spineforge-creative-blueprint.v2",
        "creative_model": "aion-labs/aion-3.5-mini",
        "creative_signature": _signature(),
        "episode_intent": {
            "title": "The Pulse of Ashen Gate",
            "story_promise": "Prove an impossible road without making a false map.",
            "protagonist_role": "Junior boundary cartographer.",
            "immediate_objective": "Capture bounded evidence before dusk.",
            "central_question": "Is the road returning or is the map failing?",
            "stakes": "False certainty can endanger Greyfen and Leyra's apprenticeship.",
            "opening_hook": "The compass answers a route the map denies.",
            "decision_pressure": "Stay for corroboration or leave with weaker evidence.",
            "climax_idea": "Hold a passive survey rig through a second pulse.",
            "local_payoff": "A defensible bounded field record.",
            "forward_hook": "Ilyan's mark proves prior presence, not motive.",
            "unresolved_question": "What did Ilyan learn here?",
            "constraints": ["Do not cross the sealed boundary."],
        },
        "creative_beats": [
            {
                "key": "arrival",
                "location_ref": "ashen_gate",
                "dramatic_function": "Break routine with impossible evidence.",
                "character_action": "Calibrate the compass.",
                "external_pressure_or_event": "The needle points through the sealed arch.",
                "discovery_or_change": "The map and witnessed signal disagree.",
                "causal_dependency_keys": [],
            },
            {
                "key": "measure",
                "location_ref": "ashen_gate",
                "dramatic_function": "Test whether the signal is residue.",
                "character_action": "Measure cadence.",
                "external_pressure_or_event": "The pulse strengthens.",
                "discovery_or_change": "The response is structured.",
                "causal_dependency_keys": ["arrival"],
            },
            {
                "key": "threat",
                "location_ref": "ashen_gate",
                "dramatic_function": "Turn observation into personal risk.",
                "character_action": "Clamp the registering needle.",
                "external_pressure_or_event": "The road tries to complete a witness mark.",
                "discovery_or_change": "Observation changes the anomaly.",
                "causal_dependency_keys": ["measure"],
            },
            {
                "key": "mark",
                "location_ref": "ashen_gate",
                "dramatic_function": "Connect the anomaly to the mentor mystery.",
                "character_action": "Inspect the far survey stone.",
                "external_pressure_or_event": "Ilyan's private mark is uncovered.",
                "discovery_or_change": "Ilyan previously surveyed here.",
                "causal_dependency_keys": ["threat"],
            },
            {
                "key": "choice",
                "location_ref": "ashen_gate",
                "dramatic_function": "Force a professional trade-off.",
                "character_action": "Choose whether to risk a second reading.",
                "external_pressure_or_event": "The light is almost gone.",
                "discovery_or_change": "Corroboration now has a real cost.",
                "causal_dependency_keys": ["mark"],
            },
            {
                "key": "capture",
                "location_ref": "ashen_gate",
                "dramatic_function": "Earn the local proof.",
                "character_action": "Hold a passive rig through the pulse.",
                "external_pressure_or_event": "A violent second pulse hits.",
                "discovery_or_change": "The anomaly is repeatable under bounded conditions.",
                "causal_dependency_keys": ["choice"],
            },
            {
                "key": "record",
                "location_ref": "ashen_gate",
                "dramatic_function": "Resolve what can honestly be claimed.",
                "character_action": "Write a bounded field record.",
                "external_pressure_or_event": "Night closes the survey window.",
                "discovery_or_change": "The anomaly can be reported without explaining its cause.",
                "causal_dependency_keys": ["capture"],
            },
        ],
        "roleplay_threads": ["Survey craft", "Evidence discipline", "Mentor trust"],
        "self_check_notes": [],
    }


def test_blueprint_is_not_forced_to_emit_episode_spine_fields() -> None:
    blueprint = SpineCreativeBlueprintV2.model_validate(_blueprint())
    beat = blueprint.creative_beats[0]
    assert not hasattr(beat, "phase")
    assert not hasattr(beat, "new_information")
    assert not hasattr(blueprint, "logistics_plan")


def test_blueprint_requires_only_backward_dependencies() -> None:
    payload = _blueprint()
    payload["creative_beats"][1]["causal_dependency_keys"] = ["capture"]
    with pytest.raises(ValidationError):
        SpineCreativeBlueprintV2.model_validate(payload)


def test_blueprint_rejects_duplicate_keys() -> None:
    payload = _blueprint()
    payload["creative_beats"][1]["key"] = "arrival"
    with pytest.raises(ValidationError):
        SpineCreativeBlueprintV2.model_validate(payload)


def test_structural_assembly_boundary_owns_strict_episode_spine() -> None:
    schema = SpineStructuralAssemblyV1.model_json_schema(by_alias=True)
    episode_schema = schema["$defs"]["EpisodeSpineV3"]
    required = set(episode_schema["required"])
    assert "beats" in required
    assert "logistics_plan" in required
    assert "reversal" in required
    assert "decision_point" in required
