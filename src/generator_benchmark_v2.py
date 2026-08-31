from __future__ import annotations

import argparse
import json
import math
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from src.generate import generate_one, load_yaml
from src.judge import judge_story
from src.schemas import GenerationRecord, JUDGE_CRITERIA, StorySpec

console = Console()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_manifest(path: Path, name: str) -> dict[str, Any]:
    if path.exists():
        return load_json(path)
    return {"benchmark": name, "created_at": datetime.now(timezone.utc).isoformat(), "entries": []}


def entry_key(model: str, spec_path: str, repeat: int) -> tuple[str, str, int]:
    return model, spec_path, repeat


def find_entry(manifest: dict[str, Any], model: str, spec_path: str, repeat: int) -> dict[str, Any] | None:
    wanted = entry_key(model, spec_path, repeat)
    for entry in manifest.get("entries", []):
        if entry_key(str(entry.get("model")), str(entry.get("spec_path")), int(entry.get("repeat", 0))) == wanted:
            return entry
    return None


def repeated_ngram_ratio(text: str, n: int = 8) -> float:
    words = text.split()
    if len(words) < n:
        return 0.0
    grams = [tuple(words[index:index + n]) for index in range(len(words) - n + 1)]
    counts = Counter(grams)
    repeated_occurrences = sum(count - 1 for count in counts.values() if count > 1)
    return round(repeated_occurrences / len(grams), 6)


def generation_phase(config: dict[str, Any], generation_config_path: Path, manifest_path: Path, *, force: bool = False) -> dict[str, Any]:
    generation_config = load_yaml(generation_config_path)
    manifest = load_manifest(manifest_path, str(config.get("name", "generator_benchmark_v2")))
    repeats = int(config.get("repeats", 2))

    for spec_path_raw in config.get("specs", []):
        spec_path = Path(str(spec_path_raw))
        spec = StorySpec.model_validate(load_yaml(spec_path))
        for model_raw in config.get("models", []):
            model = str(model_raw)
            for repeat in range(1, repeats + 1):
                existing = find_entry(manifest, model, str(spec_path), repeat)
                if existing and existing.get("generation_status") == "complete" and not force:
                    console.print(f"[dim]Skip existing[/dim] {model} | {spec_path.name} | r{repeat}")
                    continue
                entry = existing or {"model": model, "spec_path": str(spec_path), "repeat": repeat}
                if not existing:
                    manifest["entries"].append(entry)

                console.rule(f"Generate | {model} | {spec_path.name} | r{repeat}")
                started = time.perf_counter()
                try:
                    output_path, validation = generate_one(
                        generation_config,
                        spec,
                        dry_run=False,
                        model_override=model,
                    )
                    elapsed = time.perf_counter() - started
                    if output_path is None or validation is None:
                        raise RuntimeError("Generation returned no output record.")
                    record = GenerationRecord.model_validate(load_json(output_path))
                    entry.update({
                        "generation_status": "complete",
                        "story_id": record.id,
                        "story_path": str(output_path),
                        "technical_pass": validation.eligible_for_judge,
                        "word_count": validation.word_count,
                        "target_words": validation.target_words,
                        "finish_reason": validation.finish_reason,
                        "technical_reasons": validation.reasons,
                        "repeat_8gram_ratio": repeated_ngram_ratio(record.story, 8),
                        "generation_latency_seconds": round(elapsed, 3),
                        "generator_input_tokens": record.usage.input_tokens,
                        "generator_output_tokens": record.usage.output_tokens,
                        "generator_total_tokens": record.usage.total_tokens,
                        "generator_cost_usd": record.cost.usd,
                        "generator_cost_try": record.cost.try_amount,
                        "usd_try_rate": record.cost.usd_try_rate,
                        "provider": record.response_meta.get("provider"),
                        "generation_error": None,
                    })
                except Exception as exc:
                    entry.update({
                        "generation_status": "error",
                        "technical_pass": False,
                        "generation_latency_seconds": round(time.perf_counter() - started, 3),
                        "generation_error": str(exc),
                    })
                    console.print(f"[red]Generation error[/red] {model}: {exc}")
                finally:
                    save_json(manifest_path, manifest)
    return manifest


def judge_phase(config: dict[str, Any], evaluation_config_path: Path, manifest_path: Path, *, force: bool = False) -> dict[str, Any]:
    manifest = load_manifest(manifest_path, str(config.get("name", "generator_benchmark_v2")))
    for entry in manifest.get("entries", []):
        if entry.get("generation_status") != "complete":
            continue
        if not entry.get("technical_pass"):
            entry["judge_status"] = "skipped_technical_gate"
            save_json(manifest_path, manifest)
            continue
        if entry.get("judge_status") == "complete" and not force:
            continue

        started = time.perf_counter()
        try:
            judgment_path, judgment = judge_story(Path(str(entry["story_path"])), evaluation_config_path)
            elapsed = time.perf_counter() - started
            entry.update({
                "judge_status": "complete",
                "judgment_path": str(judgment_path),
                "judge_model": judgment.judge_model,
                "judge_accepted": judgment.decision.accepted,
                "judge_average": judgment.decision.average_score,
                "judge_minimum": judgment.decision.minimum_score,
                "judge_scores": judgment.result.scores,
                "critical_failures": judgment.result.critical_failures,
                "judge_latency_seconds": round(elapsed, 3),
                "judge_input_tokens": judgment.usage.input_tokens,
                "judge_output_tokens": judgment.usage.output_tokens,
                "judge_total_tokens": judgment.usage.total_tokens,
                "judge_cost_usd": judgment.cost.usd,
                "judge_cost_try": judgment.cost.try_amount,
                "judge_error": None,
            })
        except Exception as exc:
            entry.update({
                "judge_status": "error",
                "judge_latency_seconds": round(time.perf_counter() - started, 3),
                "judge_error": str(exc),
            })
            console.print(f"[red]Judge error[/red] {entry.get('story_id')}: {exc}")
        finally:
            save_json(manifest_path, manifest)
    return manifest


def mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def percentile(values: list[float], percentile_value: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(percentile_value * len(ordered)) - 1))
    return round(ordered[index], 4)


def summarize(entries: list[dict[str, Any]], models: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for model in models:
        rows = [entry for entry in entries if entry.get("model") == model]
        generated = [entry for entry in rows if entry.get("generation_status") == "complete"]
        technical = [entry for entry in generated if entry.get("technical_pass")]
        judged = [entry for entry in rows if entry.get("judge_status") == "complete"]
        accepted = [entry for entry in judged if entry.get("judge_accepted")]
        generator_costs = [float(entry["generator_cost_usd"]) for entry in generated if entry.get("generator_cost_usd") is not None]
        judge_costs = [float(entry["judge_cost_usd"]) for entry in judged if entry.get("judge_cost_usd") is not None]
        generator_try = [float(entry["generator_cost_try"]) for entry in generated if entry.get("generator_cost_try") is not None]
        judge_try = [float(entry["judge_cost_try"]) for entry in judged if entry.get("judge_cost_try") is not None]
        scores = [float(entry["judge_average"]) for entry in judged if entry.get("judge_average") is not None]
        latencies = [float(entry["generation_latency_seconds"]) for entry in generated if entry.get("generation_latency_seconds") is not None]
        repetition = [float(entry["repeat_8gram_ratio"]) for entry in generated if entry.get("repeat_8gram_ratio") is not None]
        total_cost_usd = sum(generator_costs) + sum(judge_costs)
        total_cost_try = sum(generator_try) + sum(judge_try)
        criteria: dict[str, float | None] = {}
        for criterion in JUDGE_CRITERIA:
            criteria[criterion] = mean([
                float((entry.get("judge_scores") or {})[criterion])
                for entry in judged if criterion in (entry.get("judge_scores") or {})
            ])

        result[model] = {
            "planned": len(rows),
            "generated": len(generated),
            "generation_errors": len(rows) - len(generated),
            "technical_passes": len(technical),
            "technical_pass_rate": round(len(technical) / len(rows), 4) if rows else None,
            "judged": len(judged),
            "accepted": len(accepted),
            "accept_rate_planned": round(len(accepted) / len(rows), 4) if rows else None,
            "judge_average": mean(scores),
            "criterion_averages": criteria,
            "generation_latency_mean_seconds": mean(latencies),
            "generation_latency_p95_seconds": percentile(latencies, 0.95),
            "repeat_8gram_ratio_mean": mean(repetition),
            "generator_cost_total_usd": round(sum(generator_costs), 6),
            "judge_cost_total_usd": round(sum(judge_costs), 6),
            "combined_cost_total_usd": round(total_cost_usd, 6),
            "combined_cost_total_try": round(total_cost_try, 4) if generator_try or judge_try else None,
            "combined_cost_per_planned_story_usd": round(total_cost_usd / len(rows), 6) if rows else None,
            "cost_per_accepted_story_usd": round(total_cost_usd / len(accepted), 6) if accepted else None,
            "cost_per_accepted_story_try": round(total_cost_try / len(accepted), 4) if accepted and (generator_try or judge_try) else None,
        }
    return result


def report_phase(config: dict[str, Any], manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path, str(config.get("name", "generator_benchmark_v2")))
    models = [str(model) for model in config.get("models", [])]
    summary = summarize(manifest.get("entries", []), models)
    payload = {
        "benchmark": config.get("name"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selection_rule": "quality first; reliability second; cost breaks close quality ties",
        "models": summary,
    }
    save_json(output_dir / "summary.json", payload)

    lines = [
        f"# Generator Benchmark V2 — {config.get('name')}", "",
        "Selection rule: quality first; reliability second; cost breaks close quality ties.", "",
        "| Model | Tech pass | Judge avg | Accepted/planned | 8-gram repeat | Gen p95 | Combined $ | $ / accepted | TRY / accepted |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model in models:
        item = summary[model]
        tech = "—" if item["technical_pass_rate"] is None else f"{item['technical_pass_rate'] * 100:.0f}%"
        score = "—" if item["judge_average"] is None else f"{item['judge_average']:.2f}/5"
        rep = "—" if item["repeat_8gram_ratio_mean"] is None else f"{item['repeat_8gram_ratio_mean']:.4f}"
        p95 = "—" if item["generation_latency_p95_seconds"] is None else f"{item['generation_latency_p95_seconds']:.1f}s"
        cpa = "—" if item["cost_per_accepted_story_usd"] is None else f"${item['cost_per_accepted_story_usd']:.4f}"
        cpa_try = "—" if item["cost_per_accepted_story_try"] is None else f"₺{item['cost_per_accepted_story_try']:.2f}"
        lines.append(f"| {model} | {tech} | {score} | {item['accepted']}/{item['planned']} | {rep} | {p95} | ${item['combined_cost_total_usd']:.4f} | {cpa} | {cpa_try} |")

    lines.extend(["", "## Criterion averages", "", "| Model | Instruction | Coherence | Character | Age | Creativity | Style |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for model in models:
        values = summary[model]["criterion_averages"]
        cells = ["—" if values.get(criterion) is None else f"{values[criterion]:.2f}" for criterion in JUDGE_CRITERIA]
        lines.append(f"| {model} | " + " | ".join(cells) + " |")
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    table = Table(title=str(config.get("name")))
    table.add_column("Model")
    table.add_column("Tech", justify="right")
    table.add_column("Judge", justify="right")
    table.add_column("Accepted", justify="right")
    table.add_column("$ total", justify="right")
    for model in models:
        item = summary[model]
        table.add_row(model, f"{(item['technical_pass_rate'] or 0) * 100:.0f}%", "—" if item["judge_average"] is None else f"{item['judge_average']:.2f}", f"{item['accepted']}/{item['planned']}", f"{item['combined_cost_total_usd']:.4f}")
    console.print(table)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the LUMI production generator benchmark v2.")
    parser.add_argument("phase", choices=("generate", "judge", "report", "all"), nargs="?", default="generate")
    parser.add_argument("--benchmark-config", default="configs/generator_benchmark_v2.yaml")
    parser.add_argument("--generation-config", default="configs/generation.yaml")
    parser.add_argument("--evaluation-config", default="configs/evaluation.yaml")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    config = load_config(Path(args.benchmark_config))
    output_dir = Path(str(config.get("output_dir", "runs/generator_benchmark_v2")))
    manifest_path = output_dir / "manifest.json"
    if args.phase in ("generate", "all"):
        generation_phase(config, Path(args.generation_config), manifest_path, force=args.force)
    if args.phase in ("judge", "all"):
        judge_phase(config, Path(args.evaluation_config), manifest_path, force=args.force)
    if args.phase in ("report", "all"):
        report_phase(config, manifest_path, output_dir)


if __name__ == "__main__":
    main()
