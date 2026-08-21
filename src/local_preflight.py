from __future__ import annotations

import argparse
import importlib
import json
import platform
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()

OPTIONAL_PACKAGES = (
    "torch",
    "transformers",
    "datasets",
    "peft",
    "trl",
    "bitsandbytes",
    "unsloth",
)


def package_version(name: str) -> str | None:
    try:
        module = importlib.import_module(name)
    except Exception:
        return None
    return str(getattr(module, "__version__", "installed"))


def collect_preflight() -> dict[str, Any]:
    result: dict[str, Any] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": {name: package_version(name) for name in OPTIONAL_PACKAGES},
        "cuda": {
            "available": False,
            "torch_cuda_version": None,
            "device_count": 0,
            "devices": [],
        },
    }

    try:
        import torch
    except Exception:
        return result

    result["cuda"]["available"] = bool(torch.cuda.is_available())
    result["cuda"]["torch_cuda_version"] = str(torch.version.cuda) if torch.version.cuda else None
    if not torch.cuda.is_available():
        return result

    count = int(torch.cuda.device_count())
    result["cuda"]["device_count"] = count
    for index in range(count):
        props = torch.cuda.get_device_properties(index)
        result["cuda"]["devices"].append(
            {
                "index": index,
                "name": str(props.name),
                "total_vram_gb": round(float(props.total_memory) / (1024 ** 3), 2),
                "compute_capability": f"{props.major}.{props.minor}",
            }
        )
    return result


def classify(result: dict[str, Any]) -> tuple[str, list[str]]:
    notes: list[str] = []
    python_parts = result["python"].split(".")
    python_major_minor = tuple(int(item) for item in python_parts[:2])
    if python_major_minor >= (3, 13):
        notes.append("Python 3.13+ may be incompatible with parts of the Unsloth training stack.")

    packages = result["packages"]
    if packages.get("torch") is None:
        notes.append("torch is not installed in this environment.")
        return "not_ready", notes

    cuda = result["cuda"]
    if not cuda.get("available"):
        notes.append("CUDA is not available to PyTorch.")
        return "not_ready", notes

    devices = cuda.get("devices") or []
    if not devices:
        notes.append("No CUDA GPU was detected.")
        return "not_ready", notes

    max_vram = max(float(device.get("total_vram_gb", 0)) for device in devices)
    if max_vram < 6:
        notes.append(
            "Detected VRAM is below 6 GB. Qwen3.5-4B 4-bit experiments may be very constrained; "
            "use this machine for pipeline checks or switch to a smaller checkpoint."
        )
        status = "constrained"
    elif max_vram < 8:
        notes.append("Detected VRAM is below the 8 GB training target; expect tighter sequence/batch limits.")
        status = "constrained"
    else:
        notes.append("GPU VRAM meets the current 8 GB target for the first QLoRA experiment.")
        status = "candidate_ready"

    missing = [name for name in OPTIONAL_PACKAGES if name != "torch" and packages.get(name) is None]
    if missing:
        notes.append("Training packages not installed yet: " + ", ".join(missing))
        if status == "candidate_ready":
            status = "stack_missing"
    else:
        notes.append("All expected training packages are importable.")

    return status, notes


def print_report(result: dict[str, Any], status: str, notes: list[str]) -> None:
    table = Table(title="LUMI local training preflight")
    table.add_column("Item")
    table.add_column("Value")
    table.add_row("Python", result["python"])
    table.add_row("Platform", result["platform"])
    table.add_row("CUDA available", "yes" if result["cuda"]["available"] else "no")
    table.add_row("Torch CUDA", str(result["cuda"]["torch_cuda_version"] or "—"))
    table.add_row("GPU count", str(result["cuda"]["device_count"]))
    for device in result["cuda"].get("devices") or []:
        table.add_row(
            f"GPU {device['index']}",
            f"{device['name']} | {device['total_vram_gb']:.2f} GB | CC {device['compute_capability']}",
        )
    console.print(table)

    package_table = Table(title="Training stack")
    package_table.add_column("Package")
    package_table.add_column("Version")
    for name, version in result["packages"].items():
        package_table.add_row(name, version or "not installed")
    console.print(package_table)

    console.print(f"Status: [bold]{status}[/bold]")
    for note in notes:
        console.print(f"- {note}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect local GPU and Python training-stack compatibility.")
    parser.add_argument("--json", dest="json_path", help="Optional path to save the preflight result as JSON")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = collect_preflight()
    status, notes = classify(result)
    result["status"] = status
    result["notes"] = notes
    print_report(result, status, notes)
    if args.json_path:
        path = Path(args.json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"JSON: {path}")


if __name__ == "__main__":
    main()
