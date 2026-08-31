from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.generate import count_words, load_yaml, parse_cost, parse_usage, validate_generation
from src.generator_benchmark_v2 import repeated_ngram_ratio, save_json
from src.generator_scene_first_calibration import (
    GENERATION_CONFIG_PATH,
    _brief_text,
    _call_with_retry,
    _plan_story,
    _sum_optional,
    _write_scene,
)
from src.schemas import StorySpec

CONFIG_PATH = Path("configs/generator_scene_first_calibration_v2.yaml")
REPAIR_PROMPT_PATH = Path("prompts/story_scene_repair.md")
PROMPT_VERSION = "story_scene_first_v0.2"


def _repair_scene(
    *,
    api_key: str,
    model: str,
    spec: StorySpec,
    plan: dict[str, Any],
    scene: dict[str, Any],
    scene_index: int,
    word_budget: int,
    story_so_far: str,
    current_draft: str,
    generation_config: dict[str, Any],
    config: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    min_words = round(word_budget * float(config.get("scene_min_word_ratio", 0.90)))
    max_words = round(word_budget * float(config.get("scene_max_word_ratio", 1.10)))
    user_prompt = f"""STORY BRIEF
{_brief_text(spec)}

COMPLETE SCENE PLAN
{json.dumps(plan, ensure_ascii=False, indent=2)}

PRIOR STORY PROSE
{story_so_far if story_so_far else '[No prior prose; this is the opening scene.]'}

CURRENT SCENE
Index: {scene_index}
Target words: {word_budget}
Required range: {min_words}-{max_words}
Scene specification:
{json.dumps(scene, ensure_ascii=False, indent=2)}

UNDERFILLED DRAFT
{current_draft}

Rewrite only scene {scene_index} so it lands inside {min_words}-{max_words} words while preserving continuity and the planned handoff."""
    text, body, _payload, attempts, retry_errors = _call_with_retry(
        api_key=api_key,
        model=model,
        system_prompt=REPAIR_PROMPT_PATH.read_text(encoding="utf-8").strip(),
        user_prompt=user_prompt,
        generation_config=generation_config,
        max_retries=int(config.get("max_retries", 5)),
        retry_base_seconds=float(config.get("retry_base_seconds", 5.0)),
    )
    return text.strip(), {
        "attempts": attempts,
        "retry_errors": retry_errors,
        "usage": parse_usage(body).model_dump(mode="json"),
        "cost": parse_cost(body).model_dump(mode="json"),
        "provider": body.get("provider"),
    }


def _choose_scene_version(candidates: list[str], target: int, min_words: int, max_words: int) -> str:
    inside = [text for text in candidates if min_words <= count_words(text) <= max_words]
    pool = inside or candidates
    return min(pool, key=lambda text: abs(count_words(text) - target))


def run_model(model: str, spec: StorySpec, config: dict[str, Any], generation_config: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    started = time.perf_counter()
    plan, plan_meta = _plan_story(
        api_key=api_key,
        model=model,
        spec=spec,
        generation_config=generation_config,
        config=config,
    )
    budgets = [int(value) for value in config["scene_word_budgets"]]
    scene_texts: list[str] = []
    scene_meta: list[dict[str, Any]] = []
    all_costs: list[float | None] = [plan_meta["cost"].get("usd")]
    all_costs_try: list[float | None] = [plan_meta["cost"].get("try_amount")]
    retry_count = max(0, int(plan_meta["attempts"]) - 1)

    for index, (scene, budget) in enumerate(zip(plan["scenes"], budgets, strict=True), start=1):
        story_so_far = "\n\n".join(scene_texts)
        initial, initial_meta = _write_scene(
            api_key=api_key,
            model=model,
            spec=spec,
            plan=plan,
            scene=scene,
            scene_index=index,
            word_budget=budget,
            story_so_far=story_so_far,
            generation_config=generation_config,
            config={**config, "scene_tolerance_ratio": 1 - float(config.get("scene_min_word_ratio", 0.90))},
        )
        candidates = [initial]
        repairs: list[dict[str, Any]] = []
        all_costs.append(initial_meta["cost"].get("usd"))
        all_costs_try.append(initial_meta["cost"].get("try_amount"))
        retry_count += max(0, int(initial_meta["attempts"]) - 1)

        min_words = round(budget * float(config.get("scene_min_word_ratio", 0.90)))
        max_words = round(budget * float(config.get("scene_max_word_ratio", 1.10)))
        for _ in range(int(config.get("scene_repair_attempts", 2))):
            current = _choose_scene_version(candidates, budget, min_words, max_words)
            if min_words <= count_words(current) <= max_words:
                break
            repaired, repair_meta = _repair_scene(
                api_key=api_key,
                model=model,
                spec=spec,
                plan=plan,
                scene=scene,
                scene_index=index,
                word_budget=budget,
                story_so_far=story_so_far,
                current_draft=current,
                generation_config=generation_config,
                config=config,
            )
            candidates.append(repaired)
            repairs.append({
                "actual_words": count_words(repaired),
                **repair_meta,
            })
            all_costs.append(repair_meta["cost"].get("usd"))
            all_costs_try.append(repair_meta["cost"].get("try_amount"))
            retry_count += max(0, int(repair_meta["attempts"]) - 1)

        selected = _choose_scene_version(candidates, budget, min_words, max_words)
        scene_texts.append(selected)
        scene_meta.append({
            "index": index,
            "target_words": budget,
            "required_min_words": min_words,
            "required_max_words": max_words,
            "initial_words": count_words(initial),
            "actual_words": count_words(selected),
            "scene_pass": min_words <= count_words(selected) <= max_words,
            "initial": initial_meta,
            "repairs": repairs,
        })

    title = str(plan.get("story_title") or spec.title_hint or "").strip()
    body = "\n\n".join(scene_texts).strip()
    final_story = f"{title}\n\n{body}" if title else body
    validation = validate_generation(
        story=final_story,
        spec=spec,
        finish_reason="stop",
        min_word_ratio=float(config.get("final_min_word_ratio", 0.90)),
        max_word_ratio=float(config.get("final_max_word_ratio", 1.10)),
    )
    return {
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "story_title": title,
        "plan": plan,
        "scenes": scene_meta,
        "story": final_story,
        "word_count": validation.word_count,
        "target_words": validation.target_words,
        "technical_pass": validation.eligible_for_judge,
        "technical_reasons": validation.reasons,
        "all_scenes_pass": all(bool(item["scene_pass"]) for item in scene_meta),
        "repeat_8gram_ratio": repeated_ngram_ratio(final_story, 8),
        "latency_seconds": round(time.perf_counter() - started, 3),
        "retry_count": retry_count,
        "plan_retry_errors": plan_meta["retry_errors"],
        "cost_usd": _sum_optional(all_costs),
        "cost_try": _sum_optional(all_costs_try),
    }


def main() -> None:
    load_dotenv()
    config = load_yaml(CONFIG_PATH)
    generation_config = load_yaml(GENERATION_CONFIG_PATH)
    spec = StorySpec.model_validate(load_yaml(Path(str(config["spec"]))))
    output_dir = Path(str(config["output_dir"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    manifest = {"benchmark": config["name"], "prompt_version": PROMPT_VERSION, "entries": []}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    existing_models = {
        str(entry.get("model"))
        for entry in manifest.get("entries", [])
        if entry.get("status") == "complete"
    }
    for model in [str(value) for value in config["models"]]:
        if model in existing_models:
            print(f"Skip existing {model}")
            continue
        print(f"Generate scene-first v0.2 | {model}")
        entry: dict[str, Any] = {"model": model, "status": "running"}
        manifest.setdefault("entries", []).append(entry)
        save_json(manifest_path, manifest)
        try:
            result = run_model(model, spec, config, generation_config)
            entry.update(result)
            entry["status"] = "complete"
            story_path = output_dir / f"{re.sub(r'[^a-zA-Z0-9._-]+', '_', model)}.story.txt"
            story_path.write_text(str(result["story"]), encoding="utf-8")
            entry["story_path"] = str(story_path)
        except Exception as exc:
            entry.update({"status": "error", "error": str(exc)})
        finally:
            save_json(manifest_path, manifest)

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
