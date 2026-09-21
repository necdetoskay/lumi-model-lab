import copy
import json
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from src.saga_blueprint_contract import (
    CharacterNarrativeBlueprint,
    NarrativeArchitectProfile,
    fixture_fingerprint,
    load_fixture_manifest,
    load_profile,
    validate_blueprint_payload,
    validate_profile_against_manifest,
    write_schema,
)


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "configs" / "saga_lab" / "narrative_architect_v1.yaml"
FIXTURES = (
    ROOT
    / "data"
    / "specifications"
    / "saga_lab"
    / "character_world_fixtures_v1.json"
)
SCHEMA = (
    ROOT
    / "data"
    / "specifications"
    / "saga_lab"
    / "character_narrative_blueprint_v1.schema.json"
)


def minimal_blueprint() -> dict:
    return {
        "schema": "character-narrative-blueprint.v1",
        "origin": {
            "summary": "A careful archivist grew up around municipal records.",
            "origin_facts": [
                {
                    "key": "origin_fact_01",
                    "fact": "The character has worked in the same city for decades.",
                    "importance": "CORE",
                    "mutability": "IMMUTABLE",
                    "known_by_character": True,
                    "known_by_world": True,
                }
            ],
            "formative_events": [
                {
                    "key": "formative_event_01",
                    "summary": "A flood damaged part of the archive years ago.",
                    "age_or_period": "early career",
                    "impact": "Made preservation work personally important.",
                    "related_origin_facts": ["origin_fact_01"],
                }
            ],
            "origin_relationships": [
                {
                    "key": "origin_relationship_01",
                    "subject": "former archive director",
                    "relationship_type": "mentor",
                    "historical_role": "trained the character",
                    "current_status": "DISTANT",
                    "unresolved_tension": None,
                }
            ],
            "unresolved_origin_questions": [
                {
                    "key": "origin_question_01",
                    "question": "Why were some flood-era files never restored?",
                    "importance": "MINOR",
                    "character_knows_question_exists": True,
                    "answer_predefined": False,
                }
            ],
        },
        "present_situation": {
            "summary": "The character is preparing the archive for a future move.",
            "current_role": "municipal archivist",
            "current_location_context": "city archive",
            "current_relationship_context": ["training a younger archivist"],
            "current_resources": ["catalog access"],
            "current_pressures": ["digitization backlog"],
            "current_open_questions": ["which collections need priority"],
            "immediate_desires": ["leave the archive in good order"],
            "immediate_avoidances": ["turning every old record into a crisis"],
        },
        "narrative_core": {
            "identity_anchors": [
                {"key": "identity_anchor_01", "statement": "Patient custodian of memory."}
            ],
            "core_drives": [
                {
                    "key": "drive_01",
                    "drive": "preserve useful public memory",
                    "strength": "PRIMARY",
                }
            ],
            "core_fears": [{"key": "fear_01", "fear": "important context being lost"}],
            "internal_tensions": [
                {
                    "key": "tension_01",
                    "side_a": "preserve the past",
                    "side_b": "make room for change",
                    "description": "The character values continuity but knows archives must evolve.",
                }
            ],
            "long_term_questions": [
                {
                    "key": "long_question_01",
                    "question": "What deserves to be carried forward?",
                    "must_be_answered": False,
                }
            ],
            "themes": ["memory", "change"],
        },
        "saga_blueprint": {
            "design_intent": {
                "horizon": "LONG",
                "breadth": "EXPANSIVE",
                "linear_story_plan": False,
                "mandatory_story_order": False,
                "user_may_ignore_saga": True,
            },
            "threads": [
                {
                    "key": "saga_thread_01",
                    "title": "The Missing Ledger Context",
                    "premise": "Several ordinary records may connect to an unresolved civic-history question.",
                    "importance": "SUPPORTING",
                    "themes": ["memory"],
                    "origin_links": ["origin_question_01"],
                    "character_relevance": {
                        "why_it_matters": "It tests the character's values without demanding pursuit.",
                        "affected_drives": ["drive_01"],
                        "affected_tensions": ["tension_01"],
                    },
                    "activation": {"all_of": [], "any_of": [], "must_not": []},
                    "seeds": [
                        {
                            "key": "seed_01",
                            "kind": "DOCUMENT",
                            "summary": "A catalog card references a ledger not currently on shelf.",
                            "narrative_function": "QUESTION",
                            "world_binding_hint": {
                                "preferred_scope": "LOCAL",
                                "entity_type": "DOCUMENT",
                                "description": "Prefer an existing archive collection.",
                            },
                            "visibility_policy": {
                                "initial_visibility": "DISCOVERABLE",
                                "allowed_usage": ["The missing catalog reference may be noticed."],
                                "forbidden_usage": ["Do not invent the ledger's contents."],
                                "reveal_ceiling": "Only absence and catalog metadata may be established.",
                            },
                            "eligibility_conditions": {
                                "all_of": [],
                                "any_of": [],
                                "must_not": [],
                            },
                            "may_unlock": ["milestone_01"],
                            "must_not_force_followup": True,
                        }
                    ],
                    "milestones": [
                        {
                            "key": "milestone_01",
                            "type": "DISCOVERY",
                            "summary": "The character may learn why the ledger was moved.",
                            "required": False,
                            "preconditions": {
                                "all_of": [],
                                "any_of": [],
                                "must_not": [],
                            },
                            "possible_entry_points": ["seed_01"],
                            "possible_consequences": ["A new civic-history question may open."],
                            "unlocks": [],
                            "terminal": False,
                        }
                    ],
                    "branches": [
                        {
                            "key": "branch_01",
                            "trigger": "The ledger becomes relevant to a chosen story.",
                            "paths": [
                                {
                                    "key": "branch_path_a",
                                    "description": "Investigate personally.",
                                },
                                {
                                    "key": "branch_path_b",
                                    "description": "Hand the clue to the trainee.",
                                },
                            ],
                            "all_paths_valid": True,
                        }
                    ],
                    "possible_payoffs": [
                        {
                            "key": "payoff_01",
                            "description": "A fuller understanding of one period in city history.",
                            "certainty": "POSSIBLE",
                            "required": False,
                        }
                    ],
                    "dormancy_policy": {
                        "may_remain_dormant": True,
                        "maximum_story_gap": None,
                        "requires_periodic_reminder": False,
                    },
                    "recovery_policy": {
                        "can_reconnect_after_long_absence": True,
                        "reconnection_methods": ["DOCUMENT", "NPC", "LOCATION"],
                    },
                }
            ],
            "cross_thread_links": [],
        },
        "world_integration": {
            "proposed_bindings": [
                {
                    "key": "binding_01",
                    "saga_reference": "seed_01",
                    "binding_type": "DOCUMENT",
                    "preferred_existing_entity": True,
                    "reuse_first": True,
                    "creation_allowed_if_missing": True,
                    "description": "Bind to an existing archive collection if compatible.",
                    "placement_constraints": ["must remain inside known archive context"],
                }
            ],
            "integration_rules": [
                "Saga elements must appear to belong to the world independently of the character.",
                "Prefer existing compatible entities.",
            ],
        },
        "reweave_policy": {
            "reweave_allowed": True,
            "immutable_elements": ["committed origin facts", "revealed saga facts"],
            "mutable_elements": ["future seeds", "unrevealed milestones"],
            "recommended_triggers": ["LONG_SAGA_DORMANCY", "MAJOR_CHARACTER_CHANGE"],
        },
        "safety_and_constraints": {
            "never_prewrite_story_sequence": True,
            "never_force_saga_progression": True,
            "never_assume_future_character_choice": True,
            "never_commit_future_event_as_fact": True,
            "never_reveal_hidden_information_early": True,
            "allow_saga_free_stories": True,
            "allow_thread_abandonment": True,
            "allow_thread_reactivation": True,
            "allow_multiple_concurrent_threads": True,
        },
    }


class SagaBlueprintContractTests(unittest.TestCase):
    def test_profile_and_frozen_fixture_manifest_are_consistent(self) -> None:
        profile = load_profile(PROFILE)
        manifest = load_fixture_manifest(FIXTURES)
        validate_profile_against_manifest(profile, manifest)

        self.assertEqual(profile.role_id, "narrative-architect")
        self.assertEqual(len(manifest.cases), 12)
        self.assertEqual(len(profile.quick_fixture_ids), 3)
        self.assertEqual(set(profile.full_fixture_ids), {x.case_id for x in manifest.cases})

    def test_valid_minimal_blueprint_passes(self) -> None:
        parsed = validate_blueprint_payload(minimal_blueprint())
        self.assertIsInstance(parsed, CharacterNarrativeBlueprint)
        self.assertEqual(parsed.saga_blueprint.threads[0].key, "saga_thread_01")

    def test_unknown_top_level_field_fails_closed(self) -> None:
        payload = minimal_blueprint()
        payload["future_story_plan"] = ["story_1", "story_2"]
        with self.assertRaises(ValidationError):
            validate_blueprint_payload(payload)

    def test_duplicate_seed_key_fails_closed(self) -> None:
        payload = minimal_blueprint()
        seed = copy.deepcopy(payload["saga_blueprint"]["threads"][0]["seeds"][0])
        payload["saga_blueprint"]["threads"][0]["seeds"].append(seed)
        with self.assertRaises(ValidationError):
            validate_blueprint_payload(payload)

    def test_broken_cross_reference_fails_closed(self) -> None:
        payload = minimal_blueprint()
        payload["saga_blueprint"]["threads"][0]["seeds"][0]["may_unlock"] = [
            "milestone_does_not_exist"
        ]
        with self.assertRaises(ValidationError):
            validate_blueprint_payload(payload)

    def test_fixture_fingerprint_changes_on_material_input_change(self) -> None:
        manifest = load_fixture_manifest(FIXTURES)
        original = manifest.cases[0]
        changed_payload = original.model_dump(mode="json")
        changed_payload["character"]["starting_goal"] += " and document it"
        changed = type(original).model_validate(changed_payload)
        self.assertNotEqual(fixture_fingerprint(original), fixture_fingerprint(changed))

    def test_profile_unknown_fixture_fails_before_execution(self) -> None:
        profile = load_profile(PROFILE)
        manifest = load_fixture_manifest(FIXTURES)
        changed = profile.model_copy(deep=True)
        changed.quick_fixture_ids.append("unknown_paid_case")
        with self.assertRaises(ValueError):
            validate_profile_against_manifest(changed, manifest)

    def test_committed_json_schema_is_strict_at_top_level(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["properties"]["schema"]["const"],
            "character-narrative-blueprint.v1",
        )
        self.assertIn("$defs", schema)
        self.assertFalse(schema["$defs"]["Seed"]["additionalProperties"])
        self.assertEqual(
            schema["$defs"]["DesignIntent"]["properties"]["linear_story_plan"]["const"],
            False,
        )

    def test_schema_export_command_produces_strict_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "schema.json"
            write_schema(path)
            generated = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(generated["additionalProperties"])
            self.assertEqual(
                generated["properties"]["schema"]["const"],
                "character-narrative-blueprint.v1",
            )

    def test_profile_model_rejects_unknown_fields(self) -> None:
        profile = load_profile(PROFILE)
        payload = profile.model_dump(mode="json")
        payload["provider_model"] = "hard-coded-model-is-forbidden"
        with self.assertRaises(ValidationError):
            NarrativeArchitectProfile.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
