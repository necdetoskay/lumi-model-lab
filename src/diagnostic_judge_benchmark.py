from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.generate import parse_cost, parse_usage
from src.generator_benchmark_v2 import load_config, load_json, save_json
from src.judge import build_judge_input, call_judge, load_generation, load_yaml, make_decision


def run_diagnostic_judge(
    benchmark_config_path: Path,
    evaluation_config_path: Path,
) -> dict[str, Any]:
    config = load_config(benchmark_config_path)
    output_dir = Path(str(config.get("output_dir", "runs/generator_benchmark_v2")))
    manifest_path = output_dir / "manifest.json"
    manifest = load_json(manifest_path)

    evaluation = load_yaml(evaluation_config_path)
    judge_config = evaluation.get("judge") or {}
    model_env = judge_config.get("model_env", "JUDGE_MODEL")
    model = os.getenv(model_env)
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not model:
        raise RuntimeError(f"Missing judge model in environment variable {model_env}.")
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    system_prompt = Path("prompts/story_judge.md").read_text(encoding="utf-8").strip()
    acceptance_threshold = float(judge_config.get("acceptance_threshold", 4.0))
    minimum_criterion_score = int(judge_config.get("minimum_criterion_score", 3))

    for entry in manifest.get("entries", []):
        if entry.get("generation_status") != "complete":
            continue
        if entry.get("diagnostic_judge_status") == "complete":
            continue

        record = load_generation(Path(str(entry["story_path"])))
        started = time.perf_counter()
        try:
            result, body = call_judge(
                api_key=api_key,
                model=model,
                system_prompt=system_prompt,
                user_prompt=build_judge_input(record),
                temperature=float(judge_config.get("temperature", 0.0)),
                max_tokens=int(judge_config.get("max_tokens", 3000)),
            )
            decision = make_decision(
                result,
                acceptance_threshold=acceptance_threshold,
                minimum_criterion_score=minimum_criterion_score,
            )
            usage = parse_usage(body)
            cost = parse_cost(body)
            entry.update(
                {
                    "diagnostic_judge_status": "complete",
                    "diagnostic_judge_model": model,
                    "diagnostic_judge_average": decision.average_score,
                    "diagnostic_judge_minimum": decision.minimum_score,
                    "diagnostic_judge_raw_accepted": decision.accepted,
                    "diagnostic_judge_scores": result.scores,
                    "diagnostic_critical_failures": result.critical_failures,
                    "diagnostic_judge_latency_seconds": round(time.perf_counter() - started, 3),
                    "diagnostic_judge_input_tokens": usage.input_tokens,
                    "diagnostic_judge_output_tokens": usage.output_tokens,
                    "diagnostic_judge_total_tokens": usage.total_tokens,
                    "diagnostic_judge_cost_usd": cost.usd,
                    "diagnostic_judge_cost_try": cost.try_amount,
                    "diagnostic_only": not bool(entry.get("technical_pass")),
                    "promotion_eligible": bool(entry.get("technical_pass")) and decision.accepted,
                    "diagnostic_judge_error": None,
                }
            )
        except Exception as exc:
            entry.update(
                {
                    "diagnostic_judge_status": "error",
                    "diagnostic_judge_latency_seconds": round(time.perf_counter() - started, 3),
                    "diagnostic_judge_error": str(exc),
                }
            )
        finally:
            save_json(manifest_path, manifest)

    report = {
        "benchmark": manifest.get("benchmark"),
        "judge_model": model,
        "entries": [
            {
                "model": entry.get("model"),
                "technical_pass": entry.get("technical_pass"),
                "word_count": entry.get("word_count"),
                "diagnostic_judge_average": entry.get("diagnostic_judge_average"),
                "diagnostic_judge_scores": entry.get("diagnostic_judge_scores"),
                "diagnostic_judge_raw_accepted": entry.get("diagnostic_judge_raw_accepted"),
                "promotion_eligible": entry.get("promotion_eligible"),
                "diagnostic_judge_cost_usd": entry.get("diagnostic_judge_cost_usd"),
                "diagnostic_judge_cost_try": entry.get("diagnostic_judge_cost_try"),
                "diagnostic_judge_error": entry.get("diagnostic_judge_error"),
            }
            for entry in manifest.get("entries", [])
            if entry.get("generation_status") == "complete"
        ],
    }
    save_json(output_dir / "diagnostic_judge_summary.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Judge completed benchmark stories even when they failed the technical gate, without promoting them."
    )
    parser.add_argument("--benchmark-config", default="configs/generator_benchmark_smoke.yaml")
    parser.add_argument("--evaluation-config", default="configs/evaluation.yaml")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    run_diagnostic_judge(Path(args.benchmark_config), Path(args.evaluation_config))


if __name__ == "__main__":
    main()
