from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table

console = Console()
REQUIRED_FIELDS = ("id", "example_type", "instruction", "input", "output", "source_excerpt", "source_story_id")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def count_words(text: str) -> int:
    return len(text.split())


def collect_examples(input_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(input_dir.glob("*.examples.json")):
        payload = load_json(path)
        examples = payload.get("examples")
        if not isinstance(examples, list):
            raise RuntimeError(f"{path} does not contain an examples array")
        for example in examples:
            if not isinstance(example, dict):
                raise RuntimeError(f"{path} contains a non-object example")
            row = dict(example)
            row["_source_file"] = str(path)
            rows.append(row)
    return rows


def audit_examples(examples: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    min_words = {str(k): int(v) for k, v in (config.get("min_output_words") or {}).items()}
    max_words = {str(k): int(v) for k, v in (config.get("max_output_words") or {}).items()}

    output_counts = Counter(
        normalize_text(str(row.get("output", ""))) for row in examples if str(row.get("output", "")).strip()
    )
    task_counts = Counter(
        (
            normalize_text(str(row.get("instruction", ""))),
            normalize_text(str(row.get("input", ""))),
        )
        for row in examples
        if str(row.get("instruction", "")).strip() and str(row.get("input", "")).strip()
    )

    audited: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row in examples:
        reasons: list[str] = []
        hard_failures: list[str] = []

        for field in REQUIRED_FIELDS:
            value = row.get(field)
            if not isinstance(value, str) or not value.strip():
                hard_failures.append(f"missing_or_empty:{field}")

        example_id = str(row.get("id", ""))
        if example_id in seen_ids:
            hard_failures.append("duplicate_id")
        seen_ids.add(example_id)

        kind = str(row.get("example_type", ""))
        output = str(row.get("output", ""))
        words = count_words(output)
        if kind not in min_words or kind not in max_words:
            reasons.append("unknown_example_type")
        else:
            if words < min_words[kind]:
                reasons.append(f"output_too_short:{words}<{min_words[kind]}")
            if words > max_words[kind]:
                reasons.append(f"output_too_long:{words}>{max_words[kind]}")

        normalized_output = normalize_text(output)
        if normalized_output and output_counts[normalized_output] > 1:
            hard_failures.append("exact_duplicate_output")

        task_key = (
            normalize_text(str(row.get("instruction", ""))),
            normalize_text(str(row.get("input", ""))),
        )
        if task_key != ("", "") and task_counts[task_key] > 1:
            reasons.append("duplicate_instruction_input")

        if normalize_text(str(row.get("instruction", ""))) == normalize_text(output) and output.strip():
            hard_failures.append("instruction_matches_output")

        if hard_failures:
            status = "reject"
        elif reasons:
            status = "review"
        else:
            status = "ready"

        audited.append(
            {
                **row,
                "curation": {
                    "status": status,
                    "output_words": words,
                    "review_reasons": reasons,
                    "hard_failures": hard_failures,
                },
            }
        )
    return audited


def summarize(audited: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(row["curation"]["status"] for row in audited)
    type_counts = Counter(str(row.get("example_type")) for row in audited)
    source_counts = Counter(str(row.get("source_story_id")) for row in audited)
    reason_counts: Counter[str] = Counter()
    for row in audited:
        reason_counts.update(row["curation"].get("review_reasons") or [])
        reason_counts.update(row["curation"].get("hard_failures") or [])
    return {
        "total": len(audited),
        "ready": status_counts.get("ready", 0),
        "review": status_counts.get("review", 0),
        "reject": status_counts.get("reject", 0),
        "by_type": dict(sorted(type_counts.items())),
        "by_source_story": dict(sorted(source_counts.items())),
        "issues": dict(reason_counts.most_common()),
    }


def validate_expected_shape(summary: dict[str, Any], config: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    expected_total = int(config.get("expected_total_examples", 0))
    expected_sources = int(config.get("expected_source_stories", 0))
    expected_per_story = int(config.get("expected_examples_per_story", 0))
    if expected_total and summary["total"] != expected_total:
        warnings.append(f"expected_total_examples:{expected_total}!={summary['total']}")
    if expected_sources and len(summary["by_source_story"]) != expected_sources:
        warnings.append(f"expected_source_stories:{expected_sources}!={len(summary['by_source_story'])}")
    if expected_per_story:
        for story_id, count in summary["by_source_story"].items():
            if count != expected_per_story:
                warnings.append(f"expected_examples_per_story:{story_id}:{expected_per_story}!={count}")
    return warnings


def write_outputs(audited: list[dict[str, Any]], summary: dict[str, Any], config: dict[str, Any]) -> None:
    output_dir = Path(str(config.get("output_dir", "data/curated")))
    report_dir = Path(str(config.get("report_dir", "runs/curation")))
    save_json(output_dir / "milestone1_audit.json", {"examples": audited})
    save_json(report_dir / "summary.json", summary)

    review_rows = [row for row in audited if row["curation"]["status"] != "ready"]
    save_json(report_dir / "needs_review.json", {"examples": review_rows})


def print_summary(summary: dict[str, Any], warnings: list[str]) -> None:
    table = Table(title="Milestone 1 curation audit")
    table.add_column("Metric")
    table.add_column("Count", justify="right")
    for key in ("total", "ready", "review", "reject"):
        table.add_row(key, str(summary[key]))
    console.print(table)
    console.print("By type:")
    for kind, count in summary["by_type"].items():
        console.print(f"  {kind}: {count}")
    if summary["issues"]:
        console.print("Issues:")
        for issue, count in summary["issues"].items():
            console.print(f"  {issue}: {count}")
    if warnings:
        console.print("[yellow]Shape warnings:[/yellow]")
        for warning in warnings:
            console.print(f"  {warning}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic curation checks over extracted supervised examples.")
    parser.add_argument("--config", default="configs/curation.yaml")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_yaml(Path(args.config))
    examples = collect_examples(Path(str(config.get("input_dir", "data/raw/extracted"))))
    audited = audit_examples(examples, config)
    summary = summarize(audited)
    warnings = validate_expected_shape(summary, config)
    summary["shape_warnings"] = warnings
    write_outputs(audited, summary, config)
    print_summary(summary, warnings)


if __name__ == "__main__":
    main()
