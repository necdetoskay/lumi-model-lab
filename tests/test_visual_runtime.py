from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.visual_contracts import (
    CharacterVisualProfile,
    VisualCategory,
    VisualIntent,
    VisualRequest,
)
from src.visual_provider import FixtureVisualProviderAdapter
from src.visual_routing_evidence import write_visual_routing_evidence_registry
from src.visual_runtime import generate_routed_visual


def report() -> dict:
    observations = [
        {
            "model_id": "meta/muse-image",
            "style_id": "lumi-storybook-soft",
            "category": "CHARACTER_PORTRAIT",
            "success": True,
            "validation_pass": True,
            "identity_consistency": 0.95,
            "style_consistency": 0.95,
            "latency_ms": 500,
            "cost_usd": 0.01,
            "selected_by_user": None,
            "retry_count": 0,
        }
        for _ in range(3)
    ]
    return {
        "schema": "visual-qualification-report.v1",
        "name": "runtime-live",
        "provider_mode": "openrouter",
        "evaluator_mode": "openrouter",
        "quality_tier": "STANDARD",
        "aspect_ratio": "3:4",
        "thresholds": {
            "min_runs": 3,
            "min_success_rate": 0.95,
            "min_validation_pass_rate": 0.90,
            "min_identity_consistency": 0.80,
            "min_style_consistency": 0.80,
        },
        "observations": observations,
    }


def request(*, model_id=None) -> VisualRequest:
    return VisualRequest(
        request_id="runtime",
        profile_id="profile-1",
        category=VisualCategory.CHARACTER_PORTRAIT,
        intent=VisualIntent(subject="Elara"),
        style_id="lumi-storybook-soft",
        model_id=model_id,
        character_profile=CharacterVisualProfile(
            character_id="elara",
            version="1.0.0",
            apparent_age=11,
            eyes="amber brown",
            hair={"color": "dark chestnut"},
            must_keep=["amber brown eyes"],
        ),
    )


class VisualRuntimeTests(unittest.TestCase):
    def test_routed_runtime_binds_registry_lineage_to_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "report.json"
            registry_path = root / "registry.json"
            report_path.write_text(json.dumps(report()))
            registry = write_visual_routing_evidence_registry(
                report_path,
                registry_path,
            )
            result = generate_routed_visual(
                request(),
                routing_registry_path=registry_path,
                adapter=FixtureVisualProviderAdapter(),
                evidence_dir=root / "evidence",
            )
            self.assertEqual(result.invocation.model, "meta/muse-image")
            self.assertIsNotNone(result.invocation.route_lineage)
            assert result.invocation.route_lineage is not None
            self.assertEqual(
                result.invocation.route_lineage.registry_sha256,
                registry.registry_sha256,
            )
            self.assertEqual(result.invocation.route_lineage.evidence_runs, 3)
            self.assertEqual(result.artifacts[0].model_id, "meta/muse-image")

    def test_production_routed_runtime_rejects_prelocked_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "report.json"
            registry_path = root / "registry.json"
            report_path.write_text(json.dumps(report()))
            write_visual_routing_evidence_registry(report_path, registry_path)
            with self.assertRaisesRegex(
                RuntimeError,
                "VISUAL_PRODUCTION_MODEL_LOCK_FORBIDDEN",
            ):
                generate_routed_visual(
                    request(model_id="meta/muse-image"),
                    routing_registry_path=registry_path,
                    adapter=FixtureVisualProviderAdapter(),
                    evidence_dir=root / "evidence",
                )


if __name__ == "__main__":
    unittest.main()
