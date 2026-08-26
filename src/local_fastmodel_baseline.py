from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import torch
import yaml
from rich.console import Console
from rich.table import Table
from unsloth import FastModel

console = Console()

SYSTEM_PROMPT = (
    "Sen LUMI evreni için Türkçe çocuk hikâyeleri yazan bir yazarsın. "
    "Verilen yaş aralığına, karaktere, ortama, temaya, öncül ve kısıtlara sadık kal. "
    "Hikâyeyi tamamlanmış bir sonla bitir; yalnızca hikâye metnini yaz."
)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def build_user_prompt(spec: dict[str, Any]) -> str:
    constraints = spec.get("constraints") or []
    constraint_text = "\n".join(f"- {item}" for item in constraints)
    return (
        f"Başlık ipucu: {spec.get('title_hint', '')}\n"
        f"Yaş aralığı: {spec.get('age_min')}-{spec.get('age_max')}\n"
        f"Dil: {spec.get('language', 'tr')}\n"
        f"Hedef uzunluk: yaklaşık {spec.get('target_words', 2000)} kelime\n"
        f"Ana karakter: {spec.get('protagonist', '')}\n"
        f"Ortam: {spec.get('setting', '')}\n"
        f"Tema: {spec.get('theme', '')}\n"
        f"Öncül: {spec.get('premise', '')}\n"
        f"Kısıtlar:\n{constraint_text}\n\n"
        "Bu özelliklerin tamamını koruyan, yaşa uygun, akıcı ve yaratıcı bir hikâye yaz."
    )


def word_count(text: str) -> int:
    return len([part for part in text.split() if part.strip()])


def technical_result(words: int, target: int, min_ratio: float, max_ratio: float, hit_token_limit: bool) -> dict[str, Any]:
    minimum = int(target * min_ratio)
    maximum = int(target * max_ratio)
    length_pass = minimum <= words <= maximum
    return {
        "word_count": words,
        "target_words": target,
        "min_words": minimum,
        "max_words": maximum,
        "length_pass": length_pass,
        "hit_token_limit": hit_token_limit,
        "pass": length_pass and not hit_token_limit,
    }


def run(config_path: Path, limit: int | None = None) -> dict[str, Any]:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for local baseline generation.")

    config = load_yaml(config_path)
    benchmark = load_yaml(Path(str(config["benchmark_config"])))
    spec_paths = [Path(str(item)) for item in benchmark.get("specs") or []]
    if limit is not None:
        spec_paths = spec_paths[:limit]
    if not spec_paths:
        raise RuntimeError("No benchmark specs found.")

    model_name = str(config["model"])
    max_seq_length = int(config.get("max_seq_length", 4096))
    max_new_tokens = int(config.get("max_new_tokens", 3000))
    seed = int(config.get("seed", 42))
    output_dir = Path(str(config.get("output_dir", "runs/model_baseline/pre_finetune_fastmodel")))
    output_dir.mkdir(parents=True, exist_ok=True)

    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    token = os.getenv("HF_TOKEN") or None
    console.print(f"Loading clean starting checkpoint [bold]{model_name}[/bold]...")
    model, processor = FastModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        load_in_4bit=bool(config.get("load_in_4bit", True)),
        token=token,
    )
    tokenizer = processor.tokenizer if hasattr(processor, "tokenizer") else processor

    generation = config.get("generation") or {}
    gate = config.get("technical_gate") or {}
    min_ratio = float(gate.get("min_word_ratio", 0.8))
    max_ratio = float(gate.get("max_word_ratio", 1.2))

    results: list[dict[str, Any]] = []
    for index, spec_path in enumerate(spec_paths, start=1):
        spec = load_yaml(spec_path)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(spec)},
        ]
        chat_template_kwargs: dict[str, Any] = {}
        if "enable_thinking" in generation:
            chat_template_kwargs["enable_thinking"] = bool(generation["enable_thinking"])
        rendered = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            **chat_template_kwargs,
        )
        inputs = tokenizer(rendered, return_tensors="pt").to("cuda")
        input_tokens = int(inputs["input_ids"].shape[-1])

        console.print(f"[{index}/{len(spec_paths)}] Generating {spec_path.name} ...")
        generate_kwargs: dict[str, Any] = {
            "max_new_tokens": max_new_tokens,
            "do_sample": bool(generation.get("do_sample", False)),
            "use_cache": True,
        }
        if generate_kwargs["do_sample"]:
            generate_kwargs["temperature"] = float(generation.get("temperature", 1.0))
            generate_kwargs["top_p"] = float(generation.get("top_p", 1.0))
            if "top_k" in generation:
                generate_kwargs["top_k"] = int(generation["top_k"])
        if "repetition_penalty" in generation:
            generate_kwargs["repetition_penalty"] = float(generation["repetition_penalty"])

        started = time.perf_counter()
        with torch.inference_mode():
            generated = model.generate(**inputs, **generate_kwargs)
        elapsed = time.perf_counter() - started

        new_tokens = generated[0, input_tokens:]
        output_tokens = int(new_tokens.shape[-1])
        hit_token_limit = output_tokens >= max_new_tokens
        eos_token_id = tokenizer.eos_token_id
        ended_with_eos = bool(
            eos_token_id is not None and output_tokens > 0 and int(new_tokens[-1].item()) == int(eos_token_id)
        )
        text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        words = word_count(text)
        target = int(spec.get("target_words", 2000))
        technical = technical_result(words, target, min_ratio, max_ratio, hit_token_limit)

        item = {
            "benchmark_index": index,
            "spec_path": str(spec_path),
            "title_hint": spec.get("title_hint"),
            "prompt_version": config.get("prompt_version"),
            "generation_version": config.get("generation_version"),
            "model": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "max_new_tokens": max_new_tokens,
            "ended_with_eos": ended_with_eos,
            "runtime_seconds": round(elapsed, 3),
            "technical": technical,
            "story": text,
        }
        story_path = output_dir / f"story_{index:02d}.json"
        story_path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
        results.append(item)
        console.print(
            f"  words={words} tokens={output_tokens} runtime={elapsed:.1f}s "
            f"limit={'YES' if hit_token_limit else 'no'} eos={'yes' if ended_with_eos else 'no'} "
            f"technical={'PASS' if technical['pass'] else 'FAIL'}"
        )

    peak_gb = round(float(torch.cuda.max_memory_allocated()) / (1024 ** 3), 3)
    summary = {
        "name": config.get("name"),
        "status": "complete",
        "model": model_name,
        "prompt_version": config.get("prompt_version"),
        "generation_version": config.get("generation_version"),
        "benchmark_config": str(config["benchmark_config"]),
        "stories": len(results),
        "technical_passes": sum(1 for item in results if item["technical"]["pass"]),
        "token_limit_hits": sum(1 for item in results if item["technical"]["hit_token_limit"]),
        "average_words": round(sum(item["technical"]["word_count"] for item in results) / len(results), 1),
        "total_runtime_seconds": round(sum(item["runtime_seconds"] for item in results), 3),
        "peak_allocated_vram_gb": peak_gb,
        "results": [str(output_dir / f"story_{i:02d}.json") for i in range(1, len(results) + 1)],
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    table = Table(title="LUMI FastModel pre-finetune baseline")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("model", model_name)
    table.add_row("stories", str(summary["stories"]))
    table.add_row("technical passes", f"{summary['technical_passes']}/{summary['stories']}")
    table.add_row("token limit hits", str(summary["token_limit_hits"]))
    table.add_row("average words", str(summary["average_words"]))
    table.add_row("runtime", f"{summary['total_runtime_seconds']:.1f}s")
    table.add_row("peak VRAM", f"{peak_gb:.3f} GB")
    console.print(table)
    console.print(f"Summary: {summary_path}")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the frozen local pre-finetune story benchmark with Unsloth FastModel.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(Path(args.config), limit=args.limit)


if __name__ == "__main__":
    main()
