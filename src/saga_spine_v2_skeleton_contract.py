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
from src.saga_spine_v2_contract import (
    BackgroundEnrichmentPolicy,
    CreativePermissionEnvelope,
    HiddenTruth,
    SideSagaSeed,
)

SCHEMA_ID = "character-saga-skeleton.v2"
KEY_PATTERN = r"^[a-z][a-z0-9_]*$"
SCRIPTED_SEQUENCE_PATTERN = re.compile(
    r"\b(?:episode|story|chapter|b[oö]l[uü]m)\s*\d+\b",
    re.IGNORECASE,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SagaAnchorSkeleton(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    title: str
    purpose: str
    target_state: str
    required_for_resolution: bool
    milestone_target_count: int = Field(ge=2, le=6)
    desired_progression_modes: list[
        Literal[
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
    ]


class SagaAnchorEdge(StrictModel):
    from_anchor: str = Field(pattern=KEY_PATTERN)
    to_anchor: str = Field(pattern=KEY_PATTERN)
    relationship: Literal[
        "REQUIRES",
        "MAY_ENABLE",
        "ALTERNATIVE_ROUTE",
        "MAY_CONVERGE",
    ]
    rationale: str


class RevealIntent(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    truth_key: str = Field(pattern=KEY_PATTERN)
    level: Literal["FORESHADOW", "PARTIAL", "CONFIRMED"]
    summary: str
    eligibility: Conditions
    anchor_keys: list[str]
    reveal_ceiling: str


class MainSagaSkeleton(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    title: str
    goal: str
    stakes: str
    central_mystery: str
    themes: list[str]
    entry_anchor_keys: list[str]
    resolution_anchor_key: str = Field(pattern=KEY_PATTERN)
    anchors: list[SagaAnchorSkeleton]
    anchor_edges: list[SagaAnchorEdge]
    hidden_truths: list[HiddenTruth]
    reveal_intents: list[RevealIntent]


class CharacterSagaSkeletonV2(StrictModel):
    schema_id: Literal[SCHEMA_ID] = Field(alias="schema")
    origin: Origin
    present_situation: PresentSituation
    narrative_core: NarrativeCore
    main_saga: MainSagaSkeleton
    latent_side_sagas: list[SideSagaSeed]
    creative_permission_envelope: CreativePermissionEnvelope
    world_integration: WorldIntegration
    reweave_policy: ReweavePolicy
    background_enrichment_policy: BackgroundEnrichmentPolicy
    safety_and_constraints: SafetyAndConstraints

    @model_validator(mode="after")
    def validate_skeleton(self) -> "CharacterSagaSkeletonV2":
        saga = self.main_saga

        if not 5 <= len(saga.anchors) <= 7:
            raise ValueError(
                f"main_saga must contain 5-7 anchors, got {len(saga.anchors)}"
            )

        total_target = sum(x.milestone_target_count for x in saga.anchors)
        if not 15 <= total_target <= 30:
            raise ValueError(
                f"planned milestone total must be 15-30, got {total_target}"
            )

        anchor_keys = [x.key for x in saga.anchors]
        truth_keys = [x.key for x in saga.hidden_truths]
        reveal_keys = [x.key for x in saga.reveal_intents]
        side_keys = [x.key for x in self.latent_side_sagas]

        for label, values in {
            "anchor": anchor_keys,
            "hidden_truth": truth_keys,
            "reveal_intent": reveal_keys,
            "side_saga": side_keys,
        }.items():
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {label} key")

        all_keys = anchor_keys + truth_keys + reveal_keys + side_keys
        if len(all_keys) != len(set(all_keys)):
            raise ValueError("Saga Skeleton v2 keys must be globally unique")

        anchor_set = set(anchor_keys)
        truth_set = set(truth_keys)

        if not saga.entry_anchor_keys:
            raise ValueError("main_saga requires at least one entry anchor")
        unknown_entries = sorted(set(saga.entry_anchor_keys) - anchor_set)
        if unknown_entries:
            raise ValueError(
                "unknown entry anchors: " + ", ".join(unknown_entries)
            )
        if saga.resolution_anchor_key not in anchor_set:
            raise ValueError("resolution_anchor_key must reference an anchor")

        if not saga.anchor_edges:
            raise ValueError("main_saga requires anchor graph edges")

        adjacency: dict[str, set[str]] = {key: set() for key in anchor_set}
        has_alternative_route = False
        for edge in saga.anchor_edges:
            if edge.from_anchor not in anchor_set or edge.to_anchor not in anchor_set:
                raise ValueError(
                    f"anchor edge references unknown anchor: "
                    f"{edge.from_anchor}->{edge.to_anchor}"
                )
            if edge.from_anchor == edge.to_anchor:
                raise ValueError("anchor edge cannot self-reference")
            adjacency[edge.from_anchor].add(edge.to_anchor)
            if edge.relationship == "ALTERNATIVE_ROUTE":
                has_alternative_route = True

        if not has_alternative_route:
            raise ValueError("main_saga requires at least one ALTERNATIVE_ROUTE anchor edge")

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                raise ValueError("Saga anchor graph must be acyclic")
            if node in visited:
                return
            visiting.add(node)
            for nxt in adjacency[node]:
                visit(nxt)
            visiting.remove(node)
            visited.add(node)

        for node in anchor_set:
            visit(node)

        reachable: set[str] = set()
        stack = list(saga.entry_anchor_keys)
        while stack:
            node = stack.pop()
            if node in reachable:
                continue
            reachable.add(node)
            stack.extend(adjacency[node] - reachable)

        unreachable = sorted(anchor_set - reachable)
        if unreachable:
            raise ValueError(
                "Saga anchor graph contains unreachable anchors: "
                + ", ".join(unreachable)
            )
        if saga.resolution_anchor_key not in reachable:
            raise ValueError("resolution anchor must be reachable")

        required_anchors = {
            x.key for x in saga.anchors if x.required_for_resolution
        }
        if saga.resolution_anchor_key not in required_anchors:
            raise ValueError("resolution anchor must be required_for_resolution")

        fixed_truths = {
            x.key for x in saga.hidden_truths if x.mode == "FIXED_HIDDEN"
        }
        for reveal in saga.reveal_intents:
            if reveal.truth_key not in truth_set:
                raise ValueError(
                    f"{reveal.key}: unknown truth_key {reveal.truth_key}"
                )
            unknown = sorted(set(reveal.anchor_keys) - anchor_set)
            if unknown:
                raise ValueError(
                    f"{reveal.key}: unknown anchor refs: {', '.join(unknown)}"
                )
            if reveal.level == "CONFIRMED" and reveal.truth_key not in fixed_truths:
                raise ValueError(
                    f"{reveal.key}: CONFIRMED cannot pre-resolve an unresolved-by-design truth"
                )

        if not self.latent_side_sagas:
            raise ValueError("at least one latent side-Saga seed is required")

        narrative_texts = [
            saga.title,
            saga.goal,
            saga.stakes,
            saga.central_mystery,
            *[x.title for x in saga.anchors],
            *[x.purpose for x in saga.anchors],
            *[x.premise for x in self.latent_side_sagas],
        ]
        if any(SCRIPTED_SEQUENCE_PATTERN.search(text) for text in narrative_texts):
            raise ValueError(
                "Saga Skeleton must not encode numbered Episode/Story/Chapter sequence"
            )

        return self
