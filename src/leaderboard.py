from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table

from src.model_registry import load_registry, save_json

console = Console()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def leaderboard_rows(registry: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in registry.get("entries") or []:
        screen = entry.get("screen") or {}
        cost = entry.get("cost") or {}
        dataset = entry.get("dataset") or {}
        rows.append({
            "model": entry.get("model"),
            "status": entry.get("status"),
            "judge_average": screen.get("judge_average"),
            "technical_pass_rate": screen.get("technical_pass_rate"),
            "judge_accept_rate": screen.get("accept_rate"),
            "critical_failures": screen.get("critical_failure_count", 0),
            "dataset_examples": dataset.get("examples"),
            "total_tokens": cost.get("total_tokens", 0),
            "cost_usd": cost.get("cost_usd", 0.0),
            "cost_try": cost.get("cost_try"),
            "updated_at": entry.get("updated_at"),
            "fingerprint": entry.get("fingerprint"),
        })

    def rank_key(row: dict[str, Any]) -> tuple[float, float, float]:
        judge = float(row["judge_average"]) if row.get("judge_average") is not None else -1.0
        tech = float(row["technical_pass_rate"]) if row.get("technical_pass_rate") is not None else -1.0
        cost = float(row.get("cost_usd") or 0.0)
        return (-judge, -tech, cost)

    rows.sort(key=rank_key)
    return rows


def render(rows: list[dict[str, Any]]) -> None:
    table = Table(title="LUMI model qualification leaderboard")
    table.add_column("#", justify="right")
    table.add_column("Model")
    table.add_column("Status")
    table.add_column("Judge", justify="right")
    table.add_column("Tech", justify="right")
    table.add_column("Accept", justify="right")
    table.add_column("Examples", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("USD", justify="right")
    for index, row in enumerate(rows, start=1):
        judge = row.get("judge_average")
        tech = row.get("technical_pass_rate")
        accept = row.get("judge_accept_rate")
        table.add_row(
            str(index),
            str(row.get("model")),
            str(row.get("status")),
            "—" if judge is None else f"{float(judge):.2f}",
            "—" if tech is None else f"{float(tech) * 100:.0f}%",
            "—" if accept is None else f"{float(accept) * 100:.0f}%",
            str(row.get("dataset_examples") if row.get("dataset_examples") is not None else "—"),
            f"{int(row.get('total_tokens') or 0):,}",
            f"${float(row.get('cost_usd') or 0.0):.4f}",
        )
    console.print(table)


def main() -> None:
    parser = argparse.ArgumentParser(description="Show the stored LUMI model qualification leaderboard.")
    parser.add_argument("--config", default="configs/qualification.yaml")
    args = parser.parse_args()
    config = load_yaml(Path(args.config))
    registry_path = Path(str(config.get("registry_path", "runs/model_registry/registry.json")))
    output_path = Path(str(config.get("leaderboard_path", "runs/model_registry/leaderboard.json")))
    rows = leaderboard_rows(load_registry(registry_path))
    save_json(output_path, {"rows": rows})
    render(rows)
    console.print(f"JSON: {output_path}")


if __name__ == "__main__":
    main()
