from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import time
from pathlib import Path
from typing import Any

import yaml


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


def canonical_sha256(path: Path) -> str:
    """Hash textual artifacts with canonical LF line endings for cross-platform reproducibility."""
    payload = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(payload).hexdigest()


def verify_dataset(dataset_path: Path, manifest_path: Path) -> str:
    manifest = load_json(manifest_path)
    expected = str(manifest.get("sha256") or "").strip()
    actual = canonical_sha256(dataset_path)
    if expected and actual != expected:
        raise RuntimeError(
            "Frozen training dataset SHA256 does not match its manifest even after LF normalization. "
            f"expected={expected} actual={actual}"
        )
    return actual


def training_fields(row: dict[str, Any]) -> tuple[str, str]:
    instruction = str(row.get("instruction") or "").strip()
    input_text = str(row.get("input") or "").strip()
    output = str(row.get("output") or "").strip()
    if not instruction or not input_text or not output:
        raise RuntimeError("Training row contains an empty instruction/input/output field.")
    user_text = f"{instruction}\n\nBağlam:\n{input_text}"
    return user_text, output


def _ids(value: Any) -> list[int]:
    if isinstance(value, dict):
        value = value.get("input_ids")
    if hasattr(value, "tolist"):
        value = value.tolist()
    if value and isinstance(value[0], list):
        value = value[0]
    return [int(item) for item in value]


def tokenize_row(row: dict[str, Any], tokenizer: Any, max_seq_length: int) -> dict[str, Any]:
    """Tokenize one chat row and mask every token except the assistant response."""
    user_text, output = training_fields(row)
    prompt_messages = [{"role": "user", "content": user_text}]
    full_messages = [
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": output},
    ]
    prompt_ids = _ids(
        tokenizer.apply_chat_template(
            prompt_messages,
            tokenize=True,
            add_generation_prompt=True,
        )
    )
    full_ids = _ids(
        tokenizer.apply_chat_template(
            full_messages,
            tokenize=True,
            add_generation_prompt=False,
        )
    )
    if full_ids[: len(prompt_ids)] != prompt_ids:
        raise RuntimeError("Chat template prompt is not a prefix of the full conversation; cannot mask safely.")
    if len(full_ids) > max_seq_length:
        raise RuntimeError(
            f"Training example exceeds max_seq_length without truncation: {len(full_ids)} > {max_seq_length}."
        )
    labels = [-100] * len(prompt_ids) + full_ids[len(prompt_ids) :]
    if not any(label != -100 for label in labels):
        raise RuntimeError("Assistant-only masking produced zero trainable tokens.")
    return {
        "input_ids": full_ids,
        "attention_mask": [1] * len(full_ids),
        "labels": labels,
        "token_count": len(full_ids),
        "assistant_token_count": len(full_ids) - len(prompt_ids),
    }


def row_label(row: dict[str, Any], index: int) -> str:
    metadata = row.get("metadata") or {}
    for key in ("example_id", "id", "source_example_id"):
        if row.get(key):
            return str(row[key])
        if metadata.get(key):
            return str(metadata[key])
    kind = str(metadata.get("example_type") or "unknown")
    source = str(metadata.get("source_story_id") or metadata.get("story_id") or "unknown")
    return f"row_{index + 1}:{source}:{kind}"


def token_audit(rows: list[dict[str, Any]], tokenizer: Any, max_seq_length: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tokenized: list[dict[str, Any]] = []
    lengths: list[int] = []
    labels: list[tuple[int, str]] = []
    for index, row in enumerate(rows):
        item = tokenize_row(row, tokenizer, max_seq_length)
        tokenized.append({key: value for key, value in item.items() if not key.endswith("token_count")})
        lengths.append(int(item["token_count"]))
        labels.append((int(item["token_count"]), row_label(row, index)))

    ordered = sorted(labels, reverse=True)
    sorted_lengths = sorted(lengths)
    p95_index = max(0, min(len(sorted_lengths) - 1, int(round(0.95 * (len(sorted_lengths) - 1)))))
    summary = {
        "examples": len(rows),
        "min_tokens": min(lengths),
        "median_tokens": int(statistics.median(lengths)),
        "p95_tokens": sorted_lengths[p95_index],
        "max_tokens": max(lengths),
        "over_2048": sum(1 for value in lengths if value > 2048),
        "over_4096": sum(1 for value in lengths if value > 4096),
        "over_max_seq_length": sum(1 for value in lengths if value > max_seq_length),
        "top5": [{"label": label, "tokens": count} for count, label in ordered[:5]],
    }
    return tokenized, summary


def print_audit(summary: dict[str, Any], max_seq_length: int) -> None:
    print("LUMI training token audit")
    print(f"examples            = {summary['examples']}")
    print(f"min_tokens          = {summary['min_tokens']}")
    print(f"median_tokens       = {summary['median_tokens']}")
    print(f"p95_tokens          = {summary['p95_tokens']}")
    print(f"max_tokens          = {summary['max_tokens']}")
    print(f"over_2048           = {summary['over_2048']}")
    print(f"over_4096           = {summary['over_4096']}")
    print(f"over_{max_seq_length}           = {summary['over_max_seq_length']}")
    print("top5:")
    for item in summary["top5"]:
        print(f"  {item['tokens']:5d}  {item['label']}")


def train(config_path: Path, *, audit_only: bool = False) -> dict[str, Any]:
    config = load_yaml(config_path)
    dataset_path = Path(str(config.get("dataset_path", "data/processed/milestone1_train.jsonl")))
    manifest_path = Path(str(config.get("dataset_manifest", "runs/training_dataset/manifest.json")))
    dataset_sha = verify_dataset(dataset_path, manifest_path)
    rows = load_jsonl(dataset_path)
    if not rows:
        raise RuntimeError("Training dataset is empty.")

    # Heavy imports are deliberately deferred so unit tests and data checks work in the lightweight venv.
    import torch
    from datasets import Dataset
    from transformers import DataCollatorForSeq2Seq, Trainer, TrainingArguments
    from unsloth import FastLanguageModel, is_bfloat16_supported

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for QLoRA training.")

    model_name = str(config.get("model") or config.get("base_model") or "Qwen/Qwen3.5-4B")
    max_seq_length = int(config.get("max_seq_length") or (config.get("training") or {}).get("max_seq_length", 6144))
    token = os.getenv("HF_TOKEN") or None

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    print(f"Loading {model_name} | 4-bit={bool(config.get('load_in_4bit', True))} | max_seq_length={max_seq_length}")
    model, processor = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        load_in_4bit=bool(config.get("load_in_4bit", True)),
        trust_remote_code=True,
        token=token,
    )
    tokenizer = processor.tokenizer if hasattr(processor, "tokenizer") else processor

    tokenized_rows, audit = token_audit(rows, tokenizer, max_seq_length)
    print_audit(audit, max_seq_length)
    if audit_only:
        return {"status": "audit_complete", "dataset_sha256": dataset_sha, "token_audit": audit}

    lora = config.get("lora") or {}
    targets = lora.get("target_modules") or [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ]
    if targets == "auto":
        targets = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    model = FastLanguageModel.get_peft_model(
        model,
        r=int(lora.get("r", 16)),
        target_modules=[str(item) for item in targets],
        lora_alpha=int(lora.get("alpha", 32)),
        lora_dropout=float(lora.get("dropout", 0.05)),
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=int(config.get("seed", 42)),
        use_rslora=False,
        loftq_config=None,
    )

    train_dataset = Dataset.from_list(tokenized_rows)
    collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
        padding=True,
        label_pad_token_id=-100,
        return_tensors="pt",
    )
    training = config.get("training") or {}
    output_dir = Path(str(config.get("output_dir", "adapters/qwen35_4b_m1")))
    trainer_output = Path(str(config.get("trainer_output_dir", str(output_dir) + "_trainer")))
    args = TrainingArguments(
        output_dir=str(trainer_output),
        num_train_epochs=float(training.get("epochs", 2)),
        learning_rate=float(training.get("learning_rate", 2e-4)),
        per_device_train_batch_size=int(training.get("per_device_train_batch_size", 1)),
        gradient_accumulation_steps=int(training.get("gradient_accumulation_steps", 8)),
        warmup_ratio=float(training.get("warmup_ratio", 0.03)),
        logging_steps=int(training.get("logging_steps", 1)),
        optim=str(training.get("optim", "adamw_8bit")),
        weight_decay=float(training.get("weight_decay", 0.01)),
        lr_scheduler_type=str(training.get("lr_scheduler_type", "linear")),
        report_to=str(training.get("report_to", "none")),
        save_strategy="no",
        fp16=not is_bfloat16_supported(),
        bf16=is_bfloat16_supported(),
        seed=int(config.get("seed", 42)),
        data_seed=int(config.get("seed", 42)),
        dataloader_num_workers=0,
        remove_unused_columns=False,
    )
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        data_collator=collator,
    )

    print("Starting full Milestone-1 assistant-only QLoRA training...")
    started = time.time()
    stats = trainer.train()
    wall_seconds = time.time() - started

    output_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    losses = [
        float(item["loss"])
        for item in trainer.state.log_history
        if isinstance(item, dict) and item.get("loss") is not None
    ]
    props = torch.cuda.get_device_properties(torch.cuda.current_device())
    peak_gb = round(float(torch.cuda.max_memory_allocated()) / (1024 ** 3), 3)
    training_metrics = dict(getattr(stats, "metrics", {}) or {})
    result = {
        "name": config.get("name", "qwen35_4b_4060_m1"),
        "status": "complete",
        "model": model_name,
        "method": "qlora",
        "assistant_only_loss": True,
        "dataset_path": str(dataset_path),
        "dataset_sha256": dataset_sha,
        "examples": len(rows),
        "max_seq_length": max_seq_length,
        "token_audit": audit,
        "epochs": float(training.get("epochs", 2)),
        "per_device_train_batch_size": int(training.get("per_device_train_batch_size", 1)),
        "gradient_accumulation_steps": int(training.get("gradient_accumulation_steps", 8)),
        "effective_batch_size": int(training.get("per_device_train_batch_size", 1))
        * int(training.get("gradient_accumulation_steps", 8)),
        "loss_history": losses,
        "initial_loss": losses[0] if losses else None,
        "final_loss": losses[-1] if losses else None,
        "train_runtime_seconds": float(training_metrics.get("train_runtime", wall_seconds)),
        "wall_runtime_seconds": wall_seconds,
        "peak_allocated_vram_gb": peak_gb,
        "gpu": str(props.name),
        "total_vram_gb": round(float(props.total_memory) / (1024 ** 3), 3),
        "adapter_dir": str(output_dir),
    }
    run_manifest = Path(str(config.get("run_manifest", "runs/training/qwen35_4b_4060_m1.json")))
    run_manifest.parent.mkdir(parents=True, exist_ok=True)
    run_manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")

    print("LUMI full QLoRA complete")
    print(f"examples   = {result['examples']}")
    print(f"epochs     = {result['epochs']}")
    print(f"initial    = {result['initial_loss']}")
    print(f"final      = {result['final_loss']}")
    print(f"runtime_s  = {result['train_runtime_seconds']:.1f}")
    print(f"peak_vram  = {result['peak_allocated_vram_gb']:.3f} GB")
    print(f"adapter    = {output_dir}")
    print(f"manifest   = {run_manifest}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run reproducible Milestone-1 QLoRA training with assistant-only loss.")
    parser.add_argument("--config", default="configs/training_4b_4060.yaml")
    parser.add_argument("--audit-only", action="store_true", help="Load the starting checkpoint and audit exact chat-template token lengths without training.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train(Path(args.config), audit_only=args.audit_only)


if __name__ == "__main__":
    main()
