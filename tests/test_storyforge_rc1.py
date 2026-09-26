from __future__ import annotations

import unittest
from unittest.mock import patch

from pydantic import ValidationError

from src.storyforge.contracts import StoryForgeRequest
from src.storyforge.runtime import run_storyforge


def _request_dict() -> dict:
    return {
        "schema_version": "storyforge-request.v1",
        "profile_id": "LSF-A4-W500-v1.0-rc1",
        "request_id": "unit-test",
        "active_world_id": "world-home-01",
        "always_required": [
            {"id": "character.identity", "text": "Deniz is active.", "kind": "canon"},
            {"id": "character.exact_age", "text": "Deniz is exactly 4.", "kind": "canon"},
            {"id": "world.active", "text": "Active world is world-home-01.", "kind": "canon"},
            {"id": "state.current_location", "text": "Deniz is in COMMONS_COURTYARD.", "kind": "state"},
            {"id": "state.story_revision", "text": "Revision 12.", "kind": "state"},
        ],
        "candidate_facts": [
            {"id": "relationship.ada", "text": "Ada is Deniz's friend.", "kind": "state"},
            {"id": "location.chalk_box", "text": "One short red chalk is in the box.", "kind": "state"},
            {"id": "world.physics_normal", "text": "Normal everyday physics.", "kind": "canon"},
            {"id": "inventory.blue_chalk", "text": "Deniz has blue chalk.", "kind": "state"},
        ],
        "forbidden_facts": [
            {"id": "foreign_world.secret", "text": "Foreign world fact.", "kind": "meta"}
        ],
        "story_intent": {
            "family": "friendship_emotional_social",
            "opportunity": "Deniz and Ada both notice the last short red chalk piece.",
            "stakes": "low",
            "fantasy_allowed": False,
            "references": {
                "required_fact_ids": ["relationship.ada", "location.chalk_box"],
                "hard_guard_fact_ids": ["world.physics_normal"],
            },
            "hard_constraints": [
                "No adult may solve the problem.",
                "Do not invent prior relationship conflict.",
            ],
        },
        "generation_profile": {
            "exact_age": 4,
            "target_words": 500,
            "preferred_range": [475, 525],
            "hard_range": [375, 625],
            "language_of_generation": "en",
            "delivery_language": "tr",
        },
    }


def _packet() -> dict:
    req = _request_dict()
    candidate_map = {x["id"]: x for x in req["candidate_facts"]}
    return {
        "deterministic_core": req["always_required"] + [
            candidate_map["relationship.ada"],
            candidate_map["location.chalk_box"],
            candidate_map["world.physics_normal"],
        ],
        "jev_selected_enrichment": [candidate_map["inventory.blue_chalk"]],
    }


def _plan() -> dict:
    return {
        "premise": "Deniz and Ada solve a small chalk disagreement together.",
        "beats": [
            {
                "id": f"B{i}",
                "density": "anchor" if i in {3, 6, 8} else "develop",
                "beat": f"Beat {i}",
                "uses_fact_ids": ["relationship.ada"] if i in {1, 3, 6, 8} else [],
            }
            for i in range(1, 9)
        ],
        "assumptions": [],
        "expected_outcome": {
            "proposed_state_changes": [],
            "preserved_invariants": ["Ada remains Deniz's friend."],
        },
    }


def _meta() -> dict:
    return {"usage": {}, "cost": {"usd": 0.001}, "request": {}, "parse_failures": []}


def _body(cost: float = 0.001) -> dict:
    return {
        "choices": [{"message": {"content": "x"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20, "cost": cost},
    }


class StoryForgeContractTests(unittest.TestCase):
    def test_duplicate_fact_ids_fail_closed(self):
        payload = _request_dict()
        payload["candidate_facts"].append(
            {"id": "relationship.ada", "text": "Duplicate.", "kind": "state"}
        )
        with self.assertRaises(ValidationError):
            StoryForgeRequest.model_validate(payload)

    def test_missing_direct_reference_fails_closed(self):
        payload = _request_dict()
        payload["story_intent"]["references"]["required_fact_ids"].append("inventory.missing")
        with self.assertRaises(ValidationError):
            StoryForgeRequest.model_validate(payload)


class StoryForgeRuntimeFailClosedTests(unittest.TestCase):
    @patch("src.storyforge.runtime.call_openrouter")
    @patch("src.storyforge.runtime._structured_call")
    @patch("src.storyforge.runtime._build_context")
    def test_rejected_plan_never_reaches_writer(
        self,
        mock_context,
        mock_structured,
        mock_openrouter,
    ):
        request = StoryForgeRequest.model_validate(_request_dict())
        mock_context.return_value = (_packet(), {"selected_enrichment_ids": ["inventory.blue_chalk"]})
        mock_structured.side_effect = [
            (_plan(), _meta()),
            (
                {
                    "valid": False,
                    "counts": {"critical": 0, "serious": 1},
                    "defects": [
                        {
                            "severity": "serious",
                            "class": "canon_state_consistency",
                            "beat_ids": ["B3"],
                            "why": "test blocker",
                        }
                    ],
                    "summary": "blocked",
                },
                _meta(),
            ),
        ]

        result = run_storyforge(request, api_key="test")

        self.assertEqual(result.status, "plan_rejected")
        self.assertFalse(result.publication_ready)
        mock_openrouter.assert_not_called()

    @patch("src.storyforge.runtime._audit_story")
    @patch("src.storyforge.runtime.call_openrouter")
    @patch("src.storyforge.runtime._structured_call")
    @patch("src.storyforge.runtime._build_context")
    def test_structural_story_defect_never_reaches_repair_or_translation(
        self,
        mock_context,
        mock_structured,
        mock_openrouter,
        mock_audit,
    ):
        request = StoryForgeRequest.model_validate(_request_dict())
        mock_context.return_value = (_packet(), {"selected_enrichment_ids": ["inventory.blue_chalk"]})
        mock_structured.side_effect = [
            (_plan(), _meta()),
            (
                {
                    "valid": True,
                    "counts": {"critical": 0, "serious": 0},
                    "defects": [],
                    "summary": "clean",
                },
                _meta(),
            ),
        ]
        story = ("Title\n\n" + "word " * 490).strip()
        mock_openrouter.return_value = (
            story,
            _body(),
            {"temperature": 0.72, "max_tokens": None, "reasoning": None},
        )
        structural = {
            "family": "causal_logic",
            "severity": "serious",
            "repair_scope": "structural",
            "span_ids": ["S001"],
            "reason": "requires multi-event restructure",
        }
        mock_audit.side_effect = [
            ([structural], _meta()),
            ([], _meta()),
        ]

        result = run_storyforge(request, api_key="test")

        self.assertEqual(result.status, "story_rejected")
        self.assertFalse(result.publication_ready)
        self.assertEqual(mock_openrouter.call_count, 1)
        self.assertEqual(mock_structured.call_count, 2)

    @patch("src.storyforge.runtime._audit_story")
    @patch("src.storyforge.runtime.call_openrouter")
    @patch("src.storyforge.runtime._structured_call")
    @patch("src.storyforge.runtime._build_context")
    def test_local_defect_is_repaired_then_translation_runs(
        self,
        mock_context,
        mock_structured,
        mock_openrouter,
        mock_audit,
    ):
        request = StoryForgeRequest.model_validate(_request_dict())
        mock_context.return_value = (_packet(), {"selected_enrichment_ids": ["inventory.blue_chalk"]})
        mock_structured.side_effect = [
            (_plan(), _meta()),
            (
                {
                    "valid": True,
                    "counts": {"critical": 0, "serious": 0},
                    "defects": [],
                    "summary": "clean",
                },
                _meta(),
            ),
            (
                {
                    "repairs": [
                        {
                            "old": "big black wheels",
                            "new": "wheels",
                            "why": "remove unsupported durable attributes",
                        }
                    ]
                },
                _meta(),
            ),
            (
                {"findings": [], "fidelity_clean": True},
                _meta(),
            ),
        ]
        prefix = "Title\n\nThe truck had big black wheels. "
        filler = "word " * 480
        story = (prefix + filler).strip()
        tr_story = ("Başlık\n\n" + "kelime " * 480).strip()
        mock_openrouter.side_effect = [
            (
                story,
                _body(),
                {"temperature": 0.72, "max_tokens": None, "reasoning": None},
            ),
            (
                tr_story,
                _body(),
                {"temperature": 0.2, "max_tokens": None, "reasoning": None},
            ),
        ]
        local = {
            "family": "canon_integrity",
            "severity": "serious",
            "repair_scope": "local",
            "span_ids": ["S001"],
            "reason": "unsupported durable wheel attributes",
        }
        mock_audit.side_effect = [
            ([local], _meta()),
            ([], _meta()),
            ([], _meta()),
            ([], _meta()),
        ]

        result = run_storyforge(request, api_key="test")

        self.assertEqual(result.status, "publication_ready")
        self.assertTrue(result.publication_ready)
        self.assertNotIn("big black wheels", result.english_story or "")
        self.assertEqual(mock_openrouter.call_count, 2)
        self.assertEqual(mock_structured.call_count, 4)


if __name__ == "__main__":
    unittest.main()
