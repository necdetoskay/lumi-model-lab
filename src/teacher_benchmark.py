from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from src.generate import generate_one, load_yaml
from src.judge import judge_story
from src.schemas import GenerationRecord, JUDGE_CRITERIA, JudgeRecord, StorySpec

console = Console()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_benchmark_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_manifest(path: Path, benchmark_name: str) -> dict[str, Any]:
    if path.exists():
        return load_json(path)
    return {
        "benchmark": benchmark_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "entries": [],
    }


def entry_key(model: str, spec_path: str) -> tuple[str, str]:
    return model, spec_path


def find_entry(manifest: dict[str, Any], model: str, spec_path: str) -> dict[str, Any] | None:
    key = entry_key(model, spec_path)
    for entry in manifest.get("entries", []):
        if entry_key(str(entry.get("model")), str(entry.get("spec_path"))) == key:
            return entry
    return None


def generate_phase(
    benchmark_config: dict[str, Any],
    generation_config_path: Path,
    manifest_path: Path,
    *,
    force: bool = False,
) -> dict[str, Any]:
    generation_config = load_yaml(generation_config_path)
    manifest = load_manifest(manifest_path, str(benchmark_config.get("name", "teacher_benchmark")))

    for spec_path_raw in benchmark_config.get("specs", []):
        spec_path = Path(spec_path_raw)
        spec = StorySpec.model_validate(load_yaml(spec_path))
        for model in benchmark_config.get("models", []):
            model = str(model)
            existing = find_entry(manifest, model, str(spec_path))
            if existing and existing.get("generation_status") == "complete" and not force:
                console.print(f"[dim]Skip existing[/dim] {model} | {spec_path.name}")
                continue

            entry = existing or {
                "model": model,
                "spec_path": str(spec_path),
            }
            if not existing:
                manifest["entries"].append(entry)

            console.rule(f"Generate | {model} | {spec_path.name}")
            try:
                output_path, validation = generate_one(
                    generation_config,
                    spec,
                    dry_run=False,
                    model_override=model,
                )
                if output_path is None or validation is None:
                    raise RuntimeError("Generation returned no output record.")
                generation_record = GenerationRecord.model_validate(load_json(output_path))
                entry.update(
                    {
                        "generation_status": "complete",
                        "story_id": generation_record.id,
                        "story_path": str(output_path),
                        "technical_pass": validation.eligible_for_judge,
                        "word_count": validation.word_count,
                        "finish_reason": validation.finish_reason,
                        "technical_reasons": validation.reasons,
                        "teacher_cost_usd": generation_record.cost.usd,
                        "teacher_output_tokens": generation_record.usage.output_tokens,
                        "provider": generation_record.response_meta.get("provider"),
                        "generation_error": None,
                    }
                )
                style = "green" if validation.eligible_for_judge else "yellow"
                console.print(
                    f"[{style}]{generation_record.id}[/{style}] words={validation.word_count} "
                    f"technical_pass={validation.eligible_for_judge}"
                )
            except Exception as exc:  # keep the benchmark resumable after one provider/model failure
                entry.update(
                    {
                        "generation_status": "error",
                        "technical_pass": False,
                        "generation_error": str(exc),
                    }
                )
                console.print(f"[red]Generation error[/red] {model}: {exc}")
            finally:
                save_json(manifest_path, manifest)

    return manifest


def judge_phase(
    benchmark_config: dict[str, Any],
    evaluation_config_path: Path,
    manifest_path: Path,
    *,
    force: bool = False,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path, str(benchmark_config.get("name", "teacher_benchmark")))
    if not manifest.get("entries"):
        raise RuntimeError("Benchmark manifest is empty. Run the generate phase first.")

    for entry in manifest["entries"]:
        if entry.get("generation_status") != "complete":
            continue
        if not entry.get("technical_pass"):
            entry["judge_status"] = "skipped_technical_gate"
            continue
        if entry.get("judge_status") == "complete" and not force:
            console.print(f"[dim]Skip judged[/dim] {entry.get('story_id')}")
            continue

        story_path = Path(str(entry["story_path"]))
        console.rule(f"Judge | {entry.get('model')} | {story_path.name}")
        try:
            judgment_path, judgment = judge_story(story_path, evaluation_config_path)
            entry.update(
                {
                    "judge_status": "complete",
                    "judgment_path": str(judgment_path),
                    "judge_accepted": judgment.decision.accepted,
                    "judge_average": judgment.decision.average_score,
                    "judge_minimum": judgment.decision.minimum_score,
                    "judge_scores": judgment.result.scores,
                    "critical_failures": judgment.result.critical_failures,
                    "judge_cost_usd": judgment.cost.usd,
                    "judge_error": None,
                }
            )
            style = "green" if judgment.decision.accepted else "yellow"
            console.print(
                f"[{style}]{'ACCEPTED' if judgment.decision.accepted else 'REJECTED'}[/{style}] "
                f"average={judgment.decision.average_score:.2f}/5"
            )
        except Exception as exc:
            entry.update({"judge_status": "error", "judge_error": str(exc)})
            console.print(f"[red]Judge error[/red] {entry.get('story_id')}: {exc}")
        finally:
            save_json(manifest_path, manifest)

    return manifest


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None


def summarize_entries(entries: list[dict[str, Any]], models: list[str]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for model in models:
        rows = [entry for entry in entries if entry.get("model") == model]
        generated = [entry for entry in rows if entry.get("generation_status") == "complete"]
        technical_passes = [entry for entry in generated if entry.get("technical_pass")]
        judged = [entry for entry in rows if entry.get("judge_status") == "complete"]
        accepted = [entry for entry in judged if entry.get("judge_accepted")]
        teacher_costs = [float(entry["teacher_cost_usd"]) for entry in generated if entry.get("teacher_cost_usd") is not None]
        judge_costs = [float(entry["judge_cost_usd"]) for entry in judged if entry.get("judge_cost_usd") is not None]
        judge_averages = [float(entry["judge_average"]) for entry in judged if entry.get("judge_average") is not None]
        critical_count = sum(len(entry.get("critical_failures") or []) for entry in judged)

        criterion_averages: dict[str, float | None] = {}
        for criterion in JUDGE_CRITERIA:
            values = [
                float((entry.get("judge_scores") or {})[criterion])
                for entry in judged
                if criterion in (entry.get("judge_scores") or {})
            ]
            criterion_averages[criterion] = _mean(values)

        summary[model] = {
            "planned": len(rows),
            "generated": len(generated),
            "technical_passes": len(technical_passes),
            "technical_pass_rate": round(len(technical_passes) / len(generated), 3) if generated else None,
            "judged": len(judged),
            "accepted": len(accepted),
            "accept_rate": round(len(accepted) / len(judged), 3) if judged else None,
            "judge_average": _mean(judge_averages),
            "criterion_averages": criterion_averages,
            "critical_failure_count": critical_count,
            "teacher_cost_total_usd": round(sum(teacher_costs), 6),
            "teacher_cost_mean_usd": _mean(teacher_costs),
            "judge_cost_total_usd": round(sum(judge_costs), 6),
        }
    return summary


def write_report(
    benchmark_config: dict[str, Any],
    manifest: dict[str, Any],
    output_dir: Path,
) -> tuple[Path, Path, dict[str, Any]]:
    models = [str(model) for model in benchmark_config.get("models", [])]
    summary = summarize_entries(manifest.get("entries", []), models)
    payload = {
        "benchmark": benchmark_config.get("name"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "quality_priority": benchmark_config.get("quality_priority"),
        "models": summary,
    }
    json_path = output_dir / "summary.json"
    save_json(json_path, payload)

    lines = [
        f"# Teacher Benchmark — {benchmark_config.get('name', 'benchmark')}",
        "",
        "Selection rule: quality first; technical reliability second; cost only as a tie-breaker when quality is comparable.",
        "",
        "| Model | Technical pass | Judge avg | Accepted | Critical failures | Mean teacher cost |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model in models:
        item = summary[model]
        pass_rate = item["technical_pass_rate"]
        pass_text = "—" if pass_rate is None else f"{pass_rate * 100:.0f}% ({item['technical_passes']}/{item['generated']})"
        judge_avg = "—" if item["judge_average"] is None else f"{item['judge_average']:.2f}/5"
        accepted_text = f"{item['accepted']}/{item['judged']}" if item["judged"] else "—"
        cost = "—" if item["teacher_cost_mean_usd"] is None else f"${item['teacher_cost_mean_usd']:.4f}"
        lines.append(
            f"| {model} | {pass_text} | {judge_avg} | {accepted_text} | "
            f"{item['critical_failure_count']} | {cost} |"
        )

    lines.extend(["", "## Criterion averages", ""])
    lines.append("| Model | Instruction | Coherence | Character | Age | Creativity | Style |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for model in models:
        criteria = summary[model]["criterion_averages"]
        cells = []
        for criterion in JUDGE_CRITERIA:
            value = criteria.get(criterion)
            cells.append("—" if value is None else f"{value:.2f}")
        lines.append(f"| {model} | " + " | ".join(cells) + " |")

    markdown_path = output_dir / "summary.md"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return markdown_path, json_path, payload


def print_summary(payload: dict[str, Any]) -> None:
    table = Table(title=str(payload.get("benchmark", "Teacher benchmark")))
    table.add_column("Model")
    table.add_column("Tech pass", justify="right")
    table.add_column("Judge avg", justify="right")
    table.add_column("Accepted", justify="right")
    table.add_column("Critical", justify="right")
    table.add_column("Teacher $", justify="right")
    for model, item in payload.get("models", {}).items():
        tech = item.get("technical_pass_rate")
        table.add_row(
            model,
            "—" if tech is None else f"{tech * 100:.0f}%",
            "—" if item.get("judge_average") is None else f"{item['judge_average']:.2f}",
            f"{item.get('accepted', 0)}/{item.get('judged', 0)}",
            str(item.get("critical_failure_count", 0)),
            f"{item.get('teacher_cost_total_usd', 0.0):.4f}",
        )
    console.print(table)


def report_phase(benchmark_config: dict[str, Any], manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path, str(benchmark_config.get("name", "teacher_benchmark")))
    markdown_path, json_path, payload = write_report(benchmark_config, manifest, output_dir)
    print_summary(payload)
    console.print(f"Report: {markdown_path}")
    console.print(f"JSON:   {json_path}")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the quality-first LUMI teacher benchmark.")
    parser.add_argument("phase", choices=("generate", "judge", "report", "all"), nargs="?", default="generate")
    parser.add_argument("--benchmark-config", default="configs/teacher_benchmark.yaml")
    parser.add_argument("--generation-config", default="configs/generation.yaml")
    parser.add_argument("--evaluation-config", default="configs/evaluation.yaml")
    parser.add_argument("--force", action="store_true", help="Repeat already completed work for the selected phase")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    benchmark_config = load_benchmark_config(Path(args.benchmark_config))
    output_dir = Path(benchmark_config.get("output_dir", "runs/teacher_benchmark"))
    manifest_path = output_dir / "manifest.json"

    if args.phase in ("generate", "all"):
        generate_phase(benchmark_config, Path(args.generation_config), manifest_path, force=args.force)
    if args.phase in ("judge", "all"):
        judge_phase(benchmark_config, Path(args.evaluation_config), manifest_path, force=args.force)
    if args.phase in ("report", "all"):
        report_phase(benchmark_config, manifest_path, output_dir)


if __name__ == "__main__":
    main()
