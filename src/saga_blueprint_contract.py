from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


KEY_PATTERN = r"^[a-z][a-z0-9_]*$"
BLUEPRINT_SCHEMA_ID = "character-narrative-blueprint.v1"
PROFILE_VERSION = "1"
FIXTURE_SCHEMA_VERSION = "1"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Condition(StrictModel):
    type: Literal[
        "WORLD_FACT",
        "CHARACTER_FACT",
        "RELATIONSHIP",
        "LOCATION",
        "ITEM",
        "KNOWLEDGE",
        "EVENT",
    ]
    reference: str
    condition: str


class Conditions(StrictModel):
    all_of: list[Condition] = Field(default_factory=list)
    any_of: list[Condition] = Field(default_factory=list)
    must_not: list[Condition] = Field(default_factory=list)


class OriginFact(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    fact: str
    importance: Literal["CORE", "SUPPORTING"]
    mutability: Literal["IMMUTABLE", "REINTERPRETABLE"]
    known_by_character: bool
    known_by_world: bool


class FormativeEvent(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    summary: str
    age_or_period: str | None = None
    impact: str
    related_origin_facts: list[str] = Field(default_factory=list)


class OriginRelationship(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    subject: str
    relationship_type: str
    historical_role: str
    current_status: Literal["KNOWN", "UNKNOWN", "LOST", "DISTANT", "ACTIVE", "UNCERTAIN"]
    unresolved_tension: str | None = None


class OriginQuestion(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    question: str
    importance: Literal["MAJOR", "MINOR"]
    character_knows_question_exists: bool
    answer_predefined: bool


class Origin(StrictModel):
    summary: str
    origin_facts: list[OriginFact]
    formative_events: list[FormativeEvent]
    origin_relationships: list[OriginRelationship]
    unresolved_origin_questions: list[OriginQuestion]


class PresentSituation(StrictModel):
    summary: str
    current_role: str
    current_location_context: str
    current_relationship_context: list[str] = Field(default_factory=list)
    current_resources: list[str] = Field(default_factory=list)
    current_pressures: list[str] = Field(default_factory=list)
    current_open_questions: list[str] = Field(default_factory=list)
    immediate_desires: list[str] = Field(default_factory=list)
    immediate_avoidances: list[str] = Field(default_factory=list)


class IdentityAnchor(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    statement: str


class CoreDrive(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    drive: str
    strength: Literal["PRIMARY", "SECONDARY"]


class CoreFear(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    fear: str


class InternalTension(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    side_a: str
    side_b: str
    description: str


class LongTermQuestion(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    question: str
    must_be_answered: bool = False


class NarrativeCore(StrictModel):
    identity_anchors: list[IdentityAnchor]
    core_drives: list[CoreDrive]
    core_fears: list[CoreFear]
    internal_tensions: list[InternalTension]
    long_term_questions: list[LongTermQuestion]
    themes: list[str]


class DesignIntent(StrictModel):
    horizon: Literal["LONG"]
    breadth: Literal["EXPANSIVE"]
    linear_story_plan: Literal[False]
    mandatory_story_order: Literal[False]
    user_may_ignore_saga: Literal[True]


class CharacterRelevance(StrictModel):
    why_it_matters: str
    affected_drives: list[str] = Field(default_factory=list)
    affected_tensions: list[str] = Field(default_factory=list)


class WorldBindingHint(StrictModel):
    preferred_scope: Literal["LOCAL", "REGIONAL", "WORLD", "CROSS_WORLD"]
    entity_type: Literal["NPC", "LOCATION", "ITEM", "EVENT", "RUMOR", "DOCUMENT", "NONE"]
    description: str


class VisibilityPolicy(StrictModel):
    initial_visibility: Literal["HIDDEN", "FORESHADOW_ONLY", "DISCOVERABLE"]
    allowed_usage: list[str]
    forbidden_usage: list[str]
    reveal_ceiling: str


class Seed(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    kind: Literal[
        "RUMOR",
        "NPC",
        "LOCATION",
        "ITEM",
        "DOCUMENT",
        "SYMBOL",
        "MEMORY",
        "EVENT",
        "DREAM",
        "RELATIONSHIP",
        "WORLD_PHENOMENON",
    ]
    summary: str
    narrative_function: Literal[
        "FORESHADOW",
        "QUESTION",
        "DISCOVERY",
        "CONNECTION",
        "WARNING",
        "TEMPTATION",
        "REVELATION_PRECURSOR",
    ]
    world_binding_hint: WorldBindingHint
    visibility_policy: VisibilityPolicy
    eligibility_conditions: Conditions
    may_unlock: list[str] = Field(default_factory=list)
    must_not_force_followup: Literal[True]


class Milestone(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    type: Literal[
        "DISCOVERY",
        "REVELATION",
        "DECISION",
        "RELATIONSHIP_SHIFT",
        "CONSEQUENCE",
        "CONVERGENCE",
        "TRANSFORMATION",
    ]
    summary: str
    required: bool = False
    preconditions: Conditions
    possible_entry_points: list[str] = Field(default_factory=list)
    possible_consequences: list[str] = Field(default_factory=list)
    unlocks: list[str] = Field(default_factory=list)
    terminal: bool = False


class BranchPath(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    description: str


class Branch(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    trigger: str
    paths: list[BranchPath]
    all_paths_valid: Literal[True]


class PossiblePayoff(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    description: str
    certainty: Literal["POSSIBLE"]
    required: Literal[False]


class DormancyPolicy(StrictModel):
    may_remain_dormant: Literal[True]
    maximum_story_gap: int | None = Field(default=None, ge=0)
    requires_periodic_reminder: Literal[False]


class RecoveryPolicy(StrictModel):
    can_reconnect_after_long_absence: Literal[True]
    reconnection_methods: list[
        Literal["WORLD_EVENT", "NPC", "ITEM", "RUMOR", "LOCATION", "CONSEQUENCE"]
    ]


class SagaThread(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    title: str
    premise: str
    importance: Literal["MAJOR", "SUPPORTING", "LATENT"]
    themes: list[str]
    origin_links: list[str] = Field(default_factory=list)
    character_relevance: CharacterRelevance
    activation: Conditions
    seeds: list[Seed]
    milestones: list[Milestone]
    branches: list[Branch] = Field(default_factory=list)
    possible_payoffs: list[PossiblePayoff] = Field(default_factory=list)
    dormancy_policy: DormancyPolicy
    recovery_policy: RecoveryPolicy


class CrossThreadLink(StrictModel):
    from_thread: str = Field(alias="from")
    to_thread: str = Field(alias="to")
    relationship: Literal[
        "MAY_CONVERGE",
        "SHARED_NPC",
        "SHARED_LOCATION",
        "CAUSAL",
        "THEMATIC",
        "MUTUALLY_EXCLUSIVE",
    ]
    description: str


class SagaBlueprint(StrictModel):
    design_intent: DesignIntent
    threads: list[SagaThread]
    cross_thread_links: list[CrossThreadLink] = Field(default_factory=list)


class ProposedBinding(StrictModel):
    key: str = Field(pattern=KEY_PATTERN)
    saga_reference: str
    binding_type: Literal[
        "NPC",
        "LOCATION",
        "ITEM",
        "RUMOR",
        "DOCUMENT",
        "EVENT",
        "FACTION",
        "WORLD_PHENOMENON",
    ]
    preferred_existing_entity: Literal[True]
    reuse_first: Literal[True]
    creation_allowed_if_missing: bool
    description: str
    placement_constraints: list[str] = Field(default_factory=list)


class WorldIntegration(StrictModel):
    proposed_bindings: list[ProposedBinding] = Field(default_factory=list)
    integration_rules: list[str]


class ReweavePolicy(StrictModel):
    reweave_allowed: Literal[True]
    immutable_elements: list[str]
    mutable_elements: list[str]
    recommended_triggers: list[
        Literal[
            "MAJOR_CHARACTER_CHANGE",
            "MAJOR_WORLD_CHANGE",
            "THREAD_INVALIDATED",
            "LONG_SAGA_DORMANCY",
            "MAJOR_RELATIONSHIP_CHANGE",
            "CROSS_WORLD_TRANSITION",
        ]
    ]


class SafetyAndConstraints(StrictModel):
    never_prewrite_story_sequence: Literal[True]
    never_force_saga_progression: Literal[True]
    never_assume_future_character_choice: Literal[True]
    never_commit_future_event_as_fact: Literal[True]
    never_reveal_hidden_information_early: Literal[True]
    allow_saga_free_stories: Literal[True]
    allow_thread_abandonment: Literal[True]
    allow_thread_reactivation: Literal[True]
    allow_multiple_concurrent_threads: Literal[True]


def _duplicate(values: list[str]) -> str | None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            return value
        seen.add(value)
    return None


class CharacterNarrativeBlueprint(StrictModel):
    schema_id: Literal[BLUEPRINT_SCHEMA_ID] = Field(alias="schema")
    origin: Origin
    present_situation: PresentSituation
    narrative_core: NarrativeCore
    saga_blueprint: SagaBlueprint
    world_integration: WorldIntegration
    reweave_policy: ReweavePolicy
    safety_and_constraints: SafetyAndConstraints

    @model_validator(mode="after")
    def validate_references(self) -> "CharacterNarrativeBlueprint":
        origin_fact_keys = {item.key for item in self.origin.origin_facts}
        origin_question_keys = {item.key for item in self.origin.unresolved_origin_questions}
        drive_keys = {item.key for item in self.narrative_core.core_drives}
        tension_keys = {item.key for item in self.narrative_core.internal_tensions}

        for group_name, values in {
            "origin facts": [x.key for x in self.origin.origin_facts],
            "formative events": [x.key for x in self.origin.formative_events],
            "origin relationships": [x.key for x in self.origin.origin_relationships],
            "origin questions": [x.key for x in self.origin.unresolved_origin_questions],
            "identity anchors": [x.key for x in self.narrative_core.identity_anchors],
            "core drives": [x.key for x in self.narrative_core.core_drives],
            "core fears": [x.key for x in self.narrative_core.core_fears],
            "internal tensions": [x.key for x in self.narrative_core.internal_tensions],
            "long-term questions": [x.key for x in self.narrative_core.long_term_questions],
            "saga threads": [x.key for x in self.saga_blueprint.threads],
            "world bindings": [x.key for x in self.world_integration.proposed_bindings],
        }.items():
            duplicate = _duplicate(values)
            if duplicate:
                raise ValueError(f"duplicate {group_name} key: {duplicate}")

        for event in self.origin.formative_events:
            unknown = sorted(set(event.related_origin_facts) - origin_fact_keys)
            if unknown:
                raise ValueError(
                    f"{event.key}: unknown related_origin_facts: {', '.join(unknown)}"
                )

        thread_keys = {thread.key for thread in self.saga_blueprint.threads}
        all_seed_keys: set[str] = set()

        for thread in self.saga_blueprint.threads:
            seed_keys = [seed.key for seed in thread.seeds]
            milestone_keys = [milestone.key for milestone in thread.milestones]
            branch_keys = [branch.key for branch in thread.branches]
            payoff_keys = [payoff.key for payoff in thread.possible_payoffs]

            for group_name, values in {
                "seed": seed_keys,
                "milestone": milestone_keys,
                "branch": branch_keys,
                "payoff": payoff_keys,
            }.items():
                duplicate = _duplicate(values)
                if duplicate:
                    raise ValueError(f"{thread.key}: duplicate {group_name} key: {duplicate}")

            overlap = all_seed_keys.intersection(seed_keys)
            if overlap:
                raise ValueError(
                    f"seed keys must be globally unique: {', '.join(sorted(overlap))}"
                )
            all_seed_keys.update(seed_keys)

            valid_origin_links = origin_fact_keys | origin_question_keys
            unknown_origin = sorted(set(thread.origin_links) - valid_origin_links)
            if unknown_origin:
                raise ValueError(
                    f"{thread.key}: unknown origin_links: {', '.join(unknown_origin)}"
                )

            unknown_drives = sorted(
                set(thread.character_relevance.affected_drives) - drive_keys
            )
            if unknown_drives:
                raise ValueError(
                    f"{thread.key}: unknown affected_drives: {', '.join(unknown_drives)}"
                )

            unknown_tensions = sorted(
                set(thread.character_relevance.affected_tensions) - tension_keys
            )
            if unknown_tensions:
                raise ValueError(
                    f"{thread.key}: unknown affected_tensions: {', '.join(unknown_tensions)}"
                )

            seed_set = set(seed_keys)
            milestone_set = set(milestone_keys)
            unlockable = seed_set | milestone_set
            for seed in thread.seeds:
                unknown = sorted(set(seed.may_unlock) - unlockable)
                if unknown:
                    raise ValueError(
                        f"{seed.key}: unknown may_unlock refs: {', '.join(unknown)}"
                    )
            for milestone in thread.milestones:
                unknown_entries = sorted(
                    set(milestone.possible_entry_points) - seed_set
                )
                if unknown_entries:
                    raise ValueError(
                        f"{milestone.key}: unknown possible_entry_points: "
                        + ", ".join(unknown_entries)
                    )
                unknown_unlocks = sorted(set(milestone.unlocks) - unlockable)
                if unknown_unlocks:
                    raise ValueError(
                        f"{milestone.key}: unknown unlock refs: "
                        + ", ".join(unknown_unlocks)
                    )

        for link in self.saga_blueprint.cross_thread_links:
            if link.from_thread not in thread_keys or link.to_thread not in thread_keys:
                raise ValueError(
                    f"cross_thread_link references unknown thread: "
                    f"{link.from_thread} -> {link.to_thread}"
                )
            if link.from_thread == link.to_thread:
                raise ValueError("cross_thread_link cannot self-reference")

        all_saga_refs = thread_keys | all_seed_keys
        for binding in self.world_integration.proposed_bindings:
            if binding.saga_reference not in all_saga_refs:
                raise ValueError(
                    f"{binding.key}: unknown saga_reference {binding.saga_reference}"
                )

        return self


class ReferencePolicy(StrictModel):
    deterministic_first: Literal[True]
    semantic_reference: Literal["strong_llm_judge"]
    blind_review_sample: Literal[True]


class NarrativeArchitectProfile(StrictModel):
    role_id: Literal["narrative-architect"]
    profile_version: Literal[PROFILE_VERSION]
    risk_class: Literal["L2"]
    purpose: str
    non_goals: list[str]
    input_fixture_manifest: str
    output_schema: str
    prompt_contract: str
    quick_fixture_ids: list[str]
    full_fixture_ids: list[str]
    deterministic_gates: list[str]
    semantic_metrics: list[str]
    reference_policy: ReferencePolicy
    fingerprint_inputs: list[str]
    cost_latency_capture: list[str]


class FixtureCharacter(StrictModel):
    name: str
    age: int = Field(ge=2, le=100)
    profile_type: Literal["CHILD", "SELF"]
    archetype: str
    traits: list[str]
    interests: list[str]
    starting_goal: str
    starting_relationships: list[str] = Field(default_factory=list)


class FixtureWorld(StrictModel):
    world_type: Literal[
        "REALISTIC",
        "LOW_MAGIC",
        "HIGH_FANTASY",
        "SCIENCE_FICTION",
        "HISTORICAL",
    ]
    era: str
    habitat: str
    technology_level: str
    magic_level: str
    summary: str
    locations: list[str]
    social_context: list[str]
    known_pressures: list[str]


class NarrativeFixture(StrictModel):
    case_id: str = Field(pattern=KEY_PATTERN)
    audience_band: Literal[
        "YOUNG_CHILD",
        "OLDER_CHILD",
        "TEEN",
        "YOUNG_ADULT",
        "ADULT",
        "MATURE_ADULT",
    ]
    story_mode: Literal[
        "EXPLORATION",
        "MYSTERY",
        "RELATIONSHIP",
        "ADVENTURE",
        "DISCOVERY",
        "LIFE_DRAMA",
    ]
    character: FixtureCharacter
    world: FixtureWorld
    test_intents: list[str]
    tags: list[str]


class FixtureManifest(StrictModel):
    manifest_id: Literal["saga_lab_character_world_fixtures_v1"]
    manifest_version: Literal["1"]
    fixture_schema_version: Literal[FIXTURE_SCHEMA_VERSION]
    cases: list[NarrativeFixture]

    @model_validator(mode="after")
    def unique_case_ids(self) -> "FixtureManifest":
        duplicate = _duplicate([case.case_id for case in self.cases])
        if duplicate:
            raise ValueError(f"duplicate fixture case_id: {duplicate}")
        return self


def load_profile(path: Path) -> NarrativeArchitectProfile:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return NarrativeArchitectProfile.model_validate(raw)


def load_fixture_manifest(path: Path) -> FixtureManifest:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return FixtureManifest.model_validate(raw)


def validate_profile_against_manifest(
    profile: NarrativeArchitectProfile,
    manifest: FixtureManifest,
) -> None:
    available = {case.case_id for case in manifest.cases}
    full = profile.full_fixture_ids
    quick = profile.quick_fixture_ids
    if _duplicate(full):
        raise ValueError("full_fixture_ids contains duplicates")
    if _duplicate(quick):
        raise ValueError("quick_fixture_ids contains duplicates")
    unknown = sorted((set(full) | set(quick)) - available)
    if unknown:
        raise ValueError("profile references unknown fixtures: " + ", ".join(unknown))
    if not set(quick).issubset(set(full)):
        raise ValueError("quick_fixture_ids must be a subset of full_fixture_ids")
    if set(full) != available:
        missing = sorted(available - set(full))
        raise ValueError("full_fixture_ids must cover frozen manifest: " + ", ".join(missing))


def fixture_fingerprint(case: NarrativeFixture) -> str:
    payload = case.model_dump(mode="json")
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate_blueprint_payload(payload: dict) -> CharacterNarrativeBlueprint:
    return CharacterNarrativeBlueprint.model_validate(payload)


def write_schema(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            CharacterNarrativeBlueprint.model_json_schema(by_alias=True),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Saga Lab P1 contracts.")
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--write-schema", type=Path)
    args = parser.parse_args()

    if args.write_schema:
        write_schema(args.write_schema)

    if args.profile or args.fixtures:
        if not args.profile or not args.fixtures:
            parser.error("--profile and --fixtures must be supplied together")
        profile = load_profile(args.profile)
        manifest = load_fixture_manifest(args.fixtures)
        validate_profile_against_manifest(profile, manifest)
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "role_id": profile.role_id,
                    "profile_version": profile.profile_version,
                    "fixture_count": len(manifest.cases),
                    "quick_fixture_count": len(profile.quick_fixture_ids),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
