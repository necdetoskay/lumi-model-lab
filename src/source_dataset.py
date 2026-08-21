from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from rich.console import Console

from src.teacher_benchmark import (
    generate_phase,
    judge_phase,
    load_benchmark_config,
    load_manifest,
    report_phase,
)

console = Console()


def as_runner_config(config: dict[str, Any]) -> dict[str, Any]:
    model = str(config.get("teacher_model") or "").strip()
    if not model:
        raise RuntimeError("source dataset config requires teacher_model")
    specs = list(config.get("specs") or [])
    if not specs:
        raise RuntimeError("source dataset config requires at least one spec")
    return {
        "name": config.get("name", "source_dataset"),
        "models": [model],
        "specs": specs,
        "output_dir": config.get("output_dir", "runs/source_dataset"),
        "quality_priority": {
            "primary": "judge_quality",
            "secondary": "technical_reliability",
            "tie_breaker": "cost",
        },
    }


def print_status(config: dict[str, Any], manifest_path: Path) -> None:
    manifest = load_manifest(manifest_path, str(config.get("name", "source_dataset")))
    entries = manifest.get("entries", [])
    generated = [entry for entry in entries if entry.get("generation_status") == "complete"]
    technical = [entry for entry in generated if entry.get("technical_pass")]
    judged = [entry for entry in entries if entry.get("judge_status") == "complete"]
    accepted = [entry for entry in judged if entry.get("judge_accepted")]
    target = int(config.get("target_accepted_stories", 5))

    console.rule("Source dataset status")
    console.print(f"Generated:      {len(generated)}/{len(config.get('specs') or [])}")
    console.print(f"Technical pass: {len(technical)}/{len(generated) if generated else 0}")
    console.print(f"Judged:         {len(judged)}")
    console.print(f"Accepted:       {len(accepted)}/{target}")

    if accepted:
        console.print("Accepted source stories:")
        for entry in accepted:
            console.print(
                f"  {entry.get('story_id')} | score={float(entry.get('judge_average', 0)):.2f}/5 | "
                f"{Path(str(entry.get('spec_path'))).name}"
            )

    if len(accepted) >= target:
        console.print("[green]Source-story gate passed.[/green] Ready for supervised example extraction.")
    else:
        console.print(
            f"[yellow]Source-story gate not yet passed.[/yellow] "
            f"Need {target - len(accepted)} more accepted source stor{'y' if target - len(accepted) == 1 else 'ies'}."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Milestone-1 training source stories, separate from benchmark data.")
    parser.add_argument("phase", choices=("generate", "judge", "report", "status", "all"), nargs="?", default="status")
    parser.add_argument("--config", default="configs/source_dataset.yaml")
    parser.add_argument("--generation-config", default="configs/generation.yaml")
    parser.add_argument("--evaluation-config", default="configs/evaluation.yaml")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    source_config = load_benchmark_config(Path(args.config))
    runner_config = as_runner_config(source_config)
    output_dir = Path(str(source_config.get("output_dir", "runs/source_dataset")))
    manifest_path = output_dir / "manifest.json"

    if args.phase in ("generate", "all"):
        generate_phase(runner_config, Path(args.generation_config), manifest_path, force=args.force)
    if args.phase in ("judge", "all"):
        judge_phase(runner_config, Path(args.evaluation_config), manifest_path, force=args.force)
    if args.phase in ("report", "all"):
        report_phase(runner_config, manifest_path, output_dir)
    if args.phase in ("status", "all"):
        print_status(source_config, manifest_path)


if __name__ == "__main__":
    main()
