"""Compact semantic planning -> deterministic v5 fixture. No inference or writes."""
from __future__ import annotations
from typing import Any, Literal
from pathlib import Path
from pydantic import Field
from src.spineforge_relay_v1_contracts import (StrictModel, EventPredicateV1,
    RequiredEventSpecV1, ScenePlanV1, StoryStateV1, FrozenSpineRouteV1, canonical_sha256)
from src.spineforge_relay_v1_compile import compile_scene_contract, _value_at, _tokens
from src.spineforge_relay_v1_q6 import _expected_advance
from src.spineforge_relay_v1_spatial import SpatialOperationV1, SpatialStateV1
from src.spineforge_joint_spatial import CarryGroupV1, JointMoveV1, replay_joint
from src.spineforge_seeded_design import SeededStoryDesignV2
from src.spineforge_story_design import RequestBindingV1
from src.spineforge_relay_v1_coverage import GOAL_FIELDS


class PredicateRef(StrictModel):
    event_id: str = Field(min_length=1)
    predicate_id: str = Field(min_length=1)


class GoalRefs(StrictModel):
    narrative_purpose: list[PredicateRef] = Field(min_length=1)
    objective: list[PredicateRef] = Field(min_length=1)
    turn: list[PredicateRef] = Field(min_length=1)


class OrderRef(StrictModel):
    before: PredicateRef
    after: PredicateRef


class Resolution(StrictModel):
    """A proposed resolution must cite a predicate; semantic review judges entailment."""
    kind: Literal["THREAD", "OBLIGATION"]
    id: str = Field(min_length=1)
    evidence: PredicateRef


class CompactEventV1(StrictModel):
    id: str = Field(min_length=1)
    # First predicate is the principal action; no duplicated actor/action/target.
    predicates: list[EventPredicateV1] = Field(min_length=1)
    required_observer: str | None = None
    evidence_mode: Literal["DIRECT_OBSERVATION", "ESTABLISHED_KNOWLEDGE", "EITHER"] = "DIRECT_OBSERVATION"
    separate_physical_clue_required: bool = False
    forbidden_evidence_subjects: list[str] = Field(default_factory=list)
    resulting_state: dict[str, Any] = Field(default_factory=dict)

    def expand(self):
        p = self.predicates[0]
        allowed = {"DIRECT_OBSERVATION": ["DIRECT_OBSERVATION"],
            "ESTABLISHED_KNOWLEDGE": ["STORY_STATE_KNOWLEDGE"],
            "EITHER": ["DIRECT_OBSERVATION", "STORY_STATE_KNOWLEDGE"]}[self.evidence_mode]
        return RequiredEventSpecV1(**self.model_dump(mode="json"), actor=p.subject,
            action=p.action, target=p.target, allowed_provenance=allowed,
            forbidden_provenance=["INVENTED_WORLD_RULE", "INVENTED_CLUE", "UNESTABLISHED_LORE"])


class CompactSceneV1(StrictModel):
    scene_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    narrative_purpose: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    turn: str = Field(min_length=1)
    location: str | None = None
    events: list[CompactEventV1] = Field(min_length=1)
    goal_bindings: GoalRefs
    ordered_dependencies: list[OrderRef] = Field(default_factory=list)
    spatial_operations: list[JointMoveV1 | SpatialOperationV1] = Field(default_factory=list)
    resolutions: list[Resolution] = Field(default_factory=list)
    preconditions: dict[str, Any] = Field(default_factory=dict)
    entry_requirements: list[str] = Field(default_factory=list)
    exit_requirements: list[str] = Field(default_factory=list)
    immutable_facts: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    emotional_transition: dict[str, str] | None = None
    target_words_min: int = Field(default=120, ge=40, le=2000)
    target_words_max: int = Field(default=260, ge=40, le=3000)


class CompactStoryPlanV1(StrictModel):
    schema_name: Literal["spineforge.compact-story-plan.v1"] = "spineforge.compact-story-plan.v1"
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    seed_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    premise: str = Field(min_length=1)
    character_arc: str = Field(min_length=1)
    resolution: str = Field(min_length=1)
    scenes: list[CompactSceneV1] = Field(min_length=2, max_length=12)
    carry_groups: list[CarryGroupV1] = Field(default_factory=list)
    request_bindings: list[RequestBindingV1] = Field(min_length=1)
    unresolved_questions: list[str] = Field(default_factory=list)


def compact_planner_input(request, seed):
    return dict(schema="spineforge.compact-planner-input.v1",
        request=request.model_dump(mode="json"), seed=seed.model_dump(mode="json"),
        request_sha256=canonical_sha256(request), seed_sha256=canonical_sha256(seed),
        instructions=Path("prompts/spineforge_production_compact.md").read_text(encoding="utf8"),
        output_schema=CompactStoryPlanV1.model_json_schema())


def compile_compact(request, seed, candidate: CompactStoryPlanV1):
    """Project only explicit effects and spatial operations; acceptance remains downstream."""
    if candidate.request_sha256 != canonical_sha256(request) or candidate.seed_sha256 != canonical_sha256(seed):
        raise ValueError("Stale compact request/seed binding")
    if candidate.unresolved_questions or len(candidate.scenes) != request.scene_count:
        raise ValueError("Unresolved questions or requested scene count differs")
    ids = [s.scene_id for s in candidate.scenes]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate scene identifier")
    intent = dict(language=request.language, reader_age=request.reader_age, genre=request.genre,
        tone=request.tone, premise=candidate.premise, character_arc=candidate.character_arc,
        resolution=candidate.resolution,
        resolution_bindings=[dict(scene_id=s.scene_id, **r.model_dump(mode="json")) for s in candidate.scenes for r in s.resolutions])
    spine_hash = canonical_sha256(dict(story_id=seed.story_id, route=ids))
    route = FrozenSpineRouteV1(global_spine_sha256=spine_hash, beat_ids=ids)
    state = StoryStateV1(**seed.initial_state(ids[0]), story_id=seed.story_id,
        global_spine_sha256=spine_hash, story_intent_sha256=canonical_sha256(intent))
    fixture = dict(schema="spineforge-relay.repeatability-fixture.v5", story_id=seed.story_id,
        story_intent=intent, route=ids, initial_state=seed.initial_state(ids[0]),
        relevant_character_canon=seed.relevant_character_canon,
        prop_authorization_policy=seed.prop_authorization_policy,
        topology=seed.topology.model_dump(mode="json"),
        carry_groups=[g.model_dump(mode="json") for g in candidate.carry_groups],
        scene_plans=[], coverage_plans=[], spatial_plans=[])
    resolved = set()
    for index, scene in enumerate(candidate.scenes):
        events = [e.expand() for e in scene.events]
        predicates = {(e.id, p.id): p for e in events for p in e.predicates}
        def ref(r):
            p = predicates.get((r.event_id, r.predicate_id))
            if p is None:
                raise ValueError("Unknown compact predicate reference")
            return dict(event_id=r.event_id, predicate_id=r.predicate_id, subject=p.subject, action=p.action, target=p.target)
        effects = {}
        def merge(path, value):
            if any(path == other or path.startswith(other + "/") or other.startswith(path + "/") for other in effects):
                if path in effects and effects[path] == value:
                    return
                raise ValueError("Conflicting or overlapping event effects")
            effects[path] = value
        for event in events:
            for path, value in event.resulting_state.items():
                tokens = _tokens(path)
                # Metadata, closures and spatial state are compiler-owned. No seed entity creation.
                valid = (len(tokens) >= 3 and tokens[0] == "characters" and tokens[1] in seed.characters and tokens[2] in {"knowledge", "condition", "inventory", "relationships"}
                    or len(tokens) >= 3 and tokens[0] == "objects" and tokens[1] in seed.objects and tokens[2] == "state"
                    or len(tokens) >= 2 and tokens[0] == "world" and tokens[1] not in {"spatial", "rules"})
                if not valid:
                    raise ValueError("Compiler-owned or unauthorized state effect: " + path)
                merge(path, value)
        entry = SpatialStateV1.model_validate(state.world["spatial"])
        spatial_exit = replay_joint(topology=seed.topology, entry=entry, groups=candidate.carry_groups,
            operations=scene.spatial_operations, story_state=state)
        merge("/world/spatial", spatial_exit.model_dump(mode="json"))
        for entity, pointer in seed.topology.position_state_paths.items():
            if spatial_exit.positions[entity] != entry.positions[entity]:
                merge(pointer, spatial_exit.positions[entity])
        before = state.model_dump(mode="json")
        threads = list(state.open_threads)
        finished = list(state.resolved_threads)
        obligations = [o.model_dump(mode="json") for o in state.narrative_obligations]
        for closure in scene.resolutions:
            ref(closure.evidence)
            key = (closure.kind, closure.id)
            if key in resolved:
                raise ValueError("Duplicate resolution")
            resolved.add(key)
            if closure.kind == "THREAD":
                if closure.id not in threads:
                    raise ValueError("Resolution requires an open thread")
                threads.remove(closure.id); finished.append(closure.id)
            else:
                matches = [o for o in obligations if o["id"] == closure.id and o["status"] == "OPEN"]
                if len(matches) != 1:
                    raise ValueError("Resolution requires an open obligation")
                matches[0]["status"] = "SATISFIED"
        if threads != state.open_threads:
            merge("/open_threads", threads); merge("/resolved_threads", finished)
        if obligations != before["narrative_obligations"]:
            merge("/narrative_obligations", obligations)
        preconditions = dict(scene.preconditions)
        for path in preconditions:
            if not path.startswith("/") or not _value_at(before, path)[0]:
                raise ValueError("Unknown precondition path")
        for path in ["/world/spatial", *seed.topology.position_state_paths.values()]:
            exists, value = _value_at(before, path)
            if not exists or path in preconditions and preconditions[path] != value:
                raise ValueError("Stale spatial precondition")
            preconditions[path] = value
        plan = ScenePlanV1(**{k:getattr(scene,k) for k in ["scene_id", *GOAL_FIELDS, "location", "entry_requirements", "exit_requirements", "immutable_facts", "emotional_transition", "target_words_min", "target_words_max"]},
            spine_beats=[scene.scene_id], next_spine_beat=ids[index+1] if index+1<len(ids) else None,
            required_events=events, entry_state=preconditions, required_exit_state=effects,
            allowed_state_paths=list(effects), forbidden=list(dict.fromkeys([*request.forbidden, *scene.forbidden])))
        contract = compile_scene_contract(state, plan, route)
        fixture["scene_plans"].append(plan.model_dump(mode="json"))
        fixture["coverage_plans"].append(dict(scene_id=scene.scene_id,
            obligations=[dict(id=scene.scene_id+"-"+field, source_field=field, source_text=getattr(scene,field), required_predicates=[ref(r) for r in getattr(scene.goal_bindings,field)]) for field in GOAL_FIELDS],
            ordered_dependencies=[dict(before=ref(o.before), after=ref(o.after)) for o in scene.ordered_dependencies]))
        fixture["spatial_plans"].append(dict(scene_id=scene.scene_id, operations=[o.model_dump(mode="json") for o in scene.spatial_operations], expected_exit=spatial_exit.model_dump(mode="json")))
        # Existing coverage/spatial compilers verify exact attribution and ordered movement.
        from src.spineforge_production_story import coverage_for, spatial_for
        coverage_for(fixture, plan, contract); spatial_for(fixture, plan, contract, state)
        state = _expected_advance(state, contract)
    if state.open_threads or any(o.status != "SATISFIED" for o in state.narrative_obligations):
        raise ValueError("Unresolved terminal threads/obligations")
    return SeededStoryDesignV2(request_sha256=candidate.request_sha256, seed_sha256=candidate.seed_sha256,
        fixture=fixture, request_bindings=candidate.request_bindings)
