from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.generate import parse_cost, parse_usage
from src.generator_benchmark_v2 import save_json
from src.judge import call_judge, load_yaml, make_decision
from src.schemas import StorySpec


def _build_judge_input(spec: StorySpec, story: str) -> str:
    constraints = "\n".join(f"- {item}" for item in spec.constraints) or "- None"
    return f"""Evaluate this candidate story against the brief.

BRIEF
Language: {spec.language}
Age range: {spec.age_min}-{spec.age_max}
Target words: {spec.target_words}
Title hint: {spec.title_hint or 'None'}
Protagonist: {spec.protagonist}
Setting: {spec.setting}
Theme: {spec.theme}
Premise: {spec.premise}
Constraints:
{constraints}

CANDIDATE STORY
{story}
"""


def run(*, manifest_path: Path, benchmark_config_path: Path, evaluation_config_path: Path, judge_model: str) -> dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    benchmark_config = load_yaml(benchmark_config_path)
    spec = StorySpec.model_validate(load_yaml(Path(str(benchmark_config["spec"]))))
    evaluation = load_yaml(evaluation_config_path)
    judge_config = evaluation.get("judge") or {}
    prompt_version = str(judge_config.get("prompt_version", "story_judge_v0.2"))
    system_prompt = Path("prompts/story_judge.md").read_text(encoding="utf-8").strip()
    acceptance_threshold = float(judge_config.get("acceptance_threshold", 4.0))
    minimum_criterion_score = int(judge_config.get("minimum_criterion_score", 3))

    rows: list[dict[str, Any]] = []
    for entry in manifest.get("entries", []):
        if entry.get("status") != "complete" or not entry.get("story"):
            continue
        started = time.perf_counter()
        row: dict[str, Any] = {
            "generator_model": entry.get("model"),
            "generation_prompt_version": entry.get("prompt_version"),
            "technical_pass": bool(entry.get("technical_pass")),
            "all_scenes_pass": bool(entry.get("all_scenes_pass")),
            "word_count": entry.get("word_count"),
            "generation_latency_seconds": entry.get("latency_seconds"),
            "generation_retry_count": entry.get("retry_count"),
            "generation_cost_usd": entry.get("cost_usd"),
            "generation_cost_try": entry.get("cost_try"),
        }
        try:
            result, body = call_judge(
                api_key=api_key,
                model=judge_model,
                system_prompt=system_prompt,
                user_prompt=_build_judge_input(spec, str(entry["story"])),
                temperature=float(judge_config.get("temperature", 0.0)),
                max_tokens=int(judge_config.get("max_tokens", 2500)),
                reasoning=judge_config.get("reasoning"),
                response_format=judge_config.get("response_format"),
            )
            decision = make_decision(
                result,
                acceptance_threshold=acceptance_threshold,
                minimum_criterion_score=minimum_criterion_score,
            )
            usage = parse_usage(body)
            cost = parse_cost(body)
            row.update({
                "judge_status": "complete",
                "judge_model": judge_model,
                "judge_prompt_version": prompt_version,
                "average": decision.average_score,
                "minimum": decision.minimum_score,
                "raw_accepted": decision.accepted,
                "scores": result.scores,
                "reasons": result.reasons,
                "critical_failures": result.critical_failures,
                "diagnostic_only": not bool(entry.get("technical_pass")),
                "promotion_eligible": bool(entry.get("technical_pass")) and decision.accepted,
                "judge_latency_seconds": round(time.perf_counter() - started, 3),
                "judge_input_tokens": usage.input_tokens,
                "judge_output_tokens": usage.output_tokens,
                "judge_total_tokens": usage.total_tokens,
                "judge_cost_usd": cost.usd,
                "judge_cost_try": cost.try_amount,
                "error": None,
            })
        except Exception as exc:
            row.update({
                "judge_status": "error",
                "judge_model": judge_model,
                "judge_prompt_version": prompt_version,
                "judge_latency_seconds": round(time.perf_counter() - started, 3),
                "error": str(exc),
            })
        rows.append(row)

    report = {
        "benchmark": manifest.get("benchmark"),
        "judge_model": judge_model,
        "judge_prompt_version": prompt_version,
        "entries": rows,
    }
    output_path = manifest_path.parent / "scene_first_diagnostic_judge.json"
    save_json(output_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnostic semantic judge for scene-first calibration outputs.")
    parser.add_argument("--manifest", default="runs/generator_scene_first_calibration_v3/manifest.json")
    parser.add_argument("--benchmark-config", default="configs/generator_scene_first_calibration_v3.yaml")
    parser.add_argument("--evaluation-config", default="configs/evaluation.yaml")
    parser.add_argument("--judge-model", default="anthropic/claude-sonnet-5")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    run(
        manifest_path=Path(args.manifest),
        benchmark_config_path=Path(args.benchmark_config),
        evaluation_config_path=Path(args.evaluation_config),
        judge_model=args.judge_model,
    )


if __name__ == "__main__":
    main()
