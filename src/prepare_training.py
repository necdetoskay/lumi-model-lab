from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table

console = Console()

MOJIBAKE_MARKERS = ("Ã", "Ä", "Å", "Â", "â€", "ï¿½")
TURKISH_CHARS = set("çÇğĞıİöÖşŞüÜ")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def has_mojibake(text: str) -> bool:
    return any(marker in text for marker in MOJIBAKE_MARKERS)


def build_training_rows(payload: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    examples = payload.get("examples")
    if not isinstance(examples, list):
        raise RuntimeError("Curated input must contain an examples array.")

    required_status = str(config.get("required_status", "ready"))
    fields = [str(item) for item in (config.get("fields") or ["instruction", "input", "output"])]
    metadata_fields = [str(item) for item in (config.get("metadata_fields") or [])]
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for example in examples:
        if not isinstance(example, dict):
            raise RuntimeError("Curated examples must be objects.")
        curation = example.get("curation") or {}
        if curation.get("status") != required_status:
            continue

        example_id = str(example.get("id") or "").strip()
        if not example_id:
            raise RuntimeError("Training example is missing id.")
        if example_id in seen_ids:
            raise RuntimeError(f"Duplicate training example id: {example_id}")
        seen_ids.add(example_id)

        row: dict[str, Any] = {}
        for field in fields:
            value = example.get(field)
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(f"{example_id} has empty or invalid field {field}.")
            if has_mojibake(value):
                raise RuntimeError(f"{example_id} field {field} appears to contain mojibake.")
            row[field] = value.strip()

        metadata: dict[str, Any] = {}
        for field in metadata_fields:
            if field in example:
                metadata[field] = example[field]
        row["metadata"] = metadata
        rows.append(row)

    rows.sort(key=lambda item: str((item.get("metadata") or {}).get("id", "")))
    expected = int(config.get("expected_examples", 0))
    if expected and len(rows) != expected:
        raise RuntimeError(f"Expected {expected} ready examples, found {len(rows)}.")
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    type_counts = Counter(str((row.get("metadata") or {}).get("example_type", "unknown")) for row in rows)
    source_counts = Counter(str((row.get("metadata") or {}).get("source_story_id", "unknown")) for row in rows)
    combined_text = "\n".join(
        str(row.get("instruction", "")) + "\n" + str(row.get("input", "")) + "\n" + str(row.get("output", ""))
        for row in rows
    )
    return {
        "examples": len(rows),
        "by_type": dict(sorted(type_counts.items())),
        "by_source_story": dict(sorted(source_counts.items())),
        "contains_turkish_chars": any(char in combined_text for char in TURKISH_CHARS),
        "mojibake_detected": has_mojibake(combined_text),
    }


def prepare(config_path: Path) -> dict[str, Any]:
    config = load_yaml(config_path)
    input_path = Path(str(config.get("input_path", "data/curated/milestone1_audit.json")))
    output_path = Path(str(config.get("output_path", "data/processed/milestone1_train.jsonl")))
    manifest_path = Path(str(config.get("manifest_path", "runs/training_dataset/manifest.json")))

    rows = build_training_rows(load_json(input_path), config)
    digest = write_jsonl(output_path, rows)
    summary = summarize_rows(rows)
    if summary["mojibake_detected"]:
        raise RuntimeError("Prepared training dataset contains mojibake markers.")

    manifest = {
        "name": config.get("name", "training_dataset"),
        "input_path": str(input_path),
        "output_path": str(output_path),
        "sha256": digest,
        **summary,
    }
    write_json(manifest_path, manifest)

    table = Table(title="Milestone 1 training dataset")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("examples", str(summary["examples"]))
    table.add_row("source stories", str(len(summary["by_source_story"])))
    table.add_row("types", str(len(summary["by_type"])))
    table.add_row("Turkish chars", "yes" if summary["contains_turkish_chars"] else "no")
    table.add_row("mojibake", "yes" if summary["mojibake_detected"] else "no")
    console.print(table)
    console.print(f"JSONL:  {output_path}")
    console.print(f"SHA256: {digest}")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare the frozen Milestone-1 training JSONL dataset.")
    parser.add_argument("--config", default="configs/prepare_training.yaml")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prepare(Path(args.config))


if __name__ == "__main__":
    main()
