from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
from pathlib import Path
from typing import Any

import torch
import yaml
from datasets import Dataset
from rich.console import Console
from rich.table import Table
from unsloth import FastLanguageModel, is_bfloat16_supported
from trl import SFTConfig, SFTTrainer

console = Console()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
    return rows


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def select_smoke_rows(rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    excluded = {str(item) for item in (config.get("exclude_example_types") or [])}
    max_examples = int(config.get("max_examples", 12))
    seed = int(config.get("seed", 42))

    candidates = [
        row
        for row in rows
        if str((row.get("metadata") or {}).get("example_type", "")) not in excluded
    ]
    if not candidates:
        raise RuntimeError("No training examples remain after smoke filters.")

    rng = random.Random(seed)
    rng.shuffle(candidates)
    return candidates[:max_examples]


def format_row(row: dict[str, Any], tokenizer: Any) -> dict[str, str]:
    instruction = str(row.get("instruction") or "").strip()
    input_text = str(row.get("input") or "").strip()
    output = str(row.get("output") or "").strip()
    if not instruction or not input_text or not output:
        raise RuntimeError("Smoke training row contains an empty instruction/input/output field.")

    user_text = f"{instruction}\n\nBağlam:\n{input_text}"
    messages = [
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": output},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    return {"text": text}


def build_sft_config(config: dict[str, Any]) -> SFTConfig:
    training = config.get("training") or {}
    kwargs: dict[str, Any] = {
        "output_dir": str(config.get("output_dir", "adapters/qwen35_08b_smoke")) + "_trainer",
        "max_steps": int(training.get("max_steps", 3)),
        "learning_rate": float(training.get("learning_rate", 2e-4)),
        "per_device_train_batch_size": int(training.get("per_device_train_batch_size", 1)),
        "gradient_accumulation_steps": int(training.get("gradient_accumulation_steps", 2)),
        "warmup_steps": int(training.get("warmup_steps", 0)),
        "logging_steps": int(training.get("logging_steps", 1)),
        "optim": str(training.get("optim", "adamw_8bit")),
        "weight_decay": float(training.get("weight_decay", 0.01)),
        "lr_scheduler_type": str(training.get("lr_scheduler_type", "linear")),
        "seed": int(config.get("seed", 42)),
        "report_to": str(training.get("report_to", "none")),
        "fp16": not is_bfloat16_supported(),
        "bf16": is_bfloat16_supported(),
        "dataset_text_field": "text",
        "packing": False,
    }
    fields = getattr(SFTConfig, "__dataclass_fields__", {})
    max_seq_length = int(config.get("max_seq_length", 512))
    if "max_length" in fields:
        kwargs["max_length"] = max_seq_length
    elif "max_seq_length" in fields:
        kwargs["max_seq_length"] = max_seq_length
    return SFTConfig(**kwargs)


def train(config_path: Path) -> dict[str, Any]:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for smoke training.")

    config = load_yaml(config_path)
    dataset_path = Path(str(config.get("dataset_path", "data/processed/milestone1_train.jsonl")))
    dataset_manifest_path = Path(str(config.get("dataset_manifest", "runs/training_dataset/manifest.json")))
    dataset_manifest = load_json(dataset_manifest_path)
    actual_sha = sha256(dataset_path)
    expected_sha = str(dataset_manifest.get("sha256") or "")
    if expected_sha and actual_sha != expected_sha:
        raise RuntimeError("Frozen training dataset SHA256 does not match its manifest.")

    selected = select_smoke_rows(load_jsonl(dataset_path), config)
    model_name = str(config.get("model") or "unsloth/Qwen3.5-0.8B")
    max_seq_length = int(config.get("max_seq_length", 512))
    token = os.getenv("HF_TOKEN") or None

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    console.print(f"Loading [bold]{model_name}[/bold] for smoke QLoRA...")
    model, processor = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        load_in_4bit=bool(config.get("load_in_4bit", True)),
        token=token,
        trust_remote_code=True,
    )
    tokenizer = processor.tokenizer if hasattr(processor, "tokenizer") else processor

    lora = config.get("lora") or {}
    model = FastLanguageModel.get_peft_model(
        model,
        r=int(lora.get("r", 8)),
        target_modules=[str(item) for item in (lora.get("target_modules") or [])],
        lora_alpha=int(lora.get("alpha", 8)),
        lora_dropout=float(lora.get("dropout", 0.0)),
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=int(config.get("seed", 42)),
        use_rslora=False,
        loftq_config=None,
    )

    formatted = [format_row(row, tokenizer) for row in selected]
    dataset = Dataset.from_list(formatted)
    args = build_sft_config(config)

    trainer_kwargs: dict[str, Any] = {
        "model": model,
        "train_dataset": dataset,
        "args": args,
    }
    import inspect

    params = inspect.signature(SFTTrainer.__init__).parameters
    if "processing_class" in params:
        trainer_kwargs["processing_class"] = tokenizer
    else:
        trainer_kwargs["tokenizer"] = tokenizer

    trainer = SFTTrainer(**trainer_kwargs)
    console.rule("Smoke QLoRA training")
    stats = trainer.train()

    output_dir = Path(str(config.get("output_dir", "adapters/qwen35_08b_smoke")))
    output_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    losses = [
        float(item["loss"])
        for item in trainer.state.log_history
        if isinstance(item, dict) and item.get("loss") is not None
    ]
    peak_gb = round(float(torch.cuda.max_memory_allocated()) / (1024 ** 3), 3)
    result = {
        "name": config.get("name", "smoke_training"),
        "status": "complete",
        "model": model_name,
        "dataset_sha256": actual_sha,
        "selected_examples": len(selected),
        "max_seq_length": max_seq_length,
        "max_steps": int((config.get("training") or {}).get("max_steps", 3)),
        "loss_history": losses,
        "initial_loss": losses[0] if losses else None,
        "final_loss": losses[-1] if losses else None,
        "train_runtime_seconds": float(getattr(stats, "metrics", {}).get("train_runtime", 0.0)),
        "peak_allocated_vram_gb": peak_gb,
        "adapter_dir": str(output_dir),
    }

    manifest_path = Path(str(config.get("run_manifest", "runs/smoke_training/qwen35_08b.json")))
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    table = Table(title="LUMI smoke QLoRA result")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("model", model_name)
    table.add_row("examples", str(result["selected_examples"]))
    table.add_row("steps", str(result["max_steps"]))
    table.add_row("initial loss", str(result["initial_loss"] or "—"))
    table.add_row("final loss", str(result["final_loss"] or "—"))
    table.add_row("runtime", f"{result['train_runtime_seconds']:.1f}s")
    table.add_row("peak VRAM", f"{peak_gb:.3f} GB")
    table.add_row("adapter", str(output_dir))
    console.print(table)
    console.print(f"Status: [green]{result['status']}[/green]")
    console.print(f"JSON: {manifest_path}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a conservative Qwen3.5-0.8B QLoRA smoke training pass.")
    parser.add_argument("--config", default="configs/smoke_training.yaml")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train(Path(args.config))


if __name__ == "__main__":
    main()
