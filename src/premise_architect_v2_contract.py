from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.reader_profile_v2 import ReaderDevelopmentProfileV2
from src.saga_blueprint_contract import NarrativeFixture
from src.saga_spine_v2_contract import CharacterSagaSpineV2


PREMISE_BATCH_SCHEMA = "premise-candidate-batch.v2"
PREMISE_GATE_SCHEMA = "premise-gate.v2"
STATE_SCHEMA = "premise-lab-state.v1"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PremiseLabStateV1(StrictModel):
    schema_id: Literal[STATE_SCHEMA] = Field(alias="schema")
    completed_milestone_keys: list[str]
    active_side_saga_keys: list[str]
    known_world_facts: list[str]
    recent_episode_summaries: list[str]
    requested_session: Literal["QUICK", "STANDARD", "LONG", "SPECIAL"]
    requested_mode: Literal[
        "ADVENTURE",
        "MYSTERY",
        "EXPLORATION",
        "RELATIONSHIP",
        "CALM",
    ]


class PremiseCandidateV2(StrictModel):
    key: str
    title: str
    primary_focus: Literal[
        "MAIN_SAGA",
        "SIDE_SAGA",
        "WORLD_EXPLORATION",
        "RELATIONSHIP",
        "SAGA_FREE_ADVENTURE",
        "MIXED",
    ]
    target_refs: list[str]
    differentiation_key: str
    logline: str
    protagonist_role: str
    immediate_objective: str
    inciting_event: str
    central_problem: str
    wonder_or_discovery: str
    stakes: str
    constraints: list[str]
    meaningful_choice_pressure: str
    mystery_or_forward_question: str
    local_payoff: str
    persistent_outcomes_possible: list[str]
    world_specific_elements: list[str]
    saga_progression_required: bool
    expected_session: Literal["QUICK", "STANDARD", "LONG", "SPECIAL"]

    @model_validator(mode="after")
    def validate_candidate(self) -> "PremiseCandidateV2":
        if len(self.world_specific_elements) < 2:
            raise ValueError(f"{self.key}: at least two world-specific elements required")
        if not self.persistent_outcomes_possible:
            raise ValueError(f"{self.key}: persistent outcomes required")
        if not self.constraints:
            raise ValueError(f"{self.key}: at least one real constraint required")
        return self


class PremiseCandidateBatchV2(StrictModel):
    schema_id: Literal[PREMISE_BATCH_SCHEMA] = Field(alias="schema")
    candidates: list[PremiseCandidateV2]

    @model_validator(mode="after")
    def validate_batch(self) -> "PremiseCandidateBatchV2":
        if len(self.candidates) != 3:
            raise ValueError("Premise Architect must return exactly 3 candidates")
        keys = [item.key for item in self.candidates]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate premise candidate key")
        diffs = [item.differentiation_key for item in self.candidates]
        if len(diffs) != len(set(diffs)):
            raise ValueError("premise candidates must be materially differentiated")
        focuses = {item.primary_focus for item in self.candidates}
        if len(focuses) < 2:
            raise ValueError("premise candidates must span at least two primary focuses")
        return self


class PremiseDimensionEvaluation(StrictModel):
    name: Literal[
        "PREMISE_MATURITY",
        "ROLEPLAY_IMMERSION",
        "WONDER_DISCOVERY",
        "AGENCY",
        "STAKES",
        "MYSTERY_CURIOSITY",
        "CAUSAL_POTENTIAL",
        "WORLD_INTEGRATION",
        "PERSISTENT_VALUE",
        "REPETITION_RISK",
    ]
    score: int = Field(ge=1, le=5)
    blocking_failure: bool
    reason: str


class PremiseCandidateEvaluation(StrictModel):
    candidate_key: str
    dimensions: list[PremiseDimensionEvaluation]
    verdict: Literal["ACCEPT", "REJECT"]
    blocking_reasons: list[str]

    @model_validator(mode="after")
    def validate_dimensions(self) -> "PremiseCandidateEvaluation":
        expected = {
            "PREMISE_MATURITY",
            "ROLEPLAY_IMMERSION",
            "WONDER_DISCOVERY",
            "AGENCY",
            "STAKES",
            "MYSTERY_CURIOSITY",
            "CAUSAL_POTENTIAL",
            "WORLD_INTEGRATION",
            "PERSISTENT_VALUE",
            "REPETITION_RISK",
        }
        names = [row.name for row in self.dimensions]
        if len(names) != len(set(names)) or set(names) != expected:
            raise ValueError("premise evaluation must cover every gate dimension exactly once")
        if any(row.blocking_failure for row in self.dimensions) and self.verdict != "REJECT":
            raise ValueError("blocking dimension failure requires REJECT")
        return self


class PremiseGateV2(StrictModel):
    schema_id: Literal[PREMISE_GATE_SCHEMA] = Field(alias="schema")
    evaluations: list[PremiseCandidateEvaluation]
    decision: Literal["ACCEPT", "REJECT_ALL"]
    selected_candidate_key: str | None
    decision_reason: str

    @model_validator(mode="after")
    def validate_decision(self) -> "PremiseGateV2":
        keys = [row.candidate_key for row in self.evaluations]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate candidate evaluation")
        accepted = {row.candidate_key for row in self.evaluations if row.verdict == "ACCEPT"}
        if self.decision == "REJECT_ALL":
            if self.selected_candidate_key is not None:
                raise ValueError("REJECT_ALL cannot select a candidate")
        else:
            if self.selected_candidate_key not in accepted:
                raise ValueError("selected candidate must have ACCEPT verdict")
        return self


def build_reveal_safe_premise_projection(
    *,
    spine: CharacterSagaSpineV2,
    reader: ReaderDevelopmentProfileV2,
    fixture: NarrativeFixture,
    state: PremiseLabStateV1,
) -> dict:
    milestone_map = {m.key: m for m in spine.main_saga.milestones}
    anchor_map = {a.key: a for a in spine.main_saga.anchors}
    completed = set(state.completed_milestone_keys)

    unknown_completed = sorted(completed - set(milestone_map))
    if unknown_completed:
        raise ValueError(
            "unknown completed milestones: " + ", ".join(unknown_completed)
        )

    active_anchors = set(spine.main_saga.entry_anchor_keys)
    changed = True
    while changed:
        changed = False
        for edge in spine.main_saga.edges:
            if (
                edge.from_node in completed
                and edge.to_node in anchor_map
                and edge.to_node not in active_anchors
            ):
                active_anchors.add(edge.to_node)
                changed = True

    eligible_milestones: set[str] = set()
    for edge in spine.main_saga.edges:
        if edge.to_node not in milestone_map or edge.to_node in completed:
            continue
        if edge.from_node in active_anchors or edge.from_node in completed:
            eligible_milestones.add(edge.to_node)

    side_map = {s.key: s for s in spine.latent_side_sagas}
    unknown_side = sorted(set(state.active_side_saga_keys) - set(side_map))
    if unknown_side:
        raise ValueError("unknown active side sagas: " + ", ".join(unknown_side))

    session = reader.standard_session
    if state.requested_session != "STANDARD":
        matches = [x for x in reader.optional_sessions if x.name == state.requested_session]
        if not matches:
            raise ValueError(f"reader profile lacks session {state.requested_session}")
        session = matches[0]

    projection = {
        "schema": "premise-context-projection.v2",
        "reader_profile": reader.model_dump(mode="json", by_alias=True),
        "session_target": session.model_dump(mode="json"),
        "character": {
            "name": fixture.character.name,
            "age": fixture.character.age,
            "archetype": fixture.character.archetype,
            "traits": fixture.character.traits,
            "interests": fixture.character.interests,
            "origin_summary": spine.origin.summary,
            "current_role": spine.present_situation.current_role,
            "identity_anchors": [
                row.model_dump(mode="json")
                for row in spine.narrative_core.identity_anchors
            ],
            "core_drives": [
                row.model_dump(mode="json")
                for row in spine.narrative_core.core_drives
            ],
            "internal_tensions": [
                row.model_dump(mode="json")
                for row in spine.narrative_core.internal_tensions
            ],
            "immediate_desires": spine.present_situation.immediate_desires,
            "immediate_avoidances": spine.present_situation.immediate_avoidances,
        },
        "world": {
            "world_type": fixture.world.world_type,
            "era": fixture.world.era,
            "habitat": fixture.world.habitat,
            "technology_level": fixture.world.technology_level,
            "magic_level": fixture.world.magic_level,
            "summary": fixture.world.summary,
            "locations": fixture.world.locations,
            "social_context": fixture.world.social_context,
            "known_pressures": fixture.world.known_pressures,
            "known_world_facts": state.known_world_facts,
        },
        "main_saga_public": {
            "key": spine.main_saga.key,
            "title": spine.main_saga.title,
            "goal": spine.main_saga.goal,
            "stakes": spine.main_saga.stakes,
            "central_mystery": spine.main_saga.central_mystery,
            "themes": spine.main_saga.themes,
        },
        "eligible_main_saga_milestones": [
            {
                "key": milestone_map[key].key,
                "anchor_key": milestone_map[key].anchor_key,
                "type": milestone_map[key].type,
                "summary": milestone_map[key].summary,
                "state_condition": milestone_map[key].state_condition,
                "possible_entry_vectors": milestone_map[key].possible_entry_vectors,
                "consequence_options": milestone_map[key].consequence_options,
            }
            for key in sorted(eligible_milestones)
        ],
        "active_side_sagas": [
            {
                "key": side_map[key].key,
                "arc_type": side_map[key].arc_type,
                "premise": side_map[key].premise,
                "why_it_matters": side_map[key].why_it_matters,
            }
            for key in state.active_side_saga_keys
        ],
        "recent_episode_summaries": state.recent_episode_summaries,
        "requested_mode": state.requested_mode,
        "creative_permission_envelope": spine.creative_permission_envelope.model_dump(
            mode="json"
        ),
        "rules": {
            "main_saga_progression_optional": True,
            "future_character_choice_must_remain_open": True,
            "durable_new_fact_requires_outcome_commit": True,
            "hidden_truths_not_available_to_premise_architect": True,
        },
    }

    serialized = json.dumps(projection, ensure_ascii=False)
    forbidden = [
        "hidden_statement",
        '"hidden_truths"',
        '"reveal_steps"',
        "tide_mechanism",
        "fathers_survey_findings",
    ]
    for marker in forbidden:
        if marker in serialized:
            raise RuntimeError(
                f"reveal-safe premise projection leaked forbidden marker: {marker}"
            )

    return projection
