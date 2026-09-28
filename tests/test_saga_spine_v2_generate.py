from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.saga_spine_v2_generate import generate
from tests.test_saga_spine_v2_contract import _valid_payload


FIXTURE = Path(
    "data/specifications/saga_lab/age12_shattered_meridian_fixture_v2.json"
)
PROMPT = Path("prompts/saga_narrative_architect_v2.md")
SCHEMA = Path(
    "data/specifications/saga_lab/character_saga_spine_v2.schema.json"
)


def _body() -> dict:
    return {
        "model": "test/model",
        "provider": "test-provider",
        "usage": {
            "prompt_tokens": 1000,
            "completion_tokens": 2000,
            "total_tokens": 3000,
            "completion_tokens_details": {"reasoning_tokens": 500},
            "cost": 0.123,
        },
    }


class SagaSpineV2GeneratorTests(unittest.TestCase):
    @patch("src.saga_spine_v2_generate.runtime_profile_identity", return_value={"model_id": "test/model"})
    @patch("src.saga_spine_v2_generate.require_qualification_runtime_profile", return_value={"qualification": {"ready": True}})
    @patch("src.saga_spine_v2_generate.call_structured_json_with_retry")
    def test_valid_spine_stops_at_human_review_gate(self, mock_call, _mock_require, _mock_identity):
        mock_call.return_value = (
            _valid_payload(),
            _body(),
            {
                "temperature": 0.35,
                "max_tokens": 30000,
                "reasoning": {"effort": "high"},
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
                model_override="test/model",
                api_key="test-key",
            )

            persisted = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "awaiting_human_review")
        self.assertFalse(result["publication_authority"])
        self.assertTrue(result["human_creative_review_required"])
        self.assertIsNone(result["human_review"]["verdict"])
        self.assertEqual(result["spine"]["schema"], "character-saga-spine.v2")
        self.assertEqual(len(result["spine"]["main_saga"]["milestones"]), 15)
        self.assertEqual(
            result["raw_usage"]["completion_tokens_details"]["reasoning_tokens"],
            500,
        )
        self.assertEqual(result["cost"]["usd"], 0.123)
        self.assertEqual(persisted["status"], "awaiting_human_review")

    @patch("src.saga_spine_v2_generate.runtime_profile_identity", return_value={"model_id": "test/model"})
    @patch("src.saga_spine_v2_generate.require_qualification_runtime_profile", return_value={"qualification": {"ready": True}})
    @patch("src.saga_spine_v2_generate.call_structured_json_with_retry")
    def test_invalid_spine_persists_contract_errors(self, mock_call, _mock_require, _mock_identity):
        invalid = _valid_payload()
        invalid["main_saga"]["milestones"] = invalid["main_saga"]["milestones"][:5]
        mock_call.return_value = (
            invalid,
            _body(),
            {"temperature": 0.35},
            [],
        )

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "result.json"
            with self.assertRaisesRegex(
                RuntimeError,
                "deterministic contract validation",
            ):
                generate(
                    fixture_path=FIXTURE,
                    prompt_path=PROMPT,
                    schema_path=SCHEMA,
                    out_path=out,
                    model_override="test/model",
                    api_key="test-key",
                )
            persisted = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(persisted["status"], "contract_rejected")
        self.assertTrue(persisted["contract_errors"])
        self.assertIn("raw_generated_payload", persisted)


if __name__ == "__main__":
    unittest.main()
