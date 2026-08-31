from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.generate import (
    call_openrouter,
    count_words,
    load_yaml,
    parse_cost,
    parse_usage,
    validate_generation,
)
from src.generator_benchmark_v2 import repeated_ngram_ratio, save_json
from src.schemas import StorySpec


CONFIG_PATH = Path("configs/generator_scene_first_calibration.yaml")
GENERATION_CONFIG_PATH = Path("configs/generation_benchmark_v2.yaml")
PLAN_PROMPT_PATH = Path("prompts/story_scene_plan.md")
SCENE_PROMPT_PATH = Path("prompts/story_scene_writer.md")
PROMPT_VERSION = "story_scene_first_v0.1"


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("Scene planner response did not contain a JSON object.")
        value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise RuntimeError("Scene planner response JSON must be an object.")
    scenes = value.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != 6:
        raise RuntimeError("Scene planner must return exactly 6 scenes.")
    return value


def _brief_text(spec: StorySpec) -> str:
    constraints = "\n".join(f"- {item}" for item in spec.constraints) or "- None"
    return f"""Language: {spec.language}
Age range: {spec.age_min}-{spec.age_max}
Target words: {spec.target_words}
Title hint: {spec.title_hint or 'None'}
Protagonist: {spec.protagonist}
Setting: {spec.setting}
Theme: {spec.theme}
Premise: {spec.premise}
Constraints:
{constraints}"""


def _call_with_retry(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    generation_config: dict[str, Any],
    max_retries: int,
    retry_base_seconds: float,
) -> tuple[str, dict[str, Any], dict[str, Any], int, list[str]]:
    teacher = generation_config["teacher"]
    errors: list[str] = []
    for attempt in range(1, max_retries + 1):
        try:
            story, body, payload = call_openrouter(
                api_key=api_key,
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=float(teacher.get("temperature", 0.8)),
                max_tokens=int(teacher.get("max_tokens", 7000)),
                seed=generation_config.get("seed"),
            )
            return story, body, payload, attempt, errors
        except Exception as exc:
            message = str(exc)
            errors.append(message)
            transient = "HTTP 429" in message or "HTTP 500" in message or "HTTP 502" in message or "HTTP 503" in message or "HTTP 504" in message
            if not transient or attempt >= max_retries:
                raise
            time.sleep(retry_base_seconds * attempt)
    raise RuntimeError("Retry loop exhausted unexpectedly.")


def _plan_story(
    *, api_key: str, model: str, spec: StorySpec, generation_config: dict[str, Any], config: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    text, body, _payload, attempts, retry_errors = _call_with_retry(
        api_key=api_key,
        model=model,
        system_prompt=PLAN_PROMPT_PATH.read_text(encoding="utf-8").strip(),
        user_prompt=f"Create the 6-scene plan for this story.\n\n{_brief_text(spec)}",
        generation_config=generation_config,
        max_retries=int(config.get("max_retries", 3)),
        retry_base_seconds=float(config.get("retry_base_seconds", 2.0)),
    )
    return _extract_json_object(text), {
        "attempts": attempts,
        "retry_errors": retry_errors,
        "usage": parse_usage(body).model_dump(mode="json"),
        "cost": parse_cost(body).model_dump(mode="json"),
        "provider": body.get("provider"),
    }


def _write_scene(
    *,
    api_key: str,
    model: str,
    spec: StorySpec,
    plan: dict[str, Any],
    scene: dict[str, Any],
    scene_index: int,
    word_budget: int,
    story_so_far: str,
    generation_config: dict[str, Any],
    config: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    tolerance = float(config.get("scene_tolerance_ratio", 0.20))
    min_words = round(word_budget * (1 - tolerance))
    max_words = round(word_budget * (1 + tolerance))
    user_prompt = f"""STORY BRIEF
{_brief_text(spec)}

COMPLETE SCENE PLAN
{json.dumps(plan, ensure_ascii=False, indent=2)}

CURRENT SCENE
Index: {scene_index}
Target words: {word_budget}
Preferred range: {min_words}-{max_words}
Scene specification:
{json.dumps(scene, ensure_ascii=False, indent=2)}

STORY SO FAR
{story_so_far if story_so_far else '[No prose yet; this is the opening scene.]'}

Write only scene {scene_index}. Do not rewrite prior prose."""
    text, body, _payload, attempts, retry_errors = _call_with_retry(
        api_key=api_key,
        model=model,
        system_prompt=SCENE_PROMPT_PATH.read_text(encoding="utf-8").strip(),
        user_prompt=user_prompt,
        generation_config=generation_config,
        max_retries=int(config.get("max_retries", 3)),
        retry_base_seconds=float(config.get("retry_base_seconds", 2.0)),
    )
    return text.strip(), {
        "index": scene_index,
        "target_words": word_budget,
        "actual_words": count_words(text),
        "attempts": attempts,
        "retry_errors": retry_errors,
        "usage": parse_usage(body).model_dump(mode="json"),
        "cost": parse_cost(body).model_dump(mode="json"),
        "provider": body.get("provider"),
    }


def _sum_optional(values: list[float | None]) -> float | None:
    present = [float(value) for value in values if value is not None]
    return sum(present) if present else None


def run_model(model: str, spec: StorySpec, config: dict[str, Any], generation_config: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    started = time.perf_counter()
    plan, plan_meta = _plan_story(api_key=api_key, model=model, spec=spec, generation_config=generation_config, config=config)
    budgets = [int(value) for value in config["scene_word_budgets"]]
    scenes = plan["scenes"]
    scene_texts: list[str] = []
    scene_meta: list[dict[str, Any]] = []
    for index, (scene, budget) in enumerate(zip(scenes, budgets, strict=True), start=1):
        story_so_far = "\n\n".join(scene_texts)
        text, meta = _write_scene(
            api_key=api_key,
            model=model,
            spec=spec,
            plan=plan,
            scene=scene,
            scene_index=index,
            word_budget=budget,
            story_so_far=story_so_far,
            generation_config=generation_config,
            config=config,
        )
        scene_texts.append(text)
        scene_meta.append(meta)

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

    costs = [plan_meta["cost"].get("usd")] + [meta["cost"].get("usd") for meta in scene_meta]
    costs_try = [plan_meta["cost"].get("try_amount")] + [meta["cost"].get("try_amount") for meta in scene_meta]
    retry_count = max(0, int(plan_meta["attempts"]) - 1) + sum(max(0, int(meta["attempts"]) - 1) for meta in scene_meta)
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
        "repeat_8gram_ratio": repeated_ngram_ratio(final_story, 8),
        "latency_seconds": round(time.perf_counter() - started, 3),
        "retry_count": retry_count,
        "plan_retry_errors": plan_meta["retry_errors"],
        "scene_retry_errors": [error for meta in scene_meta for error in meta["retry_errors"]],
        "cost_usd": _sum_optional(costs),
        "cost_try": _sum_optional(costs_try),
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

    existing_models = {str(entry.get("model")) for entry in manifest.get("entries", []) if entry.get("status") == "complete"}
    for model in [str(value) for value in config["models"]]:
        if model in existing_models:
            print(f"Skip existing {model}")
            continue
        print(f"Generate scene-first | {model}")
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
