from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import torch
import yaml
from rich.console import Console
from rich.table import Table
from unsloth import FastModel

console = Console()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def gib(value: int) -> float:
    return round(float(value) / (1024 ** 3), 3)


def snapshot() -> dict[str, float]:
    if not torch.cuda.is_available():
        return {"allocated_gb": 0.0, "reserved_gb": 0.0, "max_allocated_gb": 0.0}
    return {
        "allocated_gb": gib(torch.cuda.memory_allocated()),
        "reserved_gb": gib(torch.cuda.memory_reserved()),
        "max_allocated_gb": gib(torch.cuda.max_memory_allocated()),
    }


def run_probe(config_path: Path) -> dict[str, Any]:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available to PyTorch.")

    config = load_yaml(config_path)
    model_name = str(config.get("model") or "").strip()
    if not model_name:
        raise RuntimeError("model_probe config requires model.")

    max_seq_length = int(config.get("max_seq_length", 1024))
    load_in_4bit = bool(config.get("load_in_4bit", True))
    trust_remote_code = bool(config.get("trust_remote_code", True))
    output_path = Path(str(config.get("output_path", "runs/model_probe/result.json")))

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    before = snapshot()

    token = os.getenv("HF_TOKEN") or None
    console.print(f"Loading [bold]{model_name}[/bold] | 4-bit={load_in_4bit} | max_seq_length={max_seq_length}")
    model, processor = FastModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        load_in_4bit=load_in_4bit,
        trust_remote_code=trust_remote_code,
        token=token,
    )

    after = snapshot()
    device = torch.cuda.current_device()
    props = torch.cuda.get_device_properties(device)
    result = {
        "name": config.get("name", "model_probe"),
        "model": model_name,
        "max_seq_length": max_seq_length,
        "load_in_4bit": load_in_4bit,
        "gpu": str(props.name),
        "total_vram_gb": gib(props.total_memory),
        "before": before,
        "after_load": after,
        "processor_type": type(processor).__name__,
        "model_type": type(model).__name__,
        "status": "loaded",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    table = Table(title="LUMI model load probe")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("model", model_name)
    table.add_row("GPU", str(props.name))
    table.add_row("total VRAM", f"{result['total_vram_gb']:.3f} GB")
    table.add_row("allocated before", f"{before['allocated_gb']:.3f} GB")
    table.add_row("allocated after", f"{after['allocated_gb']:.3f} GB")
    table.add_row("reserved after", f"{after['reserved_gb']:.3f} GB")
    table.add_row("peak allocated", f"{after['max_allocated_gb']:.3f} GB")
    table.add_row("model type", result["model_type"])
    table.add_row("processor", result["processor_type"])
    console.print(table)
    console.print(f"Status: [green]{result['status']}[/green]")
    console.print(f"JSON: {output_path}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load a small Unsloth checkpoint and measure CUDA VRAM usage.")
    parser.add_argument("--config", default="configs/model_probe.yaml")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_probe(Path(args.config))


if __name__ == "__main__":
    main()
