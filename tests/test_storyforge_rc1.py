from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from src.storyforge.contracts import StoryForgeRequest
from src.storyforge.runtime import StoryForgeAuditContractError, StoryForgeTraceError, _audit_story, _normalize_audit, _run_traced_stage, run_storyforge
from src.story_defect_detection import segment_story


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


class StorySourceMapTests(unittest.TestCase):
    def test_segment_story_preserves_sentence_ids_and_adds_paragraph_offsets(self):
        story = "Title. First sentence.\n\nSecond paragraph has a problem."
        segments = segment_story(story)

        self.assertEqual([row["id"] for row in segments], ["S001", "S002", "S003"])
        self.assertEqual(segments[0]["paragraph_id"], "P001")
        self.assertEqual(segments[1]["paragraph_id"], "P001")
        self.assertEqual(segments[2]["paragraph_id"], "P002")

        for row in segments:
            self.assertEqual(story[row["char_start"]:row["char_end"]], row["text"])

        self.assertEqual(segments[2]["text"], "Second paragraph has a problem.")


class StoryForgeStageTraceTests(unittest.TestCase):
    def test_common_stage_trace_preserves_prior_artifacts_on_failure(self):
        evidence = {
            "cost_usd": {"planner": 0.01},
            "latency_seconds": {"planner": 1.2},
            "trace_events": [],
        }
        artifacts = {
            "profile_id": "test-profile",
            "request_id": "test-request",
            "context_packet": {"facts": ["x"]},
            "plan": {"premise": "kept"},
            "english_story": "Story already generated.",
            "turkish_story": None,
        }

        def explode():
            raise RuntimeError("boom")

        with self.assertRaises(StoryForgeTraceError) as caught:
            _run_traced_stage(
                stage="secondary_audit",
                evidence=evidence,
                artifacts=artifacts,
                fn=explode,
            )

        trace = caught.exception.trace
        self.assertEqual(trace["stage"], "secondary_audit")
        self.assertEqual(trace["english_story"], "Story already generated.")
        self.assertEqual(trace["plan"]["premise"], "kept")
        self.assertEqual(trace["evidence"]["cost_usd"]["planner"], 0.01)
        self.assertEqual(trace["evidence"]["trace_events"][-1]["status"], "failed")
        self.assertEqual(trace["evidence"]["trace_events"][-1]["error"]["type"], "RuntimeError")

    @patch("src.storyforge.runtime.call_openrouter")
    @patch("src.storyforge.runtime._structured_call")
    @patch("src.storyforge.runtime._build_context")
    def test_primary_audit_contract_failure_trace_is_json_serializable(
        self,
        mock_context,
        mock_structured,
        mock_openrouter,
    ):
        request = StoryForgeRequest.model_validate(_request_dict())
        mock_context.return_value = (
            _packet(),
            {"selected_enrichment_ids": ["inventory.blue_chalk"]},
        )
        invalid_audit = {
            "evaluations": [
                {
                    "family": family,
                    "present": family == "canon_integrity",
                    "severity": "minor" if family == "canon_integrity" else None,
                    "repair_scope": "local" if family == "canon_integrity" else None,
                    "span_ids": ["S001"] if family == "canon_integrity" else [],
                    "exact_quote": "Title." if family == "canon_integrity" else None,
                    "reason": "test contract mismatch" if family == "canon_integrity" else "",
                }
                for family in (
                    "physical_feasibility", "causal_logic", "state_continuity",
                    "epistemic_order", "spatial_consistency", "temporal_consistency",
                    "response_causality", "closure_integrity", "canon_integrity",
                )
            ]
        }
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
            (invalid_audit, _meta()),
        ]
        story = ("Title. " + "word " * 490).strip()
        mock_openrouter.return_value = (
            story,
            _body(),
            {"temperature": 0.72, "max_tokens": None, "reasoning": None},
        )

        with self.assertRaises(StoryForgeTraceError) as caught:
            run_storyforge(request, api_key="test")

        serialized = json.dumps(caught.exception.trace, ensure_ascii=False)
        self.assertIn('"stage": "primary_audit"', serialized)
        self.assertIn("Invalid blocking severity: canon_integrity:minor", serialized)
        self.assertIn("Title.", serialized)


class StoryForgeExactLocatorTests(unittest.TestCase):
    def test_valid_finding_resolves_exact_quote_to_sentence_paragraph_and_offsets(self):
        story = "Title. First sentence.\n\nProblem sentence here."
        segments = segment_story(story)
        raw = {
            "evaluations": [
                {
                    "family": family,
                    "present": family == "causal_logic",
                    "severity": "serious" if family == "causal_logic" else None,
                    "repair_scope": "local" if family == "causal_logic" else None,
                    "span_ids": ["S003"] if family == "causal_logic" else [],
                    "exact_quote": "Problem sentence" if family == "causal_logic" else None,
                    "reason": "The sentence contains the causal defect." if family == "causal_logic" else "",
                }
                for family in (
                    "physical_feasibility", "causal_logic", "state_continuity",
                    "epistemic_order", "spatial_consistency", "temporal_consistency",
                    "response_causality", "closure_integrity", "canon_integrity",
                )
            ]
        }

        findings = _normalize_audit(raw, segments)
        self.assertEqual(len(findings), 1)
        locator = findings[0]["source_locator"]
        self.assertEqual(locator["sentence_id"], "S003")
        self.assertEqual(locator["paragraph_id"], "P002")
        self.assertEqual(locator["sentence_word_start"], 1)
        self.assertEqual(locator["sentence_word_end"], 2)
        self.assertEqual(
            story[locator["char_start"]:locator["char_end"]],
            "Problem sentence",
        )


class StoryForgeAuditTraceTests(unittest.TestCase):
    @patch("src.storyforge.runtime._structured_call")
    def test_invalid_audit_contract_preserves_raw_payload_and_exact_segments(self, mock_structured):
        request = StoryForgeRequest.model_validate(_request_dict())
        raw = {
            "evaluations": [
                {
                    "family": family,
                    "present": family == "spatial_consistency",
                    "severity": "major" if family == "spatial_consistency" else None,
                    "repair_scope": "local" if family == "spatial_consistency" else None,
                    "span_ids": ["S002"] if family == "spatial_consistency" else [],
                    "exact_quote": "First sentence." if family == "spatial_consistency" else None,
                    "reason": "The object changes location without a transition." if family == "spatial_consistency" else "",
                }
                for family in (
                    "physical_feasibility", "causal_logic", "state_continuity",
                    "epistemic_order", "spatial_consistency", "temporal_consistency",
                    "response_causality", "closure_integrity", "canon_integrity",
                )
            ]
        }
        mock_structured.return_value = (raw, _meta())

        with self.assertRaises(StoryForgeAuditContractError) as caught:
            _audit_story(
                api_key="test",
                model="auditor",
                request=request,
                packet=_packet(),
                plan=_plan(),
                story="Title. First sentence. Problem sentence here.",
                seed=1,
            )

        trace = caught.exception.trace
        self.assertEqual(trace["raw_audit_payload"], raw)
        self.assertEqual(trace["contract_error"], "Invalid blocking severity: spatial_consistency:major")
        by_id = {row["id"]: row["text"] for row in trace["segments"]}
        self.assertEqual(by_id["S002"], "First sentence.")
        self.assertEqual(trace["segments"][1]["paragraph_id"], "P001")
        self.assertEqual(trace["segments"][1]["char_start"], 7)
        self.assertIn("model_meta", trace)


if __name__ == "__main__":
    unittest.main()
