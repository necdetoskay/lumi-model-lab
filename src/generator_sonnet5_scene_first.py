from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.generate import load_yaml
from src.generator_benchmark_v2 import save_json
from src.generator_scene_first_calibration import GENERATION_CONFIG_PATH
from src.generator_scene_first_calibration_v3 import PROMPT_VERSION, run_model
from src.schemas import StorySpec

CONFIG_PATH = Path("configs/generator_sonnet5_scene_first.yaml")


def _scaled_budgets(base: list[int], *, base_target: int, target: int) -> list[int]:
    raw = [value * target / base_target for value in base]
    budgets = [max(20, int(round(value))) for value in raw]
    budgets[-1] += target - sum(budgets)
    return budgets


def _key(model: str, spec_path: str) -> str:
    return f"{model}|{spec_path}"


def _reuse_glm(config: dict[str, Any], spec_path: str) -> dict[str, Any] | None:
    source_path = Path(str(config.get("reuse_glm_manifest", "")))
    if not source_path.exists():
        return None
    source = json.loads(source_path.read_text(encoding="utf-8"))
    for entry in source.get("entries", []):
        if (
            entry.get("status") == "complete"
            and entry.get("model") == "z-ai/glm-5.3-flash"
            and entry.get("prompt_version") == PROMPT_VERSION
            and entry.get("spec_path") == spec_path
        ):
            reused = copy.deepcopy(entry)
            reused["evidence_source"] = str(source_path)
            reused["reused_existing_evidence"] = True
            return reused
    return None


def main() -> None:
    load_dotenv()
    config = load_yaml(CONFIG_PATH)
    generation_config = load_yaml(GENERATION_CONFIG_PATH)
    output_dir = Path(str(config["output_dir"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    manifest: dict[str, Any] = {
        "benchmark": config["name"],
        "prompt_version": PROMPT_VERSION,
        "entries": [],
    }
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    existing = {
        _key(str(entry.get("model")), str(entry.get("spec_path")))
        for entry in manifest.get("entries", [])
        if entry.get("status") == "complete"
    }

    base_budgets = [int(value) for value in config["base_scene_word_budgets"]]
    base_target = int(config.get("base_target_words", 700))

    for spec_value in config["specs"]:
        spec_path = str(spec_value)
        spec = StorySpec.model_validate(load_yaml(Path(spec_path)))
        budgets = _scaled_budgets(base_budgets, base_target=base_target, target=spec.target_words)

        for model_value in config["models"]:
            model = str(model_value)
            run_key = _key(model, spec_path)
            if run_key in existing:
                print(f"Skip existing {model} | {Path(spec_path).name}")
                continue

            if model == "z-ai/glm-5.3-flash":
                reused = _reuse_glm(config, spec_path)
                if reused is not None:
                    print(f"Reuse GLM evidence | {Path(spec_path).name}")
                    manifest.setdefault("entries", []).append(reused)
                    existing.add(run_key)
                    save_json(manifest_path, manifest)
                    continue

            print(f"Generate Sonnet 5 head-to-head | {model} | {Path(spec_path).name} | target={spec.target_words}")
            run_config = dict(config)
            run_config["scene_word_budgets"] = budgets
            entry: dict[str, Any] = {
                "model": model,
                "spec_path": spec_path,
                "target_words": spec.target_words,
                "scene_word_budgets": budgets,
                "status": "running",
                "reused_existing_evidence": False,
            }
            manifest.setdefault("entries", []).append(entry)
            save_json(manifest_path, manifest)
            try:
                result = run_model(model, spec, run_config, generation_config)
                entry.update(result)
                entry["spec_path"] = spec_path
                entry["scene_word_budgets"] = budgets
                entry["status"] = "complete"
                slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", model)
                story_path = output_dir / f"{Path(spec_path).stem}__{slug}.story.txt"
                story_path.write_text(str(result["story"]), encoding="utf-8")
                entry["story_path"] = str(story_path)
            except Exception as exc:
                entry.update({"status": "error", "error": str(exc)})
            finally:
                save_json(manifest_path, manifest)

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
