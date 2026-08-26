from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import requests
import yaml
from rich.console import Console
from rich.table import Table

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


def technical_result(words: int, target: int, min_ratio: float, max_ratio: float) -> dict[str, Any]:
    minimum = int(target * min_ratio)
    maximum = int(target * max_ratio)
    length_pass = minimum <= words <= maximum
    return {
        "word_count": words,
        "target_words": target,
        "min_words": minimum,
        "max_words": maximum,
        "length_pass": length_pass,
        "pass": length_pass,
    }


def build_payload(config: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    generation = config.get("generation") or {}
    payload = {
        "model": str(config["model"]),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(spec)},
        ],
        "max_tokens": int(config.get("max_tokens", 4200)),
        "temperature": float(generation.get("temperature", 0.0)),
        "top_p": float(generation.get("top_p", 1.0)),
        "seed": int(config.get("seed", 42)),
        "stream": False,
    }
    if bool(config.get("disable_thinking", True)):
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    return payload


def build_headers(config: dict[str, Any]) -> dict[str, str]:
    api_key_env = config.get("api_key_env")
    if not api_key_env:
        return {}
    api_key = os.getenv(str(api_key_env))
    if not api_key:
        raise RuntimeError(f"Required API key environment variable is not set: {api_key_env}")
    return {"Authorization": f"Bearer {api_key}"}


def extract_story(response_json: dict[str, Any]) -> str:
    choices = response_json.get("choices") or []
    if not choices:
        raise RuntimeError("Local endpoint response did not contain choices.")
    message = choices[0].get("message") or {}

    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()

    reasoning_content = message.get("reasoning_content")
    if isinstance(reasoning_content, str) and reasoning_content.strip():
        return reasoning_content.strip()

    raise RuntimeError(
        "Local endpoint response did not contain story text in "
        "message.content or message.reasoning_content. "
        f"message_keys={sorted(message.keys())}"
    )


def run(config_path: Path, limit: int | None = None) -> dict[str, Any]:
    config = load_yaml(config_path)
    benchmark = load_yaml(Path(str(config["benchmark_config"])))
    spec_paths = [Path(str(item)) for item in benchmark.get("specs") or []]
    if limit is not None:
        spec_paths = spec_paths[:limit]
    if not spec_paths:
        raise RuntimeError("No benchmark specs found.")

    endpoint_url = str(config["endpoint_url"])
    timeout_seconds = int(config.get("timeout_seconds", 900))
    output_dir = Path(str(config.get("output_dir", "runs/model_baseline/pre_finetune_local_endpoint")))
    output_dir.mkdir(parents=True, exist_ok=True)
    headers = build_headers(config)

    gate = config.get("technical_gate") or {}
    min_ratio = float(gate.get("min_word_ratio", 0.8))
    max_ratio = float(gate.get("max_word_ratio", 1.2))

    results: list[dict[str, Any]] = []
    for index, spec_path in enumerate(spec_paths, start=1):
        spec = load_yaml(spec_path)
        payload = build_payload(config, spec)
        console.print(f"[{index}/{len(spec_paths)}] Generating {spec_path.name} via local endpoint ...")
        started = time.perf_counter()
        response = requests.post(endpoint_url, json=payload, headers=headers, timeout=timeout_seconds)
        response.raise_for_status()
        response_json = response.json()
        elapsed = time.perf_counter() - started
        text = extract_story(response_json)
        words = word_count(text)
        target = int(spec.get("target_words", 2000))
        technical = technical_result(words, target, min_ratio, max_ratio)
        usage = response_json.get("usage") or {}

        item = {
            "benchmark_index": index,
            "spec_path": str(spec_path),
            "title_hint": spec.get("title_hint"),
            "prompt_version": config.get("prompt_version"),
            "generation_version": config.get("generation_version"),
            "model": config.get("model"),
            "endpoint_url": endpoint_url,
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
            "runtime_seconds": round(elapsed, 3),
            "technical": technical,
            "story": text,
        }
        story_path = output_dir / f"story_{index:02d}.json"
        story_path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
        results.append(item)
        console.print(
            f"  words={words} runtime={elapsed:.1f}s "
            f"technical={'PASS' if technical['pass'] else 'FAIL'}"
        )

    summary = {
        "name": config.get("name"),
        "status": "complete",
        "model": config.get("model"),
        "endpoint_url": endpoint_url,
        "prompt_version": config.get("prompt_version"),
        "generation_version": config.get("generation_version"),
        "benchmark_config": str(config["benchmark_config"]),
        "stories": len(results),
        "technical_passes": sum(1 for item in results if item["technical"]["pass"]),
        "average_words": round(sum(item["technical"]["word_count"] for item in results) / len(results), 1),
        "total_runtime_seconds": round(sum(item["runtime_seconds"] for item in results), 3),
        "results": [str(output_dir / f"story_{i:02d}.json") for i in range(1, len(results) + 1)],
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    table = Table(title="LUMI local endpoint pre-finetune baseline")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("model", str(summary["model"]))
    table.add_row("stories", str(summary["stories"]))
    table.add_row("technical passes", f"{summary['technical_passes']}/{summary['stories']}")
    table.add_row("average words", str(summary["average_words"]))
    table.add_row("runtime", f"{summary['total_runtime_seconds']:.1f}s")
    console.print(table)
    console.print(f"Summary: {summary_path}")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a frozen story benchmark through a local OpenAI-compatible endpoint.")
    parser.add_argument("--config", default="configs/local_baseline_ornith15_9b.yaml")
    parser.add_argument("--limit", type=int, default=None, help="Generate only the first N benchmark stories.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(Path(args.config), limit=args.limit)


if __name__ == "__main__":
    main()
