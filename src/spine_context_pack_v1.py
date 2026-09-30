from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.premise_architect_v2_contract import (
    PremiseCandidateV2,
    PremiseLabStateV1,
    build_reveal_safe_premise_projection,
)
from src.reader_profile_v2 import ReaderDevelopmentProfileV2
from src.saga_blueprint_contract import NarrativeFixture
from src.saga_spine_v2_contract import CharacterSagaSpineV2


class StrictModel(BaseModel):
    model_config=ConfigDict(extra="forbid")


class RevisionRefV1(StrictModel):
    entity_type:Literal[
        "UNIVERSE","WORLD","TIMELINE","PROFILE","CHARACTER",
        "CHARACTER_STORY_STATE","SAGA","PREMISE","READER_PROFILE"
    ]
    entity_id:str
    revision:int=Field(ge=1)
    fingerprint:str


class RelationshipStateV1(StrictModel):
    key:str
    subject:str
    relationship_type:str
    state:str
    trust_or_tension:str|None=None
    known_facts:list[str]=Field(default_factory=list)


class InventoryStateV1(StrictModel):
    key:str
    name:str
    category:str
    state:str
    story_uses:list[str]=Field(default_factory=list)
    durable:bool=True


class MemoryStateV1(StrictModel):
    key:str
    summary:str
    salience:Literal["LOW","MEDIUM","HIGH","CORE"]
    usable_as_fact:bool
    source_episode_key:str|None=None


class OpportunityStateV1(StrictModel):
    key:str
    title:str
    status:Literal["ACTIVE","AVAILABLE","RUMORED","LOCKED"]
    summary:str
    source_refs:list[str]=Field(default_factory=list)
    expiry_or_pressure:str|None=None


class RecentEpisodeStateV1(StrictModel):
    episode_key:str
    summary:str
    climax_shape:str
    primary_activity:str
    main_location_pattern:str
    durable_outcomes:list[str]=Field(default_factory=list)


class MockCanonicalStateV1(StrictModel):
    schema_id:Literal["mock-lumi-canonical-state.v1"]=Field(alias="schema")
    universe_id:str
    world_id:str
    timeline_id:str
    profile_id:str
    character_id:str
    character_story_state_id:str
    revisions:list[RevisionRefV1]
    fixture_path:str
    saga_path:str
    premise_state_path:str
    reader_profile_path:str
    premise_path:str
    relationships:list[RelationshipStateV1]
    inventory:list[InventoryStateV1]
    memories:list[MemoryStateV1]
    opportunities:list[OpportunityStateV1]
    recent_episodes:list[RecentEpisodeStateV1]
    current_situation_notes:list[str]=Field(default_factory=list)
    extra_known_facts:list[str]=Field(default_factory=list)

    @model_validator(mode="after")
    def validate_revision_types(self)->"MockCanonicalStateV1":
        types={x.entity_type for x in self.revisions}
        required={
            "UNIVERSE","WORLD","TIMELINE","PROFILE","CHARACTER",
            "CHARACTER_STORY_STATE","SAGA","PREMISE","READER_PROFILE",
        }
        if not required.issubset(types):
            raise ValueError(
                "Mock canonical state missing revisions: "
                +", ".join(sorted(required-types))
            )
        return self


class SpineContextPackV1(StrictModel):
    schema_id:Literal["spine-context-pack.v1"]=Field(alias="schema")
    context_pack_id:str
    context_fingerprint:str
    built_from:Literal["MOCK_CANONICAL_STATE","LUMI_CANONICAL_STATE"]
    authority_revisions:list[RevisionRefV1]

    reader_profile:dict[str,Any]
    session_target:dict[str,Any]

    character:dict[str,Any]
    origin:dict[str,Any]
    current_situation:dict[str,Any]
    relationships:list[RelationshipStateV1]
    inventory:list[InventoryStateV1]
    memories:list[MemoryStateV1]

    world:dict[str,Any]
    knowledge_boundaries:dict[str,Any]
    saga:dict[str,Any]
    opportunities:list[OpportunityStateV1]
    recent_story_history:list[RecentEpisodeStateV1]

    approved_premise:dict[str,Any]
    creative_permission_envelope:dict[str,Any]
    authority_rules:list[str]
    hard_freezes:list[str]
    anti_repetition:dict[str,Any]


def canonical_json(value:Any)->str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",",":"),
    )


def fingerprint_value(value:Any)->str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def revision_fingerprint(*,entity_type:str,entity_id:str,revision:int)->str:
    return fingerprint_value({
        "entity_type":entity_type,
        "entity_id":entity_id,
        "revision":revision,
    })


def build_spine_context_pack(
    source:MockCanonicalStateV1,
)->SpineContextPackV1:
    fixture=NarrativeFixture.model_validate_json(
        Path(source.fixture_path).read_text(encoding="utf-8")
    )
    saga=CharacterSagaSpineV2.model_validate_json(
        Path(source.saga_path).read_text(encoding="utf-8")
    )
    state=PremiseLabStateV1.model_validate_json(
        Path(source.premise_state_path).read_text(encoding="utf-8")
    )
    reader=ReaderDevelopmentProfileV2.model_validate_json(
        Path(source.reader_profile_path).read_text(encoding="utf-8")
    )
    premise_artifact=json.loads(Path(source.premise_path).read_text(encoding="utf-8"))
    premise=PremiseCandidateV2.model_validate(premise_artifact["premise"])

    projection=build_reveal_safe_premise_projection(
        spine=saga,
        reader=reader,
        fixture=fixture,
        state=state,
    )

    known_facts=list(projection["world"]["known_world_facts"])
    for fact in source.extra_known_facts:
        if fact not in known_facts:
            known_facts.append(fact)

    accessible=[]
    rumored=[]
    locked=[]
    for row in projection["world"]["location_access"]:
        item=dict(row)
        if row["status"]=="AVAILABLE" and row["premise_usage"]=="FULL":
            accessible.append(item)
        elif row["status"]=="RUMORED":
            rumored.append(item)
        else:
            locked.append(item)

    eligible=[dict(x) for x in projection["eligible_main_saga_milestones"]]
    eligible_keys={x["key"] for x in eligible}
    intended=sorted(set(premise.target_refs)&eligible_keys)

    # Important: no hidden truth statement is copied. Only public questions,
    # eligible milestones and explicit reveal ceilings survive.
    public_questions=[
        {
            "key":q.key,
            "question":q.question,
            "must_be_answered":q.must_be_answered,
        }
        for q in saga.narrative_core.long_term_questions
    ]
    unresolved_origin_questions=[
        {
            "key":q.key,
            "question":q.question,
            "importance":q.importance,
            "character_knows_question_exists":q.character_knows_question_exists,
        }
        for q in saga.origin.unresolved_origin_questions
    ]

    origin={
        "summary":saga.origin.summary,
        "facts":[x.model_dump(mode="json") for x in saga.origin.origin_facts],
        "formative_events":[x.model_dump(mode="json") for x in saga.origin.formative_events],
        "unresolved_questions":unresolved_origin_questions,
    }

    current_situation={
        "summary":saga.present_situation.summary,
        "current_role":saga.present_situation.current_role,
        "current_location_context":saga.present_situation.current_location_context,
        "current_pressures":list(saga.present_situation.current_pressures),
        "current_open_questions":list(saga.present_situation.current_open_questions),
        "immediate_desires":list(saga.present_situation.immediate_desires),
        "immediate_avoidances":list(saga.present_situation.immediate_avoidances),
        "notes":list(source.current_situation_notes),
    }

    saga_public={
        "main":{
            "key":projection["main_saga_public"]["key"],
            "title":projection["main_saga_public"]["title"],
            "goal":projection["main_saga_public"]["goal"],
            "stakes":projection["main_saga_public"]["stakes"],
            "central_mystery":projection["main_saga_public"]["central_mystery"],
            "themes":projection["main_saga_public"]["themes"],
        },
        "eligible_milestones":eligible,
        "intended_milestone_keys":intended,
        "active_side_sagas":projection["active_side_sagas"],
        "public_long_term_questions":public_questions,
        "completed_milestone_keys":list(state.completed_milestone_keys),
    }

    knowledge={
        "known_world_facts":known_facts,
        "accessible_locations":accessible,
        "rumored_locations":rumored,
        "locked_or_limited_locations":locked,
        "reveal_policy":{
            "hidden_truth_answers_included":False,
            "future_character_choice_must_remain_open":True,
            "rumored_locations_are_foreshadow_only_until_unlocked":True,
            "known_locked_locations_cannot_be_primary_episode_locations":True,
            "milestones_are_not_committed_by_spine":True,
        },
    }

    anti_repetition={
        "recent_episode_count":len(source.recent_episodes),
        "recent_climax_shapes":[x.climax_shape for x in source.recent_episodes],
        "recent_primary_activities":[x.primary_activity for x in source.recent_episodes],
        "recent_location_patterns":[x.main_location_pattern for x in source.recent_episodes],
        "rule":"New spine should be materially distinct from recent story shapes unless the approved premise requires reuse.",
    }

    authority_rules=[
        "Spine may use only facts, states, permissions and questions present in this pack.",
        "A model may invent transient scene texture but not durable canon unless creative_permission_envelope permits it.",
        "Hidden truth answers are absent from this pack and must not be inferred as fact.",
        "RUMORED locations are foreshadow-only; locked/limited locations obey their premise_usage.",
        "Only eligible milestones may be targeted, and a spine cannot itself commit completion.",
        "Inventory capability must come from inventory entries or explicit world/character authority.",
        "Relationships may evolve only through earned episode actions; starting state remains authoritative.",
        "Memories marked usable_as_fact=false may inform emotion but cannot establish external canon.",
        "Persistent outcomes remain candidates until delivered prose and post-story commit earn them.",
    ]

    hard_freezes=list(premise.constraints)+[
        premise.local_payoff,
        "Do not reveal or assert hidden Saga answers absent from this pack.",
        "Do not silently change the supplied authority revisions/fingerprint.",
    ]

    raw={
        "schema":"spine-context-pack.v1",
        "context_pack_id":(
            f"{source.character_id}:{source.world_id}:"
            f"{premise.key}:{max(x.revision for x in source.revisions)}"
        ),
        "context_fingerprint":"PENDING",
        "built_from":"MOCK_CANONICAL_STATE",
        "authority_revisions":[x.model_dump(mode="json") for x in source.revisions],
        "reader_profile":projection["reader_profile"],
        "session_target":projection["session_target"],
        "character":projection["character"],
        "origin":origin,
        "current_situation":current_situation,
        "relationships":[x.model_dump(mode="json") for x in source.relationships],
        "inventory":[x.model_dump(mode="json") for x in source.inventory],
        "memories":[x.model_dump(mode="json") for x in source.memories],
        "world":{
            "world_type":projection["world"]["world_type"],
            "era":projection["world"]["era"],
            "habitat":projection["world"]["habitat"],
            "technology_level":projection["world"]["technology_level"],
            "magic_level":projection["world"]["magic_level"],
            "summary":projection["world"]["summary"],
            "social_context":projection["world"]["social_context"],
            "known_pressures":projection["world"]["known_pressures"],
        },
        "knowledge_boundaries":knowledge,
        "saga":saga_public,
        "opportunities":[x.model_dump(mode="json") for x in source.opportunities],
        "recent_story_history":[x.model_dump(mode="json") for x in source.recent_episodes],
        "approved_premise":premise.model_dump(mode="json"),
        "creative_permission_envelope":projection["creative_permission_envelope"],
        "authority_rules":authority_rules,
        "hard_freezes":hard_freezes,
        "anti_repetition":anti_repetition,
    }
    fingerprint=fingerprint_value({k:v for k,v in raw.items() if k!="context_fingerprint"})
    raw["context_fingerprint"]=fingerprint
    return SpineContextPackV1.model_validate(raw)


def write_spine_context_pack(
    *,
    source_path:Path,
    out_path:Path,
)->SpineContextPackV1:
    source=MockCanonicalStateV1.model_validate_json(source_path.read_text(encoding="utf-8"))
    pack=build_spine_context_pack(source)
    out_path.parent.mkdir(parents=True,exist_ok=True)
    out_path.write_text(
        json.dumps(pack.model_dump(mode="json",by_alias=True),ensure_ascii=False,indent=2)+"\n",
        encoding="utf-8",
    )
    return pack
