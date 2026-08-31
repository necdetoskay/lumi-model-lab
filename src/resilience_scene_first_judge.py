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
from src.scene_first_diagnostic_judge import _build_judge_input
from src.schemas import StorySpec


def run(*, manifest_path: Path, evaluation_config_path: Path, judge_model: str) -> dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
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
        if not bool(entry.get("technical_pass")):
            rows.append({
                "generator_model": entry.get("model"),
                "spec_path": entry.get("spec_path"),
                "target_words": entry.get("target_words"),
                "word_count": entry.get("word_count"),
                "technical_pass": False,
                "all_scenes_pass": bool(entry.get("all_scenes_pass")),
                "judge_status": "skipped_technical_failure",
                "promotion_eligible": False,
            })
            continue

        spec_path = Path(str(entry["spec_path"]))
        spec = StorySpec.model_validate(load_yaml(spec_path))
        started = time.perf_counter()
        row: dict[str, Any] = {
            "generator_model": entry.get("model"),
            "spec_path": str(spec_path),
            "target_words": entry.get("target_words"),
            "word_count": entry.get("word_count"),
            "technical_pass": True,
            "all_scenes_pass": bool(entry.get("all_scenes_pass")),
            "generation_latency_seconds": entry.get("latency_seconds"),
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
                "promotion_eligible": decision.accepted,
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
                "promotion_eligible": False,
                "error": str(exc),
            })
        rows.append(row)

    report = {
        "benchmark": manifest.get("benchmark"),
        "judge_model": judge_model,
        "judge_prompt_version": prompt_version,
        "policy": "judge technical-pass entries only; technical failures are preserved as skipped evidence",
        "entries": rows,
    }
    output_path = manifest_path.parent / "resilience_scene_first_judge.json"
    save_json(output_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Canonical Sonnet judge for generator resilience scene-first outputs.")
    parser.add_argument("--manifest", default="runs/generator_resilience_scene_first/manifest.json")
    parser.add_argument("--evaluation-config", default="configs/evaluation.yaml")
    parser.add_argument("--judge-model", default="anthropic/claude-sonnet-5")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    run(
        manifest_path=Path(args.manifest),
        evaluation_config_path=Path(args.evaluation_config),
        judge_model=args.judge_model,
    )


if __name__ == "__main__":
    main()
