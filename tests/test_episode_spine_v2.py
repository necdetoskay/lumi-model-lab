from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from src.episode_spine_v2_contract import EpisodeSpineGateV2, EpisodeSpineV2
from src.episode_spine_v2_generate import generate


SPINE = Path(
    "data/specifications/saga_lab/age12_shattered_meridian_gate_b_approved_v1.json"
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
PREMISE = Path(
    "data/specifications/story_lab/age12_shattered_meridian_episode1_premise_approved_v1.json"
)
ARCHITECT_PROMPT = Path("prompts/episode_spine_architect_v2.md")
GATE_PROMPT = Path("prompts/episode_spine_gate_v2.md")


def _beat(
    key: str,
    phase: str,
    deps: list[str],
    location: str,
    purpose: str,
) -> dict:
    return {
        "key": key,
        "phase": phase,
        "purpose": purpose,
        "location_ref": location,
        "character_action": f"Deniz takes a deliberate action for {key}.",
        "external_event": f"The world creates a concrete response during {key}.",
        "new_information": f"Evidence changes Deniz's understanding during {key}.",
        "causal_dependency_keys": deps,
        "escalation_delta": f"Pressure changes materially during {key}.",
        "state_change": f"A durable story state changes during {key}.",
        "payoff_contribution": f"This beat contributes to the payoff through {key}.",
    }


def _spine_payload() -> dict:
    return {
        "schema": "episode-spine.v2",
        "premise_key": "beacon_drift_first_log",
        "title": "The Angle That Wouldn't Match",
        "exact_age": 12,
        "session": "STANDARD",
        "target_words_min": 1600,
        "target_words_max": 2500,
        "episode_role": "MAIN_SAGA_ENTRY",
        "story_promise": (
            "Deniz earns credible evidence that the chart and beacon disagree "
            "without claiming more than the measurements support."
        ),
        "protagonist_role": (
            "Apprentice surveyor responsible for a supervised calibration check."
        ),
        "immediate_objective": (
            "Determine whether the strange reading deserves formal logging "
            "before the tide window closes."
        ),
        "central_question": (
            "Is the discrepancy real, and can Deniz prove enough without overclaiming?"
        ),
        "stakes": (
            "A weak claim can cost trust while silence can lose the anomaly "
            "for another season."
        ),
        "constraints": [
            "limited tide window",
            "supervised instrument access",
            "mentor demands reproducible evidence",
        ],
        "opening_hook": "A routine calibration gives Deniz an impossible angle.",
        "beats": [
            _beat(
                "b1_impossible_angle",
                "HOOK",
                [],
                "beacon_ridge",
                "Expose the impossible reading.",
            ),
            _beat(
                "b2_check_instrument",
                "ORIENT",
                ["b1_impossible_angle"],
                "beacon_ridge",
                "Establish Deniz's method and field role.",
            ),
            _beat(
                "b3_tide_window_closes",
                "COMPLICATION",
                ["b2_check_instrument"],
                "beacon_ridge",
                "Create the time constraint.",
            ),
            _beat(
                "b4_compare_harbor_record",
                "INVESTIGATION",
                ["b3_tide_window_closes"],
                "meridian_harbor",
                "Seek an independent comparison source.",
            ),
            _beat(
                "b5_easy_explanation_breaks",
                "REVERSAL",
                ["b4_compare_harbor_record"],
                "meridian_harbor",
                "Invalidate the simplest instrument-error explanation.",
            ),
            _beat(
                "b6_access_pressure",
                "ESCALATION",
                ["b5_easy_explanation_breaks"],
                "beacon_ridge",
                "Tighten access and evidence pressure.",
            ),
            _beat(
                "b7_report_or_retest",
                "DECISION",
                ["b6_access_pressure"],
                "beacon_ridge",
                "Force a credible evidence trade-off.",
            ),
            _beat(
                "b8_final_measurement",
                "CLIMAX",
                ["b7_report_or_retest"],
                "beacon_ridge",
                "Use prior method and evidence to resolve the local uncertainty.",
            ),
            _beat(
                "b9_formal_log",
                "PAYOFF",
                ["b8_final_measurement"],
                "meridian_harbor",
                "Deliver a local payoff and preserve evidence.",
            ),
        ],
        "escalation_ladder": [
            "One strange reading could be ordinary instrument error.",
            "Independent comparison makes the easy explanation insufficient.",
            "The tide and access window creates a real cost to gathering more proof.",
            "Deniz must choose how much evidence is enough to justify a formal report.",
        ],
        "reversal": (
            "The comparison source does not confirm the expected instrument fault; "
            "instead it makes the mismatch look reproducible under the same tide band."
        ),
        "decision_point": {
            "pressure": (
                "The measurement window is closing and Deniz does not yet know "
                "whether one more test will strengthen the case or erase the chance to report it."
            ),
            "options": [
                "Log the anomaly now with explicit uncertainty and preserve the evidence.",
                "Use the remaining window for one more controlled retest before reporting.",
            ],
            "what_is_unknown": (
                "Whether a final retest will corroborate the drift before the tide changes."
            ),
            "outcome_uncommitted": True,
        },
        "climax": (
            "Deniz applies the calibration method established earlier, cross-checks "
            "the result against the independent reference, and earns enough evidence "
            "to distinguish a real discrepancy from simple instrument error."
        ),
        "local_payoff": (
            "The anomaly receives a provisional formal log entry and Deniz's method "
            "is taken seriously enough to justify future investigation."
        ),
        "forward_hook": (
            "The local mismatch is now real enough to ask whether other beacons show "
            "the same pattern, without answering why."
        ),
        "persistent_outcome_candidates": [
            {
                "type": "KNOWLEDGE",
                "description": "A dated, reproducible beacon discrepancy exists.",
                "commit_condition": (
                    "The delivered story must show a valid measurement and independent corroboration."
                ),
            },
            {
                "type": "RELATIONSHIP",
                "description": "The mentor's trust in Deniz's method may change.",
                "commit_condition": (
                    "The delivered story must show the mentor reacting to Deniz's actual method and evidence."
                ),
            },
            {
                "type": "SAGA_STATE",
                "description": "first_discrepancy_logged may become complete.",
                "commit_condition": (
                    "StoryOutcome confirms the discrepancy was formally logged with reproducible evidence."
                ),
            },
        ],
        "saga_progression": {
            "intended_milestone_keys": ["first_discrepancy_logged"],
            "commit_only_if_earned": True,
            "completion_evidence": [
                "A beacon reading differs materially from the official expectation.",
                "Deniz performs a methodologically credible check against simple instrument error.",
                "The anomaly is preserved in a durable field or harbor record.",
            ],
        },
        "anti_repetition_signature": {
            "core_problem_shape": (
                "scientific field anomaly under evidence and credibility pressure"
            ),
            "primary_activity": (
                "calibration, independent comparison, controlled retest, reporting"
            ),
            "main_location_pattern": "Beacon Ridge fieldwork linked to Meridian Harbor records",
            "climax_shape": "evidence synthesis under a closing measurement window",
            "distinct_from_recent_episodes_because": (
                "This is the first Episode and establishes the cartography evidence loop."
            ),
        },
        "writer_rules": [
            "Do not reveal the cause of the beacon drift.",
            "Do not reveal who built the ancient markers.",
            "Do not resolve the father's fate.",
            "Do not make the mentor secretly guilty of suppressing evidence.",
            "Do not mark the Saga milestone complete unless the prose earns every completion-evidence condition.",
            "Keep the climax dependent on evidence already introduced before the climax.",
        ],
    }


DIMENSIONS = [
    "AGE_MATURITY",
    "CAUSAL_COHERENCE",
    "ESCALATION",
    "AGENCY",
    "REVERSAL_QUALITY",
    "CLIMAX_PAYOFF",
    "WORLD_IMMERSION",
    "SAGA_ALIGNMENT",
    "LOCAL_SATISFACTION",
    "WRITER_EXECUTABILITY",
    "REPETITION_SAFETY",
]


def _gate_payload(decision: str = "ACCEPT", score: int = 4) -> dict:
    return {
        "schema": "episode-spine-gate.v2",
        "dimensions": [
            {
                "name": name,
                "score": score,
                "blocking_failure": False,
                "reason": f"{name} meets the qualification bar.",
            }
            for name in DIMENSIONS
        ],
        "decision": decision,
        "blocking_reasons": [],
        "decision_reason": "The spine is executable and causally complete.",
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


class EpisodeSpineContractTests(unittest.TestCase):
    def test_valid_spine_passes(self):
        spine = EpisodeSpineV2.model_validate(_spine_payload())
        self.assertEqual(len(spine.beats), 9)
        self.assertEqual(
            spine.saga_progression.intended_milestone_keys,
            ["first_discrepancy_logged"],
        )

    def test_rejects_too_few_beats(self):
        payload = _spine_payload()
        payload["beats"] = payload["beats"][:7]
        with self.assertRaisesRegex(ValidationError, "8-12 beats"):
            EpisodeSpineV2.model_validate(payload)

    def test_rejects_future_or_unknown_causal_dependency(self):
        payload = _spine_payload()
        payload["beats"][2]["causal_dependency_keys"] = ["b9_formal_log"]
        with self.assertRaisesRegex(
            ValidationError,
            "dependencies must reference earlier beats",
        ):
            EpisodeSpineV2.model_validate(payload)

    def test_accept_gate_cannot_bypass_protected_threshold(self):
        payload = _gate_payload()
        for row in payload["dimensions"]:
            if row["name"] == "CAUSAL_COHERENCE":
                row["score"] = 2
        with self.assertRaisesRegex(ValidationError, "protected thresholds"):
            EpisodeSpineGateV2.model_validate(payload)

    def test_blocking_gate_failure_requires_replan(self):
        payload = _gate_payload()
        payload["dimensions"][0]["blocking_failure"] = True
        with self.assertRaisesRegex(ValidationError, "requires REPLAN"):
            EpisodeSpineGateV2.model_validate(payload)


class EpisodeSpineGeneratorTests(unittest.TestCase):
    @patch(
        "src.episode_spine_v2_generate.runtime_profile_identity",
        side_effect=lambda model: {"model_id": model},
    )
    @patch(
        "src.episode_spine_v2_generate.require_qualification_runtime_profile",
        return_value={"qualification": {"ready": True}},
    )
    @patch(
        "src.episode_spine_v2_generate.call_structured_json_with_retry"
    )
    def test_generator_stops_at_human_review(
        self,
        mock_call,
        _mock_require,
        _mock_identity,
    ):
        mock_call.side_effect = [
            (
                _spine_payload(),
                _body(0.06),
                {
                    "temperature": 0.35,
                    "max_tokens": 10000,
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
                    "max_tokens": 6000,
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
                premise_path=PREMISE,
                architect_prompt_path=ARCHITECT_PROMPT,
                gate_prompt_path=GATE_PROMPT,
                out_path=out,
                architect_model_override="architect/model",
                gate_model_override="gate/model",
                api_key="test-key",
            )
            persisted = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "awaiting_human_review")
        self.assertFalse(result["episode_writer_authorized"])
        self.assertEqual(result["gate"]["decision"], "ACCEPT")
        self.assertAlmostEqual(result["total_cost_usd"], 0.08)
        self.assertIsNone(result["human_review"]["verdict"])
        self.assertFalse(result["human_review"]["episode_writer_authorized"])
        self.assertEqual(persisted["status"], "awaiting_human_review")

        architect_input = json.loads(
            mock_call.call_args_list[0].kwargs["user_prompt"]
        )
        self.assertEqual(
            architect_input["required_intended_milestone_keys"],
            ["first_discrepancy_logged"],
        )
        self.assertEqual(
            architect_input["allowed_location_refs"],
            ["beacon_ridge", "meridian_harbor"],
        )
        self.assertEqual(
            architect_input["required_session"]["target_words_min"],
            1600,
        )
        self.assertEqual(
            architect_input["required_session"]["target_words_max"],
            2500,
        )

    @patch(
        "src.episode_spine_v2_generate.runtime_profile_identity",
        side_effect=lambda model: {"model_id": model},
    )
    @patch(
        "src.episode_spine_v2_generate.require_qualification_runtime_profile",
        return_value={"qualification": {"ready": True}},
    )
    @patch(
        "src.episode_spine_v2_generate.call_structured_json_with_retry"
    )
    def test_generator_rejects_location_outside_approved_premise(
        self,
        mock_call,
        _mock_require,
        _mock_identity,
    ):
        payload = _spine_payload()
        payload["beats"][3]["location_ref"] = "tide_observatory"
        mock_call.return_value = (
            payload,
            _body(0.06),
            {
                "temperature": 0.35,
                "max_tokens": 10000,
                "reasoning": {"effort": "low"},
                "response_format": {"type": "json_object"},
            },
            [],
        )

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "result.json"
            with self.assertRaisesRegex(
                RuntimeError,
                "Episode Spine Architect failed contract validation",
            ):
                generate(
                    spine_path=SPINE,
                    reader_path=READER,
                    fixture_path=FIXTURE,
                    state_path=STATE,
                    premise_path=PREMISE,
                    architect_prompt_path=ARCHITECT_PROMPT,
                    gate_prompt_path=GATE_PROMPT,
                    out_path=out,
                    architect_model_override="architect/model",
                    gate_model_override="gate/model",
                    api_key="test-key",
                )
            persisted = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(persisted["status"], "architect_contract_rejected")
        self.assertIn(
            "location outside approved premise",
            persisted["contract_error"]["message"],
        )


if __name__ == "__main__":
    unittest.main()
