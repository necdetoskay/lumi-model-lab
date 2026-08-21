from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml
from dotenv import load_dotenv
from rich.console import Console

from src.schemas import CostInfo, GenerationRecord, StorySpec, TokenUsage


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
PROMPT_VERSION = "story_teacher_v0.1"
DRY_RUN_MODEL_PLACEHOLDER = "<TEACHER_MODEL not set; dry-run only>"
console = Console()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_teacher_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def build_user_prompt(spec: StorySpec) -> str:
    constraints = "\n".join(f"- {item}" for item in spec.constraints) or "- None"
    return f"""Create one finished story using this brief.

Language: {spec.language}
Age range: {spec.age_min}-{spec.age_max}
Target length: approximately {spec.target_words} words
Title hint: {spec.title_hint or 'Choose an appropriate title'}
Protagonist: {spec.protagonist}
Setting: {spec.setting}
Theme: {spec.theme}
Premise: {spec.premise}
Additional constraints:
{constraints}

Return only the story text.
"""


def extract_text_content(content: Any) -> str | None:
    """Normalize text from OpenAI-compatible string or content-part responses."""
    if isinstance(content, str):
        text = content.strip()
        return text or None

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
        combined = "\n".join(parts).strip()
        return combined or None

    return None


def call_openrouter(*, api_key: str, model: str, system_prompt: str, user_prompt: str,
                    temperature: float, max_tokens: int, seed: int | None) -> tuple[str, dict[str, Any], dict[str, Any]]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        # Story generation benefits from spending the output budget on the final
        # prose rather than hidden/visible reasoning tokens. OpenRouter normalizes
        # `effort: none` for models that support disabling reasoning.
        "reasoning": {"effort": "none", "exclude": True},
    }
    if seed is not None:
        payload["seed"] = seed

    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/necdetoskay/lumi-model-lab",
            "X-Title": "LUMI Model Lab",
        },
        json=payload,
        timeout=180,
    )
    response.raise_for_status()
    body = response.json()

    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError(f"OpenRouter response contains no choices: {body}")

    choice = choices[0] or {}
    message = choice.get("message") or {}
    content = extract_text_content(message.get("content"))
    if not content:
        usage = body.get("usage") or {}
        completion_details = usage.get("completion_tokens_details") or {}
        diagnostic = {
            "model": body.get("model") or model,
            "finish_reason": choice.get("finish_reason"),
            "completion_tokens": usage.get("completion_tokens"),
            "reasoning_tokens": completion_details.get("reasoning_tokens"),
            "has_reasoning": bool(message.get("reasoning") or message.get("reasoning_details")),
            "content_type": type(message.get("content")).__name__,
        }
        raise RuntimeError(
            "OpenRouter returned no final story text. Diagnostic: "
            + json.dumps(diagnostic, ensure_ascii=False)
        )

    return content, body, payload


def parse_usage(body: dict[str, Any]) -> TokenUsage:
    usage = body.get("usage") or {}
    return TokenUsage(
        input_tokens=usage.get("prompt_tokens"),
        output_tokens=usage.get("completion_tokens"),
        total_tokens=usage.get("total_tokens"),
    )


def parse_cost(body: dict[str, Any]) -> CostInfo:
    usage = body.get("usage") or {}
    raw_cost = usage.get("cost")
    usd_cost = float(raw_cost) if raw_cost is not None else None

    rate_raw = os.getenv("USD_TRY_RATE")
    rate = float(rate_raw) if rate_raw else None
    try_amount = usd_cost * rate if usd_cost is not None and rate is not None else None
    return CostInfo(usd=usd_cost, try_amount=try_amount, usd_try_rate=rate)


def next_story_id(raw_dir: Path) -> str:
    indexes: list[int] = []
    for path in raw_dir.glob("story_*.json"):
        try:
            indexes.append(int(path.stem.split("_")[-1]))
        except ValueError:
            continue
    return f"story_{(max(indexes, default=0) + 1):04d}"


def save_record(record: GenerationRecord, raw_dir: Path) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_path = raw_dir / f"{record.id}.json"
    output_path.write_text(
        json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def generate_one(config: dict[str, Any], spec: StorySpec, dry_run: bool = False) -> Path | None:
    teacher = config["teacher"]
    output = config["output"]
    model_env = teacher.get("model_env", "TEACHER_MODEL")
    configured_model = os.getenv(model_env)
    api_key = os.getenv("OPENROUTER_API_KEY")

    if dry_run:
        model = configured_model or DRY_RUN_MODEL_PLACEHOLDER
    else:
        if not configured_model:
            raise RuntimeError(f"Missing model name in environment variable {model_env}.")
        if not api_key:
            raise RuntimeError("Missing OPENROUTER_API_KEY.")
        model = configured_model

    system_prompt = load_teacher_prompt(Path("prompts/story_teacher.md"))
    user_prompt = build_user_prompt(spec)

    if dry_run:
        console.rule("Dry run")
        console.print(f"Model: {model}")
        console.print(f"Prompt version: {PROMPT_VERSION}")
        console.print(user_prompt)
        return None

    story, body, request_payload = call_openrouter(
        api_key=api_key,
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=float(teacher.get("temperature", 0.8)),
        max_tokens=int(teacher.get("max_tokens", 3500)),
        seed=config.get("seed"),
    )

    raw_dir = Path(output.get("raw_dir", "data/raw"))
    story_id = next_story_id(raw_dir)
    record = GenerationRecord(
        id=story_id,
        created_at=datetime.now(timezone.utc),
        teacher_model=model,
        prompt_version=PROMPT_VERSION,
        spec=spec,
        story=story,
        usage=parse_usage(body),
        cost=parse_cost(body),
        request={
            "temperature": request_payload.get("temperature"),
            "max_tokens": request_payload.get("max_tokens"),
            "seed": request_payload.get("seed"),
            "reasoning": request_payload.get("reasoning"),
        },
        response_meta={
            "openrouter_id": body.get("id"),
            "model": body.get("model"),
            "provider": body.get("provider"),
            "finish_reason": (body.get("choices") or [{}])[0].get("finish_reason"),
        },
    )
    return save_record(record, raw_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic LUMI teacher stories via OpenRouter.")
    parser.add_argument("--spec", default="data/specifications/example_story.yaml")
    parser.add_argument("--config", default="configs/generation.yaml")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    if args.count < 1:
        raise SystemExit("--count must be at least 1")

    config = load_yaml(Path(args.config))
    spec = StorySpec.model_validate(load_yaml(Path(args.spec)))

    for index in range(args.count):
        output_path = generate_one(config, spec, dry_run=args.dry_run)
        if output_path:
            console.print(f"[green]Generated[/green] {output_path}")
        elif args.dry_run:
            break
        if index + 1 < args.count:
            console.print(f"Completed {index + 1}/{args.count}")


if __name__ == "__main__":
    main()
