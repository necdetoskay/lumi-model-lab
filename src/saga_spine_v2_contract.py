from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.saga_blueprint_contract import (
    Conditions,
    NarrativeCore,
    Origin,
    PresentSituation,
    ReweavePolicy,
    SafetyAndConstraints,
    WorldIntegration,
)


SCHEMA_ID = "character-saga-spine.v2"
KEY_PATTERN = r"^[a-z][a-z0-9_]*$"
SCRIPTED_SEQUENCE_PATTERN = re.compile(
    r"\b(?:episode|story|chapter|b[oö]l[uü]m)\s*\d+\b",
    re.IGNORECASE,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SagaAnchor(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    title: str
    purpose: str
    target_state: str
    milestone_keys: list[str]
    required_for_resolution: bool


class SagaMilestone(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    anchor_key: str = Field(pattern=KEY_PATTERN)
    type: Literal[
        "DISCOVERY",
        "REVELATION",
        "DECISION",
        "RELATIONSHIP_SHIFT",
        "CONSEQUENCE",
        "CONVERGENCE",
        "TRANSFORMATION",
        "ACCESS",
        "EVIDENCE",
    ]
    summary: str
    state_condition: str
    required_for_anchor: bool
    possible_entry_vectors: list[
        Literal[
            "RUMOR",
            "NPC",
            "LOCATION",
            "ITEM",
            "DOCUMENT",
            "SYMBOL",
            "WORLD_EVENT",
            "CONSEQUENCE",
            "RELATIONSHIP",
            "EXPLORATION",
        ]
    ]
    reveal_keys: list[str]
    consequence_options: list[str]
    skippable_if_alternate_route_satisfies_anchor: bool


class SagaEdge(StrictModel):
    from_node: str = Field(pattern=KEY_PATTERN)
    to_node: str = Field(pattern=KEY_PATTERN)
    relationship: Literal[
        "REQUIRES",
        "MAY_ENABLE",
        "ALTERNATIVE_ROUTE",
        "MAY_CONVERGE",
    ]
    rationale: str


class HiddenTruth(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    mode: Literal["FIXED_HIDDEN", "UNRESOLVED_BY_DESIGN"]
    question: str
    hidden_statement: str | None = None
    character_knows_question_exists: bool

    @model_validator(mode="after")
    def validate_mode(self) -> "HiddenTruth":
        if self.mode == "FIXED_HIDDEN" and not (self.hidden_statement or "").strip():
            raise ValueError(f"{self.key}: FIXED_HIDDEN requires hidden_statement")
        if self.mode == "UNRESOLVED_BY_DESIGN" and self.hidden_statement is not None:
            raise ValueError(
                f"{self.key}: UNRESOLVED_BY_DESIGN cannot predefine hidden_statement"
            )
        return self


class RevealStep(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    truth_key: str = Field(pattern=KEY_PATTERN)
    level: Literal["FORESHADOW", "PARTIAL", "CONFIRMED"]
    summary: str
    eligibility: Conditions
    milestone_keys: list[str]
    reveal_ceiling: str


class SideSagaSeed(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    arc_type: Literal[
        "SIDE",
        "WORLD",
        "RELATIONSHIP",
        "PERSONAL",
        "EMERGENT",
    ]
    premise: str
    why_it_matters: str
    activation: Conditions
    initial_visibility: Literal["HIDDEN", "FORESHADOW_ONLY", "DISCOVERABLE"]
    must_not_force_followup: Literal[True]
    remains_proposed_until_activated: Literal[True]


class CreativePermissionEnvelope(StrictModel):
    allowed_entity_types: list[
        Literal[
            "NPC",
            "LOCATION",
            "ITEM",
            "RUMOR",
            "DOCUMENT",
            "EVENT",
            "FACTION",
            "WORLD_PHENOMENON",
            "TRANSIENT_SCENE_DETAIL",
        ]
    ]
    allowed_scopes: list[Literal["LOCAL", "REGIONAL", "WORLD", "CROSS_WORLD"]]
    creation_constraints: list[str]
    forbidden_creations: list[str]
    durable_creation_requires_outcome_commit: Literal[True]


class BackgroundEnrichmentPolicy(StrictModel):
    may_propose_latent_quests: Literal[True]
    may_propose_saga_links: Literal[True]
    may_propose_world_events: Literal[True]
    may_propose_npc_arcs: Literal[True]
    may_mutate_user_dependent_canon_while_absent: Literal[False]
    outputs_remain_proposed_or_latent: Literal[True]


class MainSaga(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    title: str
    goal: str
    stakes: str
    central_mystery: str
    themes: list[str]
    entry_anchor_keys: list[str]
    resolution_anchor_key: str = Field(pattern=KEY_PATTERN)
    anchors: list[SagaAnchor]
    milestones: list[SagaMilestone]
    edges: list[SagaEdge]
    hidden_truths: list[HiddenTruth]
    reveal_steps: list[RevealStep]


class CharacterSagaSpineV2(StrictModel):
    schema_id: Literal[SCHEMA_ID] = Field(alias="schema")
    origin: Origin
    present_situation: PresentSituation
    narrative_core: NarrativeCore
    main_saga: MainSaga
    latent_side_sagas: list[SideSagaSeed]
    creative_permission_envelope: CreativePermissionEnvelope
    world_integration: WorldIntegration
    reweave_policy: ReweavePolicy
    background_enrichment_policy: BackgroundEnrichmentPolicy
    safety_and_constraints: SafetyAndConstraints

    @model_validator(mode="after")
    def validate_graph(self) -> "CharacterSagaSpineV2":
        saga = self.main_saga

        if not 5 <= len(saga.anchors) <= 7:
            raise ValueError(
                f"main_saga must contain 5-7 anchors, got {len(saga.anchors)}"
            )
        if not 15 <= len(saga.milestones) <= 30:
            raise ValueError(
                f"main_saga must contain 15-30 milestones, got {len(saga.milestones)}"
            )

        anchor_keys = [item.key for item in saga.anchors]
        milestone_keys = [item.key for item in saga.milestones]
        truth_keys = [item.key for item in saga.hidden_truths]
        reveal_keys = [item.key for item in saga.reveal_steps]
        side_keys = [item.key for item in self.latent_side_sagas]

        for label, values in {
            "anchor": anchor_keys,
            "milestone": milestone_keys,
            "hidden_truth": truth_keys,
            "reveal": reveal_keys,
            "side_saga": side_keys,
        }.items():
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {label} key")

        all_keys = anchor_keys + milestone_keys + truth_keys + reveal_keys + side_keys
        if len(all_keys) != len(set(all_keys)):
            raise ValueError("Saga Spine v2 keys must be globally unique")

        anchor_set = set(anchor_keys)
        milestone_set = set(milestone_keys)
        truth_set = set(truth_keys)
        reveal_set = set(reveal_keys)
        graph_nodes = anchor_set | milestone_set

        if not saga.entry_anchor_keys:
            raise ValueError("main_saga requires at least one entry anchor")
        unknown_entries = sorted(set(saga.entry_anchor_keys) - anchor_set)
        if unknown_entries:
            raise ValueError(
                "unknown entry anchors: " + ", ".join(unknown_entries)
            )
        if saga.resolution_anchor_key not in anchor_set:
            raise ValueError("resolution_anchor_key must reference an anchor")

        milestone_map = {item.key: item for item in saga.milestones}
        for anchor in saga.anchors:
            if len(anchor.milestone_keys) < 2:
                raise ValueError(f"{anchor.key}: anchor requires at least two milestones")
            unknown = sorted(set(anchor.milestone_keys) - milestone_set)
            if unknown:
                raise ValueError(
                    f"{anchor.key}: unknown milestone refs: {', '.join(unknown)}"
                )
            mismatched = [
                key
                for key in anchor.milestone_keys
                if milestone_map[key].anchor_key != anchor.key
            ]
            if mismatched:
                raise ValueError(
                    f"{anchor.key}: milestone anchor mismatch: {', '.join(mismatched)}"
                )

        assigned = [key for anchor in saga.anchors for key in anchor.milestone_keys]
        if sorted(assigned) != sorted(milestone_keys):
            raise ValueError("every main Saga milestone must belong to exactly one anchor")

        for milestone in saga.milestones:
            if milestone.anchor_key not in anchor_set:
                raise ValueError(
                    f"{milestone.key}: unknown anchor_key {milestone.anchor_key}"
                )
            unknown_reveals = sorted(set(milestone.reveal_keys) - reveal_set)
            if unknown_reveals:
                raise ValueError(
                    f"{milestone.key}: unknown reveal refs: {', '.join(unknown_reveals)}"
                )

        if not saga.edges:
            raise ValueError("main_saga requires graph edges")

        adjacency: dict[str, set[str]] = {key: set() for key in graph_nodes}
        has_alternate_route = False
        for edge in saga.edges:
            if edge.from_node not in graph_nodes or edge.to_node not in graph_nodes:
                raise ValueError(
                    f"edge references unknown node: {edge.from_node}->{edge.to_node}"
                )
            if edge.from_node == edge.to_node:
                raise ValueError("Saga graph edge cannot self-reference")
            adjacency[edge.from_node].add(edge.to_node)
            if edge.relationship == "ALTERNATIVE_ROUTE":
                has_alternate_route = True

        if not has_alternate_route:
            raise ValueError("main_saga requires at least one ALTERNATIVE_ROUTE edge")

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                raise ValueError("Saga progression graph must be acyclic")
            if node in visited:
                return
            visiting.add(node)
            for nxt in adjacency[node]:
                visit(nxt)
            visiting.remove(node)
            visited.add(node)

        for node in graph_nodes:
            visit(node)

        reachable: set[str] = set()
        stack = list(saga.entry_anchor_keys)
        while stack:
            node = stack.pop()
            if node in reachable:
                continue
            reachable.add(node)
            stack.extend(adjacency[node] - reachable)

        if saga.resolution_anchor_key not in reachable:
            raise ValueError("resolution anchor must be reachable from an entry anchor")

        required_anchors = {
            item.key for item in saga.anchors if item.required_for_resolution
        }
        unreachable_required = sorted(required_anchors - reachable)
        if unreachable_required:
            raise ValueError(
                "required anchors unreachable: " + ", ".join(unreachable_required)
            )

        for reveal in saga.reveal_steps:
            if reveal.truth_key not in truth_set:
                raise ValueError(
                    f"{reveal.key}: unknown truth_key {reveal.truth_key}"
                )
            unknown = sorted(set(reveal.milestone_keys) - milestone_set)
            if unknown:
                raise ValueError(
                    f"{reveal.key}: unknown milestone refs: {', '.join(unknown)}"
                )

        fixed_truths = {
            item.key for item in saga.hidden_truths if item.mode == "FIXED_HIDDEN"
        }
        for reveal in saga.reveal_steps:
            if reveal.level == "CONFIRMED" and reveal.truth_key not in fixed_truths:
                raise ValueError(
                    f"{reveal.key}: CONFIRMED cannot pre-resolve an unresolved-by-design truth"
                )

        narrative_texts = [
            saga.title,
            saga.goal,
            saga.stakes,
            saga.central_mystery,
            *[item.title for item in saga.anchors],
            *[item.purpose for item in saga.anchors],
            *[item.summary for item in saga.milestones],
            *[item.premise for item in self.latent_side_sagas],
        ]
        scripted = [
            text for text in narrative_texts if SCRIPTED_SEQUENCE_PATTERN.search(text)
        ]
        if scripted:
            raise ValueError(
                "Saga Spine must not encode numbered Episode/Story/Chapter sequence"
            )

        if not self.latent_side_sagas:
            raise ValueError("at least one latent side-Saga seed is required")

        return self
