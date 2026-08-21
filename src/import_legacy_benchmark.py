from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from rich.console import Console

from src.model_registry import load_registry, upsert_entry
from src.teacher_benchmark import summarize_entries

console = Console()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def portable_path(raw: str) -> Path:
    return Path(raw.replace("\\", "/"))


def judge_usage(entry: dict[str, Any]) -> tuple[int, int, int, float, str | None]:
    raw = entry.get("judgment_path")
    if not raw:
        return 0, 0, 0, float(entry.get("judge_cost_usd") or 0.0), None
    path = portable_path(str(raw))
    if not path.exists():
        return 0, 0, 0, float(entry.get("judge_cost_usd") or 0.0), None
    payload = load_json(path)
    usage = payload.get("usage") or {}
    cost = payload.get("cost") or {}
    return (
        int(usage.get("input_tokens") or 0),
        int(usage.get("output_tokens") or 0),
        int(usage.get("total_tokens") or 0),
        float(cost.get("usd") or entry.get("judge_cost_usd") or 0.0),
        payload.get("judge_model"),
    )


def import_manifest(manifest_path: Path, registry_path: Path) -> int:
    manifest = load_json(manifest_path)
    entries = list(manifest.get("entries") or [])
    models = sorted({str(entry.get("model")) for entry in entries if entry.get("model")})
    summaries = summarize_entries(entries, models)
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    imported = 0

    for model in models:
        rows = [entry for entry in entries if entry.get("model") == model]
        teacher_output = sum(int(entry.get("teacher_output_tokens") or 0) for entry in rows)
        teacher_cost = sum(float(entry.get("teacher_cost_usd") or 0.0) for entry in rows)
        judge_input = judge_output = judge_total = 0
        judge_cost = 0.0
        judge_models: set[str] = set()
        for entry in rows:
            i, o, t, c, judge_model = judge_usage(entry)
            judge_input += i
            judge_output += o
            judge_total += t or i + o
            judge_cost += c
            if judge_model:
                judge_models.add(str(judge_model))

        fingerprint_raw = f"legacy|{manifest_sha}|{model}".encode("utf-8")
        fingerprint = "legacy-" + hashlib.sha256(fingerprint_raw).hexdigest()
        summary = summaries[model]
        registry_entry = {
            "model": model,
            "fingerprint": fingerprint,
            "qualification_version": "legacy_teacher_benchmark_import",
            "judge_model": ", ".join(sorted(judge_models)) or None,
            "status": "legacy_screened",
            "updated_at": manifest.get("created_at"),
            "run_dir": str(manifest_path.parent),
            "screen": summary,
            "dataset": {},
            "reasons": ["imported_from_pre_qualification_teacher_benchmark"],
            "cost": {
                "api_calls": len([r for r in rows if r.get("generation_status") == "complete"]) + len([r for r in rows if r.get("judge_status") == "complete"]),
                "input_tokens": judge_input,
                "output_tokens": teacher_output + judge_output,
                "total_tokens": teacher_output + judge_total,
                "cost_usd": round(teacher_cost + judge_cost, 8),
                "cost_try": None,
                "usd_try_rate": None,
                "by_stage": {
                    "legacy_teacher_generation": {
                        "output_tokens": teacher_output,
                        "cost_usd": round(teacher_cost, 8),
                    },
                    "legacy_judge": {
                        "input_tokens": judge_input,
                        "output_tokens": judge_output,
                        "total_tokens": judge_total,
                        "cost_usd": round(judge_cost, 8),
                    },
                },
                "token_accounting_note": "Legacy generation manifests stored teacher output tokens but not teacher input tokens; total_tokens is therefore a lower bound.",
            },
            "fingerprint_files": {str(manifest_path): manifest_sha},
        }
        upsert_entry(registry_path, registry_entry)
        imported += 1
        console.print(
            f"Imported {model}: tech={summary.get('technical_pass_rate')} "
            f"judge={summary.get('judge_average')} cost=${registry_entry['cost']['cost_usd']:.4f}"
        )

    console.print(f"Imported models: {imported}")
    console.print(f"Registry: {registry_path}")
    return imported


def main() -> None:
    parser = argparse.ArgumentParser(description="Import pre-qualification teacher benchmark history into the model registry.")
    parser.add_argument("--manifest", default="runs/teacher_benchmark/manifest.json")
    parser.add_argument("--registry", default="runs/model_registry/registry.json")
    args = parser.parse_args()
    import_manifest(Path(args.manifest), Path(args.registry))


if __name__ == "__main__":
    main()
