from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.saga_spine_v2_contract import (
    CharacterSagaSpineV2,
    RevealStep,
    SagaAnchor,
    SagaEdge,
    SagaMilestone,
)
from src.saga_spine_v2_skeleton_contract import CharacterSagaSkeletonV2


SCHEMA_ID = "saga-milestone-expansion.v2"
KEY_PATTERN = r"^[a-z][a-z0-9_]*$"
SCRIPTED_SEQUENCE_PATTERN = re.compile(
    r"\b(?:episode|story|chapter|b[oö]l[uü]m)\s*\d+\b",
    re.IGNORECASE,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnchorMilestoneOrder(StrictModel):
    anchor_key: str = Field(pattern=KEY_PATTERN)
    ordered_milestone_keys: list[str]


class RevealBinding(StrictModel):
    reveal_key: str = Field(pattern=KEY_PATTERN)
    milestone_keys: list[str]


class SagaMilestoneExpansionV2(StrictModel):
    schema_id: Literal[SCHEMA_ID] = Field(alias="schema")
    source_saga_key: str = Field(pattern=KEY_PATTERN)
    milestones: list[SagaMilestone]
    anchor_orders: list[AnchorMilestoneOrder]
    reveal_bindings: list[RevealBinding]
    resolution_milestone_keys: list[str]

    @model_validator(mode="after")
    def validate_internal(self) -> "SagaMilestoneExpansionV2":
        keys = [m.key for m in self.milestones]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate milestone key")

        if not 15 <= len(self.milestones) <= 30:
            raise ValueError(
                f"milestone expansion must contain 15-30 milestones, got {len(self.milestones)}"
            )

        milestone_set = set(keys)
        ordered = [
            key
            for row in self.anchor_orders
            for key in row.ordered_milestone_keys
        ]
        if len(ordered) != len(set(ordered)):
            raise ValueError("milestone order contains duplicate references")
        if set(ordered) != milestone_set:
            raise ValueError("anchor_orders must cover every milestone exactly once")

        if not self.resolution_milestone_keys:
            raise ValueError("resolution_milestone_keys cannot be empty")
        unknown_resolution = sorted(
            set(self.resolution_milestone_keys) - milestone_set
        )
        if unknown_resolution:
            raise ValueError(
                "unknown resolution milestones: " + ", ".join(unknown_resolution)
            )

        narrative = [
            text
            for m in self.milestones
            for text in [m.summary, m.state_condition, *m.consequence_options]
        ]
        if any(SCRIPTED_SEQUENCE_PATTERN.search(text or "") for text in narrative):
            raise ValueError("milestones must not encode numbered Episode/Story/Chapter sequence")

        for m in self.milestones:
            if not m.possible_entry_vectors:
                raise ValueError(f"{m.key}: at least one entry vector is required")
            if not m.consequence_options:
                raise ValueError(f"{m.key}: at least one consequence option is required")

        return self


def merge_expansion_with_skeleton(
    skeleton: CharacterSagaSkeletonV2,
    expansion: SagaMilestoneExpansionV2,
) -> CharacterSagaSpineV2:
    saga = skeleton.main_saga
    if expansion.source_saga_key != saga.key:
        raise ValueError(
            f"source_saga_key mismatch: {expansion.source_saga_key} != {saga.key}"
        )

    anchor_map = {a.key: a for a in saga.anchors}
    milestone_map = {m.key: m for m in expansion.milestones}
    reveal_map = {r.key: r for r in saga.reveal_intents}

    if len(expansion.milestones) != sum(
        a.milestone_target_count for a in saga.anchors
    ):
        raise ValueError("milestone count must equal approved skeleton target total")

    order_map = {row.anchor_key: row.ordered_milestone_keys for row in expansion.anchor_orders}
    if set(order_map) != set(anchor_map):
        raise ValueError("anchor_orders must cover every approved anchor exactly once")

    for anchor_key, anchor in anchor_map.items():
        ordered = order_map[anchor_key]
        if len(ordered) != anchor.milestone_target_count:
            raise ValueError(
                f"{anchor_key}: expected {anchor.milestone_target_count} milestones, got {len(ordered)}"
            )
        for key in ordered:
            if milestone_map[key].anchor_key != anchor_key:
                raise ValueError(
                    f"{key}: milestone anchor mismatch for {anchor_key}"
                )

        present_modes = {milestone_map[key].type for key in ordered}
        missing_modes = sorted(set(anchor.desired_progression_modes) - present_modes)
        if missing_modes:
            raise ValueError(
                f"{anchor_key}: missing desired progression modes: {', '.join(missing_modes)}"
            )

    reveal_bindings = {r.reveal_key: r.milestone_keys for r in expansion.reveal_bindings}
    if set(reveal_bindings) != set(reveal_map):
        raise ValueError("reveal_bindings must cover every approved reveal intent exactly once")

    for reveal_key, milestone_keys in reveal_bindings.items():
        if not milestone_keys:
            raise ValueError(f"{reveal_key}: reveal binding cannot be empty")
        allowed_anchors = set(reveal_map[reveal_key].anchor_keys)
        for milestone_key in milestone_keys:
            if milestone_key not in milestone_map:
                raise ValueError(f"{reveal_key}: unknown milestone {milestone_key}")
            if milestone_map[milestone_key].anchor_key not in allowed_anchors:
                raise ValueError(
                    f"{reveal_key}: milestone {milestone_key} is outside approved reveal anchors"
                )

    resolution_anchor = saga.resolution_anchor_key
    for key in expansion.resolution_milestone_keys:
        if milestone_map[key].anchor_key != resolution_anchor:
            raise ValueError(
                f"{key}: resolution milestone must belong to {resolution_anchor}"
            )

    anchors = [
        SagaAnchor(
            key=a.key,
            title=a.title,
            purpose=a.purpose,
            target_state=a.target_state,
            milestone_keys=order_map[a.key],
            required_for_resolution=a.required_for_resolution,
        )
        for a in saga.anchors
    ]

    edges: list[SagaEdge] = []
    for anchor in saga.anchors:
        ordered = order_map[anchor.key]
        edges.append(
            SagaEdge(
                from_node=anchor.key,
                to_node=ordered[0],
                relationship="REQUIRES",
                rationale="Approved anchor enters its first milestone state.",
            )
        )
        for left, right in zip(ordered, ordered[1:]):
            edges.append(
                SagaEdge(
                    from_node=left,
                    to_node=right,
                    relationship="MAY_ENABLE",
                    rationale="Within-anchor progression may enable the next milestone state without fixing an Episode number.",
                )
            )

    for macro in saga.anchor_edges:
        from_last = order_map[macro.from_anchor][-1]
        edges.append(
            SagaEdge(
                from_node=from_last,
                to_node=macro.to_anchor,
                relationship=macro.relationship,
                rationale=macro.rationale,
            )
        )

    reveal_steps = [
        RevealStep(
            key=r.key,
            truth_key=r.truth_key,
            level=r.level,
            summary=r.summary,
            eligibility=r.eligibility,
            milestone_keys=reveal_bindings[r.key],
            reveal_ceiling=r.reveal_ceiling,
        )
        for r in saga.reveal_intents
    ]

    milestone_reveal_refs: dict[str, list[str]] = {key: [] for key in milestone_map}
    for reveal_key, keys in reveal_bindings.items():
        for key in keys:
            milestone_reveal_refs[key].append(reveal_key)

    milestones = []
    for row in expansion.milestones:
        data = row.model_dump(mode="json")
        data["reveal_keys"] = sorted(milestone_reveal_refs[row.key])
        milestones.append(SagaMilestone.model_validate(data))

    return CharacterSagaSpineV2.model_validate(
        {
            "schema": "character-saga-spine.v2",
            "origin": skeleton.origin.model_dump(mode="json"),
            "present_situation": skeleton.present_situation.model_dump(mode="json"),
            "narrative_core": skeleton.narrative_core.model_dump(mode="json"),
            "main_saga": {
                "key": saga.key,
                "title": saga.title,
                "goal": saga.goal,
                "stakes": saga.stakes,
                "central_mystery": saga.central_mystery,
                "themes": saga.themes,
                "entry_anchor_keys": saga.entry_anchor_keys,
                "resolution_anchor_key": saga.resolution_anchor_key,
                "resolution_milestone_keys": expansion.resolution_milestone_keys,
                "anchors": [a.model_dump(mode="json") for a in anchors],
                "milestones": [m.model_dump(mode="json") for m in milestones],
                "edges": [e.model_dump(mode="json") for e in edges],
                "hidden_truths": [h.model_dump(mode="json") for h in saga.hidden_truths],
                "reveal_steps": [r.model_dump(mode="json") for r in reveal_steps],
            },
            "latent_side_sagas": [
                s.model_dump(mode="json") for s in skeleton.latent_side_sagas
            ],
            "creative_permission_envelope": skeleton.creative_permission_envelope.model_dump(mode="json"),
            "world_integration": skeleton.world_integration.model_dump(mode="json"),
            "reweave_policy": skeleton.reweave_policy.model_dump(mode="json"),
            "background_enrichment_policy": skeleton.background_enrichment_policy.model_dump(mode="json"),
            "safety_and_constraints": skeleton.safety_and_constraints.model_dump(mode="json"),
        }
    )
