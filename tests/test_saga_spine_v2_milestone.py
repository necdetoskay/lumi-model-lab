from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.saga_spine_v2_milestone_contract import (
    SagaMilestoneExpansionV2,
    merge_expansion_with_skeleton,
)
from src.saga_spine_v2_milestone_generate import generate
from src.saga_spine_v2_skeleton_contract import CharacterSagaSkeletonV2


SKELETON = Path(
    "data/specifications/saga_lab/age12_shattered_meridian_gate_a_approved_v1.json"
)
PROMPT = Path("prompts/saga_milestone_architect_v2.md")

REVIEWED_DRAFT = Path(
    "data/specifications/saga_lab/age12_shattered_meridian_gate_b_reviewed_v1.json"
)
REVISION = Path(
    "data/specifications/saga_lab/age12_shattered_meridian_gate_b_revision_v1.json"
)


def _load_skeleton() -> CharacterSagaSkeletonV2:
    return CharacterSagaSkeletonV2.model_validate_json(
        SKELETON.read_text(encoding="utf-8")
    )


def _expansion_payload() -> dict:
    skeleton = _load_skeleton()
    milestones = []
    anchor_orders = []

    entry_by_type = {
        "DISCOVERY": ["EXPLORATION", "LOCATION"],
        "EVIDENCE": ["DOCUMENT", "EXPLORATION"],
        "ACCESS": ["NPC", "LOCATION"],
        "RELATIONSHIP_SHIFT": ["RELATIONSHIP", "NPC"],
        "CONVERGENCE": ["DOCUMENT", "CONSEQUENCE"],
        "REVELATION": ["DOCUMENT", "WORLD_EVENT"],
        "DECISION": ["CONSEQUENCE", "RELATIONSHIP"],
        "CONSEQUENCE": ["WORLD_EVENT", "CONSEQUENCE"],
    }

    for anchor in skeleton.main_saga.anchors:
        keys = []
        modes = list(anchor.desired_progression_modes)
        while len(modes) < anchor.milestone_target_count:
            modes.append(modes[-1])
        for index in range(anchor.milestone_target_count):
            key = f"{anchor.key}_m{index + 1}"
            keys.append(key)
            mode = modes[index]
            milestones.append(
                {
                    "key": key,
                    "anchor_key": anchor.key,
                    "type": mode,
                    "summary": (
                        f"A meaningful {mode.lower()} state is established for "
                        f"{anchor.title} without fixing an Episode."
                    ),
                    "state_condition": (
                        f"The durable {mode.lower()} condition for {anchor.key} "
                        "is verifiably true."
                    ),
                    "required_for_anchor": index == anchor.milestone_target_count - 1,
                    "possible_entry_vectors": entry_by_type.get(
                        mode, ["EXPLORATION"]
                    ),
                    "reveal_keys": [],
                    "consequence_options": [
                        "May change which evidence route is credible.",
                        "May alter access, reputation, or future opportunity."
                    ],
                    "skippable_if_alternate_route_satisfies_anchor": (
                        not anchor.required_for_resolution
                    ),
                }
            )
        anchor_orders.append(
            {
                "anchor_key": anchor.key,
                "ordered_milestone_keys": keys,
            }
        )

    return {
        "schema": "saga-milestone-expansion.v2",
        "source_saga_key": skeleton.main_saga.key,
        "milestones": milestones,
        "anchor_orders": anchor_orders,
        "reveal_bindings": [
            {
                "reveal_key": "reveal_drift_pattern",
                "milestone_keys": ["noticing_the_drift_m2"],
            },
            {
                "reveal_key": "reveal_marker_age",
                "milestone_keys": ["drowned_causeway_route_m2"],
            },
            {
                "reveal_key": "reveal_tide_mechanism_confirmed",
                "milestone_keys": ["observatory_access_m3"],
            },
            {
                "reveal_key": "reveal_fathers_notes_fragment",
                "milestone_keys": ["beacon_ridge_route_m2"],
            },
        ],
        "resolution_milestone_keys": ["true_cause_confronted_m3"],
    }


def _body() -> dict:
    return {
        "model": "anthropic/claude-sonnet-5",
        "provider": "test-provider",
        "usage": {
            "prompt_tokens": 1200,
            "completion_tokens": 1800,
            "total_tokens": 3000,
            "completion_tokens_details": {"reasoning_tokens": 200},
            "cost": 0.08,
        },
    }


class SagaMilestoneExpansionContractTests(unittest.TestCase):
    def test_valid_expansion_merges_to_full_spine(self):
        skeleton = _load_skeleton()
        expansion = SagaMilestoneExpansionV2.model_validate(_expansion_payload())
        full = merge_expansion_with_skeleton(skeleton, expansion)

        self.assertEqual(full.main_saga.goal, skeleton.main_saga.goal)
        self.assertEqual(len(full.main_saga.milestones), 15)
        self.assertEqual(len(full.main_saga.anchors), 5)
        self.assertEqual(
            full.main_saga.resolution_milestone_keys,
            ["true_cause_confronted_m3"],
        )
        self.assertEqual(
            full.main_saga.entry_anchor_keys,
            ["noticing_the_drift"],
        )

    def test_rejects_missing_desired_progression_mode(self):
        payload = _expansion_payload()
        for row in payload["milestones"]:
            if row["anchor_key"] == "beacon_ridge_route":
                row["type"] = "EVIDENCE"
        skeleton = _load_skeleton()
        expansion = SagaMilestoneExpansionV2.model_validate(payload)
        with self.assertRaisesRegex(ValueError, "missing desired progression modes"):
            merge_expansion_with_skeleton(skeleton, expansion)

    def test_rejects_reveal_binding_outside_approved_anchor(self):
        payload = _expansion_payload()
        payload["reveal_bindings"][1]["milestone_keys"] = [
            "beacon_ridge_route_m1"
        ]
        skeleton = _load_skeleton()
        expansion = SagaMilestoneExpansionV2.model_validate(payload)
        with self.assertRaisesRegex(ValueError, "outside approved reveal anchors"):
            merge_expansion_with_skeleton(skeleton, expansion)

    def test_rejects_wrong_anchor_milestone_count(self):
        payload = _expansion_payload()
        payload["anchor_orders"][0]["ordered_milestone_keys"].pop()
        with self.assertRaisesRegex(ValueError, "cover every milestone exactly once"):
            SagaMilestoneExpansionV2.model_validate(payload)


class SagaMilestoneExpansionGeneratorTests(unittest.TestCase):
    @patch(
        "src.saga_spine_v2_milestone_generate.runtime_profile_identity",
        return_value={"model_id": "anthropic/claude-sonnet-5"},
    )
    @patch(
        "src.saga_spine_v2_milestone_generate.require_qualification_runtime_profile",
        return_value={"qualification": {"ready": True}},
    )
    @patch(
        "src.saga_spine_v2_milestone_generate.call_structured_json_with_retry"
    )
    def test_generator_stops_at_human_review(
        self,
        mock_call,
        _mock_require,
        _mock_identity,
    ):
        mock_call.return_value = (
            _expansion_payload(),
            _body(),
            {
                "temperature": 0.30,
                "max_tokens": 12000,
                "reasoning": {"effort": "low", "exclude": True},
                "response_format": {"type": "json_object"},
            },
            [],
        )

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "result.json"
            result = generate(
                skeleton_path=SKELETON,
                prompt_path=PROMPT,
                out_path=out,
                model_override="anthropic/claude-sonnet-5",
                api_key="test-key",
            )
            persisted = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "awaiting_human_review")
        self.assertFalse(result["episode_generation_authorized"])
        self.assertIsNone(result["human_review"]["verdict"])
        self.assertEqual(len(result["full_spine_candidate"]["main_saga"]["milestones"]), 15)
        self.assertEqual(
            result["full_spine_candidate"]["main_saga"]["goal"],
            _load_skeleton().main_saga.goal,
        )
        request_payload = json.loads(mock_call.call_args.kwargs["user_prompt"])
        self.assertIn("approved_skeleton", request_payload)
        self.assertIn("output_contract", request_payload)
        self.assertTrue(
            request_payload["qualification_rules"]["approved_gate_a_must_remain_unchanged"]
        )

        self.assertIsNone(request_payload["previous_reviewed_expansion"])
        self.assertIsNone(request_payload["human_revision_directives"])



    @patch(
        "src.saga_spine_v2_milestone_generate.runtime_profile_identity",
        return_value={"model_id": "anthropic/claude-sonnet-5"},
    )
    @patch(
        "src.saga_spine_v2_milestone_generate.require_qualification_runtime_profile",
        return_value={"qualification": {"ready": True}},
    )
    @patch(
        "src.saga_spine_v2_milestone_generate.call_structured_json_with_retry"
    )
    def test_generator_injects_reviewed_draft_and_targeted_revision(
        self,
        mock_call,
        _mock_require,
        _mock_identity,
    ):
        revised = _expansion_payload()
        mock_call.return_value = (
            revised,
            _body(),
            {
                "temperature": 0.30,
                "max_tokens": 12000,
                "reasoning": {"effort": "low", "exclude": True},
                "response_format": {"type": "json_object"},
            },
            [],
        )

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "result.json"
            result = generate(
                skeleton_path=SKELETON,
                prompt_path=PROMPT,
                out_path=out,
                model_override="anthropic/claude-sonnet-5",
                api_key="test-key",
                reviewed_draft_path=REVIEWED_DRAFT,
                revision_directives_path=REVISION,
            )

        request_payload = json.loads(mock_call.call_args.kwargs["user_prompt"])
        self.assertEqual(
            request_payload["human_revision_directives"]["source_run_id"],
            36414846876,
        )
        self.assertEqual(
            request_payload["human_revision_directives"]["source_verdict"],
            "REVISE",
        )
        self.assertEqual(
            request_payload["previous_reviewed_expansion"]["source_saga_key"],
            "the_uncharted_disagreement",
        )
        self.assertGreaterEqual(
            len(request_payload["human_revision_directives"]["must_change"]),
            5,
        )
        self.assertEqual(result["status"], "awaiting_human_review")
        self.assertFalse(result["episode_generation_authorized"])

if __name__ == "__main__":
    unittest.main()
