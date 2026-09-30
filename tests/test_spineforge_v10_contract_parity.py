from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.spineforge_v10_contract import (
    DecisionBranchDraftV10,
    PersistentOutcomeDraftV10,
    StructuralFrameV10,
    StructuralResolutionV10,
)


def _resolution_payload() -> dict:
    return {
        "schema": "spineforge-structural-resolution.v1",
        "reversal": {
            "prior_belief": "old",
            "evidence": [
                {
                    "claim": "observed clue",
                    "supporting_beat_keys": ["beat_one"],
                    "certainty": "OBSERVED",
                }
            ],
            "reinterpretation": "new",
            "inference_ceiling": "bounded",
            "unresolved_after_reversal": "open",
        },
        "decision_point": {
            "pressure": "time",
            "branches": [
                {
                    "key": "option_one",
                    "option": "one",
                    "immediate_action": "act",
                    "evidence_state_after_choice": "state",
                    "cost_or_risk": "cost",
                    "relationship_or_access_effect": "effect",
                    "climax_requirement": "climax",
                    "local_payoff_if_earned": "payoff",
                },
                {
                    "key": "option_two",
                    "option": "two",
                    "immediate_action": "act",
                    "evidence_state_after_choice": "state",
                    "cost_or_risk": "cost",
                    "relationship_or_access_effect": "effect",
                    "climax_requirement": "climax",
                    "local_payoff_if_earned": "payoff",
                },
            ],
            "what_is_unknown": "unknown",
        },
        "persistent_outcome_candidates": [
            {
                "type": "KNOWLEDGE",
                "description": "bounded fact",
                "commit_condition": "earned in prose",
            }
        ],
        "saga_progression": {"completion_evidence": ["evidence"]},
        "anti_repetition_signature": {
            "core_problem_shape": "shape",
            "primary_activity": "activity",
            "main_location_pattern": "pattern",
            "climax_shape": "climax",
            "distinct_from_recent_episodes_because": "fresh",
        },
    }


def test_v10_rejects_v9_free_text_certainty_at_resolution_boundary() -> None:
    payload = _resolution_payload()
    payload["reversal"]["evidence"][0]["certainty"] = (
        "Witnessed: the map entry. Attribution is only an inference."
    )
    with pytest.raises(ValidationError, match="OBSERVED"):
        StructuralResolutionV10.model_validate(payload)


def test_v10_resolution_schema_exposes_certainty_enum_to_model_prompt() -> None:
    schema = StructuralResolutionV10.model_json_schema(by_alias=True)
    enum_values = schema["$defs"]["ReversalEvidenceDraftV10"]["properties"]["certainty"]["enum"]
    assert enum_values == ["OBSERVED", "INFERRED", "HYPOTHESIS"]


def test_v10_frame_rejects_noncanonical_episode_role() -> None:
    with pytest.raises(ValidationError):
        StructuralFrameV10.model_validate(
            {
                "schema": "spineforge-structural-frame.v1",
                "preserved_creative_strengths": ["a", "b"],
                "title": "t",
                "episode_role": "main saga discovery episode",
                "story_promise": "p",
                "protagonist_role": "r",
                "immediate_objective": "o",
                "central_question": "q",
                "stakes": "s",
                "constraints": ["c"],
                "opening_hook": "h",
                "logistics": {
                    "time_window": "day",
                    "movement_constraints": ["stay outside"],
                    "feasibility_rationale": "valid",
                },
                "escalation_ladder": ["1", "2", "3"],
                "climax": "c",
                "local_payoff": "p",
                "forward_hook": "f",
                "writer_rules": ["w"],
            }
        )


def test_v10_decision_key_matches_episode_spine_pattern() -> None:
    with pytest.raises(ValidationError):
        DecisionBranchDraftV10.model_validate(
            {
                "key": "Bad Key",
                "option": "one",
                "immediate_action": "act",
                "evidence_state_after_choice": "state",
                "cost_or_risk": "cost",
                "relationship_or_access_effect": "effect",
                "climax_requirement": "climax",
                "local_payoff_if_earned": "payoff",
            }
        )


def test_v10_persistent_outcome_type_matches_episode_spine_literal() -> None:
    with pytest.raises(ValidationError):
        PersistentOutcomeDraftV10.model_validate(
            {
                "type": "WORLD_STATE",
                "description": "x",
                "commit_condition": "y",
            }
        )
