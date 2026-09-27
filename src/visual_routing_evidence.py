from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from src.visual_contracts import (
    StrictModel,
    VisualCategory,
    VisualQualityTier,
    VisualRequest,
    VisualRouteLineage,
)
from src.visual_model_registry import (
    require_visual_model_profile,
    visual_model_profile_identity,
)
from src.visual_qualification import (
    VisualQualificationObservation,
    VisualQualificationRow,
    VisualQualificationThresholds,
    aggregate_visual_qualification,
)
from src.visual_router import VisualRoutingPolicy, route_visual_model
from src.visual_style_registry import (
    resolve_visual_style_profile,
    visual_style_profile_identity,
)


class VisualRoutingEvidenceEntry(StrictModel):
    schema_id: Literal["visual-routing-evidence-entry.v1"] = Field(
        default="visual-routing-evidence-entry.v1",
        alias="schema",
        serialization_alias="schema",
    )
    model_id: str
    style_id: str
    style_version: str
    category: VisualCategory
    quality_tier: VisualQualityTier
    aspect_ratio: str
    model_profile_sha256: str
    style_profile_sha256: str
    evidence_runs: int = Field(ge=1)
    success_rate: float = Field(ge=0, le=1)
    validation_pass_rate: float = Field(ge=0, le=1)
    identity_consistency: float | None = Field(default=None, ge=0, le=1)
    style_consistency: float | None = Field(default=None, ge=0, le=1)
    retry_rate: float = Field(ge=0, le=1)
    average_latency_ms: float | None = Field(default=None, ge=0)
    p95_latency_ms: float | None = Field(default=None, ge=0)
    average_cost_usd: float | None = Field(default=None, ge=0)
    cost_per_accepted_image_usd: float | None = Field(default=None, ge=0)


class VisualRoutingEvidenceRegistry(StrictModel):
    schema_id: Literal["visual-routing-evidence-registry.v1"] = Field(
        default="visual-routing-evidence-registry.v1",
        alias="schema",
        serialization_alias="schema",
    )
    registry_sha256: str
    generated_at: datetime
    source_report_name: str
    source_report_sha256: str
    provider_mode: str
    evaluator_mode: str
    production_authorized: bool
    quality_tier: VisualQualityTier
    aspect_ratio: str
    entries: list[VisualRoutingEvidenceEntry]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_registry_payload(registry: VisualRoutingEvidenceRegistry) -> dict[str, Any]:
    payload = registry.model_dump(mode="json", by_alias=True)
    payload["registry_sha256"] = ""
    return payload


def _registry_sha256(registry: VisualRoutingEvidenceRegistry) -> str:
    encoded = json.dumps(
        _canonical_registry_payload(registry),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def _recompute_rows(report: dict[str, Any]) -> list[VisualQualificationRow]:
    observations = [
        VisualQualificationObservation.model_validate(raw)
        for raw in report.get("observations") or []
    ]
    if not observations:
        raise RuntimeError("VISUAL_ROUTING_EVIDENCE_NO_OBSERVATIONS")
    thresholds = VisualQualificationThresholds.model_validate(
        report.get("thresholds") or {}
    )
    return aggregate_visual_qualification(observations, thresholds=thresholds)


def build_visual_routing_evidence_registry(
    report_path: Path,
) -> VisualRoutingEvidenceRegistry:
    raw_bytes = report_path.read_bytes()
    report = json.loads(raw_bytes.decode("utf-8"))
    if report.get("schema") != "visual-qualification-report.v1":
        raise RuntimeError("VISUAL_ROUTING_EVIDENCE_BAD_REPORT_SCHEMA")

    provider_mode = str(report.get("provider_mode") or "")
    evaluator_mode = str(report.get("evaluator_mode") or "")
    quality_tier = VisualQualityTier(str(report.get("quality_tier") or "STANDARD"))
    aspect_ratio = str(report.get("aspect_ratio") or "3:4")
    rows = _recompute_rows(report)

    entries: list[VisualRoutingEvidenceEntry] = []
    for row in rows:
        if not row.qualified:
            continue
        model = require_visual_model_profile(
            row.model_id,
            category=row.category,
            style_id=row.style_id,
            require_qualified=False,
        )
        style = resolve_visual_style_profile(row.style_id)
        model_identity = visual_model_profile_identity(model.model_id)
        style_identity = visual_style_profile_identity(style.id, style.version)
        entries.append(
            VisualRoutingEvidenceEntry(
                model_id=row.model_id,
                style_id=row.style_id,
                style_version=style.version,
                category=row.category,
                quality_tier=quality_tier,
                aspect_ratio=aspect_ratio,
                model_profile_sha256=model_identity["profile_sha256"],
                style_profile_sha256=style_identity["profile_sha256"],
                evidence_runs=row.runs,
                success_rate=row.success_rate,
                validation_pass_rate=row.validation_pass_rate,
                identity_consistency=row.identity_consistency,
                style_consistency=row.style_consistency,
                retry_rate=row.retry_rate,
                average_latency_ms=row.average_latency_ms,
                p95_latency_ms=row.p95_latency_ms,
                average_cost_usd=row.average_cost_usd,
                cost_per_accepted_image_usd=row.cost_per_accepted_image_usd,
            )
        )

    registry = VisualRoutingEvidenceRegistry(
        registry_sha256="",
        generated_at=datetime.now(timezone.utc),
        source_report_name=str(report.get("name") or report_path.stem),
        source_report_sha256=_sha256_bytes(raw_bytes),
        provider_mode=provider_mode,
        evaluator_mode=evaluator_mode,
        production_authorized=(
            provider_mode != "fixture"
            and evaluator_mode != "fixture"
            and bool(entries)
        ),
        quality_tier=quality_tier,
        aspect_ratio=aspect_ratio,
        entries=entries,
    )
    return registry.model_copy(
        update={"registry_sha256": _registry_sha256(registry)}
    )


def write_visual_routing_evidence_registry(
    report_path: Path,
    output_path: Path,
) -> VisualRoutingEvidenceRegistry:
    registry = build_visual_routing_evidence_registry(report_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            registry.model_dump(mode="json", by_alias=True),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return registry


def load_visual_routing_evidence_registry(
    path: Path,
) -> VisualRoutingEvidenceRegistry:
    registry = VisualRoutingEvidenceRegistry.model_validate(
        json.loads(path.read_text(encoding="utf-8"))
    )
    actual = _registry_sha256(registry)
    if actual != registry.registry_sha256:
        raise RuntimeError("VISUAL_ROUTING_EVIDENCE_REGISTRY_HASH_MISMATCH")
    return registry


def _entry_to_row(entry: VisualRoutingEvidenceEntry) -> VisualQualificationRow:
    return VisualQualificationRow(
        model_id=entry.model_id,
        style_id=entry.style_id,
        category=entry.category,
        runs=entry.evidence_runs,
        success_rate=entry.success_rate,
        validation_pass_rate=entry.validation_pass_rate,
        identity_consistency=entry.identity_consistency,
        style_consistency=entry.style_consistency,
        user_selection_rate=None,
        retry_rate=entry.retry_rate,
        average_latency_ms=entry.average_latency_ms,
        p95_latency_ms=entry.p95_latency_ms,
        average_cost_usd=entry.average_cost_usd,
        cost_per_accepted_image_usd=entry.cost_per_accepted_image_usd,
        qualified=True,
        rejection_reasons=[],
    )


def select_visual_route_lineage(
    registry_path: Path,
    request: VisualRequest,
    *,
    policy: VisualRoutingPolicy | None = None,
) -> VisualRouteLineage:
    registry = load_visual_routing_evidence_registry(registry_path)
    if not registry.production_authorized:
        raise RuntimeError("VISUAL_ROUTING_EVIDENCE_NOT_PRODUCTION_AUTHORIZED")

    candidates = [
        entry
        for entry in registry.entries
        if entry.style_id == request.style_id
        and entry.category == request.category
        and entry.quality_tier == request.quality_tier
        and entry.aspect_ratio == request.aspect_ratio
        and (
            request.style_version is None
            or entry.style_version == request.style_version
        )
        and (
            request.model_id is None
            or entry.model_id == request.model_id
        )
    ]
    if not candidates:
        raise RuntimeError(
            "VISUAL_ROUTING_EVIDENCE_NO_MATCH: "
            f"{request.style_id}/{request.category.value}/"
            f"{request.quality_tier.value}/{request.aspect_ratio}"
        )

    valid: list[VisualRoutingEvidenceEntry] = []
    for entry in candidates:
        model = require_visual_model_profile(
            entry.model_id,
            category=entry.category,
            style_id=entry.style_id,
            require_qualified=False,
        )
        style = resolve_visual_style_profile(entry.style_id, entry.style_version)
        if (
            visual_model_profile_identity(model.model_id)["profile_sha256"]
            != entry.model_profile_sha256
        ):
            continue
        if (
            visual_style_profile_identity(style.id, style.version)["profile_sha256"]
            != entry.style_profile_sha256
        ):
            continue
        valid.append(entry)

    if not valid:
        raise RuntimeError("VISUAL_ROUTING_EVIDENCE_STALE_PROFILE_FINGERPRINT")

    decision = route_visual_model(
        category=request.category,
        style_id=request.style_id,
        rows=[_entry_to_row(entry) for entry in valid],
        policy=policy,
    )
    selected = next(
        entry for entry in valid if entry.model_id == decision.model_id
    )
    return VisualRouteLineage(
        registry_sha256=registry.registry_sha256,
        source_report_sha256=registry.source_report_sha256,
        model_id=selected.model_id,
        style_id=selected.style_id,
        style_version=selected.style_version,
        category=selected.category,
        quality_tier=selected.quality_tier,
        aspect_ratio=selected.aspect_ratio,
        score=decision.score,
        evidence_runs=selected.evidence_runs,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build immutable production visual routing evidence"
    )
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--require-production-authorized",
        action="store_true",
        help="Fail if the report cannot authorize any production routing entries.",
    )
    args = parser.parse_args()

    registry = write_visual_routing_evidence_registry(args.report, args.output)
    if args.require_production_authorized and not registry.production_authorized:
        raise RuntimeError("VISUAL_ROUTING_EVIDENCE_NOT_PRODUCTION_AUTHORIZED")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "registry_sha256": registry.registry_sha256,
                "source_report_sha256": registry.source_report_sha256,
                "production_authorized": registry.production_authorized,
                "qualified_entries": len(registry.entries),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
