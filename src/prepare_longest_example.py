from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from transformers import AutoProcessor


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSONL at line {line_number}: {exc}") from exc
            if not isinstance(row, dict):
                raise RuntimeError(f"Training row {line_number} must be an object.")
            rows.append(row)
    if not rows:
        raise RuntimeError("Training dataset is empty.")
    return rows


def render_for_audit(row: dict[str, Any]) -> str:
    instruction = str(row.get("instruction") or "").strip()
    input_text = str(row.get("input") or "").strip()
    output = str(row.get("output") or "").strip()
    if not instruction or not input_text or not output:
        raise RuntimeError("Training row contains an empty instruction/input/output field.")
    return f"{instruction}\n\n{input_text}\n\n{output}".strip()


def prepare(
    *,
    dataset_path: Path,
    model_name: str,
    output_dataset: Path,
    output_manifest: Path,
) -> dict[str, Any]:
    processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
    tokenizer = processor.tokenizer if hasattr(processor, "tokenizer") else processor

    rows = load_jsonl(dataset_path)
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for index, row in enumerate(rows):
        text = render_for_audit(row)
        token_count = len(tokenizer(text, add_special_tokens=True)["input_ids"])
        scored.append((token_count, index, row))

    token_count, row_index, row = max(scored, key=lambda item: item[0])
    payload = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()

    output_dataset.parent.mkdir(parents=True, exist_ok=True)
    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    output_dataset.write_bytes(payload)

    metadata = row.get("metadata") or {}
    result = {
        "examples": 1,
        "sha256": digest,
        "output_path": str(output_dataset),
        "source_dataset": str(dataset_path),
        "model": model_name,
        "row_index": row_index,
        "token_count": token_count,
        "example_type": metadata.get("example_type"),
        "example_id": row.get("example_id") or row.get("id"),
    }
    output_manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"row_index = {row_index}")
    print(f"tokens    = {token_count}")
    print(f"type      = {result['example_type']}")
    print(f"example_id= {result['example_id']}")
    print(f"dataset   = {output_dataset}")
    print(f"manifest  = {output_manifest}")
    print(f"sha256    = {digest}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare the longest frozen Milestone-1 example for a QLoRA VRAM stress test.")
    parser.add_argument("--dataset", default="data/processed/milestone1_train.jsonl")
    parser.add_argument("--model", default="Qwen/Qwen3.5-4B")
    parser.add_argument("--output-dataset", default="runs/tmp/longest_train.jsonl")
    parser.add_argument("--output-manifest", default="runs/tmp/longest_manifest.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prepare(
        dataset_path=Path(args.dataset),
        model_name=args.model,
        output_dataset=Path(args.output_dataset),
        output_manifest=Path(args.output_manifest),
    )


if __name__ == "__main__":
    main()
