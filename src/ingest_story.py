from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

from src.curate_examples import (
    apply_manual_overrides,
    audit_examples,
    collect_examples,
    summarize as summarize_curation,
    validate_expected_shape,
    write_outputs as write_curation_outputs,
)
from src.extract_examples import run_extraction
from src.generate import validate_generation
from src.judge import judge_story
from src.prepare_training import prepare
from src.schemas import CostInfo, GenerationRecord, StorySpec, TokenUsage

console = Console()


class ExternalStory(BaseModel):
    id: str = Field(min_length=1)
    source_type: str = "generated_story"
    source_model: str | None = None
    language: str = "tr"
    title: str = Field(min_length=1)
    age_min: int = Field(default=6, ge=3, le=12)
    age_max: int = Field(default=8, ge=3, le=12)
    target_words: int = Field(default=2000, ge=300, le=5000)
    protagonist: str = Field(min_length=1)
    setting: str = Field(min_length=1)
    theme: str | list[str]
    premise: str = Field(min_length=1)
    constraints: list[str] = Field(default_factory=list)
    story: str = Field(min_length=1)
    suitability: dict[str, Any] = Field(default_factory=dict)
    training_eligible: bool | None = None
    metadata_confidence: dict[str, Any] = Field(default_factory=dict)
    extraction_notes: dict[str, Any] = Field(default_factory=dict)

    def normalized_theme(self) -> str:
        if isinstance(self.theme, str):
            value = self.theme.strip()
        else:
            value = ", ".join(item.strip() for item in self.theme if item.strip())
        if not value:
            raise RuntimeError("theme must contain at least one non-empty value")
        return value

    def to_story_spec(self) -> StorySpec:
        if self.age_max < self.age_min:
            raise RuntimeError("age_max must be greater than or equal to age_min")
        return StorySpec(
            title_hint=self.title.strip(),
            age_min=self.age_min,
            age_max=self.age_max,
            language=self.language.strip(),
            target_words=self.target_words,
            protagonist=self.protagonist.strip(),
            setting=self.setting.strip(),
            theme=self.normalized_theme(),
            premise=self.premise.strip(),
            constraints=[item.strip() for item in self.constraints if item.strip()],
        )


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} must contain one YAML object")
    return payload


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip())
    return normalized.strip("_.-") or "story"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_source_record(
    source: ExternalStory,
    *,
    source_path: Path,
    prompt_version: str,
    min_word_ratio: float,
    max_word_ratio: float,
) -> GenerationRecord:
    spec = source.to_story_spec()
    technical = validate_generation(
        story=source.story,
        spec=spec,
        finish_reason="stop",
        min_word_ratio=min_word_ratio,
        max_word_ratio=max_word_ratio,
    )
    return GenerationRecord(
        id=source.id,
        created_at=datetime.now(timezone.utc),
        teacher_model=source.source_model or "external/manual",
        provider="external",
        prompt_version=prompt_version,
        spec=spec,
        story=source.story.strip(),
        usage=TokenUsage(input_tokens=None, output_tokens=None, total_tokens=None),
        cost=CostInfo(usd=None, try_amount=None, usd_try_rate=None),
        technical_validation=technical,
        request={
            "source_type": source.source_type,
            "source_path": str(source_path),
            "declared_training_eligible": source.training_eligible,
            "declared_suitability": source.suitability,
        },
        response_meta={
            "source_model": source.source_model,
            "metadata_confidence": source.metadata_confidence,
            "extraction_notes": source.extraction_notes,
            "finish_reason": "stop",
        },
    )


def save_generation_record(path: Path, record: GenerationRecord) -> None:
    write_json(path, record.model_dump(mode="json"))


def make_source_manifest(
    record: GenerationRecord,
    source_path: Path,
    judgment_path: Path,
    judgment: Any,
) -> dict[str, Any]:
    return {
        "benchmark": "manual_ingest_source",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "entries": [
            {
                "model": record.teacher_model,
                "spec_path": str(source_path),
                "generation_status": "complete",
                "story_id": record.id,
                "story_path": str(source_path),
                "technical_pass": record.technical_validation.eligible_for_judge,
                "word_count": record.technical_validation.word_count,
                "finish_reason": record.technical_validation.finish_reason,
                "technical_reasons": record.technical_validation.reasons,
                "teacher_cost_usd": None,
                "judge_status": "complete",
                "judgment_path": str(judgment_path),
                "judge_accepted": judgment.decision.accepted,
                "judge_average": judgment.decision.average_score,
                "judge_minimum": judgment.decision.minimum_score,
                "judge_scores": judgment.result.scores,
                "critical_failures": judgment.result.critical_failures,
                "judge_cost_usd": judgment.cost.usd,
            }
        ],
    }


def print_result(report: dict[str, Any]) -> None:
    table = Table(title="External story ingest")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("story", str(report.get("story_id")))
    table.add_row("status", str(report.get("status")))
    table.add_row("words", str(report.get("word_count", "—")))
    table.add_row("technical", "PASS" if report.get("technical_pass") else "FAIL")
    judge = report.get("judge") or {}
    table.add_row("judge", "—" if judge.get("average") is None else f"{float(judge['average']):.2f}/5")
    dataset = report.get("dataset") or {}
    table.add_row("ready examples", str(dataset.get("ready", "—")))
    table.add_row("review", str(dataset.get("review", "—")))
    table.add_row("reject", str(dataset.get("reject", "—")))
    console.print(table)
    if report.get("reasons"):
        console.print("Reasons: " + ", ".join(str(item) for item in report["reasons"]))
    if report.get("train_jsonl"):
        console.print(f"Training JSONL: {report['train_jsonl']}")


def run_ingest(input_path: Path, config_path: Path, *, force: bool = False) -> dict[str, Any]:
    config = load_yaml(config_path)
    source_payload = load_yaml(input_path)
    source = ExternalStory.model_validate(source_payload)
    digest = file_sha256(input_path)
    run_root = Path(str(config.get("run_root", "runs/manual_ingest")))
    run_dir = run_root / f"{slug(source.id)}__{digest[:10]}"
    final_report_path = run_dir / "final_report.json"

    if final_report_path.exists() and not force:
        existing = json.loads(final_report_path.read_text(encoding="utf-8"))
        console.print("[yellow]ALREADY INGESTED[/yellow] Exact input file was processed before.")
        print_result(existing)
        return existing

    run_dir.mkdir(parents=True, exist_ok=True)
    write_yaml(run_dir / "input_snapshot.yaml", source_payload)

    gate = config.get("technical_gate") or {}
    record = build_source_record(
        source,
        source_path=input_path,
        prompt_version=str(config.get("source_prompt_version", "generated_story_source_v1")),
        min_word_ratio=float(gate.get("min_word_ratio", 0.80)),
        max_word_ratio=float(gate.get("max_word_ratio", 1.20)),
    )
    source_record_path = run_dir / "source" / f"{source.id}.json"
    save_generation_record(source_record_path, record)

    base_report: dict[str, Any] = {
        "story_id": source.id,
        "input_sha256": digest,
        "source_model": source.source_model,
        "declared_training_eligible": source.training_eligible,
        "declared_suitability": source.suitability,
        "word_count": record.technical_validation.word_count,
        "technical_pass": record.technical_validation.eligible_for_judge,
        "technical_reasons": record.technical_validation.reasons,
        "run_dir": str(run_dir),
    }

    console.rule("1/4 Schema + technical gate")
    if not record.technical_validation.eligible_for_judge:
        report = {
            **base_report,
            "status": "rejected_technical",
            "reasons": record.technical_validation.reasons,
            "judge": {},
            "dataset": {},
        }
        write_json(final_report_path, report)
        print_result(report)
        return report
    console.print(f"[green]PASS[/green] words={record.technical_validation.word_count}")

    console.rule("2/4 Independent judge")
    evaluation_config = load_yaml(Path(str(config.get("evaluation_config", "configs/evaluation.yaml"))))
    evaluation_config = dict(evaluation_config)
    judge_config = dict(evaluation_config.get("judge") or {})
    judge_config["output_dir"] = str(run_dir / "judge")
    evaluation_config["judge"] = judge_config
    evaluation_config_path = run_dir / "configs" / "evaluation.yaml"
    write_yaml(evaluation_config_path, evaluation_config)

    judgment_path, judgment = judge_story(source_record_path, evaluation_config_path)
    judge_summary = {
        "accepted": judgment.decision.accepted,
        "average": judgment.decision.average_score,
        "minimum": judgment.decision.minimum_score,
        "scores": judgment.result.scores,
        "critical_failures": judgment.result.critical_failures,
        "cost_usd": judgment.cost.usd,
        "input_tokens": judgment.usage.input_tokens,
        "output_tokens": judgment.usage.output_tokens,
        "total_tokens": judgment.usage.total_tokens,
    }
    require_accept = bool((config.get("judge_gate") or {}).get("require_accept", True))
    if require_accept and not judgment.decision.accepted:
        report = {
            **base_report,
            "status": "rejected_judge",
            "reasons": judgment.decision.reasons,
            "judge": judge_summary,
            "dataset": {},
        }
        write_json(final_report_path, report)
        print_result(report)
        return report
    console.print(f"[green]ACCEPTED[/green] average={judgment.decision.average_score:.2f}/5")

    source_manifest_path = run_dir / "source" / "manifest.json"
    write_json(
        source_manifest_path,
        make_source_manifest(record, source_record_path, judgment_path, judgment),
    )

    console.rule("3/4 Supervised extraction")
    extraction_config = load_yaml(Path(str(config.get("extraction_config", "configs/extraction.yaml"))))
    extraction_config = dict(extraction_config)
    extraction_config.update(
        {
            "source_manifest": str(source_manifest_path),
            "output_dir": str(run_dir / "extracted"),
            "run_dir": str(run_dir / "extraction"),
        }
    )
    extraction_config_path = run_dir / "configs" / "extraction.yaml"
    write_yaml(extraction_config_path, extraction_config)
    extraction_manifest = run_extraction(extraction_config_path, force=force)
    complete = [item for item in extraction_manifest.get("entries") or [] if item.get("status") == "complete"]
    extracted_count = sum(int(item.get("example_count", 0)) for item in complete)
    expected_examples = int(config.get("expected_examples", 11))
    if extracted_count != expected_examples:
        report = {
            **base_report,
            "status": "rejected_extraction",
            "reasons": [f"expected_examples:{expected_examples}!={extracted_count}"],
            "judge": judge_summary,
            "dataset": {"extracted": extracted_count},
        }
        write_json(final_report_path, report)
        print_result(report)
        return report

    console.rule("4/4 Curation + training JSONL")
    curation_config = load_yaml(Path(str(config.get("curation_config", "configs/curation.yaml"))))
    curation_config = dict(curation_config)
    curation_config.update(
        {
            "input_dir": str(run_dir / "extracted"),
            "output_dir": str(run_dir / "curated"),
            "report_dir": str(run_dir / "curation"),
            "expected_source_stories": 1,
            "expected_examples_per_story": expected_examples,
            "expected_total_examples": expected_examples,
        }
    )
    curation_config.pop("manual_overrides", None)
    curation_config_path = run_dir / "configs" / "curation.yaml"
    write_yaml(curation_config_path, curation_config)

    examples = collect_examples(run_dir / "extracted")
    audited = audit_examples(examples, curation_config)
    audited = apply_manual_overrides(audited, {}, curation_config)
    curation_summary = summarize_curation(audited)
    warnings = validate_expected_shape(curation_summary, curation_config)
    curation_summary["shape_warnings"] = warnings
    write_curation_outputs(audited, curation_summary, curation_config)

    ready = int(curation_summary.get("ready", 0))
    review = int(curation_summary.get("review", 0))
    reject = int(curation_summary.get("reject", 0))
    if ready != expected_examples or review or reject or warnings:
        report = {
            **base_report,
            "status": "needs_manual_review",
            "reasons": ["curation_gate_not_clean"],
            "judge": judge_summary,
            "dataset": {
                "extracted": extracted_count,
                "ready": ready,
                "review": review,
                "reject": reject,
                "shape_warnings": warnings,
            },
        }
        write_json(final_report_path, report)
        print_result(report)
        return report

    prepare_config = load_yaml(Path(str(config.get("prepare_training_config", "configs/prepare_training.yaml"))))
    prepare_config = dict(prepare_config)
    prepare_config.update(
        {
            "name": f"manual_ingest__{source.id}",
            "input_path": str(run_dir / "curated" / "milestone1_audit.json"),
            "output_path": str(run_dir / "dataset" / "train.jsonl"),
            "manifest_path": str(run_dir / "dataset" / "manifest.json"),
            "expected_examples": expected_examples,
        }
    )
    prepare_config_path = run_dir / "configs" / "prepare_training.yaml"
    write_yaml(prepare_config_path, prepare_config)
    dataset_manifest = prepare(prepare_config_path)

    report = {
        **base_report,
        "status": "training_ready",
        "reasons": [],
        "judge": judge_summary,
        "dataset": {
            "extracted": extracted_count,
            "ready": ready,
            "review": review,
            "reject": reject,
            "sha256": dataset_manifest.get("sha256"),
        },
        "train_jsonl": str(run_dir / "dataset" / "train.jsonl"),
        "dataset_manifest": str(run_dir / "dataset" / "manifest.json"),
    }
    write_json(final_report_path, report)
    print_result(report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate, judge, extract, curate, and prepare one external LUMI source story."
    )
    parser.add_argument("--input", required=True, help="YAML story generated by an external/manual source")
    parser.add_argument("--config", default="configs/manual_ingest.yaml")
    parser.add_argument("--force", action="store_true", help="Repeat an identical previously processed input")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    run_ingest(Path(args.input), Path(args.config), force=args.force)


if __name__ == "__main__":
    main()
