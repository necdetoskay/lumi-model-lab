from __future__ import annotations

import argparse
import copy
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field

from src.visual_contracts import StrictModel
from src.visual_qualification import VisualQualificationRow


class VisualScreeningPolicy(StrictModel):
    promotion_name: str = "visual-live-promotion-v1"
    top_k_per_cell: int = Field(default=2, ge=1)
    min_success_rate: float = Field(default=1.0, ge=0, le=1)
    min_validation_pass_rate: float = Field(default=1.0, ge=0, le=1)
    min_identity_consistency: float = Field(default=0.70, ge=0, le=1)
    min_style_consistency: float = Field(default=0.70, ge=0, le=1)
    quality_weight: float = Field(default=0.75, ge=0)
    reliability_weight: float = Field(default=0.15, ge=0)
    latency_weight: float = Field(default=0.05, ge=0)
    cost_weight: float = Field(default=0.05, ge=0)
    promotion_additional_runs_per_cell: int = Field(default=2, ge=1)
    promotion_max_known_generation_cost_usd: float = Field(default=5.0, ge=0)


def _inverse_normalized(value: float | None, maximum: float) -> float:
    if value is None or maximum <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - value / maximum))


def _eligible(row: VisualQualificationRow, policy: VisualScreeningPolicy) -> bool:
    return (
        row.success_rate >= policy.min_success_rate
        and row.validation_pass_rate >= policy.min_validation_pass_rate
        and row.identity_consistency is not None
        and row.identity_consistency >= policy.min_identity_consistency
        and row.style_consistency is not None
        and row.style_consistency >= policy.min_style_consistency
    )


def select_visual_promotion_cells(
    report: dict[str, Any],
    *,
    policy: VisualScreeningPolicy | None = None,
) -> dict[str, Any]:
    if report.get("schema") != "visual-qualification-report.v1":
        raise RuntimeError("Unsupported visual screening report schema")
    policy = policy or VisualScreeningPolicy()
    rows = [VisualQualificationRow.model_validate(raw) for raw in report.get("rows") or []]
    if not rows:
        raise RuntimeError("Visual screening report contains no qualification rows")

    grouped: dict[tuple[str, str], list[VisualQualificationRow]] = defaultdict(list)
    for row in rows:
        grouped[(row.style_id, row.category.value)].append(row)

    selected_cells: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    for (style_id, category), candidates in sorted(grouped.items()):
        eligible = [row for row in candidates if _eligible(row, policy)]
        max_latency = max(
            [float(row.average_latency_ms or row.p95_latency_ms or 0) for row in eligible]
            or [0.0]
        )
        known_costs = [
            float(row.average_cost_usd)
            for row in eligible
            if row.average_cost_usd is not None
        ]
        max_cost = max(known_costs or [0.0])
        min_cost = min(known_costs or [0.0])
        scored: list[tuple[float, VisualQualificationRow]] = []
        for row in eligible:
            quality = (
                float(row.identity_consistency or 0)
                + float(row.style_consistency or 0)
                + row.validation_pass_rate
            ) / 3.0
            reliability = row.success_rate * (1.0 - row.retry_rate)
            latency = _inverse_normalized(
                float(row.average_latency_ms or row.p95_latency_ms or 0),
                max_latency,
            )
            if row.average_cost_usd is None:
                # Unknown pricing must not be interpreted as free/cheap.
                cost = 0.0
            elif max_cost <= 0:
                cost = 0.5
            elif max_cost == min_cost:
                cost = 0.5
            else:
                cost = max(
                    0.0,
                    min(
                        1.0,
                        1.0
                        - (
                            (float(row.average_cost_usd) - min_cost)
                            / (max_cost - min_cost)
                        ),
                    ),
                )
            score = (
                policy.quality_weight * quality
                + policy.reliability_weight * reliability
                + policy.latency_weight * latency
                + policy.cost_weight * cost
            )
            scored.append((score, row))

        scored.sort(key=lambda item: (-item[0], item[1].model_id))
        winners = scored[: policy.top_k_per_cell]
        for score, row in winners:
            selected_cells.append(
                {
                    "model_id": row.model_id,
                    "style_id": style_id,
                    "category": category,
                    "screen_score": round(score, 6),
                    "screen_runs": row.runs,
                    "identity_consistency": row.identity_consistency,
                    "style_consistency": row.style_consistency,
                    "average_latency_ms": row.average_latency_ms,
                    "average_cost_usd": row.average_cost_usd,
                }
            )
        groups.append(
            {
                "style_id": style_id,
                "category": category,
                "candidate_count": len(candidates),
                "eligible_count": len(eligible),
                "selected_count": len(winners),
            }
        )

    return {
        "schema": "visual-screening-shortlist.v1",
        "source_report": report.get("name"),
        "top_k_per_cell": policy.top_k_per_cell,
        "selected_cells": selected_cells,
        "selected_cells_count": len(selected_cells),
        "groups": groups,
        "groups_without_candidates": sum(
            1 for group in groups if group["selected_count"] == 0
        ),
    }


def build_promotion_config(
    *,
    base_config: dict[str, Any],
    shortlist: dict[str, Any],
    seed_report_path: str,
    policy: VisualScreeningPolicy,
) -> dict[str, Any]:
    if shortlist.get("schema") != "visual-screening-shortlist.v1":
        raise RuntimeError("Unsupported visual screening shortlist schema")
    selected = shortlist.get("selected_cells") or []
    if not selected:
        raise RuntimeError("Visual screening produced no promotion candidates")

    config = copy.deepcopy(base_config)
    config["name"] = policy.promotion_name or f"{base_config['name']}-promotion"
    config.pop("models", None)
    config.pop("styles", None)
    config.pop("categories", None)
    config.pop("screening", None)
    config["cells"] = [
        {
            "model_id": item["model_id"],
            "style_id": item["style_id"],
            "category": item["category"],
        }
        for item in selected
    ]
    config["seed_reports"] = [seed_report_path]
    target_min_runs = int((base_config.get("thresholds") or {}).get("min_runs") or 3)
    minimum_screen_runs = min(
        int(item.get("screen_runs") or 0)
        for item in selected
    )
    additional_runs = max(
        policy.promotion_additional_runs_per_cell,
        target_min_runs - minimum_screen_runs,
        1,
    )
    config["runs_per_cell"] = additional_runs

    new_generation_calls = len(config["cells"]) * additional_runs
    config["execution_guard"] = {
        "max_generation_calls": new_generation_calls,
        "max_evaluator_calls": new_generation_calls,
        "max_total_provider_calls": new_generation_calls * 2,
        "max_known_generation_cost_usd": (
            policy.promotion_max_known_generation_cost_usd
        ),
        "fail_on_unknown_pricing": False,
        "require_explicit_paid_authorization": True,
    }
    config["promotion_source"] = {
        "schema": shortlist["schema"],
        "source_report": shortlist.get("source_report"),
        "top_k_per_cell": shortlist["top_k_per_cell"],
        "seed_report_path": seed_report_path,
        "target_min_runs": target_min_runs,
        "minimum_screen_runs": minimum_screen_runs,
        "additional_runs_per_cell": additional_runs,
    }
    return config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a no-cost promotion shortlist from a visual screen"
    )
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--base-config", type=Path, required=True)
    parser.add_argument("--shortlist-out", type=Path, required=True)
    parser.add_argument("--promotion-config-out", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    base_config = yaml.safe_load(args.base_config.read_text(encoding="utf-8")) or {}
    policy = VisualScreeningPolicy.model_validate(base_config.get("screening") or {})
    shortlist = select_visual_promotion_cells(report, policy=policy)
    promotion = build_promotion_config(
        base_config=base_config,
        shortlist=shortlist,
        seed_report_path=str(args.report),
        policy=policy,
    )

    args.shortlist_out.parent.mkdir(parents=True, exist_ok=True)
    args.promotion_config_out.parent.mkdir(parents=True, exist_ok=True)
    args.shortlist_out.write_text(
        json.dumps(shortlist, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    args.promotion_config_out.write_text(
        yaml.safe_dump(promotion, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "selected_cells": shortlist["selected_cells_count"],
                "groups_without_candidates": shortlist["groups_without_candidates"],
                "promotion_additional_runs_per_cell": (
                    promotion["runs_per_cell"]
                ),
                "promotion_generation_calls": (
                    shortlist["selected_cells_count"]
                    * promotion["runs_per_cell"]
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
