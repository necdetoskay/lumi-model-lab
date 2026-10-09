"""Versioned planner boundary: event goal refs and typed spatial declarations.

No synonym inference: physical predicates come only from explicitly declared steps.
The frozen v1 compiler/admission checks still validate the expanded proposal.
"""
from typing import Literal
from pathlib import Path
from pydantic import Field
from src.spineforge_relay_v1_contracts import StrictModel, EventPredicateV1, canonical_sha256
from src.spineforge_production_compact import (CompactSceneV1, CompactStoryPlanV1,
    PredicateRef, GoalRefs, OrderRef, compile_compact)
from src.spineforge_relay_v1_spatial import SpatialOperationV1
from src.spineforge_joint_spatial import JointMoveV1


class GoalEventsV2(StrictModel):
    narrative_purpose: list[str] = Field(min_length=1)
    objective: list[str] = Field(min_length=1)
    turn: list[str] = Field(min_length=1)


class EventAnchorV2(StrictModel):
    event_id: str = Field(min_length=1)
    predicate_id: str | None = None


class EventOrderV2(StrictModel):
    before: EventAnchorV2
    after: EventAnchorV2


class SpatialStepV2(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    kind: Literal["LOCATE", "MOVE", "BLOCK", "RELEASE", "ACCESS", "JOINT_MOVE"]
    subject: str = Field(min_length=1)
    target: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    edge_id: str | None = None
    constraint_id: str | None = None


class CompactSceneV2(CompactSceneV1):
    goal_bindings: GoalEventsV2
    ordered_dependencies: list[EventOrderV2] = Field(default_factory=list)
    spatial_operations: list[SpatialStepV2] = Field(default_factory=list)


class CompactStoryPlanV2(CompactStoryPlanV1):
    schema_name: Literal["spineforge.compact-story-plan.v2"] = "spineforge.compact-story-plan.v2"
    scenes: list[CompactSceneV2] = Field(min_length=2, max_length=12)


def compact_planner_input_v2(request, seed):
    return dict(schema="spineforge.compact-planner-input.v2",
        request=request.model_dump(mode="json"), seed=seed.model_dump(mode="json"),
        request_sha256=canonical_sha256(request), seed_sha256=canonical_sha256(seed),
        instructions=Path("prompts/spineforge_production_compact_v2.md").read_text(encoding="utf8"),
        output_schema=CompactStoryPlanV2.model_json_schema())


def compile_compact_v2(request, seed, candidate: CompactStoryPlanV2):
    raw = candidate.model_dump(mode="json")
    raw["schema_name"] = "spineforge.compact-story-plan.v1"
    for scene, expanded in zip(candidate.scenes, raw["scenes"]):
        events = {e.id: e.model_copy(deep=True) for e in scene.events}
        if len(events) != len(scene.events):
            raise ValueError("Duplicate event identifier")
        # The planner declares movement; code derives its exact evidence triple.
        operations = []
        for step in scene.spatial_operations:
            known = {g.id for g in candidate.carry_groups} if step.kind == "JOINT_MOVE" else set(seed.topology.position_state_paths)
            if step.subject not in known:
                raise ValueError("Spatial step subject must be an established tracked entity or declared group")
            event = events.get(step.event_id)
            if event is None or event.evidence_mode == "ESTABLISHED_KNOWLEDGE":
                raise ValueError("Spatial step needs an existing event permitting direct evidence")
            matches = [p for p in event.predicates if (p.subject,p.action,p.target) == (step.subject,step.kind,step.target)]
            if len(matches) > 1:
                raise ValueError("Ambiguous existing spatial predicate")
            if matches:
                pid = matches[0].id
            else:
                pid = "SP_" + step.id
                if any(p.id == pid for p in event.predicates):
                    raise ValueError("Derived spatial predicate ID collision")
                event.predicates.append(EventPredicateV1(id=pid, subject=step.subject, action=step.kind, target=step.target))
            op = {**step.model_dump(mode="json"), "predicate_id":pid}
            if step.kind == "JOINT_MOVE":
                if step.constraint_id is not None or step.edge_id is None:
                    raise ValueError("Joint movement requires an edge and no constraint field")
                op.pop("constraint_id")
                operations.append(JointMoveV1.model_validate(op))
            else:
                operations.append(SpatialOperationV1.model_validate(op))
        def anchor(value):
            event = events.get(value.event_id)
            if event is None:
                raise ValueError("Unknown ordered event")
            return PredicateRef(event_id=value.event_id, predicate_id=value.predicate_id or event.predicates[0].id)
        goals = {}
        covered = set()
        for field in ("narrative_purpose", "objective", "turn"):
            selected = getattr(scene.goal_bindings,field)
            if len(set(selected)) != len(selected) or any(e not in events for e in selected):
                raise ValueError("Duplicate or unknown goal event")
            covered.update(selected)
            # Selecting an event explicitly includes its complete predicate spec.
            goals[field] = [PredicateRef(event_id=eid,predicate_id=p.id) for eid in selected for p in events[eid].predicates]
        if covered != set(events):
            raise ValueError("Every required event needs an explicit goal binding")
        expanded["events"] = [e.model_dump(mode="json") for e in events.values()]
        expanded["goal_bindings"] = GoalRefs(**goals).model_dump(mode="json")
        expanded["ordered_dependencies"] = [OrderRef(before=anchor(o.before),after=anchor(o.after)).model_dump(mode="json") for o in scene.ordered_dependencies]
        expanded["spatial_operations"] = [o.model_dump(mode="json") for o in operations]
    return compile_compact(request,seed,CompactStoryPlanV1.model_validate(raw))
