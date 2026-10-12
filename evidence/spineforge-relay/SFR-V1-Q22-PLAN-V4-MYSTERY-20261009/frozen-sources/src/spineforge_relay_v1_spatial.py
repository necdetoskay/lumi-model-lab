"""Versioned spatial sidecar; historical scene/state serialization is unchanged.

Planning supplies topology and ordered operations. A semantic guard supplies exact
predicate anchors; local checks enforce graph connectivity, persistent blocking,
operation order and state bindings. Quote presence alone is never semantic proof.
"""
from __future__ import annotations

from typing import Literal
from pydantic import Field, model_validator
from src.spineforge_relay_v1_contracts import (
    StrictModel, SceneContractV1, StoryStateV1, ValidationFinding, canonical_sha256,
)
from src.spineforge_relay_v1_events import PredicateEvidenceV1
from src.spineforge_relay_v1_compile import _value_at


class SpatialEdgeV1(StrictModel):
    id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    passage: str = Field(min_length=1)
    bidirectional: bool = False
    allowed_entities: list[str] = Field(min_length=1)


class SpatialTopologyV1(StrictModel):
    schema_name: Literal["spineforge-relay.spatial-topology.v1"] = "spineforge-relay.spatial-topology.v1"
    locations: list[str] = Field(min_length=1)
    edges: list[SpatialEdgeV1]
    position_state_paths: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_graph(self):
        if len(set(self.locations)) != len(self.locations):
            raise ValueError("Duplicate locations")
        if len({e.id for e in self.edges}) != len(self.edges):
            raise ValueError("Duplicate edges")
        for edge in self.edges:
            if edge.source not in self.locations or edge.destination not in self.locations or edge.source == edge.destination:
                raise ValueError("Edge endpoints must be distinct declared locations")
            if len(set(edge.allowed_entities)) != len(edge.allowed_entities):
                raise ValueError("Duplicate allowed entities")
        for pointer in self.position_state_paths.values():
            if not pointer.startswith("/"):
                raise ValueError("Position binding must be an absolute state pointer")
        return self


class AccessConstraintV1(StrictModel):
    id: str = Field(min_length=1)
    blocker: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    target: str = Field(min_length=1)
    active: bool


class SpatialStateV1(StrictModel):
    topology_sha256: str
    positions: dict[str, str]
    access_constraints: list[AccessConstraintV1] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_constraints(self):
        if len({c.id for c in self.access_constraints}) != len(self.access_constraints):
            raise ValueError("Duplicate access constraints")
        return self


class SpatialOperationV1(StrictModel):
    id: str = Field(min_length=1)
    kind: Literal["LOCATE", "MOVE", "BLOCK", "RELEASE", "ACCESS"]
    subject: str = Field(min_length=1)
    target: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    predicate_id: str = Field(min_length=1)
    edge_id: str | None = None
    constraint_id: str | None = None


class SpatialContractV1(StrictModel):
    schema_name: Literal["spineforge-relay.spatial-contract.v1"] = "spineforge-relay.spatial-contract.v1"
    scene_contract_sha256: str
    story_state_sha256: str
    topology: SpatialTopologyV1
    entry: SpatialStateV1
    operations: list[SpatialOperationV1]
    exit: SpatialStateV1


def replay_spatial(topology: SpatialTopologyV1, entry: SpatialStateV1,
                   operations: list[SpatialOperationV1]) -> SpatialStateV1:
    """Fail closed on invented paths and access before an explicit release."""
    if entry.topology_sha256 != canonical_sha256(topology):
        raise ValueError("Spatial topology fingerprint mismatch")
    state = entry.model_copy(deep=True)
    if any(p not in topology.locations for p in state.positions.values()):
        raise ValueError("Undeclared entity location")
    if len({op.id for op in operations}) != len(operations):
        raise ValueError("Duplicate spatial operations")
    constraints = {c.id: c for c in state.access_constraints}
    edges = {e.id: e for e in topology.edges}
    for op in operations:
        if op.kind == "LOCATE":
            if op.subject in state.positions or op.target not in topology.locations or op.edge_id is not None or op.constraint_id is not None:
                raise ValueError("LOCATE can only establish an untracked entity at a declared location")
            state.positions[op.subject] = op.target
            continue
        if op.subject not in state.positions:
            raise ValueError("Unknown spatial subject")
        if op.kind == "MOVE":
            if op.constraint_id is not None or op.edge_id not in edges:
                raise ValueError("MOVE requires one declared edge")
            edge = edges[op.edge_id]
            origin = state.positions[op.subject]
            connected = (origin, op.target) == (edge.source, edge.destination) or (
                edge.bidirectional and (origin, op.target) == (edge.destination, edge.source))
            if not connected or op.subject not in edge.allowed_entities:
                raise ValueError("Movement violates topology or entity passage constraint")
            if any(c.active and c.subject == op.subject and c.target in {op.target, edge.id} for c in constraints.values()):
                raise ValueError("Movement bypasses an active access constraint")
            state.positions[op.subject] = op.target
        elif op.kind in {"BLOCK", "RELEASE"}:
            if op.edge_id is not None or op.constraint_id not in constraints:
                raise ValueError("Posture transition requires a declared constraint")
            constraint = constraints[op.constraint_id]
            if (op.subject, op.target) != (constraint.blocker, constraint.target):
                raise ValueError("Only the bound blocker can change this posture")
            active = op.kind == "BLOCK"
            if constraint.active == active:
                raise ValueError("Posture transition must change state")
            if state.positions.get(constraint.blocker) != state.positions.get(constraint.subject):
                raise ValueError("Posture transition requires co-location")
            constraint.active = active
        else:
            if op.edge_id is not None or op.constraint_id is not None:
                raise ValueError("ACCESS cannot silently mutate a constraint")
            if any(c.active and (c.subject, c.target) == (op.subject, op.target) for c in constraints.values()):
                raise ValueError("Access precedes blocker release")
    return state


def compile_spatial_contract(*, scene: SceneContractV1, state: StoryStateV1,
                             topology: SpatialTopologyV1, operations: list[SpatialOperationV1],
                             expected_exit: SpatialStateV1) -> SpatialContractV1:
    if scene.story_state_sha256 != canonical_sha256(state):
        raise ValueError("Stale scene/state binding")
    entry = SpatialStateV1.model_validate(state.world["spatial"])
    payload = state.model_dump(mode="json")
    for entity, pointer in topology.position_state_paths.items():
        exists, location = _value_at(payload, pointer)
        if exists and entry.positions.get(entity) != location:
            raise ValueError("Spatial entry conflicts with canonical entity location")
    predicates = {(e.id, p.id): p for e in scene.required_events for p in e.predicates}
    used = set()
    for op in operations:
        key = (op.event_id, op.predicate_id)
        if key not in predicates or key in used:
            raise ValueError("Spatial operation requires a unique scene predicate")
        used.add(key)
        predicate = predicates[key]
        if (predicate.subject, predicate.action, predicate.target) != (op.subject, op.kind, op.target):
            raise ValueError("Spatial predicate attribution mismatch")
    exit_state = replay_spatial(topology, entry, operations)
    for entity, pointer in topology.position_state_paths.items():
        exists, location = _value_at(payload, pointer)
        for changed_path, changed_value in scene.required_exit_state.items():
            if pointer == changed_path:
                exists, location = True, changed_value
            elif pointer.startswith(changed_path + "/"):
                exists, location = _value_at(changed_value, pointer[len(changed_path):])
        if exists and exit_state.positions.get(entity) != location:
            raise ValueError("Spatial exit conflicts with canonical entity location")
    if exit_state != expected_exit or scene.required_exit_state.get("/world/spatial") != exit_state.model_dump(mode="json"):
        raise ValueError("Spatial exit must match deterministic replay and frozen scene exit")
    return SpatialContractV1(scene_contract_sha256=canonical_sha256(scene), story_state_sha256=canonical_sha256(state),
                             topology=topology, entry=entry, operations=operations, exit=exit_state)


def evaluate_spatial(*, contract: SpatialContractV1, scene: SceneContractV1, state: StoryStateV1,
                     prose: str, evidence: list[PredicateEvidenceV1]) -> list[ValidationFinding]:
    findings = []
    def block(message):
        findings.append(ValidationFinding(code="SPATIAL_CONTRACT", family="spatial", severity="BLOCKING", message=message))
    try:
        rebound = compile_spatial_contract(scene=scene, state=state, topology=contract.topology,
                                          operations=contract.operations, expected_exit=contract.exit)
        if rebound != contract:
            raise ValueError("Spatial contract fingerprint drift")
    except (ValueError, KeyError) as exc:
        block(str(exc))
        return findings
    previous_end = 0
    for op in contract.operations:
        rows = [r for r in evidence if (r.event_id, r.predicate_id) == (op.event_id, op.predicate_id)]
        if len(rows) != 1:
            block(f"Missing or duplicate spatial evidence: {op.id}")
            continue
        row = rows[0]
        if row.verdict != "SUPPORTED" or row.provenance != "DIRECT_OBSERVATION" or row.state_pointer is not None:
            block(f"Spatial transition requires supported direct observation: {op.id}")
        if (row.subject, row.action, row.target) != (op.subject, op.kind, op.target):
            block(f"Spatial evidence attribution mismatch: {op.id}")
        quote = row.exact_text
        # Repeated/overlapping anchors cannot establish a unique temporal order.
        if not quote.strip() or prose.count(quote) != 1:
            block(f"Spatial anchor must occur exactly once: {op.id}")
            continue
        start = prose.index(quote)
        if start < previous_end:
            block(f"Spatial operation order is not grounded: {op.id}")
        previous_end = start + len(quote)
    return findings
