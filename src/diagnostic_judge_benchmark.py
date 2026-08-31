from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.generate import parse_cost, parse_usage
from src.generator_benchmark_v2 import load_config, load_json, save_json
from src.judge import build_judge_input, call_judge, load_generation, load_yaml, make_decision


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", value).strip("_")


def _run_key(model: str, prompt_version: str) -> str:
    return f"{model}@{prompt_version}"


def _legacy_run(entry: dict[str, Any]) -> dict[str, Any] | None:
    model = entry.get("diagnostic_judge_model")
    status = entry.get("diagnostic_judge_status")
    if not model or not status:
        return None
    return {
        "status": status,
        "judge_model": model,
        "prompt_version": "story_judge_v0.1",
        "average": entry.get("diagnostic_judge_average"),
        "minimum": entry.get("diagnostic_judge_minimum"),
        "raw_accepted": entry.get("diagnostic_judge_raw_accepted"),
        "scores": entry.get("diagnostic_judge_scores"),
        "critical_failures": entry.get("diagnostic_critical_failures"),
        "latency_seconds": entry.get("diagnostic_judge_latency_seconds"),
        "input_tokens": entry.get("diagnostic_judge_input_tokens"),
        "output_tokens": entry.get("diagnostic_judge_output_tokens"),
        "total_tokens": entry.get("diagnostic_judge_total_tokens"),
        "cost_usd": entry.get("diagnostic_judge_cost_usd"),
        "cost_try": entry.get("diagnostic_judge_cost_try"),
        "diagnostic_only": entry.get("diagnostic_only"),
        "promotion_eligible": entry.get("promotion_eligible"),
        "error": entry.get("diagnostic_judge_error"),
    }


def _ensure_run_history(entry: dict[str, Any]) -> dict[str, Any]:
    runs = entry.setdefault("diagnostic_judge_runs", {})
    legacy = _legacy_run(entry)
    if legacy:
        legacy_key = _run_key(str(legacy["judge_model"]), str(legacy["prompt_version"]))
        if legacy_key not in runs and str(legacy["judge_model"]) not in runs:
            runs[legacy_key] = legacy
    return runs


def run_diagnostic_judge(
    benchmark_config_path: Path,
    evaluation_config_path: Path,
    *,
    judge_model: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    config = load_config(benchmark_config_path)
    output_dir = Path(str(config.get("output_dir", "runs/generator_benchmark_v2")))
    manifest_path = output_dir / "manifest.json"
    manifest = load_json(manifest_path)

    evaluation = load_yaml(evaluation_config_path)
    judge_config = evaluation.get("judge") or {}
    model_env = judge_config.get("model_env", "JUDGE_MODEL")
    model = judge_model or os.getenv(model_env)
    prompt_version = str(judge_config.get("prompt_version", "story_judge_v0.1"))
    run_key = _run_key(str(model), prompt_version) if model else ""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not model:
        raise RuntimeError(
            f"Missing judge model. Pass --judge-model or set environment variable {model_env}."
        )
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    system_prompt = Path("prompts/story_judge.md").read_text(encoding="utf-8").strip()
    acceptance_threshold = float(judge_config.get("acceptance_threshold", 4.0))
    minimum_criterion_score = int(judge_config.get("minimum_criterion_score", 3))

    for entry in manifest.get("entries", []):
        if entry.get("generation_status") != "complete":
            continue

        runs = _ensure_run_history(entry)
        existing = runs.get(run_key)
        if existing and existing.get("status") == "complete" and not force:
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
            run = {
                "status": "complete",
                "judge_model": model,
                "prompt_version": prompt_version,
                "average": decision.average_score,
                "minimum": decision.minimum_score,
                "raw_accepted": decision.accepted,
                "scores": result.scores,
                "critical_failures": result.critical_failures,
                "latency_seconds": round(time.perf_counter() - started, 3),
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "total_tokens": usage.total_tokens,
                "cost_usd": cost.usd,
                "cost_try": cost.try_amount,
                "diagnostic_only": not bool(entry.get("technical_pass")),
                "promotion_eligible": bool(entry.get("technical_pass")) and decision.accepted,
                "error": None,
            }
            runs[run_key] = run
        except Exception as exc:
            runs[run_key] = {
                "status": "error",
                "judge_model": model,
                "prompt_version": prompt_version,
                "latency_seconds": round(time.perf_counter() - started, 3),
                "error": str(exc),
            }
        finally:
            save_json(manifest_path, manifest)

    report_entries: list[dict[str, Any]] = []
    for entry in manifest.get("entries", []):
        if entry.get("generation_status") != "complete":
            continue
        run = (_ensure_run_history(entry)).get(run_key) or {}
        report_entries.append(
            {
                "model": entry.get("model"),
                "technical_pass": entry.get("technical_pass"),
                "word_count": entry.get("word_count"),
                "diagnostic_judge_average": run.get("average"),
                "diagnostic_judge_scores": run.get("scores"),
                "diagnostic_judge_raw_accepted": run.get("raw_accepted"),
                "promotion_eligible": run.get("promotion_eligible"),
                "diagnostic_judge_latency_seconds": run.get("latency_seconds"),
                "diagnostic_judge_input_tokens": run.get("input_tokens"),
                "diagnostic_judge_output_tokens": run.get("output_tokens"),
                "diagnostic_judge_total_tokens": run.get("total_tokens"),
                "diagnostic_judge_cost_usd": run.get("cost_usd"),
                "diagnostic_judge_cost_try": run.get("cost_try"),
                "diagnostic_judge_error": run.get("error"),
            }
        )

    report = {
        "benchmark": manifest.get("benchmark"),
        "judge_model": model,
        "prompt_version": prompt_version,
        "run_key": run_key,
        "entries": report_entries,
    }
    save_json(output_dir / f"diagnostic_judge_{_slug(run_key)}.json", report)

    comparison: dict[str, Any] = {
        "benchmark": manifest.get("benchmark"),
        "judges": {},
    }
    judge_runs = sorted(
        {
            judge_name
            for entry in manifest.get("entries", [])
            for judge_name in (_ensure_run_history(entry)).keys()
        }
    )
    for judge_name in judge_runs:
        rows = []
        total_cost_usd = 0.0
        for entry in manifest.get("entries", []):
            if entry.get("generation_status") != "complete":
                continue
            run = (_ensure_run_history(entry)).get(judge_name) or {}
            if run.get("cost_usd") is not None:
                total_cost_usd += float(run["cost_usd"])
            rows.append(
                {
                    "generator_model": entry.get("model"),
                    "average": run.get("average"),
                    "scores": run.get("scores"),
                    "raw_accepted": run.get("raw_accepted"),
                    "latency_seconds": run.get("latency_seconds"),
                    "cost_usd": run.get("cost_usd"),
                    "cost_try": run.get("cost_try"),
                    "error": run.get("error"),
                }
            )
        comparison["judges"][judge_name] = {
            "total_cost_usd": round(total_cost_usd, 6),
            "entries": rows,
        }
    save_json(output_dir / "diagnostic_judge_comparison.json", comparison)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Judge completed benchmark stories even when they failed the technical gate, without promoting them."
    )
    parser.add_argument("--benchmark-config", default="configs/generator_benchmark_smoke.yaml")
    parser.add_argument("--evaluation-config", default="configs/evaluation.yaml")
    parser.add_argument(
        "--judge-model",
        help="OpenRouter model slug for this diagnostic run; overrides JUDGE_MODEL without requiring a provider-specific API key.",
    )
    parser.add_argument("--force", action="store_true", help="Repeat this judge model/prompt version even if its run is already complete.")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    run_diagnostic_judge(
        Path(args.benchmark_config),
        Path(args.evaluation_config),
        judge_model=args.judge_model,
        force=args.force,
    )


if __name__ == "__main__":
    main()
