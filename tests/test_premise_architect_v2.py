from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from src.premise_architect_v2_contract import (
    PremiseCandidateBatchV2,
    PremiseCandidateEvaluation,
    PremiseGateV2,
    PremiseLabStateV1,
    build_premise_gate_protected_context,
    build_reveal_safe_premise_projection,
)
from src.premise_architect_v2_generate import generate
from src.reader_profile_v2 import ReaderDevelopmentProfileV2
from src.saga_blueprint_contract import NarrativeFixture
from src.saga_spine_v2_contract import CharacterSagaSpineV2


SPINE = Path(
    "data/specifications/saga_lab/age12_shattered_meridian_full_spine_v1.json"
)
READER = Path(
    "data/specifications/reader_profiles/age12_adventure_v2.json"
)
FIXTURE = Path(
    "data/specifications/saga_lab/age12_shattered_meridian_fixture_v2.json"
)
STATE = Path(
    "data/specifications/story_lab/age12_shattered_meridian_initial_state_v1.json"
)
ARCHITECT_PROMPT = Path("prompts/premise_architect_v2.md")
GATE_PROMPT = Path("prompts/premise_gate_v2.md")


def _candidate(
    *,
    key: str,
    title: str,
    focus: str,
    refs: list[str],
    location_refs: list[str],
    differentiation: str,
    saga_progression_required: bool,
) -> dict:
    return {
        "key": key,
        "title": title,
        "location_refs": location_refs,
        "primary_focus": focus,
        "target_refs": refs,
        "differentiation_key": differentiation,
        "logline": "Deniz faces a world-specific problem that requires evidence, judgment, and action.",
        "protagonist_role": "apprentice cartographer responsible for making a credible field judgment",
        "immediate_objective": "Establish what is actually happening before acting on incomplete evidence.",
        "inciting_event": "A trusted navigation assumption fails under conditions where it should have held.",
        "central_problem": "The evidence conflicts and Deniz cannot safely treat either source as automatically correct.",
        "wonder_or_discovery": "A familiar part of the Shattered Meridian behaves according to a deeper pattern Deniz has never measured before.",
        "stakes": "A wrong conclusion can damage trust, access, or route safety.",
        "constraints": [
            "Time and access are limited.",
            "Deniz must distinguish observation from assumption."
        ],
        "meaningful_choice_pressure": "Deniz must decide which evidence to pursue first without knowing which path will prove more reliable.",
        "mystery_or_forward_question": "Why does the world disagree with the chart here, and is the cause local or systemic?",
        "local_payoff": "Deniz earns a concrete new understanding or capability by resolving the Episode's immediate uncertainty.",
        "persistent_outcomes_possible": [
            "new verified knowledge",
            "changed relationship trust",
            "new access or opportunity"
        ],
        "world_specific_elements": [
            "Meridian Harbor navigation culture",
            "Shattered Meridian beacon/tide systems"
        ],
        "saga_progression_required": saga_progression_required,
        "expected_session": "STANDARD"
    }


def _batch_payload() -> dict:
    return {
        "schema": "premise-candidate-batch.v2",
        "candidates": [
            _candidate(
                key="premise_drift_test",
                title="The Reading That Refuses to Fail",
                focus="MAIN_SAGA",
                refs=["first_discrepancy_logged"],
                location_refs=["beacon_ridge"],
                differentiation="scientific falsification under field pressure",
                saga_progression_required=True,
            ),
            _candidate(
                key="premise_friend_rivalry",
                title="Two Ways to Measure a Harbor",
                focus="RELATIONSHIP",
                refs=["friend_expedition_rivalry"],
                location_refs=["meridian_harbor"],
                differentiation="friendly methodological rivalry with shared consequence",
                saga_progression_required=False,
            ),
            _candidate(
                key="premise_tide_window",
                title="The Harbor That Moves at Low Tide",
                focus="WORLD_EXPLORATION",
                refs=["WORLD_EXPLORATION"],
                location_refs=["meridian_harbor"],
                differentiation="world exploration driven by harbor tide geometry",
                saga_progression_required=False,
            ),
        ],
    }


DIMENSIONS = [
    "PREMISE_MATURITY",
    "ROLEPLAY_IMMERSION",
    "WONDER_DISCOVERY",
    "AGENCY",
    "STAKES",
    "MYSTERY_CURIOSITY",
    "CAUSAL_POTENTIAL",
    "WORLD_INTEGRATION",
    "PERSISTENT_VALUE",
    "REPETITION_SAFETY",
    "REVEAL_SAFETY",
    "PROGRESSION_INTEGRITY",
]


def _evaluation(candidate_key: str, verdict: str, score: int = 4) -> dict:
    return {
        "candidate_key": candidate_key,
        "dimensions": [
            {
                "name": name,
                "score": score,
                "blocking_failure": False,
                "reason": f"{name} is adequately supported by the premise."
            }
            for name in DIMENSIONS
        ],
        "verdict": verdict,
        "blocking_reasons": [],
    }


def _gate_payload() -> dict:
    return {
        "schema": "premise-gate.v2",
        "evaluations": [
            _evaluation("premise_drift_test", "ACCEPT", 4),
            _evaluation("premise_friend_rivalry", "REJECT", 3),
            _evaluation("premise_tide_window", "ACCEPT", 4),
        ],
        "decision": "ACCEPT",
        "selected_candidate_key": "premise_drift_test",
        "decision_reason": "The selected premise best combines age fit, agency, world integration, and persistent value."
    }


def _body(cost: float) -> dict:
    return {
        "model": "test/model",
        "provider": "test-provider",
        "usage": {
            "prompt_tokens": 1000,
            "completion_tokens": 1200,
            "total_tokens": 2200,
            "completion_tokens_details": {"reasoning_tokens": 100},
            "cost": cost,
        },
    }


class PremiseContextProjectionTests(unittest.TestCase):
    def test_initial_projection_is_reveal_safe_and_only_exposes_eligible_targets(self):
        spine = CharacterSagaSpineV2.model_validate_json(
            SPINE.read_text(encoding="utf-8")
        )
        reader = ReaderDevelopmentProfileV2.model_validate_json(
            READER.read_text(encoding="utf-8")
        )
        fixture = NarrativeFixture.model_validate_json(
            FIXTURE.read_text(encoding="utf-8")
        )
        state = PremiseLabStateV1.model_validate_json(
            STATE.read_text(encoding="utf-8")
        )

        projection = build_reveal_safe_premise_projection(
            spine=spine,
            reader=reader,
            fixture=fixture,
            state=state,
        )

        self.assertEqual(
            [x["key"] for x in projection["eligible_main_saga_milestones"]],
            ["first_discrepancy_logged"],
        )
        self.assertEqual(
            [x["key"] for x in projection["active_side_sagas"]],
            ["friend_expedition_rivalry"],
        )
        access = {
            row["key"]: (row["status"], row["premise_usage"])
            for row in projection["world"]["location_access"]
        }
        self.assertEqual(access["beacon_ridge"], ("AVAILABLE", "FULL"))
        self.assertEqual(access["tide_observatory"], ("KNOWN_LOCKED", "MENTION_ONLY"))
        self.assertEqual(access["outer_mist_line"], ("RUMORED", "FORESHADOW_ONLY"))

        raw = json.dumps(projection, ensure_ascii=False)
        self.assertNotIn("hidden_statement", raw)
        self.assertNotIn('"hidden_truths"', raw)
        self.assertNotIn('"reveal_steps"', raw)
        self.assertNotIn("tide_mechanism", raw)
        self.assertNotIn("fathers_survey_findings", raw)

        protected = build_premise_gate_protected_context(
            spine=spine,
            state=state,
        )
        protected_raw = json.dumps(protected, ensure_ascii=False)
        self.assertIn("hidden_truths", protected)
        self.assertIn("reveal_steps", protected)
        self.assertIn("tide_mechanism", protected_raw)
        self.assertTrue(protected["rules"]["judge_only"])


class PremiseContractTests(unittest.TestCase):
    def test_valid_batch_requires_real_candidate_diversity(self):
        batch = PremiseCandidateBatchV2.model_validate(_batch_payload())
        self.assertEqual(len(batch.candidates), 3)
        self.assertEqual(len({c.primary_focus for c in batch.candidates}), 3)

    def test_rejects_three_cosmetic_variants(self):
        payload = _batch_payload()
        for row in payload["candidates"]:
            row["primary_focus"] = "MAIN_SAGA"
        with self.assertRaisesRegex(ValidationError, "at least two primary focuses"):
            PremiseCandidateBatchV2.model_validate(payload)

    def test_accept_verdict_cannot_bypass_protected_thresholds(self):
        payload = _evaluation("premise_bad", "ACCEPT", 4)
        for row in payload["dimensions"]:
            if row["name"] == "PREMISE_MATURITY":
                row["score"] = 2
        with self.assertRaisesRegex(ValidationError, "protected thresholds"):
            PremiseCandidateEvaluation.model_validate(payload)

    def test_accept_requires_perfect_reveal_and_progression_integrity(self):
        for protected_name in ("REVEAL_SAFETY", "PROGRESSION_INTEGRITY"):
            payload = _evaluation("premise_bad", "ACCEPT", 5)
            for row in payload["dimensions"]:
                if row["name"] == protected_name:
                    row["score"] = 4
            with self.assertRaisesRegex(ValidationError, "protected thresholds"):
                PremiseCandidateEvaluation.model_validate(payload)

    def test_gate_reject_all_cannot_select_candidate(self):
        payload = _gate_payload()
        payload["decision"] = "REJECT_ALL"
        with self.assertRaisesRegex(ValidationError, "cannot select"):
            PremiseGateV2.model_validate(payload)


class PremiseGeneratorTests(unittest.TestCase):
    @patch(
        "src.premise_architect_v2_generate.runtime_profile_identity",
        side_effect=lambda model: {"model_id": model},
    )
    @patch(
        "src.premise_architect_v2_generate.require_qualification_runtime_profile",
        return_value={"qualification": {"ready": True}},
    )
    @patch(
        "src.premise_architect_v2_generate.call_structured_json_with_retry"
    )
    def test_generator_stops_at_human_review_after_architect_and_gate(
        self,
        mock_call,
        _mock_require,
        _mock_identity,
    ):
        mock_call.side_effect = [
            (
                _batch_payload(),
                _body(0.05),
                {
                    "temperature": 0.55,
                    "max_tokens": 9000,
                    "reasoning": {"effort": "low"},
                    "response_format": {"type": "json_object"},
                },
                [],
            ),
            (
                _gate_payload(),
                _body(0.02),
                {
                    "temperature": 0.10,
                    "max_tokens": 6500,
                    "reasoning": {"effort": "low"},
                    "response_format": {"type": "json_object"},
                },
                [],
            ),
        ]

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "result.json"
            result = generate(
                spine_path=SPINE,
                reader_path=READER,
                fixture_path=FIXTURE,
                state_path=STATE,
                architect_prompt_path=ARCHITECT_PROMPT,
                gate_prompt_path=GATE_PROMPT,
                out_path=out,
                architect_model_override="architect/model",
                gate_model_override="gate/model",
                api_key="test-key",
            )
            persisted = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "awaiting_human_review")
        self.assertFalse(result["episode_spine_authorized"])
        self.assertEqual(result["gate"]["decision"], "ACCEPT")
        self.assertEqual(
            result["gate"]["selected_candidate_key"],
            "premise_drift_test",
        )
        self.assertAlmostEqual(result["total_cost_usd"], 0.07)
        self.assertIsNone(result["human_review"]["verdict"])
        self.assertEqual(persisted["status"], "awaiting_human_review")

        architect_input = json.loads(
            mock_call.call_args_list[0].kwargs["user_prompt"]
        )
        self.assertNotIn("protected_judge_context", architect_input)
        self.assertEqual(
            architect_input["available_target_refs"],
            [
                "SAGA_FREE",
                "WORLD_EXPLORATION",
                "first_discrepancy_logged",
                "friend_expedition_rivalry",
            ],
        )
        self.assertEqual(
            architect_input["available_primary_location_refs"],
            ["beacon_ridge", "meridian_harbor"],
        )
        self.assertTrue(
            architect_input["premise_context"]["rules"][
                "hidden_truths_not_available_to_premise_architect"
            ]
        )

        gate_input = json.loads(
            mock_call.call_args_list[1].kwargs["user_prompt"]
        )
        self.assertIn("protected_judge_context", gate_input)
        self.assertTrue(
            gate_input["protected_judge_context"]["rules"]["judge_only"]
        )
        self.assertIn(
            "hidden_truths",
            gate_input["protected_judge_context"],
        )



    @patch(
        "src.premise_architect_v2_generate.runtime_profile_identity",
        side_effect=lambda model: {"model_id": model},
    )
    @patch(
        "src.premise_architect_v2_generate.require_qualification_runtime_profile",
        return_value={"qualification": {"ready": True}},
    )
    @patch(
        "src.premise_architect_v2_generate.call_structured_json_with_retry"
    )
    def test_generator_rejects_candidate_that_uses_locked_location(
        self,
        mock_call,
        _mock_require,
        _mock_identity,
    ):
        batch = _batch_payload()
        batch["candidates"][2]["location_refs"] = ["tide_observatory"]
        mock_call.return_value = (
            batch,
            _body(0.05),
            {
                "temperature": 0.55,
                "max_tokens": 9000,
                "reasoning": {"effort": "low"},
                "response_format": {"type": "json_object"},
            },
            [],
        )

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "result.json"
            with self.assertRaisesRegex(
                RuntimeError,
                "Premise Architect output failed contract validation",
            ):
                generate(
                    spine_path=SPINE,
                    reader_path=READER,
                    fixture_path=FIXTURE,
                    state_path=STATE,
                    architect_prompt_path=ARCHITECT_PROMPT,
                    gate_prompt_path=GATE_PROMPT,
                    out_path=out,
                    architect_model_override="architect/model",
                    gate_model_override="gate/model",
                    api_key="test-key",
                )
            persisted = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(persisted["status"], "architect_contract_rejected")
        self.assertIn("locked/non-FULL locations", persisted["contract_error"]["message"])

if __name__ == "__main__":
    unittest.main()
