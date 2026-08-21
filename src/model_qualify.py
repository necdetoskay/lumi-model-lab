from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from src.cost_ledger import collect_qualification_costs
from src.curate_examples import (
    apply_manual_overrides,
    audit_examples,
    collect_examples,
    summarize as summarize_curation,
    validate_expected_shape,
    write_outputs as write_curation_outputs,
)
from src.extract_examples import run_extraction
from src.model_registry import (
    build_fingerprint,
    find_by_fingerprint,
    load_registry,
    model_slug,
    save_json,
    upsert_entry,
)
from src.prepare_training import prepare
from src.source_dataset import as_runner_config
from src.teacher_benchmark import (
    generate_phase,
    judge_phase,
    load_benchmark_config,
    report_phase,
    summarize_entries,
)

console = Console()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def screen_gate(summary: dict[str, Any], gates: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    tech = summary.get("technical_pass_rate")
    accept = summary.get("accept_rate")
    judge_avg = summary.get("judge_average")
    critical = int(summary.get("critical_failure_count") or 0)

    if tech is None or tech < float(gates.get("min_technical_pass_rate", 0.8)):
        reasons.append("technical_pass_rate_below_threshold")
    if accept is None or accept < float(gates.get("min_judge_accept_rate", 0.8)):
        reasons.append("judge_accept_rate_below_threshold")
    if judge_avg is None or judge_avg < float(gates.get("min_average_judge_score", 4.0)):
        reasons.append("judge_average_below_threshold")
    if critical > int(gates.get("max_critical_failures", 0)):
        reasons.append("critical_failures_above_threshold")
    return not reasons, reasons


def technical_screen_gate(summary: dict[str, Any], gates: dict[str, Any]) -> tuple[bool, list[str]]:
    tech = summary.get("technical_pass_rate")
    minimum = float(gates.get("min_technical_pass_rate", 0.8))
    if tech is None or tech < minimum:
        return False, ["technical_pass_rate_below_threshold"]
    return True, []


def generation_error_reasons(manifest: dict[str, Any], model: str) -> list[str]:
    errors = [
        entry for entry in manifest.get("entries") or []
        if entry.get("model") == model and entry.get("generation_status") == "error"
    ]
    if not errors:
        return []
    reasons = [f"generation_errors_present:{len(errors)}"]
    for entry in errors[:3]:
        spec = Path(str(entry.get("spec_path", "unknown"))).name
        message = str(entry.get("generation_error") or "unknown generation error")
        if len(message) > 240:
            message = message[:237] + "..."
        reasons.append(f"{spec}: {message}")
    return reasons


def source_gate(manifest: dict[str, Any], required: int) -> tuple[bool, int]:
    accepted = [
        entry for entry in manifest.get("entries") or []
        if entry.get("generation_status") == "complete"
        and entry.get("technical_pass")
        and entry.get("judge_status") == "complete"
        and entry.get("judge_accepted")
    ]
    return len(accepted) >= required, len(accepted)


def make_entry(
    *, model: str, fingerprint: str, hashes: dict[str, str], judge_model: str | None,
    run_dir: Path, status: str, screen: dict[str, Any] | None = None,
    dataset: dict[str, Any] | None = None, reasons: list[str] | None = None,
) -> dict[str, Any]:
    ledger = collect_qualification_costs(run_dir)
    return {
        "model": model,
        "fingerprint": fingerprint,
        "qualification_version": "model_qualification_v1",
        "judge_model": judge_model,
        "status": status,
        "updated_at": now_iso(),
        "run_dir": str(run_dir),
        "screen": screen or {},
        "dataset": dataset or {},
        "reasons": reasons or [],
        "cost": ledger,
        "fingerprint_files": hashes,
    }


def print_entry(entry: dict[str, Any]) -> None:
    table = Table(title="LUMI model qualification")
    table.add_column("Metric")
    table.add_column("Value")
    screen = entry.get("screen") or {}
    cost = entry.get("cost") or {}
    dataset = entry.get("dataset") or {}
    table.add_row("model", str(entry.get("model")))
    table.add_row("status", str(entry.get("status")))
    table.add_row("technical", str(screen.get("technical_pass_rate", "—")))
    table.add_row("judge avg", str(screen.get("judge_average", "—")))
    table.add_row("judge accept", str(screen.get("accept_rate", "—")))
    table.add_row("dataset examples", str(dataset.get("examples", "—")))
    table.add_row("input tokens", str(cost.get("input_tokens", 0)))
    table.add_row("output tokens", str(cost.get("output_tokens", 0)))
    table.add_row("total tokens", str(cost.get("total_tokens", 0)))
    table.add_row("total cost USD", f"${float(cost.get('cost_usd', 0.0)):.6f}")
    if cost.get("cost_try") is not None:
        table.add_row("total cost TRY", f"₺{float(cost['cost_try']):.2f}")
    console.print(table)
    if entry.get("reasons"):
        console.print("Reasons: " + ", ".join(str(item) for item in entry["reasons"]))


def list_registry(registry_path: Path, model_filter: str | None = None) -> None:
    registry = load_registry(registry_path)
    entries = list(registry.get("entries") or [])
    if model_filter:
        entries = [item for item in entries if item.get("model") == model_filter]
    entries.sort(key=lambda item: str(item.get("updated_at", "")), reverse=True)
    if not entries:
        console.print("No qualification records found.")
        return
    table = Table(title="LUMI model registry")
    table.add_column("Model")
    table.add_column("Status")
    table.add_column("Judge", justify="right")
    table.add_column("Tech", justify="right")
    table.add_column("Examples", justify="right")
    table.add_column("Cost USD", justify="right")
    for entry in entries:
        screen = entry.get("screen") or {}
        cost = entry.get("cost") or {}
        dataset = entry.get("dataset") or {}
        table.add_row(
            str(entry.get("model")),
            str(entry.get("status")),
            "—" if screen.get("judge_average") is None else f"{float(screen['judge_average']):.2f}",
            "—" if screen.get("technical_pass_rate") is None else f"{float(screen['technical_pass_rate']) * 100:.0f}%",
            str(dataset.get("examples", "—")),
            f"${float(cost.get('cost_usd', 0.0)):.4f}",
        )
    console.print(table)


def run_qualification(model: str, config_path: Path, *, screen_only: bool, rerun: bool) -> dict[str, Any]:
    config = load_yaml(config_path)
    registry_path = Path(str(config.get("registry_path", "runs/model_registry/registry.json")))
    judge_model = os.getenv("JUDGE_MODEL")
    fingerprint, hashes = build_fingerprint(
        model,
        config,
        extra_identity={"judge_model": judge_model},
    )
    existing = find_by_fingerprint(load_registry(registry_path), fingerprint)
    if existing and not rerun:
        console.print("[yellow]ALREADY TESTED[/yellow] Same model + experiment fingerprint already exists.")
        print_entry(existing)
        return existing

    root = Path(str(config.get("qualification_root", "runs/qualifications")))
    run_dir = root / f"{model_slug(model)}__{fingerprint[:10]}"
    config_dir = run_dir / "configs"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1 — frozen teacher benchmark generation.
    benchmark = load_benchmark_config(Path(str(config["benchmark_config"])))
    benchmark = dict(benchmark)
    benchmark["name"] = f"qualification_screen__{model_slug(model)}"
    benchmark["models"] = [model]
    benchmark["output_dir"] = str(run_dir / "screen")
    benchmark_config_path = config_dir / "benchmark.yaml"
    write_yaml(benchmark_config_path, benchmark)
    screen_manifest = run_dir / "screen" / "manifest.json"

    console.rule("1/6 Technical benchmark")
    generated_manifest = generate_phase(
        benchmark,
        Path(str(config["generation_config"])),
        screen_manifest,
        force=rerun,
    )
    generated_summary = summarize_entries(generated_manifest.get("entries", []), [model])[model]
    generation_reasons = generation_error_reasons(generated_manifest, model)
    if generation_reasons:
        entry = make_entry(
            model=model, fingerprint=fingerprint, hashes=hashes, judge_model=judge_model,
            run_dir=run_dir, status="generation_error", screen=generated_summary, reasons=generation_reasons,
        )
        upsert_entry(registry_path, entry)
        save_json(run_dir / "final_report.json", entry)
        print_entry(entry)
        return entry

    tech_ok, tech_reasons = technical_screen_gate(generated_summary, config.get("screen_gates") or {})
    if not tech_ok:
        entry = make_entry(
            model=model, fingerprint=fingerprint, hashes=hashes, judge_model=judge_model,
            run_dir=run_dir, status="rejected_technical", screen=generated_summary, reasons=tech_reasons,
        )
        upsert_entry(registry_path, entry)
        save_json(run_dir / "final_report.json", entry)
        print_entry(entry)
        return entry

    # Stage 2 — judge only if technical gate passes.
    console.rule("2/6 Judge benchmark")
    judged_manifest = judge_phase(
        benchmark,
        Path(str(config["evaluation_config"])),
        screen_manifest,
        force=rerun,
    )
    report_phase(benchmark, screen_manifest, run_dir / "screen")
    screen_summary = summarize_entries(judged_manifest.get("entries", []), [model])[model]
    qualified, reasons = screen_gate(screen_summary, config.get("screen_gates") or {})
    if not qualified:
        entry = make_entry(
            model=model, fingerprint=fingerprint, hashes=hashes, judge_model=judge_model,
            run_dir=run_dir, status="rejected_judge", screen=screen_summary, reasons=reasons,
        )
        upsert_entry(registry_path, entry)
        save_json(run_dir / "final_report.json", entry)
        print_entry(entry)
        return entry

    if screen_only:
        entry = make_entry(
            model=model, fingerprint=fingerprint, hashes=hashes, judge_model=judge_model,
            run_dir=run_dir, status="screen_passed", screen=screen_summary,
        )
        upsert_entry(registry_path, entry)
        save_json(run_dir / "final_report.json", entry)
        print_entry(entry)
        return entry

    # Stage 3 — create independent training source stories.
    console.rule("3/6 Training source stories")
    source_config = load_yaml(Path(str(config["source_dataset_config"])))
    source_config = dict(source_config)
    source_config["teacher_model"] = model
    source_config["output_dir"] = str(run_dir / "source")
    source_config_path = config_dir / "source_dataset.yaml"
    write_yaml(source_config_path, source_config)
    source_runner = as_runner_config(source_config)
    source_manifest_path = run_dir / "source" / "manifest.json"
    generated_source_manifest = generate_phase(
        source_runner,
        Path(str(config["generation_config"])),
        source_manifest_path,
        force=rerun,
    )
    source_generation_reasons = generation_error_reasons(generated_source_manifest, model)
    if source_generation_reasons:
        entry = make_entry(
            model=model, fingerprint=fingerprint, hashes=hashes, judge_model=judge_model,
            run_dir=run_dir, status="generation_error", screen=screen_summary,
            reasons=["source_generation_failed", *source_generation_reasons],
        )
        upsert_entry(registry_path, entry)
        save_json(run_dir / "final_report.json", entry)
        print_entry(entry)
        return entry

    source_manifest = judge_phase(
        source_runner,
        Path(str(config["evaluation_config"])),
        source_manifest_path,
        force=rerun,
    )
    report_phase(source_runner, source_manifest_path, run_dir / "source")
    required_sources = int((config.get("full_gates") or {}).get("required_accepted_source_stories", 5))
    source_ok, accepted_count = source_gate(source_manifest, required_sources)
    if not source_ok:
        entry = make_entry(
            model=model, fingerprint=fingerprint, hashes=hashes, judge_model=judge_model,
            run_dir=run_dir, status="rejected_source_gate", screen=screen_summary,
            dataset={"accepted_source_stories": accepted_count},
            reasons=["accepted_source_stories_below_requirement"],
        )
        upsert_entry(registry_path, entry)
        save_json(run_dir / "final_report.json", entry)
        print_entry(entry)
        return entry

    # Stage 4 — supervised example extraction.
    console.rule("4/6 Supervised extraction")
    extraction_config = load_yaml(Path(str(config["extraction_config"])))
    extraction_config = dict(extraction_config)
    extraction_config.update({
        "source_manifest": str(source_manifest_path),
        "output_dir": str(run_dir / "extracted"),
        "run_dir": str(run_dir / "extraction"),
        "model": model,
    })
    extraction_config_path = config_dir / "extraction.yaml"
    write_yaml(extraction_config_path, extraction_config)
    extraction_manifest = run_extraction(extraction_config_path, force=rerun)
    complete_extractions = [item for item in extraction_manifest.get("entries") or [] if item.get("status") == "complete"]
    extracted_count = sum(int(item.get("example_count", 0)) for item in complete_extractions)

    # Stage 5 — deterministic curation. Manual-review findings stop the pipeline.
    console.rule("5/6 Curation gate")
    curation_config = load_yaml(Path(str(config["curation_config"])))
    curation_config = dict(curation_config)
    curation_config.update({
        "input_dir": str(run_dir / "extracted"),
        "output_dir": str(run_dir / "curated"),
        "report_dir": str(run_dir / "curation"),
    })
    curation_config.pop("manual_overrides", None)
    curation_config_path = config_dir / "curation.yaml"
    write_yaml(curation_config_path, curation_config)
    examples = collect_examples(run_dir / "extracted")
    audited = audit_examples(examples, curation_config)
    audited = apply_manual_overrides(audited, {}, curation_config)
    curation_summary = summarize_curation(audited)
    curation_summary["shape_warnings"] = validate_expected_shape(curation_summary, curation_config)
    write_curation_outputs(audited, curation_summary, curation_config)

    full_gates = config.get("full_gates") or {}
    required_ready = int(full_gates.get("required_ready_examples", 55))
    needs_review = int(curation_summary.get("review", 0))
    rejects = int(curation_summary.get("reject", 0))
    ready = int(curation_summary.get("ready", 0))
    if ready < required_ready or (full_gates.get("require_zero_review", True) and needs_review) or (
        full_gates.get("require_zero_reject", True) and rejects
    ):
        entry = make_entry(
            model=model, fingerprint=fingerprint, hashes=hashes, judge_model=judge_model,
            run_dir=run_dir, status="needs_manual_review", screen=screen_summary,
            dataset={
                "accepted_source_stories": accepted_count,
                "extracted_examples": extracted_count,
                "ready": ready,
                "review": needs_review,
                "reject": rejects,
            },
            reasons=["curation_gate_not_clean"],
        )
        upsert_entry(registry_path, entry)
        save_json(run_dir / "final_report.json", entry)
        print_entry(entry)
        return entry

    # Stage 6 — build frozen JSONL dataset.
    console.rule("6/6 Training dataset")
    prepare_config = load_yaml(Path(str(config["prepare_training_config"])))
    prepare_config = dict(prepare_config)
    prepare_config.update({
        "input_path": str(run_dir / "curated" / "milestone1_audit.json"),
        "output_path": str(run_dir / "dataset" / "train.jsonl"),
        "manifest_path": str(run_dir / "dataset" / "manifest.json"),
        "expected_examples": required_ready,
    })
    prepare_config_path = config_dir / "prepare_training.yaml"
    write_yaml(prepare_config_path, prepare_config)
    dataset_manifest = prepare(prepare_config_path)

    entry = make_entry(
        model=model, fingerprint=fingerprint, hashes=hashes, judge_model=judge_model,
        run_dir=run_dir, status="qualified", screen=screen_summary,
        dataset={
            "accepted_source_stories": accepted_count,
            "extracted_examples": extracted_count,
            "examples": dataset_manifest.get("examples"),
            "sha256": dataset_manifest.get("sha256"),
            "path": dataset_manifest.get("output_path"),
        },
    )
    upsert_entry(registry_path, entry)
    save_json(run_dir / "final_report.json", entry)
    print_entry(entry)
    return entry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Qualify an OpenRouter model through the frozen LUMI model-lab pipeline.")
    parser.add_argument("--model", help="OpenRouter model id, for example aion-labs/aion-3.0")
    parser.add_argument("--config", default="configs/qualification.yaml")
    parser.add_argument("--screen", action="store_true", help="Stop after benchmark + judge qualification")
    parser.add_argument("--rerun", action="store_true", help="Repeat the same experiment fingerprint intentionally")
    parser.add_argument("--status", action="store_true", help="Show stored records for --model without running it")
    parser.add_argument("--list", action="store_true", help="List all model qualification records")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    config = load_yaml(Path(args.config))
    registry_path = Path(str(config.get("registry_path", "runs/model_registry/registry.json")))
    if args.list:
        list_registry(registry_path)
        return
    if args.status:
        if not args.model:
            raise SystemExit("--status requires --model")
        list_registry(registry_path, args.model)
        return
    if not args.model:
        raise SystemExit("--model is required unless --list is used")
    run_qualification(args.model, Path(args.config), screen_only=args.screen, rerun=args.rerun)


if __name__ == "__main__":
    main()
