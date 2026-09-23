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
    require_qualification_runtime_profile,
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

SOURCE_RETRYABLE_TECHNICAL_REASONS = {
    "below_minimum_word_count",
    "above_maximum_word_count",
}
SOURCE_MAX_TECHNICAL_RETRIES = 2


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


def can_resume_from_screen(existing: dict[str, Any] | None, *, screen_only: bool, rerun: bool) -> bool:
    resumable_statuses = {"screen_passed", "rejected_source_gate"}
    return bool(
        existing
        and not rerun
        and not screen_only
        and existing.get("status") in resumable_statuses
        and existing.get("screen")
        and existing.get("run_dir")
    )


def retryable_source_entries(
    manifest: dict[str, Any],
    model: str,
    *,
    max_retries: int = SOURCE_MAX_TECHNICAL_RETRIES,
) -> list[dict[str, Any]]:
    retryable: list[dict[str, Any]] = []
    for entry in manifest.get("entries") or []:
        if entry.get("model") != model:
            continue
        if entry.get("generation_status") != "complete" or entry.get("technical_pass"):
            continue
        reasons = set(entry.get("technical_reasons") or [])
        if not reasons or not reasons.issubset(SOURCE_RETRYABLE_TECHNICAL_REASONS):
            continue
        if int(entry.get("technical_retry_count") or 0) >= max_retries:
            continue
        retryable.append(entry)
    return retryable


def retry_source_technical_failures(
    *,
    source_runner: dict[str, Any],
    generation_config_path: Path,
    source_manifest_path: Path,
    model: str,
    config_dir: Path,
) -> dict[str, Any]:
    if not source_manifest_path.exists():
        return {"entries": []}

    generation_config = load_yaml(generation_config_path)
    base_seed = generation_config.get("seed")

    for attempt in range(1, SOURCE_MAX_TECHNICAL_RETRIES + 1):
        manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        targets = retryable_source_entries(manifest, model)
        if not targets:
            return manifest

        console.rule(f"Source technical retry {attempt}/{SOURCE_MAX_TECHNICAL_RETRIES}")
        previous: dict[str, dict[str, Any]] = {}
        for entry in targets:
            key = str(entry.get("spec_path"))
            previous[key] = {
                "story_id": entry.get("story_id"),
                "word_count": entry.get("word_count"),
                "technical_reasons": list(entry.get("technical_reasons") or []),
                "teacher_cost_usd": entry.get("teacher_cost_usd"),
                "teacher_output_tokens": entry.get("teacher_output_tokens"),
                "technical_retry_count": int(entry.get("technical_retry_count") or 0),
                "retry_history": list(entry.get("retry_history") or []),
            }
            entry["generation_status"] = "retry_pending"
            console.print(
                f"[yellow]Retry[/yellow] {Path(key).name} | "
                f"words={entry.get('word_count')} | reasons={entry.get('technical_reasons')}"
            )
        save_json(source_manifest_path, manifest)

        retry_config = dict(generation_config)
        if isinstance(base_seed, int):
            retry_config["seed"] = base_seed + attempt
        retry_config_path = config_dir / f"generation_source_retry_{attempt}.yaml"
        write_yaml(retry_config_path, retry_config)
        manifest = generate_phase(
            source_runner,
            retry_config_path,
            source_manifest_path,
            force=False,
        )

        for entry in manifest.get("entries") or []:
            key = str(entry.get("spec_path"))
            if key not in previous:
                continue
            before = previous[key]
            old_cost = float(before.get("teacher_cost_usd") or 0.0)
            new_cost = float(entry.get("teacher_cost_usd") or 0.0)
            old_tokens = int(before.get("teacher_output_tokens") or 0)
            new_tokens = int(entry.get("teacher_output_tokens") or 0)
            history = list(before.get("retry_history") or [])
            history.append(
                {
                    "attempt": int(before.get("technical_retry_count") or 0) + 1,
                    "previous_story_id": before.get("story_id"),
                    "previous_word_count": before.get("word_count"),
                    "previous_reasons": before.get("technical_reasons"),
                    "retry_story_id": entry.get("story_id"),
                    "retry_word_count": entry.get("word_count"),
                    "retry_reasons": list(entry.get("technical_reasons") or []),
                    "seed": retry_config.get("seed"),
                    "retry_cost_usd": new_cost,
                    "retry_output_tokens": new_tokens,
                }
            )
            entry["technical_retry_count"] = int(before.get("technical_retry_count") or 0) + 1
            entry["retry_history"] = history
            entry["teacher_cost_usd"] = round(old_cost + new_cost, 9)
            entry["teacher_output_tokens"] = old_tokens + new_tokens
        save_json(source_manifest_path, manifest)

    return json.loads(source_manifest_path.read_text(encoding="utf-8"))


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
    # Cost-bearing qualification is fail-closed: generic/family fallbacks may be
    # useful for exploratory runtime calls, but they are not evidence that a new
    # model's transport contract has been verified.
    require_qualification_runtime_profile(model)
    config = load_yaml(config_path)
    registry_path = Path(str(config.get("registry_path", "runs/model_registry/registry.json")))
    judge_model = os.getenv("JUDGE_MODEL")
    fingerprint, hashes = build_fingerprint(
        model,
        config,
        extra_identity={"judge_model": judge_model},
    )
    existing = find_by_fingerprint(load_registry(registry_path), fingerprint)
    resume_from_screen = can_resume_from_screen(existing, screen_only=screen_only, rerun=rerun)
    if existing and not rerun and not resume_from_screen:
        console.print("[yellow]ALREADY TESTED[/yellow] Same model + experiment fingerprint already exists.")
        print_entry(existing)
        return existing

    root = Path(str(config.get("qualification_root", "runs/qualifications")))
    default_run_dir = root / f"{model_slug(model)}__{fingerprint[:10]}"
    run_dir = Path(str(existing["run_dir"])) if resume_from_screen and existing else default_run_dir
    config_dir = run_dir / "configs"
    run_dir.mkdir(parents=True, exist_ok=True)

    if resume_from_screen and existing:
        screen_summary = dict(existing.get("screen") or {})
        console.rule("Resume qualification")
        console.print("[green]SCREEN REUSED[/green] Exact fingerprint already passed benchmark + judge.")
        console.print("Continuing directly at Stage 3; no benchmark or screen-judge calls will be repeated.")
    else:
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

    generated_source_manifest = retry_source_technical_failures(
        source_runner=source_runner,
        generation_config_path=Path(str(config["generation_config"])),
        source_manifest_path=source_manifest_path,
        model=model,
        config_dir=config_dir,
    )

    source_manifest = judge_phase(
        source_runner,
        Path(str(config["evaluation_config"])),
        source_manifest_path,
        force=rerun,
    )
    report_phase(source_runner, source_manifest_path, run_dir / "source")
    required_sources = int((config.get("full_gates") or {}).get("required_accepted_source_stories", 5))
    source_ok, accepted_count = source_gate(source_manifest, required_sources)
    retry_count = sum(int(entry.get("technical_retry_count") or 0) for entry in source_manifest.get("entries") or [])
    if not source_ok:
        entry = make_entry(
            model=model, fingerprint=fingerprint, hashes=hashes, judge_model=judge_model,
            run_dir=run_dir, status="rejected_source_gate", screen=screen_summary,
            dataset={"accepted_source_stories": accepted_count, "source_technical_retries": retry_count},
            reasons=["accepted_source_stories_below_requirement"],
        )
        upsert_entry(registry_path, entry)
        save_json(run_dir / "final_report.json", entry)
        print_entry(entry)
        return entry

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
                "source_technical_retries": retry_count,
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
            "source_technical_retries": retry_count,
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
