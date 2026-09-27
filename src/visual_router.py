from __future__ import annotations

from pydantic import Field

from src.visual_contracts import StrictModel, VisualCategory
from src.visual_model_registry import require_visual_model_profile
from src.visual_qualification import VisualQualificationRow


class VisualRoutingPolicy(StrictModel):
    quality_weight: float = Field(default=0.60, ge=0)
    reliability_weight: float = Field(default=0.20, ge=0)
    latency_weight: float = Field(default=0.10, ge=0)
    cost_weight: float = Field(default=0.10, ge=0)


class VisualRouteDecision(StrictModel):
    model_id: str
    style_id: str
    category: VisualCategory
    score: float
    evidence_runs: int
    reason: str


def _inverse_normalized(value: float | None, maximum: float) -> float:
    if value is None or maximum <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - (value / maximum)))


def route_visual_model(
    *,
    category: VisualCategory,
    style_id: str,
    rows: list[VisualQualificationRow],
    policy: VisualRoutingPolicy | None = None,
) -> VisualRouteDecision:
    policy = policy or VisualRoutingPolicy()
    candidates = [
        row for row in rows
        if row.category == category and row.style_id == style_id and row.qualified
    ]
    if not candidates:
        raise RuntimeError(
            f"VISUAL_ROUTE_NO_QUALIFIED_MODEL: {style_id}/{category.value}"
        )

    # Re-check the profile registry at routing time so stale evidence cannot route
    # to an inactive or incompatible model.
    checked: list[VisualQualificationRow] = []
    for row in candidates:
        try:
            require_visual_model_profile(
                row.model_id,
                category=category,
                style_id=style_id,
            )
        except RuntimeError:
            continue
        checked.append(row)
    if not checked:
        raise RuntimeError(
            f"VISUAL_ROUTE_NO_ACTIVE_MODEL: {style_id}/{category.value}"
        )

    max_latency = max(
        [float(row.p95_latency_ms or row.average_latency_ms or 0) for row in checked] or [0.0]
    )
    known_costs = [
        float(row.cost_per_accepted_image_usd or row.average_cost_usd)
        for row in checked
        if (row.cost_per_accepted_image_usd or row.average_cost_usd) is not None
    ]
    max_cost = max(known_costs or [0.0])
    min_cost = min(known_costs or [0.0])

    scored: list[tuple[float, VisualQualificationRow]] = []
    for row in checked:
        identity = row.identity_consistency or 0.0
        style = row.style_consistency or 0.0
        quality = (identity + style + row.validation_pass_rate) / 3.0
        reliability = row.success_rate * (1.0 - row.retry_rate)
        latency = _inverse_normalized(
            float(row.p95_latency_ms or row.average_latency_ms or 0), max_latency
        )
        row_cost = row.cost_per_accepted_image_usd or row.average_cost_usd
        if row_cost is None:
            cost = 0.0
        elif max_cost <= 0 or max_cost == min_cost:
            cost = 0.5
        else:
            cost = max(
                0.0,
                min(
                    1.0,
                    1.0
                    - ((float(row_cost) - min_cost) / (max_cost - min_cost)),
                ),
            )
        score = (
            policy.quality_weight * quality
            + policy.reliability_weight * reliability
            + policy.latency_weight * latency
            + policy.cost_weight * cost
        )
        scored.append((score, row))

    score, winner = max(scored, key=lambda item: (item[0], item[1].runs, item[1].model_id))
    return VisualRouteDecision(
        model_id=winner.model_id,
        style_id=style_id,
        category=category,
        score=round(score, 6),
        evidence_runs=winner.runs,
        reason=(
            "qualified evidence route using quality, reliability, latency and "
            "cost; user style remains model-independent"
        ),
    )
