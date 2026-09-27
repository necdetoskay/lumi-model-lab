from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from src.visual_contracts import (
    CharacterSceneVisualState,
    CharacterVisualProfile,
    StoryVisualState,
    VisualCategory,
    VisualIntent,
    VisualRequest,
    WorldVisualProfile,
)
from src.visual_generation import generate_visual
from src.visual_model_registry import resolve_visual_model_profile
from src.visual_provider import FixtureVisualProviderAdapter, OpenRouterImageAdapter
from src.visual_qualification import (
    VisualQualificationObservation,
    VisualQualificationThresholds,
    aggregate_visual_qualification,
)
from src.visual_router import route_visual_model
from src.visual_semantic_evaluator import (
    FixtureVisualSemanticEvaluator,
    OpenRouterVisualSemanticEvaluator,
    evaluate_visual_artifact,
)


def load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != "visual-qualification.v1":
        raise RuntimeError(
            f"Unsupported visual qualification schema: {payload.get('schema_version')!r}"
        )
    return payload


def _character(payload: dict[str, Any]) -> CharacterVisualProfile:
    return CharacterVisualProfile.model_validate(payload)


def _world(payload: dict[str, Any]) -> WorldVisualProfile:
    return WorldVisualProfile.model_validate(payload)


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _matrix_definition(
    config: dict[str, Any],
) -> tuple[list[str], list[str], list[VisualCategory], int, list[dict[str, str]]]:
    runs_per_cell = int(config.get("runs_per_cell") or 1)
    if runs_per_cell < 1:
        raise RuntimeError("Qualification config runs_per_cell must be >= 1")

    explicit_cells = config.get("cells") or []
    if explicit_cells:
        if not isinstance(explicit_cells, list):
            raise RuntimeError("Qualification config cells must be a list")
        cells: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for raw in explicit_cells:
            if not isinstance(raw, dict):
                raise RuntimeError("Qualification config cell must be an object")
            model_id = str(raw.get("model_id") or "").strip()
            style_id = str(raw.get("style_id") or "").strip()
            category = VisualCategory(str(raw.get("category") or ""))
            if not model_id or not style_id:
                raise RuntimeError(
                    "Qualification config explicit cells require model_id and style_id"
                )
            key = (model_id, style_id, category.value)
            if key in seen:
                raise RuntimeError(
                    "Qualification config contains duplicate explicit cell: "
                    + "/".join(key)
                )
            seen.add(key)
            cells.append(
                {
                    "model_id": model_id,
                    "style_id": style_id,
                    "category": category.value,
                }
            )
        models = _ordered_unique([cell["model_id"] for cell in cells])
        styles = _ordered_unique([cell["style_id"] for cell in cells])
        categories = [
            VisualCategory(value)
            for value in _ordered_unique([cell["category"] for cell in cells])
        ]
        return models, styles, categories, runs_per_cell, cells

    models = [str(item) for item in config.get("models") or []]
    styles = [str(item) for item in config.get("styles") or []]
    categories = [VisualCategory(str(item)) for item in config.get("categories") or []]
    if not models or not styles or not categories:
        raise RuntimeError(
            "Qualification config requires models/styles/categories or explicit cells"
        )
    cells = [
        {
            "model_id": model_id,
            "style_id": style_id,
            "category": category.value,
        }
        for model_id in models
        for style_id in styles
        for category in categories
    ]
    return models, styles, categories, runs_per_cell, cells


def _load_seed_observations(
    config: dict[str, Any],
    *,
    allowed_cells: set[tuple[str, str, str]],
    provider_mode: str,
    evaluator_mode: str,
) -> list[VisualQualificationObservation]:
    seed_reports = [str(item) for item in config.get("seed_reports") or []]
    if len(seed_reports) != len(set(seed_reports)):
        raise RuntimeError("Qualification config seed_reports contains duplicates")

    observations: list[VisualQualificationObservation] = []
    for raw_path in seed_reports:
        path = Path(raw_path)
        if not path.exists():
            raise RuntimeError(f"Visual qualification seed report does not exist: {path}")
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("schema") != "visual-qualification-report.v1":
            raise RuntimeError(f"Unsupported visual seed report schema: {path}")
        if str(report.get("provider_mode")) != provider_mode:
            raise RuntimeError(f"Visual seed provider mode mismatch: {path}")
        if str(report.get("evaluator_mode")) != evaluator_mode:
            raise RuntimeError(f"Visual seed evaluator mode mismatch: {path}")

        for raw in report.get("observations") or []:
            observation = VisualQualificationObservation.model_validate(raw)
            key = (
                observation.model_id,
                observation.style_id,
                observation.category.value,
            )
            if key in allowed_cells:
                observations.append(observation)
    return observations


def build_qualification_plan(config: dict[str, Any]) -> dict[str, Any]:
    models, styles, categories, runs_per_cell, candidate_cells = _matrix_definition(config)
    provider_mode = str(config.get("provider_mode") or "fixture")
    evaluator_mode = str(config.get("evaluator_mode") or "fixture")
    cells: list[dict[str, str]] = []
    skipped_cells: list[dict[str, str]] = []
    unknown_pricing_models: set[str] = set()
    known_generation_cost_usd = 0.0

    for cell in candidate_cells:
        model_id = cell["model_id"]
        style_id = cell["style_id"]
        category = VisualCategory(cell["category"])
        profile = resolve_visual_model_profile(model_id)

        if category not in profile.supported_categories:
            skipped_cells.append({**cell, "reason": "CATEGORY_UNSUPPORTED"})
            continue
        if profile.supported_styles and style_id not in profile.supported_styles:
            skipped_cells.append({**cell, "reason": "STYLE_UNSUPPORTED"})
            continue

        cells.append(cell)
        hint = profile.pricing.published_hint
        unit = profile.pricing.published_unit
        if hint is not None and unit == "image":
            known_generation_cost_usd += float(hint) * runs_per_cell
        elif profile.provider != "fixture":
            unknown_pricing_models.add(model_id)

    allowed_cells = {
        (cell["model_id"], cell["style_id"], cell["category"]) for cell in cells
    }
    seed_observations = _load_seed_observations(
        config,
        allowed_cells=allowed_cells,
        provider_mode=provider_mode,
        evaluator_mode=evaluator_mode,
    )
    seed_runs: dict[tuple[str, str, str], int] = defaultdict(int)
    for observation in seed_observations:
        seed_runs[
            (
                observation.model_id,
                observation.style_id,
                observation.category.value,
            )
        ] += 1

    thresholds = VisualQualificationThresholds.model_validate(
        config.get("thresholds") or {}
    )
    cells_reaching_min_runs = sum(
        1
        for cell in cells
        if seed_runs[(cell["model_id"], cell["style_id"], cell["category"])]
        + runs_per_cell
        >= thresholds.min_runs
    )

    generation_calls = len(cells) * runs_per_cell
    evaluator_calls = generation_calls
    return {
        "schema": "visual-qualification-plan.v1",
        "name": config["name"],
        "provider_mode": provider_mode,
        "evaluator_mode": evaluator_mode,
        "models": models,
        "styles": styles,
        "categories": [item.value for item in categories],
        "runs_per_cell": runs_per_cell,
        "candidate_cells": len(candidate_cells),
        "executable_cells": len(cells),
        "skipped_cells_count": len(skipped_cells),
        "generation_calls": generation_calls,
        "evaluator_calls": evaluator_calls,
        "total_provider_calls": generation_calls
        + (evaluator_calls if evaluator_mode == "openrouter" else 0),
        "known_generation_cost_usd": round(known_generation_cost_usd, 6),
        "unknown_pricing_models": sorted(unknown_pricing_models),
        "evaluator_cost_known": evaluator_mode == "fixture",
        "seed_reports": [str(item) for item in config.get("seed_reports") or []],
        "seed_observations_count": len(seed_observations),
        "cells_reaching_min_runs": cells_reaching_min_runs,
        "minimum_runs_required": thresholds.min_runs,
        "cells": cells,
        "skipped_cells": skipped_cells,
    }


def plan_visual_qualification(config_path: Path) -> dict[str, Any]:
    return build_qualification_plan(load_config(config_path))


def _enforce_execution_guard(
    config: dict[str, Any],
    plan: dict[str, Any],
    *,
    authorize_paid: bool,
) -> None:
    guard = dict(config.get("execution_guard") or {})
    is_live = plan["provider_mode"] != "fixture" or plan["evaluator_mode"] != "fixture"

    if is_live and bool(guard.get("require_explicit_paid_authorization", True)):
        if not authorize_paid:
            raise RuntimeError(
                "LIVE_VISUAL_QUALIFICATION_NOT_AUTHORIZED: "
                "explicit paid authorization is required"
            )

    limits = {
        "max_generation_calls": "generation_calls",
        "max_evaluator_calls": "evaluator_calls",
        "max_total_provider_calls": "total_provider_calls",
    }
    for config_key, plan_key in limits.items():
        limit = guard.get(config_key)
        if limit is not None and int(plan[plan_key]) > int(limit):
            raise RuntimeError(
                "VISUAL_QUALIFICATION_GUARD_EXCEEDED: "
                f"{plan_key}={plan[plan_key]} > {config_key}={limit}"
            )

    known_cost_limit = guard.get("max_known_generation_cost_usd")
    if (
        known_cost_limit is not None
        and float(plan["known_generation_cost_usd"]) > float(known_cost_limit)
    ):
        raise RuntimeError(
            "VISUAL_QUALIFICATION_GUARD_EXCEEDED: "
            f"known_generation_cost_usd={plan['known_generation_cost_usd']} "
            f"> max_known_generation_cost_usd={known_cost_limit}"
        )

    if guard.get("fail_on_unknown_pricing") and plan["unknown_pricing_models"]:
        raise RuntimeError(
            "VISUAL_QUALIFICATION_UNKNOWN_PRICING: "
            + ", ".join(plan["unknown_pricing_models"])
        )


def _request(
    config: dict[str, Any],
    *,
    model_id: str,
    style_id: str,
    category: VisualCategory,
    run_index: int,
) -> VisualRequest:
    fixture = config["fixture"]
    intent_payload = dict((fixture.get("intents") or {}).get(category.value) or {})
    if not intent_payload:
        raise RuntimeError(f"Qualification fixture missing intent for {category.value}")
    character = _character(fixture["character"])
    world = _world(fixture["world"])
    kwargs: dict[str, Any] = {}
    if category in {VisualCategory.CHARACTER_PORTRAIT, VisualCategory.CHARACTER_SCENE}:
        kwargs["character_profile"] = character
    if category in {
        VisualCategory.ENVIRONMENT,
        VisualCategory.WORLD_KEY_ART,
        VisualCategory.MAP_ART,
    }:
        kwargs["world_profile"] = world
    if category == VisualCategory.COVER_ART:
        kwargs["character_profile"] = character
        kwargs["world_profile"] = world
    if category == VisualCategory.CHARACTER_SCENE:
        kwargs["story_visual_state"] = StoryVisualState(
            story_id="visual-qualification-story",
            scene_id="scene-1",
            character_states={
                character.character_id: CharacterSceneVisualState(
                    clothing_changes=["right sleeve lightly muddy"],
                    inventory_visible=["small silver key"],
                )
            },
            weather="light rain",
            time_of_day="late afternoon",
        )
    return VisualRequest(
        request_id=(
            f"{config['name']}:{model_id}:{style_id}:{category.value}:{run_index}"
        ),
        profile_id="visual-qualification-profile",
        category=category,
        intent=VisualIntent.model_validate(intent_payload),
        style_id=style_id,
        model_id=model_id,
        quality_tier=config.get("quality_tier", "STANDARD"),
        aspect_ratio=str(config.get("aspect_ratio") or "3:4"),
        **kwargs,
    )


def run_visual_qualification(
    config_path: Path,
    *,
    evidence_dir: Path | None = None,
    authorize_paid: bool = False,
) -> dict[str, Any]:
    config = load_config(config_path)
    plan = build_qualification_plan(config)
    _enforce_execution_guard(config, plan, authorize_paid=authorize_paid)

    evidence_dir = evidence_dir or Path(
        str(config.get("evidence_dir") or "runs/visual_qualification")
    ) / config["name"]
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "qualification_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    mode = plan["provider_mode"]
    evaluator_mode = plan["evaluator_mode"]
    api_key = os.getenv("OPENROUTER_API_KEY")

    if mode == "fixture":
        adapter = FixtureVisualProviderAdapter()
    elif mode == "openrouter":
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is required for live visual qualification"
            )
        adapter = OpenRouterImageAdapter(api_key=api_key)
    else:
        raise RuntimeError(f"Unsupported provider_mode: {mode}")

    if evaluator_mode == "fixture":
        evaluator = FixtureVisualSemanticEvaluator()
    elif evaluator_mode == "openrouter":
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for live visual evaluation")
        evaluator = OpenRouterVisualSemanticEvaluator(
            api_key=api_key,
            model_id=str(config.get("evaluator_model") or "openai/gpt-5.6-luna"),
        )
    else:
        raise RuntimeError(f"Unsupported evaluator_mode: {evaluator_mode}")

    allowed_cells = {
        (cell["model_id"], cell["style_id"], cell["category"])
        for cell in plan["cells"]
    }
    seed_observations = _load_seed_observations(
        config,
        allowed_cells=allowed_cells,
        provider_mode=mode,
        evaluator_mode=evaluator_mode,
    )
    new_observations: list[VisualQualificationObservation] = []

    for cell in plan["cells"]:
        model_id = cell["model_id"]
        style_id = cell["style_id"]
        category = VisualCategory(cell["category"])
        for run_index in range(1, int(plan["runs_per_cell"]) + 1):
            request = _request(
                config,
                model_id=model_id,
                style_id=style_id,
                category=category,
                run_index=run_index,
            )
            result = generate_visual(
                request,
                adapter=adapter,
                evidence_dir=evidence_dir,
                require_qualified=False,
            )
            evaluation = evaluate_visual_artifact(
                request=request,
                artifact=result.artifacts[0],
                evaluator=evaluator,
                evidence_dir=evidence_dir,
            )
            new_observations.append(
                VisualQualificationObservation(
                    model_id=model_id,
                    style_id=style_id,
                    category=category,
                    success=result.invocation.status == "SUCCESS",
                    validation_pass=evaluation.result.status.value == "PASS",
                    identity_consistency=evaluation.result.identity_consistency,
                    style_consistency=evaluation.result.style_consistency,
                    latency_ms=result.invocation.latency_ms,
                    cost_usd=result.invocation.cost_usd,
                    retry_count=result.invocation.retry_attempt,
                )
            )

    observations = seed_observations + new_observations
    thresholds = VisualQualificationThresholds.model_validate(
        config.get("thresholds") or {}
    )
    rows = aggregate_visual_qualification(observations, thresholds=thresholds)
    routes: list[dict[str, Any]] = []
    for style_id in plan["styles"]:
        for category_value in plan["categories"]:
            category = VisualCategory(category_value)
            try:
                route = route_visual_model(
                    category=category,
                    style_id=style_id,
                    rows=rows,
                )
            except RuntimeError:
                continue
            routes.append(route.model_dump(mode="json"))

    report = {
        "schema": "visual-qualification-report.v1",
        "name": config["name"],
        "provider_mode": mode,
        "evaluator_mode": evaluator_mode,
        "models": plan["models"],
        "styles": plan["styles"],
        "categories": plan["categories"],
        "runs_per_cell": plan["runs_per_cell"],
        "quality_tier": str(config.get("quality_tier") or "STANDARD"),
        "aspect_ratio": str(config.get("aspect_ratio") or "3:4"),
        "thresholds": (config.get("thresholds") or {}),
        "plan": {
            key: value
            for key, value in plan.items()
            if key not in {"cells", "skipped_cells"}
        },
        "seed_observations_count": len(seed_observations),
        "new_observations": [
            item.model_dump(mode="json") for item in new_observations
        ],
        "observations": [item.model_dump(mode="json") for item in observations],
        "rows": [item.model_dump(mode="json") for item in rows],
        "routes": routes,
        "qualified_rows": sum(row.qualified for row in rows),
        "total_rows": len(rows),
    }
    (evidence_dir / "qualification_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LUMI visual qualification matrix")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Print the resolved matrix/call/cost plan without provider access.",
    )
    parser.add_argument(
        "--authorize-paid",
        action="store_true",
        help="Explicitly authorize a live provider/evaluator run.",
    )
    args = parser.parse_args()

    if args.plan_only:
        print(
            json.dumps(
                plan_visual_qualification(args.config),
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    report = run_visual_qualification(
        args.config,
        evidence_dir=args.evidence_dir,
        authorize_paid=args.authorize_paid,
    )
    print(
        json.dumps(
            {
                "name": report["name"],
                "qualified_rows": report["qualified_rows"],
                "total_rows": report["total_rows"],
                "routes": len(report["routes"]),
                "generation_calls": report["plan"]["generation_calls"],
                "evaluator_calls": report["plan"]["evaluator_calls"],
                "seed_observations_count": report["seed_observations_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
