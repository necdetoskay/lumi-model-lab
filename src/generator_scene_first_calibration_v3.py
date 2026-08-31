from __future__ import annotations

import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.generate import call_openrouter, count_words, load_yaml, parse_cost, parse_usage, validate_generation
from src.generator_benchmark_v2 import repeated_ngram_ratio, save_json
from src.generator_scene_first_calibration import GENERATION_CONFIG_PATH, _brief_text, _extract_json_object, _sum_optional
from src.schemas import StorySpec

CONFIG_PATH = Path("configs/generator_scene_first_calibration_v3.yaml")
PLAN_PROMPT_PATH = Path("prompts/story_scene_plan.md")
SCENE_PROMPT_PATH = Path("prompts/story_scene_writer.md")
REPAIR_PROMPT_PATH = Path("prompts/story_scene_repair.md")
PROMPT_VERSION = "story_scene_first_v0.3"


def _is_transient(message: str) -> bool:
    lowered = message.lower()
    tokens = (
        "http 429", "http 500", "http 502", "http 503", "http 504",
        "'code': 429", "'code': 500", "'code': 502", "'code': 503", "'code': 504",
        '"code": 429', '"code": 500', '"code": 502', '"code": 503', '"code": 504',
        "temporarily rate-limited", "upstream error", "internal error occurred",
    )
    return any(token in lowered for token in tokens)


def _call_with_retry_v3(*, api_key: str, model: str, system_prompt: str, user_prompt: str,
                        generation_config: dict[str, Any], max_retries: int,
                        retry_base_seconds: float) -> tuple[str, dict[str, Any], dict[str, Any], int, list[str]]:
    teacher = generation_config["teacher"]
    errors: list[str] = []
    for attempt in range(1, max_retries + 1):
        try:
            text, body, payload = call_openrouter(
                api_key=api_key,
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=float(teacher.get("temperature", 0.8)),
                max_tokens=int(teacher.get("max_tokens", 7000)),
                seed=generation_config.get("seed"),
            )
            return text, body, payload, attempt, errors
        except Exception as exc:
            message = str(exc)
            errors.append(message)
            if not _is_transient(message) or attempt >= max_retries:
                raise
            time.sleep(retry_base_seconds * attempt)
    raise RuntimeError("Retry loop exhausted unexpectedly.")


def _plan_story(*, api_key: str, model: str, spec: StorySpec,
                generation_config: dict[str, Any], config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    text, body, _payload, attempts, errors = _call_with_retry_v3(
        api_key=api_key,
        model=model,
        system_prompt=PLAN_PROMPT_PATH.read_text(encoding="utf-8").strip(),
        user_prompt=f"Create the 6-scene plan for this story.\n\n{_brief_text(spec)}",
        generation_config=generation_config,
        max_retries=int(config.get("max_retries", 5)),
        retry_base_seconds=float(config.get("retry_base_seconds", 5.0)),
    )
    return _extract_json_object(text), {
        "attempts": attempts,
        "retry_errors": errors,
        "usage": parse_usage(body).model_dump(mode="json"),
        "cost": parse_cost(body).model_dump(mode="json"),
        "provider": body.get("provider"),
    }


def _request_scene(*, api_key: str, model: str, spec: StorySpec, plan: dict[str, Any],
                   scene: dict[str, Any], scene_index: int, acceptance_target: int,
                   request_target: int, min_words: int, max_words: int,
                   story_so_far: str, current_draft: str | None,
                   generation_config: dict[str, Any], config: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if current_draft is None:
        system_prompt = SCENE_PROMPT_PATH.read_text(encoding="utf-8").strip()
        draft_section = ""
        instruction = f"Write only scene {scene_index}. Do not rewrite prior prose."
    else:
        system_prompt = REPAIR_PROMPT_PATH.read_text(encoding="utf-8").strip()
        draft_section = f"\nCURRENT DRAFT TO REWRITE\n{current_draft}\n"
        instruction = f"Rewrite only scene {scene_index}; preserve its events and handoff, but adjust narrative density."

    user_prompt = f"""STORY BRIEF
{_brief_text(spec)}

COMPLETE SCENE PLAN
{json.dumps(plan, ensure_ascii=False, indent=2)}

PRIOR STORY PROSE
{story_so_far if story_so_far else '[No prior prose; this is the opening scene.]'}

CURRENT SCENE
Index: {scene_index}
Canonical scene budget: {acceptance_target} words
Accepted final range: {min_words}-{max_words} words
Control target for this attempt: approximately {request_target} words
Scene specification:
{json.dumps(scene, ensure_ascii=False, indent=2)}
{draft_section}
The control target compensates for the previous length error; the accepted scene must still land inside {min_words}-{max_words} words.
Use meaningful action, observation, dialogue, sensory detail, or consequence. Do not add later-scene events or filler.
{instruction}"""
    text, body, _payload, attempts, errors = _call_with_retry_v3(
        api_key=api_key,
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        generation_config=generation_config,
        max_retries=int(config.get("max_retries", 5)),
        retry_base_seconds=float(config.get("retry_base_seconds", 5.0)),
    )
    return text.strip(), {
        "actual_words": count_words(text),
        "request_target_words": request_target,
        "attempts": attempts,
        "retry_errors": errors,
        "usage": parse_usage(body).model_dump(mode="json"),
        "cost": parse_cost(body).model_dump(mode="json"),
        "provider": body.get("provider"),
    }


def _adaptive_target(canonical_target: int, actual_words: int, config: dict[str, Any]) -> int:
    if actual_words <= 0:
        return canonical_target
    factor = canonical_target / actual_words
    factor = max(float(config.get("adaptive_min_factor", 0.65)), min(float(config.get("adaptive_max_factor", 1.60)), factor))
    return max(20, int(round(canonical_target * factor)))


def _choose(candidates: list[tuple[str, dict[str, Any]]], target: int, min_words: int, max_words: int) -> tuple[str, dict[str, Any]]:
    inside = [item for item in candidates if min_words <= count_words(item[0]) <= max_words]
    pool = inside or candidates
    return min(pool, key=lambda item: abs(count_words(item[0]) - target))


def run_model(model: str, spec: StorySpec, config: dict[str, Any], generation_config: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    started = time.perf_counter()
    plan, plan_meta = _plan_story(api_key=api_key, model=model, spec=spec,
                                  generation_config=generation_config, config=config)
    budgets = [int(v) for v in config["scene_word_budgets"]]
    scene_texts: list[str] = []
    scene_meta: list[dict[str, Any]] = []
    costs: list[float | None] = [plan_meta["cost"].get("usd")]
    costs_try: list[float | None] = [plan_meta["cost"].get("try_amount")]
    retry_count = max(0, int(plan_meta["attempts"]) - 1)

    for index, (scene, budget) in enumerate(zip(plan["scenes"], budgets, strict=True), start=1):
        min_words = round(budget * float(config.get("scene_min_word_ratio", 0.90)))
        max_words = round(budget * float(config.get("scene_max_word_ratio", 1.10)))
        story_so_far = "\n\n".join(scene_texts)
        candidates: list[tuple[str, dict[str, Any]]] = []

        text, meta = _request_scene(
            api_key=api_key, model=model, spec=spec, plan=plan, scene=scene,
            scene_index=index, acceptance_target=budget, request_target=budget,
            min_words=min_words, max_words=max_words, story_so_far=story_so_far,
            current_draft=None, generation_config=generation_config, config=config,
        )
        candidates.append((text, meta))
        costs.append(meta["cost"].get("usd")); costs_try.append(meta["cost"].get("try_amount"))
        retry_count += max(0, int(meta["attempts"]) - 1)

        for _ in range(int(config.get("scene_repair_attempts", 3))):
            current_text, _current_meta = _choose(candidates, budget, min_words, max_words)
            current_words = count_words(current_text)
            if min_words <= current_words <= max_words:
                break
            request_target = _adaptive_target(budget, current_words, config)
            repaired, repair_meta = _request_scene(
                api_key=api_key, model=model, spec=spec, plan=plan, scene=scene,
                scene_index=index, acceptance_target=budget, request_target=request_target,
                min_words=min_words, max_words=max_words, story_so_far=story_so_far,
                current_draft=current_text, generation_config=generation_config, config=config,
            )
            candidates.append((repaired, repair_meta))
            costs.append(repair_meta["cost"].get("usd")); costs_try.append(repair_meta["cost"].get("try_amount"))
            retry_count += max(0, int(repair_meta["attempts"]) - 1)

        selected, selected_meta = _choose(candidates, budget, min_words, max_words)
        scene_texts.append(selected)
        scene_meta.append({
            "index": index,
            "target_words": budget,
            "required_min_words": min_words,
            "required_max_words": max_words,
            "actual_words": count_words(selected),
            "scene_pass": min_words <= count_words(selected) <= max_words,
            "attempt_versions": [
                {
                    "actual_words": count_words(text_value),
                    "request_target_words": meta_value.get("request_target_words"),
                    "attempts": meta_value.get("attempts"),
                    "retry_errors": meta_value.get("retry_errors"),
                    "provider": meta_value.get("provider"),
                }
                for text_value, meta_value in candidates
            ],
        })

    title = str(plan.get("story_title") or spec.title_hint or "").strip()
    body = "\n\n".join(scene_texts).strip()
    story = f"{title}\n\n{body}" if title else body
    validation = validate_generation(
        story=story, spec=spec, finish_reason="stop",
        min_word_ratio=float(config.get("final_min_word_ratio", 0.90)),
        max_word_ratio=float(config.get("final_max_word_ratio", 1.10)),
    )
    return {
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "story_title": title,
        "plan": plan,
        "scenes": scene_meta,
        "story": story,
        "word_count": validation.word_count,
        "target_words": validation.target_words,
        "technical_pass": validation.eligible_for_judge,
        "technical_reasons": validation.reasons,
        "all_scenes_pass": all(bool(item["scene_pass"]) for item in scene_meta),
        "repeat_8gram_ratio": repeated_ngram_ratio(story, 8),
        "latency_seconds": round(time.perf_counter() - started, 3),
        "retry_count": retry_count,
        "plan_retry_errors": plan_meta["retry_errors"],
        "cost_usd": _sum_optional(costs),
        "cost_try": _sum_optional(costs_try),
    }


def main() -> None:
    load_dotenv()
    config = load_yaml(CONFIG_PATH)
    generation_config = load_yaml(GENERATION_CONFIG_PATH)
    spec = StorySpec.model_validate(load_yaml(Path(str(config["spec"]))))
    output_dir = Path(str(config["output_dir"])); output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    manifest = {"benchmark": config["name"], "prompt_version": PROMPT_VERSION, "entries": []}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    existing = {str(e.get("model")) for e in manifest.get("entries", []) if e.get("status") == "complete"}
    for model in [str(v) for v in config["models"]]:
        if model in existing:
            print(f"Skip existing {model}")
            continue
        print(f"Generate scene-first v0.3 | {model}")
        entry: dict[str, Any] = {"model": model, "status": "running"}
        manifest.setdefault("entries", []).append(entry); save_json(manifest_path, manifest)
        try:
            result = run_model(model, spec, config, generation_config)
            entry.update(result); entry["status"] = "complete"
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
