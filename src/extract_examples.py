from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from rich.console import Console

from src.generate import OPENROUTER_URL, build_model_options, parse_cost, parse_usage
from src.judge import extract_json_object
from src.schemas import GenerationRecord

console = Console()


def load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def accepted_source_entries(source_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        entry
        for entry in source_manifest.get("entries", [])
        if entry.get("generation_status") == "complete"
        and entry.get("technical_pass")
        and entry.get("judge_status") == "complete"
        and entry.get("judge_accepted")
    ]


def build_full_story_example(record: GenerationRecord) -> dict[str, Any]:
    spec = record.spec
    constraints = "\n".join(f"- {item}" for item in spec.constraints) or "- None"
    instruction = (
        f"{spec.age_min}-{spec.age_max} yaş için, verilen özetten hareketle yaklaşık "
        f"{spec.target_words} kelimelik tamamlanmış bir Türkçe çocuk hikâyesi yaz."
    )
    input_text = f"""Başlık ipucu: {spec.title_hint or 'Uygun bir başlık seç'}
Ana karakter: {spec.protagonist}
Mekân: {spec.setting}
Tema: {spec.theme}
Öncül: {spec.premise}
Kısıtlar:
{constraints}"""
    return {
        "example_type": "full_story_from_brief",
        "instruction": instruction,
        "input": input_text,
        "output": record.story,
        "source_excerpt": "approved full source story",
    }


def build_extraction_input(record: GenerationRecord, derived_counts: dict[str, int]) -> str:
    counts = "\n".join(f"- {name}: {count}" for name, count in derived_counts.items())
    return f"""Create derivative supervised examples from this approved source story.

REQUESTED COUNTS
{counts}

SOURCE METADATA
Story id: {record.id}
Language: {record.spec.language}
Age range: {record.spec.age_min}-{record.spec.age_max}
Protagonist: {record.spec.protagonist}
Setting: {record.spec.setting}
Theme: {record.spec.theme}
Premise: {record.spec.premise}

APPROVED SOURCE STORY
{record.story}
"""


def plan_extraction_chunks(derived_counts: dict[str, int], max_examples_per_call: int) -> list[dict[str, int]]:
    if max_examples_per_call < 1:
        raise RuntimeError("max_examples_per_call must be at least 1.")

    chunks: list[dict[str, int]] = []
    current: dict[str, int] = {}
    current_total = 0

    for example_type, requested in derived_counts.items():
        remaining = requested
        while remaining > 0:
            capacity = max_examples_per_call - current_total
            if capacity == 0:
                chunks.append(current)
                current = {}
                current_total = 0
                capacity = max_examples_per_call

            take = min(remaining, capacity)
            current[example_type] = current.get(example_type, 0) + take
            current_total += take
            remaining -= take

            if current_total == max_examples_per_call:
                chunks.append(current)
                current = {}
                current_total = 0

    if current:
        chunks.append(current)
    return chunks


def validate_derived_examples(payload: dict[str, Any], derived_counts: dict[str, int]) -> list[dict[str, str]]:
    examples = payload.get("examples")
    if not isinstance(examples, list):
        raise RuntimeError("Extractor response must contain an examples array.")

    required_fields = ("example_type", "instruction", "input", "output", "source_excerpt")
    normalized: list[dict[str, str]] = []
    counts = {key: 0 for key in derived_counts}

    for index, item in enumerate(examples, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"Example {index} must be an object.")
        row: dict[str, str] = {}
        for field in required_fields:
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(f"Example {index} has empty or invalid {field}.")
            row[field] = value.strip()
        kind = row["example_type"]
        if kind not in derived_counts:
            raise RuntimeError(f"Example {index} has unexpected type {kind!r}.")
        counts[kind] += 1
        normalized.append(row)

    if counts != derived_counts:
        raise RuntimeError(f"Extractor type counts do not match request. expected={derived_counts}, got={counts}")
    return normalized


def call_extractor(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    payload.update(build_model_options(model, None))

    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/necdetoskay/lumi-model-lab",
            "X-Title": "LUMI Model Lab",
        },
        json=payload,
        timeout=240,
    )
    if not response.ok:
        try:
            detail: Any = response.json()
        except ValueError:
            detail = response.text[:2000]
        raise RuntimeError(f"OpenRouter extractor HTTP {response.status_code}: {detail}")

    body = response.json()
    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError(f"OpenRouter extractor response contains no choices: {body}")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        usage = body.get("usage") or {}
        raise RuntimeError(
            "OpenRouter extractor response did not contain text content. "
            f"finish_reason={choices[0].get('finish_reason')!r}, "
            f"completion_tokens={usage.get('completion_tokens')!r}."
        )
    return content, body, payload


def extract_derived_in_chunks(
    *,
    record: GenerationRecord,
    derived_counts: dict[str, int],
    max_examples_per_call: int,
    api_key: str,
    model: str,
    system_prompt: str,
    temperature: float,
    max_tokens: int,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    chunks = plan_extraction_chunks(derived_counts, max_examples_per_call)
    all_examples: list[dict[str, str]] = []
    calls: list[dict[str, Any]] = []

    for index, chunk_counts in enumerate(chunks, start=1):
        console.print(f"  chunk {index}/{len(chunks)}: {chunk_counts}")
        content, body, request_payload = call_extractor(
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            user_prompt=build_extraction_input(record, chunk_counts),
            temperature=temperature,
            max_tokens=max_tokens,
        )
        parsed = extract_json_object(content)
        rows = validate_derived_examples(parsed, chunk_counts)
        all_examples.extend(rows)

        usage = parse_usage(body)
        cost = parse_cost(body)
        choice = (body.get("choices") or [{}])[0]
        calls.append(
            {
                "chunk": index,
                "requested_counts": chunk_counts,
                "example_count": len(rows),
                "cost_usd": cost.usd,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "provider": body.get("provider"),
                "finish_reason": choice.get("finish_reason"),
                "reasoning": request_payload.get("reasoning"),
            }
        )

    combined_counts = {key: 0 for key in derived_counts}
    for row in all_examples:
        combined_counts[row["example_type"]] += 1
    if combined_counts != derived_counts:
        raise RuntimeError(
            f"Combined extractor counts do not match request. expected={derived_counts}, got={combined_counts}"
        )
    return all_examples, calls


def run_extraction(config_path: Path, *, force: bool = False) -> dict[str, Any]:
    config = load_yaml(config_path)
    source_manifest_path = Path(str(config.get("source_manifest", "runs/source_dataset/manifest.json")))
    source_manifest = load_json(source_manifest_path)
    accepted = accepted_source_entries(source_manifest)
    if not accepted:
        raise RuntimeError("No accepted source stories found. Complete source generation and judging first.")

    model = str(config.get("model") or "").strip()
    if not model:
        raise RuntimeError("Extraction config requires model.")
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    derived_counts = {str(k): int(v) for k, v in (config.get("derived_counts") or {}).items()}
    if not derived_counts or any(value < 1 for value in derived_counts.values()):
        raise RuntimeError("Extraction config requires positive derived_counts.")
    target_per_story = 1 + sum(derived_counts.values())
    configured_target = int(config.get("examples_per_story", target_per_story))
    if configured_target != target_per_story:
        raise RuntimeError(
            f"examples_per_story must equal 1 + derived_counts total ({target_per_story}); got {configured_target}."
        )

    max_examples_per_call = int(config.get("max_derived_examples_per_call", 4))
    chunks = plan_extraction_chunks(derived_counts, max_examples_per_call)

    output_dir = Path(str(config.get("output_dir", "data/raw/extracted")))
    run_dir = Path(str(config.get("run_dir", "runs/example_extraction")))
    manifest_path = run_dir / "manifest.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else {
        "name": config.get("name", "example_extraction"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "entries": [],
    }
    entries_by_story = {str(entry.get("source_story_id")): entry for entry in manifest.get("entries", [])}
    system_prompt = Path("prompts/example_extractor.md").read_text(encoding="utf-8").strip()

    for source_entry in accepted:
        story_id = str(source_entry["story_id"])
        existing = entries_by_story.get(story_id)
        if existing and existing.get("status") == "complete" and not force:
            console.print(f"[dim]Skip extracted[/dim] {story_id}")
            continue

        story_path = Path(str(source_entry["story_path"]))
        record = GenerationRecord.model_validate(load_json(story_path))
        entry = existing or {"source_story_id": story_id, "source_story_path": str(story_path)}
        if not existing:
            manifest["entries"].append(entry)
            entries_by_story[story_id] = entry

        console.rule(f"Extract | {model} | {story_id}")
        try:
            derived, call_records = extract_derived_in_chunks(
                record=record,
                derived_counts=derived_counts,
                max_examples_per_call=max_examples_per_call,
                api_key=api_key,
                model=model,
                system_prompt=system_prompt,
                temperature=float(config.get("temperature", 0.2)),
                max_tokens=int(config.get("max_tokens", 9000)),
            )
            examples = [build_full_story_example(record), *derived]
            for index, example in enumerate(examples, start=1):
                example["id"] = f"{story_id}_ex_{index:02d}"
                example["source_story_id"] = story_id
                example["teacher_model"] = record.teacher_model
                example["source_judge_average"] = source_entry.get("judge_average")

            output_path = output_dir / f"{story_id}.examples.json"
            output_payload = {
                "source_story_id": story_id,
                "source_story_path": str(story_path),
                "prompt_version": config.get("prompt_version", "example_extractor_v0.1"),
                "extraction_model": model,
                "extraction_mode": "chunked",
                "max_derived_examples_per_call": max_examples_per_call,
                "examples": examples,
            }
            save_json(output_path, output_payload)

            total_cost = sum(float(call["cost_usd"]) for call in call_records if call.get("cost_usd") is not None)
            total_input = sum(int(call["input_tokens"]) for call in call_records if call.get("input_tokens") is not None)
            total_output = sum(int(call["output_tokens"]) for call in call_records if call.get("output_tokens") is not None)
            entry.update(
                {
                    "status": "complete",
                    "output_path": str(output_path),
                    "example_count": len(examples),
                    "derived_count": len(derived),
                    "extraction_mode": "chunked",
                    "chunk_count": len(chunks),
                    "calls": call_records,
                    "cost_usd": round(total_cost, 8),
                    "input_tokens": total_input,
                    "output_tokens": total_output,
                    "error": None,
                }
            )
            console.print(f"[green]{story_id}[/green] examples={len(examples)} chunks={len(chunks)}")
        except Exception as exc:
            entry.update({"status": "error", "error": str(exc)})
            console.print(f"[red]Extraction error[/red] {story_id}: {exc}")
        finally:
            save_json(manifest_path, manifest)

    complete = [entry for entry in manifest.get("entries", []) if entry.get("status") == "complete"]
    total_examples = sum(int(entry.get("example_count", 0)) for entry in complete)
    console.rule("Extraction status")
    console.print(f"Accepted source stories: {len(accepted)}")
    console.print(f"Extracted stories:       {len(complete)}/{len(accepted)}")
    console.print(f"Raw supervised examples: {total_examples}")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract Milestone-1 supervised examples from accepted source stories.")
    parser.add_argument("--config", default="configs/extraction.yaml")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    run_extraction(Path(args.config), force=args.force)


if __name__ == "__main__":
    main()
