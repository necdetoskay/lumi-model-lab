from copy import deepcopy
import pytest
from src.spineforge_relay_v1_contracts import canonical_sha256
from src.spineforge_relay_v1_spatial import (
    SpatialTopologyV1, SpatialStateV1, SpatialOperationV1, replay_spatial,
)


def setup_space():
    topology = SpatialTopologyV1(locations=["shore", "upper", "lower"], edges=[
        dict(id="door", source="shore", destination="upper", passage="doorway", bidirectional=True,
             allowed_entities=["child", "friend"]),
        dict(id="stair", source="upper", destination="lower", passage="narrow_stair", bidirectional=True,
             allowed_entities=["child", "friend", "small_animal"]),
    ])
    entry = SpatialStateV1(topology_sha256=canonical_sha256(topology),
        positions={"child": "upper", "friend": "upper", "mother": "upper", "small_animal": "upper"},
        access_constraints=[dict(id="nest_guard", blocker="mother", subject="child", target="compass", active=True)])
    return topology, entry


def op(kind, subject="child", target="compass", **kw):
    return SpatialOperationV1(id=kind, kind=kind, subject=subject, target=target,
                             event_id="event", predicate_id=kind, **kw)


def test_blocker_survives_scene_boundary_and_requires_transition():
    topology, entry = setup_space()
    first_exit = replay_spatial(topology, entry, [])
    with pytest.raises(ValueError, match="Access precedes"):
        replay_spatial(topology, first_exit, [op("ACCESS")])
    after = replay_spatial(topology, first_exit, [
        op("RELEASE", subject="mother", constraint_id="nest_guard"), op("ACCESS")])
    assert not after.access_constraints[0].active
    assert entry.access_constraints[0].active


def test_release_after_access_is_rejected():
    topology, entry = setup_space()
    with pytest.raises(ValueError, match="Access precedes"):
        replay_spatial(topology, entry, [op("ACCESS"), op("RELEASE", subject="mother", constraint_id="nest_guard")])


def test_same_door_connects_entry_and_exit():
    topology, entry = setup_space()
    shore = replay_spatial(topology, entry, [op("MOVE", target="shore", edge_id="door")])
    upper = replay_spatial(topology, shore, [op("MOVE", target="upper", edge_id="door")])
    assert upper.positions == entry.positions


@pytest.mark.parametrize("edge,target", [("stair", "shore"), ("invented", "shore"), ("door", "lower")])
def test_wrong_edge_or_invented_route_rejected(edge, target):
    topology, entry = setup_space()
    with pytest.raises(ValueError):
        replay_spatial(topology, entry, [op("MOVE", target=target, edge_id=edge)])


def test_broad_entity_cannot_fit_passage():
    topology, entry = setup_space()
    with pytest.raises(ValueError, match="passage"):
        replay_spatial(topology, entry, [op("MOVE", subject="mother", target="lower", edge_id="stair")])


def test_other_entity_cannot_release_mother_constraint():
    topology, entry = setup_space()
    with pytest.raises(ValueError, match="bound blocker"):
        replay_spatial(topology, entry, [op("RELEASE", subject="friend", constraint_id="nest_guard")])


def test_repeated_release_and_remote_release_rejected():
    topology, entry = setup_space()
    released = replay_spatial(topology, entry, [op("RELEASE", subject="mother", constraint_id="nest_guard")])
    with pytest.raises(ValueError, match="change state"):
        replay_spatial(topology, released, [op("RELEASE", subject="mother", constraint_id="nest_guard")])
    remote = entry.model_copy(deep=True)
    remote.positions["mother"] = "lower"
    with pytest.raises(ValueError, match="co-location"):
        replay_spatial(topology, remote, [op("RELEASE", subject="mother", constraint_id="nest_guard")])


def test_changed_topology_rejected():
    topology, entry = setup_space()
    altered = topology.model_copy(deep=True)
    altered.edges[0].destination = "lower"
    with pytest.raises(ValueError, match="fingerprint"):
        replay_spatial(altered, entry, [])


def test_blocked_destination_cannot_be_traversed():
    topology, entry = setup_space()
    entry.access_constraints[0].target = "door"
    with pytest.raises(ValueError, match="bypasses"):
        replay_spatial(topology, entry, [op("MOVE", target="shore", edge_id="door")])


def test_graph_duplicate_or_unknown_endpoint_rejected():
    topology, _ = setup_space()
    raw = topology.model_dump(mode="json")
    raw["edges"].append(deepcopy(raw["edges"][0]))
    with pytest.raises(ValueError, match="Duplicate edges"):
        SpatialTopologyV1.model_validate(raw)
    raw["edges"].pop()
    raw["edges"][0]["destination"] = "secret_room"
    with pytest.raises(ValueError, match="endpoints"):
        SpatialTopologyV1.model_validate(raw)
