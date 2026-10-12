"""Atomic movement of a declared carry group; legacy spatial schemas remain frozen."""
from typing import Literal
from pydantic import Field, model_validator
from src.spineforge_relay_v1_contracts import StrictModel, canonical_sha256, ValidationFinding
from src.spineforge_relay_v1_spatial import SpatialTopologyV1, SpatialStateV1, SpatialOperationV1, replay_spatial
from src.spineforge_relay_v1_compile import _value_at


class CarryGroupV1(StrictModel):
    id: str = Field(min_length=1)
    carriers: list[str] = Field(min_length=2)
    carried_object: str = Field(min_length=1)
    carried_by_state_pointer: str

    @model_validator(mode="after")
    def binding(self):
        if len(set(self.carriers)) != len(self.carriers) or self.carried_object in self.carriers:
            raise ValueError("Carry group requires distinct carriers and object")
        escaped = self.carried_object.replace("~", "~0").replace("/", "~1")
        if self.carried_by_state_pointer != "/objects/" + escaped + "/state/carried_by":
            raise ValueError("Carry group must bind the object's canonical carried_by field")
        return self


class JointMoveV1(StrictModel):
    id: str = Field(min_length=1)
    kind: Literal["JOINT_MOVE"]
    subject: str = Field(min_length=1)
    target: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    predicate_id: str = Field(min_length=1)
    edge_id: str = Field(min_length=1)


class JointSpatialContractV1(StrictModel):
    schema_name: Literal["spineforge-relay.joint-spatial-contract.v1"] = "spineforge-relay.joint-spatial-contract.v1"
    scene_contract_sha256: str
    story_state_sha256: str
    topology: SpatialTopologyV1
    carry_groups: list[CarryGroupV1]
    entry: SpatialStateV1
    operations: list[JointMoveV1 | SpatialOperationV1]
    exit: SpatialStateV1


def replay_joint(*, topology, entry, groups, operations, story_state):
    if any(g.id in entry.positions for g in groups):
        raise ValueError("Group identity cannot alias a tracked entity")
    if len({g.id for g in groups}) != len(groups):
        raise ValueError("Duplicate carry group")
    if len({o.id for o in operations}) != len(operations):
        raise ValueError("Duplicate spatial operation")
    # Base replay validates topology hash, locations and initial constraints.
    current = replay_spatial(topology, entry, [])
    active = {}
    payload = story_state.model_dump(mode="json")
    for group in groups:
        members = group.carriers + [group.carried_object]
        if any(m not in topology.position_state_paths or m not in current.positions for m in members):
            raise ValueError("Carry group members require tracked canonical positions")
        for carrier in group.carriers:
            if carrier not in story_state.characters or topology.position_state_paths[carrier] != "/characters/" + carrier.replace("~", "~0").replace("/", "~1") + "/location":
                raise ValueError("Carrier must be a canonically tracked character")
        object_path = "/objects/" + group.carried_object.replace("~", "~0").replace("/", "~1") + "/location"
        if topology.position_state_paths[group.carried_object] != object_path or group.carried_object not in story_state.objects:
            raise ValueError("Carried object must bind its canonical location")
        exists, carriers = _value_at(payload, group.carried_by_state_pointer)
        if not exists or not isinstance(carriers, list) or any(not isinstance(c,str) for c in carriers) or len(set(carriers)) != len(carriers):
            raise ValueError("Missing or invalid canonical carry state")
        if carriers:
            if set(carriers) != set(group.carriers):
                raise ValueError("Carry group does not match established hold")
            if any(set(members) & set(other.carriers + [other.carried_object]) for other in active.values()):
                raise ValueError("Overlapping active carry groups")
            if len({current.positions[m] for m in members}) != 1:
                raise ValueError("Established carry group must be co-located")
            active[group.id] = group
    for name, obj in story_state.objects.items():
        carriers = obj.state.get("carried_by", [])
        if isinstance(carriers,list) and len(carriers)>=2 and not any(g.carried_object==name for g in active.values()):
            raise ValueError("Established shared carry requires a declared group")
    edges = {e.id: e for e in topology.edges}
    for op in operations:
        if isinstance(op, JointMoveV1):
            group = active.get(op.subject)
            edge = edges.get(op.edge_id)
            if group is None or edge is None:
                raise ValueError("Joint move requires established hold and declared edge")
            members = group.carriers + [group.carried_object]
            origins = {current.positions[m] for m in members}
            if len(origins) != 1:
                raise ValueError("Joint move members must be co-located")
            origin = next(iter(origins))
            if (origin, op.target) != (edge.source, edge.destination) and not (edge.bidirectional and (origin, op.target) == (edge.destination, edge.source)):
                raise ValueError("Joint move violates topology")
            if not set(members).issubset(edge.allowed_entities):
                raise ValueError("Passage must permit every carrier and the object")
            if any(c.active and c.subject in members and c.target in {edge.id, op.target} for c in current.access_constraints):
                raise ValueError("Joint move bypasses a member's active constraint")
            # All checks precede the single complete group update.
            current.positions.update({m: op.target for m in members})
        else:
            if op.kind == "MOVE" and any(op.subject in g.carriers + [g.carried_object] for g in active.values()):
                raise ValueError("Individual movement cannot split an active carry group")
            current = replay_spatial(topology, current, [op])
    return current


def compile_joint_spatial(*, scene, state, topology, groups, operations, expected_exit):
    if scene.story_state_sha256 != canonical_sha256(state):
        raise ValueError("Stale scene/state binding")
    entry = SpatialStateV1.model_validate(state.world["spatial"])
    payload = state.model_dump(mode="json")
    for entity, pointer in topology.position_state_paths.items():
        exists, location = _value_at(payload, pointer)
        if not exists or entry.positions.get(entity) != location:
            raise ValueError("Spatial entry conflicts with canonical location")
    predicates = {(e.id,p.id):p for e in scene.required_events for p in e.predicates}
    used = set()
    for op in operations:
        key = (op.event_id,op.predicate_id)
        p = predicates.get(key)
        if key in used or p is None or (p.subject,p.action,p.target) != (op.subject,op.kind,op.target):
            raise ValueError("Spatial operation requires one exactly attributed predicate")
        used.add(key)
    exit_state = replay_joint(topology=topology,entry=entry,groups=groups,operations=operations,story_state=state)
    for entity, pointer in topology.position_state_paths.items():
        exists, location = _value_at(payload,pointer)
        for changed, value in scene.required_exit_state.items():
            if pointer == changed:
                exists,location = True,value
            elif pointer.startswith(changed+"/"):
                exists,location = _value_at(value,pointer[len(changed):])
        if not exists or exit_state.positions.get(entity) != location:
            raise ValueError("Joint spatial exit conflicts with canonical location")
    if exit_state != expected_exit or scene.required_exit_state.get("/world/spatial") != exit_state.model_dump(mode="json"):
        raise ValueError("Joint exit must match replay and scene exit")
    return JointSpatialContractV1(scene_contract_sha256=canonical_sha256(scene),story_state_sha256=canonical_sha256(state),topology=topology,carry_groups=groups,entry=entry,operations=operations,exit=exit_state)


def evaluate_joint_spatial(*, contract, scene, state, prose, evidence):
    findings = []
    def block(message):
        findings.append(ValidationFinding(code="JOINT_SPATIAL",family="spatial",severity="BLOCKING",message=message))
    try:
        rebound = compile_joint_spatial(scene=scene,state=state,topology=contract.topology,groups=contract.carry_groups,operations=contract.operations,expected_exit=contract.exit)
        if rebound != contract:
            raise ValueError("Joint spatial fingerprint drift")
    except (ValueError,KeyError,TypeError) as exc:
        block(str(exc)); return findings
    previous_end = 0
    for op in contract.operations:
        rows = [r for r in evidence if (r.event_id,r.predicate_id)==(op.event_id,op.predicate_id)]
        if len(rows)!=1:
            block("Missing or duplicate spatial evidence"); continue
        row = rows[0]
        if row.verdict!="SUPPORTED" or row.provenance!="DIRECT_OBSERVATION" or row.state_pointer is not None or (row.subject,row.action,row.target)!=(op.subject,op.kind,op.target):
            block("Unsupported or misattributed direct movement evidence")
        quote = row.exact_text
        if not quote.strip() or prose.count(quote)!=1:
            block("Movement requires one unique anchor"); continue
        start = prose.index(quote)
        if start < previous_end:
            block("Movement order is not grounded")
        previous_end = start+len(quote)
    return findings
