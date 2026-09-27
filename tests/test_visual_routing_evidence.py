from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.visual_contracts import (
    CharacterVisualProfile,
    VisualCategory,
    VisualIntent,
    VisualQualityTier,
    VisualRequest,
)
from src.visual_routing_evidence import (
    build_visual_routing_evidence_registry,
    load_visual_routing_evidence_registry,
    select_visual_route_lineage,
    write_visual_routing_evidence_registry,
)


def observation(
    model_id: str,
    *,
    identity: float,
    style: float,
    latency: int,
    cost: float | None,
) -> dict:
    return {
        "model_id": model_id,
        "style_id": "lumi-storybook-soft",
        "category": "CHARACTER_PORTRAIT",
        "success": True,
        "validation_pass": True,
        "identity_consistency": identity,
        "style_consistency": style,
        "latency_ms": latency,
        "cost_usd": cost,
        "selected_by_user": None,
        "retry_count": 0,
    }


def live_report() -> dict:
    observations = []
    for _ in range(3):
        observations.append(
            observation(
                "meta/muse-image",
                identity=0.96,
                style=0.96,
                latency=1000,
                cost=0.01,
            )
        )
        observations.append(
            observation(
                "bytedance-seed/seedream-4.5",
                identity=0.85,
                style=0.85,
                latency=100,
                cost=0.04,
            )
        )
    return {
        "schema": "visual-qualification-report.v1",
        "name": "live-promotion",
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
        # Deliberately untrusted/forged rows. Registry construction must ignore them.
        "rows": [
            {
                "model_id": "openai/gpt-image-2.5-sunburst",
                "style_id": "lumi-storybook-soft",
                "category": "CHARACTER_PORTRAIT",
                "runs": 99,
                "success_rate": 1.0,
                "validation_pass_rate": 1.0,
                "identity_consistency": 1.0,
                "style_consistency": 1.0,
                "user_selection_rate": None,
                "retry_rate": 0.0,
                "average_latency_ms": 1.0,
                "p95_latency_ms": 1.0,
                "average_cost_usd": 0.0,
                "cost_per_accepted_image_usd": 0.0,
                "qualified": True,
                "rejection_reasons": [],
            }
        ],
        "observations": observations,
    }


def fixture_report() -> dict:
    return {
        "schema": "visual-qualification-report.v1",
        "name": "fixture-promotion",
        "provider_mode": "fixture",
        "evaluator_mode": "fixture",
        "quality_tier": "STANDARD",
        "aspect_ratio": "3:4",
        "thresholds": {
            "min_runs": 3,
            "min_success_rate": 1.0,
            "min_validation_pass_rate": 1.0,
            "min_identity_consistency": 1.0,
            "min_style_consistency": 1.0,
        },
        "observations": [
            observation(
                "fixture/lumi-visual-v1",
                identity=1.0,
                style=1.0,
                latency=1,
                cost=0.0,
            )
            for _ in range(3)
        ],
    }


def request() -> VisualRequest:
    return VisualRequest(
        request_id="runtime-route",
        profile_id="profile-1",
        category=VisualCategory.CHARACTER_PORTRAIT,
        intent=VisualIntent(subject="Elara"),
        style_id="lumi-storybook-soft",
        quality_tier=VisualQualityTier.STANDARD,
        aspect_ratio="3:4",
        character_profile=CharacterVisualProfile(
            character_id="elara",
            version="1.0.0",
            apparent_age=11,
            eyes="amber brown",
            hair={"color": "dark chestnut"},
            must_keep=["amber brown eyes"],
        ),
    )


class VisualRoutingEvidenceTests(unittest.TestCase):
    def test_registry_recomputes_qualification_from_observations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "report.json"
            report_path.write_text(json.dumps(live_report()))
            registry = build_visual_routing_evidence_registry(report_path)
            self.assertTrue(registry.production_authorized)
            self.assertEqual(
                {entry.model_id for entry in registry.entries},
                {"meta/muse-image", "bytedance-seed/seedream-4.5"},
            )
            self.assertNotIn(
                "openai/gpt-image-2.5-sunburst",
                {entry.model_id for entry in registry.entries},
            )

    def test_fixture_registry_cannot_authorize_production_routing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "report.json"
            registry_path = root / "registry.json"
            report_path.write_text(json.dumps(fixture_report()))
            registry = write_visual_routing_evidence_registry(
                report_path,
                registry_path,
            )
            self.assertFalse(registry.production_authorized)
            with self.assertRaisesRegex(
                RuntimeError,
                "VISUAL_ROUTING_EVIDENCE_NOT_PRODUCTION_AUTHORIZED",
            ):
                select_visual_route_lineage(registry_path, request())

    def test_registry_hash_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "report.json"
            registry_path = root / "registry.json"
            report_path.write_text(json.dumps(live_report()))
            write_visual_routing_evidence_registry(report_path, registry_path)
            payload = json.loads(registry_path.read_text())
            payload["entries"][0]["evidence_runs"] = 999
            registry_path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(
                RuntimeError,
                "VISUAL_ROUTING_EVIDENCE_REGISTRY_HASH_MISMATCH",
            ):
                load_visual_routing_evidence_registry(registry_path)

    def test_exact_cell_route_selects_quality_first_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "report.json"
            registry_path = root / "registry.json"
            report_path.write_text(json.dumps(live_report()))
            write_visual_routing_evidence_registry(report_path, registry_path)
            lineage = select_visual_route_lineage(registry_path, request())
            self.assertEqual(lineage.model_id, "meta/muse-image")
            self.assertEqual(lineage.evidence_runs, 3)
            self.assertEqual(lineage.quality_tier, VisualQualityTier.STANDARD)
            self.assertEqual(lineage.aspect_ratio, "3:4")

    def test_unqualified_quality_tier_has_no_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "report.json"
            registry_path = root / "registry.json"
            report_path.write_text(json.dumps(live_report()))
            write_visual_routing_evidence_registry(report_path, registry_path)
            premium = request().model_copy(
                update={"quality_tier": VisualQualityTier.PREMIUM}
            )
            with self.assertRaisesRegex(
                RuntimeError,
                "VISUAL_ROUTING_EVIDENCE_NO_MATCH",
            ):
                select_visual_route_lineage(registry_path, premium)


if __name__ == "__main__":
    unittest.main()
