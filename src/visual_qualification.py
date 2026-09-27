from __future__ import annotations

import math
from collections import defaultdict
from statistics import mean
from typing import Iterable

from pydantic import Field

from src.visual_contracts import StrictModel, VisualCategory


class VisualQualificationObservation(StrictModel):
    model_id: str
    style_id: str
    category: VisualCategory
    success: bool
    validation_pass: bool
    identity_consistency: float | None = Field(default=None, ge=0, le=1)
    style_consistency: float | None = Field(default=None, ge=0, le=1)
    latency_ms: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    selected_by_user: bool | None = None
    retry_count: int = Field(default=0, ge=0)


class VisualQualificationThresholds(StrictModel):
    min_runs: int = Field(default=3, ge=1)
    min_success_rate: float = Field(default=0.95, ge=0, le=1)
    min_validation_pass_rate: float = Field(default=0.90, ge=0, le=1)
    min_identity_consistency: float = Field(default=0.80, ge=0, le=1)
    min_style_consistency: float = Field(default=0.80, ge=0, le=1)


class VisualQualificationRow(StrictModel):
    model_id: str
    style_id: str
    category: VisualCategory
    runs: int
    success_rate: float
    validation_pass_rate: float
    identity_consistency: float | None
    style_consistency: float | None
    user_selection_rate: float | None
    retry_rate: float
    average_latency_ms: float | None
    p95_latency_ms: float | None
    average_cost_usd: float | None
    cost_per_accepted_image_usd: float | None
    qualified: bool
    rejection_reasons: list[str] = Field(default_factory=list)


def _avg(values: list[float]) -> float | None:
    return round(mean(values), 6) if values else None


def _p95(values: list[int]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return float(ordered[index])


def aggregate_visual_qualification(
    observations: Iterable[VisualQualificationObservation],
    *,
    thresholds: VisualQualificationThresholds | None = None,
) -> list[VisualQualificationRow]:
    thresholds = thresholds or VisualQualificationThresholds()
    grouped: dict[tuple[str, str, VisualCategory], list[VisualQualificationObservation]] = defaultdict(list)
    for observation in observations:
        grouped[(observation.model_id, observation.style_id, observation.category)].append(observation)

    rows: list[VisualQualificationRow] = []
    for (model_id, style_id, category), items in sorted(
        grouped.items(), key=lambda item: (item[0][0], item[0][1], item[0][2].value)
    ):
        runs = len(items)
        success_rate = sum(item.success for item in items) / runs
        validation_rate = sum(item.validation_pass for item in items) / runs
        identity = _avg([
            item.identity_consistency for item in items
            if item.identity_consistency is not None
        ])
        style = _avg([
            item.style_consistency for item in items
            if item.style_consistency is not None
        ])
        selected = [item.selected_by_user for item in items if item.selected_by_user is not None]
        selection_rate = (
            round(sum(bool(item) for item in selected) / len(selected), 6)
            if selected else None
        )
        latencies = [item.latency_ms for item in items if item.latency_ms is not None]
        costs = [item.cost_usd for item in items if item.cost_usd is not None]
        accepted = [item for item in items if item.success and item.validation_pass]
        accepted_costs = [
            item.cost_usd for item in accepted if item.cost_usd is not None
        ]
        reasons: list[str] = []
        if runs < thresholds.min_runs:
            reasons.append("INSUFFICIENT_RUNS")
        if success_rate < thresholds.min_success_rate:
            reasons.append("SUCCESS_RATE")
        if validation_rate < thresholds.min_validation_pass_rate:
            reasons.append("VALIDATION_PASS_RATE")
        if identity is None or identity < thresholds.min_identity_consistency:
            reasons.append("IDENTITY_CONSISTENCY")
        if style is None or style < thresholds.min_style_consistency:
            reasons.append("STYLE_CONSISTENCY")

        rows.append(
            VisualQualificationRow(
                model_id=model_id,
                style_id=style_id,
                category=category,
                runs=runs,
                success_rate=round(success_rate, 6),
                validation_pass_rate=round(validation_rate, 6),
                identity_consistency=identity,
                style_consistency=style,
                user_selection_rate=selection_rate,
                retry_rate=round(sum(item.retry_count > 0 for item in items) / runs, 6),
                average_latency_ms=_avg([float(value) for value in latencies]),
                p95_latency_ms=_p95(latencies),
                average_cost_usd=_avg([float(value) for value in costs]),
                cost_per_accepted_image_usd=(
                    round(sum(accepted_costs) / len(accepted), 6)
                    if accepted and len(accepted_costs) == len(accepted)
                    else None
                ),
                qualified=not reasons,
                rejection_reasons=reasons,
            )
        )
    return rows
