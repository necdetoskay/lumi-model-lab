from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from rich.console import Console

from src.generate import generate_one
from src.schemas import StorySpec

console = Console()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the five M1.1 termination-focused teacher source stories.")
    parser.add_argument("--plan", default="configs/m11_sources.yaml")
    parser.add_argument("--model", help="Override TEACHER_MODEL for this run.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_dotenv()
    plan = load_yaml(Path(args.plan))
    generation_config = load_yaml(Path(str(plan.get("generation_config", "configs/generation.yaml"))))
    spec_paths = [Path(str(item)) for item in plan.get("specs") or []]
    if not spec_paths:
        raise SystemExit("M1.1 plan contains no source specs.")

    completed = 0
    eligible = 0
    for index, spec_path in enumerate(spec_paths, start=1):
        spec = StorySpec.model_validate(load_yaml(spec_path))
        console.rule(f"M1.1 source {index}/{len(spec_paths)} — {spec_path.name}")
        output_path, validation = generate_one(
            generation_config,
            spec,
            dry_run=args.dry_run,
            model_override=args.model,
        )
        if args.dry_run:
            continue
        completed += 1
        if validation and validation.eligible_for_judge:
            eligible += 1
        console.print(f"saved={output_path}")
        if validation:
            console.print(
                f"words={validation.word_count} finish_reason={validation.finish_reason} "
                f"eligible={validation.eligible_for_judge}"
            )

    if not args.dry_run:
        console.rule("M1.1 source generation summary")
        console.print(f"completed={completed}/{len(spec_paths)}")
        console.print(f"technical_gate_pass={eligible}/{len(spec_paths)}")


if __name__ == "__main__":
    main()
