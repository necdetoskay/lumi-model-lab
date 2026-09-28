from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from src.saga_spine_v2_skeleton_contract import CharacterSagaSkeletonV2
from src.saga_spine_v2_skeleton_generate import generate
from tests.test_saga_spine_v2_contract import _valid_payload


FIXTURE = Path(
    "data/specifications/saga_lab/age12_shattered_meridian_fixture_v2.json"
)
PROMPT = Path("prompts/saga_narrative_architect_skeleton_v2.md")
SCHEMA = Path(
    "data/specifications/saga_lab/character_saga_skeleton_v2.schema.json"
)

REVISION = Path(
    "data/specifications/saga_lab/age12_shattered_meridian_gate_a_revision_v1.json"
)


def _skeleton_payload() -> dict:
    full = _valid_payload()
    main = full["main_saga"]
    milestones = {x["key"]: x for x in main["milestones"]}

    anchors = []
    for anchor in main["anchors"]:
        modes = []
        for key in anchor["milestone_keys"]:
            mode = milestones[key]["type"]
            if mode not in modes:
                modes.append(mode)
        anchors.append(
            {
                "key": anchor["key"],
                "title": anchor["title"],
                "purpose": anchor["purpose"],
                "target_state": anchor["target_state"],
                "required_for_resolution": anchor["required_for_resolution"],
                "milestone_target_count": len(anchor["milestone_keys"]),
                "desired_progression_modes": modes,
            }
        )

    reveals = []
    for row in main["reveal_steps"]:
        anchor_keys = []
        for milestone_key in row["milestone_keys"]:
            anchor_key = milestones[milestone_key]["anchor_key"]
            if anchor_key not in anchor_keys:
                anchor_keys.append(anchor_key)
        reveals.append(
            {
                "key": row["key"],
                "truth_key": row["truth_key"],
                "level": row["level"],
                "summary": row["summary"],
                "eligibility": row["eligibility"],
                "anchor_keys": anchor_keys,
                "reveal_ceiling": row["reveal_ceiling"],
            }
        )

    return {
        "schema": "character-saga-skeleton.v2",
        "origin": full["origin"],
        "present_situation": full["present_situation"],
        "narrative_core": full["narrative_core"],
        "main_saga": {
            "key": main["key"],
            "title": main["title"],
            "goal": main["goal"],
            "stakes": main["stakes"],
            "central_mystery": main["central_mystery"],
            "themes": main["themes"],
            "entry_anchor_keys": ["anchor_1"],
            "resolution_anchor_key": "anchor_5",
            "anchors": anchors,
            "anchor_edges": [
                {
                    "from_anchor": "anchor_1",
                    "to_anchor": "anchor_2",
                    "relationship": "REQUIRES",
                    "rationale": "Primary evidence can open the second phase.",
                },
                {
                    "from_anchor": "anchor_1",
                    "to_anchor": "anchor_3",
                    "relationship": "ALTERNATIVE_ROUTE",
                    "rationale": "A different discovery can open a parallel route.",
                },
                {
                    "from_anchor": "anchor_2",
                    "to_anchor": "anchor_4",
                    "relationship": "MAY_ENABLE",
                    "rationale": "One route can prepare convergence.",
                },
                {
                    "from_anchor": "anchor_3",
                    "to_anchor": "anchor_4",
                    "relationship": "MAY_CONVERGE",
                    "rationale": "Parallel evidence can converge here.",
                },
                {
                    "from_anchor": "anchor_4",
                    "to_anchor": "anchor_5",
                    "relationship": "REQUIRES",
                    "rationale": "Resolution becomes reachable only after convergence.",
                },
            ],
            "hidden_truths": main["hidden_truths"],
            "reveal_intents": reveals,
        },
        "latent_side_sagas": full["latent_side_sagas"],
        "creative_permission_envelope": full["creative_permission_envelope"],
        "world_integration": full["world_integration"],
        "reweave_policy": full["reweave_policy"],
        "background_enrichment_policy": full["background_enrichment_policy"],
        "safety_and_constraints": full["safety_and_constraints"],
    }


def _body() -> dict:
    return {
        "model": "anthropic/claude-sonnet-5",
        "provider": "test-provider",
        "usage": {
            "prompt_tokens": 1000,
            "completion_tokens": 3000,
            "total_tokens": 4000,
            "completion_tokens_details": {"reasoning_tokens": 800},
            "cost": 0.05,
        },
    }


class SagaSkeletonV2ContractTests(unittest.TestCase):
    def test_valid_skeleton_passes(self):
        payload = _skeleton_payload()
        result = CharacterSagaSkeletonV2.model_validate(payload)
        self.assertEqual(len(result.main_saga.anchors), 5)
        self.assertEqual(
            sum(x.milestone_target_count for x in result.main_saga.anchors),
            15,
        )

    def test_rejects_planned_milestone_total_below_15(self):
        payload = _skeleton_payload()
        for anchor in payload["main_saga"]["anchors"]:
            anchor["milestone_target_count"] = 2
        with self.assertRaisesRegex(ValidationError, "planned milestone total"):
            CharacterSagaSkeletonV2.model_validate(payload)

    def test_rejects_missing_alternative_route(self):
        payload = _skeleton_payload()
        payload["main_saga"]["anchor_edges"] = [
            row
            for row in payload["main_saga"]["anchor_edges"]
            if row["relationship"] != "ALTERNATIVE_ROUTE"
        ]
        with self.assertRaisesRegex(ValidationError, "ALTERNATIVE_ROUTE"):
            CharacterSagaSkeletonV2.model_validate(payload)

    def test_rejects_cycle(self):
        payload = _skeleton_payload()
        payload["main_saga"]["anchor_edges"].append(
            {
                "from_anchor": "anchor_5",
                "to_anchor": "anchor_1",
                "relationship": "MAY_ENABLE",
                "rationale": "Invalid cycle.",
            }
        )
        with self.assertRaisesRegex(ValidationError, "acyclic"):
            CharacterSagaSkeletonV2.model_validate(payload)

    def test_rejects_scripted_episode_language(self):
        payload = _skeleton_payload()
        payload["main_saga"]["anchors"][0]["purpose"] = (
            "Episode 1 forces the character to find the clue."
        )
        with self.assertRaisesRegex(ValidationError, "must not encode numbered"):
            CharacterSagaSkeletonV2.model_validate(payload)


class SagaSkeletonV2GeneratorTests(unittest.TestCase):
    @patch(
        "src.saga_spine_v2_skeleton_generate.runtime_profile_identity",
        return_value={"model_id": "anthropic/claude-sonnet-5"},
    )
    @patch(
        "src.saga_spine_v2_skeleton_generate.require_qualification_runtime_profile",
        return_value={"qualification": {"ready": True}},
    )
    @patch(
        "src.saga_spine_v2_skeleton_generate.call_structured_json_with_retry"
    )
    def test_valid_skeleton_stops_before_milestone_expansion(
        self,
        mock_call,
        _mock_require,
        _mock_identity,
    ):
        mock_call.return_value = (
            _skeleton_payload(),
            _body(),
            {
                "temperature": 0.30,
                "max_tokens": 10000,
                "reasoning": {"effort": "low", "exclude": True},
                "response_format": {"type": "json_object"},
            },
            [],
        )

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "result.json"
            result = generate(
                fixture_path=FIXTURE,
                prompt_path=PROMPT,
                schema_path=SCHEMA,
                out_path=out,
                model_override="anthropic/claude-sonnet-5",
                api_key="test-key",
            )
            persisted = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "awaiting_human_review")
        self.assertFalse(result["milestone_expansion_authorized"])
        self.assertFalse(
            result["human_review"]["milestone_expansion_authorized"]
        )
        self.assertEqual(
            result["skeleton"]["schema"],
            "character-saga-skeleton.v2",
        )
        self.assertEqual(persisted["status"], "awaiting_human_review")
        self.assertEqual(
            result["raw_usage"]["completion_tokens_details"]["reasoning_tokens"],
            800,
        )

        kwargs = mock_call.call_args.kwargs
        self.assertEqual(kwargs["request_class"], "saga_architect")
        self.assertEqual(kwargs["max_tokens"], 10000)
        request_payload = json.loads(kwargs["user_prompt"])
        self.assertIn("output_contract", request_payload)
        self.assertEqual(
            request_payload["output_contract"]["properties"]["schema"]["const"],
            "character-saga-skeleton.v2",
        )
        self.assertIn("contract_rules", request_payload)
        self.assertIn("requested_shape", request_payload)
        self.assertEqual(
            request_payload["qualification_rules"]["main_saga_anchor_count"],
            5,
        )
        self.assertEqual(
            request_payload["qualification_rules"]["planned_milestone_total"],
            15,
        )

        self.assertIsNone(request_payload["human_revision_directives"])



    @patch(
        "src.saga_spine_v2_skeleton_generate.runtime_profile_identity",
        return_value={"model_id": "anthropic/claude-sonnet-5"},
    )
    @patch(
        "src.saga_spine_v2_skeleton_generate.require_qualification_runtime_profile",
        return_value={"qualification": {"ready": True}},
    )
    @patch(
        "src.saga_spine_v2_skeleton_generate.call_structured_json_with_retry"
    )
    def test_human_revision_directives_are_injected_without_authorizing_expansion(
        self,
        mock_call,
        _mock_require,
        _mock_identity,
    ):
        mock_call.return_value = (
            _skeleton_payload(),
            _body(),
            {
                "temperature": 0.30,
                "max_tokens": 10000,
                "reasoning": {"effort": "low", "exclude": True},
                "response_format": {"type": "json_object"},
            },
            [],
        )

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "result.json"
            result = generate(
                fixture_path=FIXTURE,
                prompt_path=PROMPT,
                schema_path=SCHEMA,
                out_path=out,
                model_override="anthropic/claude-sonnet-5",
                api_key="test-key",
                revision_directives_path=REVISION,
            )

        request_payload = json.loads(mock_call.call_args.kwargs["user_prompt"])
        directives = request_payload["human_revision_directives"]
        self.assertEqual(directives["source_run_id"], 36410908865)
        self.assertEqual(directives["source_verdict"], "REVISE")
        self.assertGreaterEqual(len(directives["must_change"]), 5)
        self.assertFalse(result["milestone_expansion_authorized"])
        self.assertFalse(
            result["human_review"]["milestone_expansion_authorized"]
        )

if __name__ == "__main__":
    unittest.main()
