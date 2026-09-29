from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SPINE_SCHEMA = "episode-spine.v2"
GATE_SCHEMA = "episode-spine-gate.v2"
KEY_PATTERN = r"^[a-z][a-z0-9_]*$"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EpisodeBeatV2(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    phase: Literal[
        "HOOK",
        "ORIENT",
        "COMPLICATION",
        "INVESTIGATION",
        "ESCALATION",
        "REVERSAL",
        "DECISION",
        "CLIMAX",
        "PAYOFF",
        "TAG",
    ]
    purpose: str
    location_ref: str
    character_action: str
    external_event: str
    new_information: str
    causal_dependency_keys: list[str]
    escalation_delta: str
    state_change: str
    payoff_contribution: str


class ReversalEvidenceV2(StrictModel):
    claim: str
    supporting_beat_keys: list[str]
    certainty: Literal["OBSERVED", "INFERRED", "HYPOTHESIS"]


class ReversalV2(StrictModel):
    prior_belief: str
    evidence: list[ReversalEvidenceV2]
    reinterpretation: str
    inference_ceiling: str
    unresolved_after_reversal: str

    @model_validator(mode="after")
    def validate_evidence(self) -> "ReversalV2":
        if not self.evidence:
            raise ValueError("reversal requires explicit supporting evidence")
        if any(not row.supporting_beat_keys for row in self.evidence):
            raise ValueError("every reversal evidence claim needs supporting beat keys")
        return self


class DecisionBranchV2(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    option: str
    immediate_action: str
    evidence_state_after_choice: str
    cost_or_risk: str
    relationship_or_access_effect: str
    climax_requirement: str
    local_payoff_if_earned: str


class DecisionPointV2(StrictModel):
    pressure: str
    branches: list[DecisionBranchV2]
    what_is_unknown: str
    outcome_uncommitted: Literal[True]

    @model_validator(mode="after")
    def validate_branches(self) -> "DecisionPointV2":
        if len(self.branches) < 2:
            raise ValueError("decision point requires at least two credible branches")
        branch_keys = [branch.key for branch in self.branches]
        if len(branch_keys) != len(set(branch_keys)):
            raise ValueError("decision point branch keys must be unique")
        return self


class LogisticsPlanV2(StrictModel):
    time_window: str
    location_sequence: list[str]
    movement_constraints: list[str]
    feasibility_rationale: str


class PersistentOutcomeCandidateV2(StrictModel):
    type: Literal[
        "KNOWLEDGE",
        "RELATIONSHIP",
        "REPUTATION",
        "ACCESS",
        "ITEM",
        "RUMOR",
        "OPPORTUNITY",
        "LOCATION_STATE",
        "SAGA_STATE",
    ]
    description: str
    commit_condition: str


class SagaProgressionIntentV2(StrictModel):
    intended_milestone_keys: list[str]
    commit_only_if_earned: Literal[True]
    completion_evidence: list[str]


class AntiRepetitionSignatureV2(StrictModel):
    core_problem_shape: str
    primary_activity: str
    main_location_pattern: str
    climax_shape: str
    distinct_from_recent_episodes_because: str


class EpisodeSpineV2(StrictModel):
    schema_id: Literal[SPINE_SCHEMA] = Field(alias="schema")
    premise_key: str
    title: str
    exact_age: int = Field(ge=3, le=120)
    session: Literal["QUICK", "STANDARD", "LONG", "SPECIAL"]
    target_words_min: int = Field(ge=100)
    target_words_max: int = Field(ge=100)
    episode_role: Literal[
        "MAIN_SAGA_ENTRY",
        "MAIN_SAGA_PROGRESS",
        "SIDE_SAGA",
        "WORLD_EXPLORATION",
        "RELATIONSHIP",
        "SAGA_FREE",
        "MIXED",
    ]
    story_promise: str
    protagonist_role: str
    immediate_objective: str
    central_question: str
    stakes: str
    constraints: list[str]
    opening_hook: str
    logistics_plan: LogisticsPlanV2
    beats: list[EpisodeBeatV2]
    escalation_ladder: list[str]
    reversal: ReversalV2
    decision_point: DecisionPointV2
    climax: str
    local_payoff: str
    forward_hook: str
    persistent_outcome_candidates: list[PersistentOutcomeCandidateV2]
    saga_progression: SagaProgressionIntentV2
    anti_repetition_signature: AntiRepetitionSignatureV2
    writer_rules: list[str]

    @model_validator(mode="after")
    def validate_spine(self) -> "EpisodeSpineV2":
        if self.target_words_min > self.target_words_max:
            raise ValueError("target_words_min cannot exceed target_words_max")
        if not 8 <= len(self.beats) <= 12:
            raise ValueError(
                f"Episode Spine requires 8-12 beats, got {len(self.beats)}"
            )

        beat_keys = [beat.key for beat in self.beats]
        if len(beat_keys) != len(set(beat_keys)):
            raise ValueError("duplicate beat key")

        required_phases = {
            "HOOK",
            "COMPLICATION",
            "REVERSAL",
            "DECISION",
            "CLIMAX",
            "PAYOFF",
        }
        phases = {beat.phase for beat in self.beats}
        missing = sorted(required_phases - phases)
        if missing:
            raise ValueError(
                "Episode Spine missing required phases: " + ", ".join(missing)
            )

        seen: set[str] = set()
        for index, beat in enumerate(self.beats):
            if index > 0 and not beat.causal_dependency_keys:
                raise ValueError(
                    f"{beat.key}: every non-opening beat needs a causal dependency"
                )
            unknown_or_future = [
                ref for ref in beat.causal_dependency_keys if ref not in seen
            ]
            if unknown_or_future:
                raise ValueError(
                    f"{beat.key}: dependencies must reference earlier beats: "
                    + ", ".join(unknown_or_future)
                )
            seen.add(beat.key)

        reversal_index = next(
            index for index, beat in enumerate(self.beats) if beat.phase == "REVERSAL"
        )
        pre_reversal_keys = {beat.key for beat in self.beats[:reversal_index]}
        for evidence in self.reversal.evidence:
            unsupported = [
                ref for ref in evidence.supporting_beat_keys
                if ref not in pre_reversal_keys
            ]
            if unsupported:
                raise ValueError(
                    "reversal evidence must reference beats established before reversal: "
                    + ", ".join(unsupported)
                )

        if len(self.escalation_ladder) < 3:
            raise ValueError("Episode Spine requires at least 3 escalation steps")
        if not self.constraints:
            raise ValueError("Episode Spine requires constraints")
        if not self.persistent_outcome_candidates:
            raise ValueError("Episode Spine requires persistent outcome candidates")
        if not self.writer_rules:
            raise ValueError("Episode Spine requires writer rules")
        if not self.saga_progression.completion_evidence:
            raise ValueError("Saga progression requires completion evidence")
        return self


class EpisodeSpineDimensionEvaluationV2(StrictModel):
    name: Literal[
        "AGE_MATURITY",
        "CAUSAL_COHERENCE",
        "ESCALATION",
        "AGENCY",
        "REVERSAL_QUALITY",
        "CLIMAX_PAYOFF",
        "WORLD_IMMERSION",
        "SAGA_ALIGNMENT",
        "LOCAL_SATISFACTION",
        "WRITER_EXECUTABILITY",
        "REPETITION_SAFETY",
    ]
    score: int = Field(ge=1, le=5)
    blocking_failure: bool
    reason: str


class EpisodeSpineGateV2(StrictModel):
    schema_id: Literal[GATE_SCHEMA] = Field(alias="schema")
    dimensions: list[EpisodeSpineDimensionEvaluationV2]
    decision: Literal["ACCEPT", "REPLAN"]
    blocking_reasons: list[str]
    decision_reason: str

    @model_validator(mode="after")
    def validate_gate(self) -> "EpisodeSpineGateV2":
        expected = {
            "AGE_MATURITY",
            "CAUSAL_COHERENCE",
            "ESCALATION",
            "AGENCY",
            "REVERSAL_QUALITY",
            "CLIMAX_PAYOFF",
            "WORLD_IMMERSION",
            "SAGA_ALIGNMENT",
            "LOCAL_SATISFACTION",
            "WRITER_EXECUTABILITY",
            "REPETITION_SAFETY",
        }
        names = [row.name for row in self.dimensions]
        if len(names) != len(set(names)) or set(names) != expected:
            raise ValueError("Episode Spine Gate must cover every dimension exactly once")

        if any(row.blocking_failure for row in self.dimensions):
            if self.decision != "REPLAN":
                raise ValueError("blocking Spine failure requires REPLAN")

        if self.decision == "ACCEPT":
            scores = {row.name: row.score for row in self.dimensions}
            minimums = {
                "AGE_MATURITY": 4,
                "CAUSAL_COHERENCE": 4,
                "ESCALATION": 4,
                "AGENCY": 4,
                "REVERSAL_QUALITY": 3,
                "CLIMAX_PAYOFF": 4,
                "WORLD_IMMERSION": 4,
                "SAGA_ALIGNMENT": 4,
                "LOCAL_SATISFACTION": 4,
                "WRITER_EXECUTABILITY": 4,
                "REPETITION_SAFETY": 3,
            }
            failures = [
                f"{name}:{scores[name]}<{minimum}"
                for name, minimum in minimums.items()
                if scores[name] < minimum
            ]
            if failures:
                raise ValueError(
                    "ACCEPT Episode Spine misses protected thresholds: "
                    + ", ".join(failures)
                )
        return self
