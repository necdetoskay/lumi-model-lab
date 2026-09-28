from __future__ import annotations

import copy
import unittest

from pydantic import ValidationError

from src.saga_spine_v2_contract import CharacterSagaSpineV2


def _conditions() -> dict:
    return {"all_of": [], "any_of": [], "must_not": []}


def _valid_payload() -> dict:
    anchors = []
    milestones = []
    edges = []

    for anchor_index in range(1, 6):
        anchor_key = f"anchor_{anchor_index}"
        keys = [f"m_{anchor_index}_{i}" for i in range(1, 4)]
        anchors.append(
            {
                "key": anchor_key,
                "title": f"Anchor {anchor_index}",
                "purpose": f"Move the long-horizon mystery into state {anchor_index}.",
                "target_state": f"The character has earned narrative state {anchor_index}.",
                "milestone_keys": keys,
                "required_for_resolution": True,
            }
        )
        for milestone_index, key in enumerate(keys, start=1):
            milestones.append(
                {
                    "key": key,
                    "anchor_key": anchor_key,
                    "type": "DISCOVERY" if milestone_index == 1 else "EVIDENCE",
                    "summary": f"Meaningful discovery {anchor_index}-{milestone_index}.",
                    "state_condition": f"Evidence state {anchor_index}-{milestone_index} is established.",
                    "required_for_anchor": milestone_index == 3,
                    "possible_entry_vectors": ["EXPLORATION", "RUMOR"],
                    "reveal_keys": ["reveal_1"] if key == "m_2_1" else [],
                    "consequence_options": ["May open a new route without forcing it."],
                    "skippable_if_alternate_route_satisfies_anchor": milestone_index != 3,
                }
            )

        edges.extend(
            [
                {
                    "from_node": anchor_key,
                    "to_node": keys[0],
                    "relationship": "REQUIRES",
                    "rationale": "Anchor begins with a meaningful discovery opportunity.",
                },
                {
                    "from_node": keys[0],
                    "to_node": keys[1],
                    "relationship": "MAY_ENABLE",
                    "rationale": "Evidence may deepen after the first discovery.",
                },
                {
                    "from_node": keys[1],
                    "to_node": keys[2],
                    "relationship": "MAY_ENABLE",
                    "rationale": "The anchor can mature toward its target state.",
                },
            ]
        )
        if anchor_index < 5:
            edges.append(
                {
                    "from_node": keys[2],
                    "to_node": f"anchor_{anchor_index + 1}",
                    "relationship": "MAY_CONVERGE",
                    "rationale": "The completed state can open the next long-horizon anchor.",
                }
            )

    edges.append(
        {
            "from_node": "anchor_1",
            "to_node": "m_1_2",
            "relationship": "ALTERNATIVE_ROUTE",
            "rationale": "A different clue may bypass the first discovery without changing the destination.",
        }
    )

    return {
        "schema": "character-saga-spine.v2",
        "origin": {
            "summary": "Deniz has always been drawn to unexplained maps and distant places.",
            "origin_facts": [
                {
                    "key": "curious_cartographer",
                    "fact": "Deniz carefully records places and symbols that seem important.",
                    "importance": "CORE",
                    "mutability": "IMMUTABLE",
                    "known_by_character": True,
                    "known_by_world": True,
                }
            ],
            "formative_events": [],
            "origin_relationships": [],
            "unresolved_origin_questions": [
                {
                    "key": "first_map_question",
                    "question": "Why did an old map contain a region absent from newer maps?",
                    "importance": "MAJOR",
                    "character_knows_question_exists": True,
                    "answer_predefined": False,
                }
            ],
        },
        "present_situation": {
            "summary": "Deniz is ready for a first serious expedition.",
            "current_role": "young explorer and map keeper",
            "current_location_context": "A known coastal settlement at the edge of a larger unexplored region.",
            "current_relationship_context": [],
            "current_resources": ["personal notebook", "basic travel kit"],
            "current_pressures": ["The safe travel season will not last forever."],
            "current_open_questions": ["What lies beyond the mapped northern route?"],
            "immediate_desires": ["Find evidence that the old map is not a mistake."],
            "immediate_avoidances": ["Do not risk others merely to satisfy curiosity."],
        },
        "narrative_core": {
            "identity_anchors": [
                {"key": "careful_explorer", "statement": "Deniz explores boldly but records evidence carefully."}
            ],
            "core_drives": [
                {"key": "discover_truth", "drive": "Understand places others dismiss as impossible.", "strength": "PRIMARY"}
            ],
            "core_fears": [
                {"key": "mislead_others", "fear": "Being so certain of a theory that others are led into danger."}
            ],
            "internal_tensions": [
                {
                    "key": "wonder_vs_proof",
                    "side_a": "Follow wonder quickly.",
                    "side_b": "Demand enough evidence before acting.",
                    "description": "Discovery is exciting, but certainty must be earned.",
                }
            ],
            "long_term_questions": [
                {
                    "key": "what_is_missing",
                    "question": "Why are parts of the world absent from accepted maps?",
                    "must_be_answered": False,
                }
            ],
            "themes": ["discovery", "evidence", "responsibility"],
        },
        "main_saga": {
            "key": "broken_atlas",
            "title": "The Broken Atlas",
            "goal": "Discover why several regions have vanished from modern maps and determine what connects them.",
            "stakes": "Wrong conclusions can close routes, endanger expeditions, or hide important truths from the world.",
            "central_mystery": "Different lost locations share symbols that should not belong to the same culture or era.",
            "themes": ["exploration", "evidence", "uncertain history"],
            "entry_anchor_keys": ["anchor_1"],
            "resolution_anchor_key": "anchor_5",
            "resolution_milestone_keys": ["m_5_3"],
            "anchors": anchors,
            "milestones": milestones,
            "edges": edges,
            "hidden_truths": [
                {
                    "key": "truth_1",
                    "mode": "FIXED_HIDDEN",
                    "question": "Are the missing regions connected by deliberate map alteration?",
                    "hidden_statement": "At least one historical map revision deliberately removed a real route.",
                    "character_knows_question_exists": False,
                },
                {
                    "key": "truth_2",
                    "mode": "UNRESOLVED_BY_DESIGN",
                    "question": "Who ultimately benefited from the missing regions being forgotten?",
                    "hidden_statement": None,
                    "character_knows_question_exists": False,
                },
            ],
            "reveal_steps": [
                {
                    "key": "reveal_1",
                    "truth_key": "truth_1",
                    "level": "PARTIAL",
                    "summary": "Evidence may establish that two map revisions disagree for non-random reasons.",
                    "eligibility": _conditions(),
                    "milestone_keys": ["m_2_1"],
                    "reveal_ceiling": "Do not reveal who changed the maps or why.",
                }
            ],
        },
        "latent_side_sagas": [
            {
                "key": "side_compass",
                "arc_type": "SIDE",
                "premise": "A damaged expedition compass reacts strangely near a few unrelated locations.",
                "why_it_matters": "It can create optional exploration without hijacking the Main Saga.",
                "activation": _conditions(),
                "initial_visibility": "HIDDEN",
                "must_not_force_followup": True,
                "remains_proposed_until_activated": True,
            }
        ],
        "creative_permission_envelope": {
            "allowed_entity_types": [
                "NPC",
                "LOCATION",
                "ITEM",
                "RUMOR",
                "DOCUMENT",
                "EVENT",
                "FACTION",
                "WORLD_PHENOMENON",
                "TRANSIENT_SCENE_DETAIL",
            ],
            "allowed_scopes": ["LOCAL", "REGIONAL", "WORLD"],
            "creation_constraints": [
                "New durable facts remain proposals until outcome commit.",
                "Prefer reuse of established entities when they fit naturally.",
            ],
            "forbidden_creations": [
                "Do not invent a future choice for Deniz.",
                "Do not expose hidden Saga truth before its reveal ceiling.",
            ],
            "durable_creation_requires_outcome_commit": True,
        },
        "world_integration": {
            "proposed_bindings": [],
            "integration_rules": ["Reuse existing world entities before proposing new durable entities."],
        },
        "reweave_policy": {
            "reweave_allowed": True,
            "immutable_elements": ["committed past story outcomes"],
            "mutable_elements": ["future route proposals", "unused latent side-Saga seeds"],
            "recommended_triggers": ["THREAD_INVALIDATED", "LONG_SAGA_DORMANCY"],
        },
        "background_enrichment_policy": {
            "may_propose_latent_quests": True,
            "may_propose_saga_links": True,
            "may_propose_world_events": True,
            "may_propose_npc_arcs": True,
            "may_mutate_user_dependent_canon_while_absent": False,
            "outputs_remain_proposed_or_latent": True,
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


class SagaSpineV2ContractTests(unittest.TestCase):
    def test_valid_graph_contract_passes(self):
        spine = CharacterSagaSpineV2.model_validate(_valid_payload())
        self.assertEqual(len(spine.main_saga.anchors), 5)
        self.assertEqual(len(spine.main_saga.milestones), 15)
        self.assertEqual(spine.main_saga.resolution_milestone_keys, ["m_5_3"])

    def test_rejects_too_few_milestones(self):
        payload = _valid_payload()
        payload["main_saga"]["milestones"] = payload["main_saga"]["milestones"][:-1]
        with self.assertRaisesRegex(ValidationError, "15-30 milestones"):
            CharacterSagaSpineV2.model_validate(payload)

    def test_rejects_scripted_episode_sequence(self):
        payload = _valid_payload()
        payload["main_saga"]["anchors"][0]["purpose"] = "Episode 1 sends Deniz to the northern cave."
        with self.assertRaisesRegex(ValidationError, "must not encode numbered"):
            CharacterSagaSpineV2.model_validate(payload)

    def test_rejects_unresolved_truth_with_confirmed_reveal(self):
        payload = _valid_payload()
        payload["main_saga"]["reveal_steps"].append(
            {
                "key": "reveal_2",
                "truth_key": "truth_2",
                "level": "CONFIRMED",
                "summary": "Predetermine the answer that should remain open.",
                "eligibility": _conditions(),
                "milestone_keys": ["m_4_1"],
                "reveal_ceiling": "Full answer.",
            }
        )
        payload["main_saga"]["milestones"][9]["reveal_keys"] = ["reveal_2"]
        with self.assertRaisesRegex(ValidationError, "cannot pre-resolve"):
            CharacterSagaSpineV2.model_validate(payload)

    def test_rejects_cycle(self):
        payload = _valid_payload()
        payload["main_saga"]["edges"].append(
            {
                "from_node": "m_5_3",
                "to_node": "anchor_1",
                "relationship": "MAY_ENABLE",
                "rationale": "Invalid loop.",
            }
        )
        with self.assertRaisesRegex(ValidationError, "must be acyclic"):
            CharacterSagaSpineV2.model_validate(payload)

    def test_rejects_orphan_graph_node(self):
        payload = _valid_payload()
        # m_1_1 can be orphaned while the explicit ALTERNATIVE_ROUTE
        # anchor_1 -> m_1_2 still preserves the route to resolution.
        payload["main_saga"]["edges"] = [
            edge
            for edge in payload["main_saga"]["edges"]
            if edge["to_node"] != "m_1_1" and edge["from_node"] != "m_1_1"
        ]
        with self.assertRaisesRegex(ValidationError, "unreachable nodes"):
            CharacterSagaSpineV2.model_validate(payload)

    def test_rejects_graph_without_alternative_route(self):
        payload = _valid_payload()
        payload["main_saga"]["edges"] = [
            edge
            for edge in payload["main_saga"]["edges"]
            if edge["relationship"] != "ALTERNATIVE_ROUTE"
        ]
        with self.assertRaisesRegex(ValidationError, "ALTERNATIVE_ROUTE"):
            CharacterSagaSpineV2.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
