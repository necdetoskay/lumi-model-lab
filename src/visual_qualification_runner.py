from __future__ import annotations

import argparse
import json
import os
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
    if category in {VisualCategory.ENVIRONMENT, VisualCategory.WORLD_KEY_ART, VisualCategory.MAP_ART}:
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
        request_id=f"{config['name']}:{model_id}:{style_id}:{category.value}:{run_index}",
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
) -> dict[str, Any]:
    config = load_config(config_path)
    evidence_dir = evidence_dir or Path(str(config.get("evidence_dir") or "runs/visual_qualification")) / config["name"]
    evidence_dir.mkdir(parents=True, exist_ok=True)
    mode = str(config.get("provider_mode") or "fixture")
    evaluator_mode = str(config.get("evaluator_mode") or "fixture")
    api_key = os.getenv("OPENROUTER_API_KEY")

    if mode == "fixture":
        adapter = FixtureVisualProviderAdapter()
    elif mode == "openrouter":
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for live visual qualification")
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

    models = [str(item) for item in config.get("models") or []]
    styles = [str(item) for item in config.get("styles") or []]
    categories = [VisualCategory(str(item)) for item in config.get("categories") or []]
    runs_per_cell = int(config.get("runs_per_cell") or 1)
    if not models or not styles or not categories:
        raise RuntimeError("Qualification config requires models, styles and categories")

    observations: list[VisualQualificationObservation] = []
    for model_id in models:
        for style_id in styles:
            for category in categories:
                for run_index in range(1, runs_per_cell + 1):
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
                    observations.append(
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

    thresholds = VisualQualificationThresholds.model_validate(config.get("thresholds") or {})
    rows = aggregate_visual_qualification(observations, thresholds=thresholds)
    routes: list[dict[str, Any]] = []
    for style_id in styles:
        for category in categories:
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
        "models": models,
        "styles": styles,
        "categories": [item.value for item in categories],
        "runs_per_cell": runs_per_cell,
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
    args = parser.parse_args()
    report = run_visual_qualification(args.config, evidence_dir=args.evidence_dir)
    print(json.dumps(
        {
            "name": report["name"],
            "qualified_rows": report["qualified_rows"],
            "total_rows": report["total_rows"],
            "routes": len(report["routes"]),
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
