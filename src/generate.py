from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml
from dotenv import load_dotenv
from rich.console import Console

from src.model_registry import normalize_openrouter_request
from src.schemas import (
    CostInfo,
    GenerationRecord,
    StorySpec,
    TechnicalValidation,
    TokenUsage,
)


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504, 520, 522, 524, 529}
OPENROUTER_RETRY_DELAYS_SECONDS = (2.0, 5.0, 10.0)
OPENROUTER_SHARED_POOL_429_RETRY_DELAYS_SECONDS = (5.0, 10.0, 20.0, 30.0, 45.0)
PROMPT_VERSION = "story_teacher_v0.2"
DRY_RUN_MODEL_PLACEHOLDER = "<TEACHER_MODEL not set; dry-run only>"
console = Console()


class OpenRouterCallError(RuntimeError):
    """Provider/runtime failure with sanitized request/response evidence attached."""

    def __init__(self, message: str, trace: dict[str, Any]):
        super().__init__(message)
        self.trace = trace


def _is_shared_pool_rate_limit(status_code: int, error_body: Any) -> bool:
    if status_code != 429 or not isinstance(error_body, dict):
        return False
    error = error_body.get("error")
    if not isinstance(error, dict):
        return False
    metadata = error.get("metadata")
    if isinstance(metadata, dict):
        if metadata.get("limit_source") == "upstream_provider_shared_pool":
            return True
        raw = str(metadata.get("raw") or "").lower()
        if "temporarily rate-limited upstream" in raw:
            return True
    message = str(error.get("message") or "").lower()
    return "temporarily rate-limited upstream" in message


def _retry_delays_for_response(status_code: int, error_body: Any) -> tuple[float, ...] | None:
    if _is_shared_pool_rate_limit(status_code, error_body):
        return OPENROUTER_SHARED_POOL_429_RETRY_DELAYS_SECONDS
    if status_code in OPENROUTER_TRANSIENT_STATUS_CODES:
        return OPENROUTER_RETRY_DELAYS_SECONDS
    return None


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_teacher_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def build_user_prompt(spec: StorySpec) -> str:
    constraints = "\n".join(f"- {item}" for item in spec.constraints) or "- None"
    min_words = round(spec.target_words * 0.90)
    max_words = round(spec.target_words * 1.10)
    return f"""Create one finished story using this brief.

Language: {spec.language}
Age range: {spec.age_min}-{spec.age_max}
Target length: {spec.target_words} words
Required length range: {min_words}-{max_words} words
Title hint: {spec.title_hint or 'Choose an appropriate title'}
Protagonist: {spec.protagonist}
Setting: {spec.setting}
Theme: {spec.theme}
Premise: {spec.premise}
Additional constraints:
{constraints}

Length is part of the task: do not finish substantially before {min_words} words. Reach the target naturally with meaningful events, observations, decisions, and consequences rather than repetition. Complete the ending before the output limit.

Return only the story text.
"""


def _extract_text_content(message: dict[str, Any]) -> str | None:
    content = message.get("content")
    if isinstance(content, str):
        return content.strip() or None
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
        return "\n".join(parts).strip() or None
    return None


def build_model_options(model: str, seed: int | None) -> dict[str, Any]:
    """Return the effective model-specific OpenRouter option delta.

    Runtime quirks live in the canonical model runtime profile registry.
    Callers do not branch on model ids.
    """
    base: dict[str, Any] = {}
    if seed is not None:
        base["seed"] = seed
    return normalize_openrouter_request(
        model,
        base,
        request_class="teacher_story",
        structured_output=False,
    )


def _extract_stream_text_content(delta: dict[str, Any]) -> str:
    content = delta.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)
    return ""


def _aggregate_openrouter_stream(response: requests.Response, model: str) -> dict[str, Any]:
    content_parts: list[str] = []
    usage: dict[str, Any] = {}
    finish_reason: str | None = None
    response_id: str | None = None
    response_model: str | None = None
    provider: str | None = None

    for raw_line in response.iter_lines(decode_unicode=True):
        if raw_line is None:
            continue
        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else str(raw_line)
        line = line.strip("\r\n")
        if not line or line.startswith(":") or not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        try:
            chunk = json.loads(data)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"OpenRouter stream contained invalid JSON: {data[:500]}") from exc
        if chunk.get("error"):
            raise RuntimeError(f"OpenRouter streaming error for model {model}: {chunk['error']}")

        response_id = chunk.get("id") or response_id
        response_model = chunk.get("model") or response_model
        provider = chunk.get("provider") or provider
        if isinstance(chunk.get("usage"), dict):
            usage = dict(chunk["usage"])

        choices = chunk.get("choices") or []
        if not choices:
            continue
        choice = choices[0] or {}
        delta = choice.get("delta") or {}
        text = _extract_stream_text_content(delta)
        if text:
            content_parts.append(text)
        if choice.get("finish_reason") is not None:
            finish_reason = choice.get("finish_reason")

    return {
        "id": response_id,
        "model": response_model or model,
        "provider": provider,
        "choices": [
            {
                "message": {"role": "assistant", "content": "".join(content_parts)},
                "finish_reason": finish_reason,
            }
        ],
        "usage": usage,
    }


def call_openrouter(*, api_key: str, model: str, system_prompt: str, user_prompt: str,
                    temperature: float, max_tokens: int | None, seed: int | None,
                    request_class: str = "teacher_story",
                    structured_output: bool = False,
                    forbid_output_token_limit: bool = False,
                    forbid_ambiguous_paid_retry: bool = False) -> tuple[str, dict[str, Any], dict[str, Any]]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if seed is not None:
        payload["seed"] = seed
    payload = normalize_openrouter_request(
        model,
        payload,
        request_class=request_class,
        structured_output=structured_output,
    )

    if forbid_output_token_limit:
        # Check the FINAL normalized outbound body; model runtime profiles
        # may inject an output cap even if the caller passed None.
        from experiments.sera.request_policy import enforce_no_output_token_limit
        enforce_no_output_token_limit(payload)

    stream_enabled = payload.get("stream") is True

    response = None
    transport_error: Exception | None = None
    attempt = 0
    while True:
        try:
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
                stream=stream_enabled,
            )
            transport_error = None
        except (requests.Timeout, requests.ConnectionError) as exc:
            transport_error = exc
            if forbid_ambiguous_paid_retry:
                # The request might have reached the provider and been
                # billed despite the lost response. Do not blindly resend.
                raise OpenRouterCallError(
                    "OPENROUTER_UNKNOWN_CHARGE_NO_RESEND",
                    {
                        "stage": "transport_unknown_billable",
                        "model": model,
                        "request_class": request_class,
                        "request": payload,
                        "attempts": attempt + 1,
                        "retry_suppressed": True,
                        "needs_provider_idempotent_reconciliation": True,
                        "error": {"type": type(exc).__name__},
                    },
                ) from exc
            if attempt >= len(OPENROUTER_RETRY_DELAYS_SECONDS):
                message_text = (
                    "OpenRouter transport failed after "
                    f"{len(OPENROUTER_RETRY_DELAYS_SECONDS) + 1} attempts "
                    f"for model {model}: {exc}"
                )
                raise OpenRouterCallError(
                    message_text,
                    {
                        "stage": "transport",
                        "model": model,
                        "request_class": request_class,
                        "request": payload,
                        "attempts": attempt + 1,
                        "error": {
                            "type": type(exc).__name__,
                            "message": str(exc),
                        },
                    },
                ) from exc
            time.sleep(OPENROUTER_RETRY_DELAYS_SECONDS[attempt])
            attempt += 1
            continue

        if response.ok:
            break

        try:
            error_body: Any = response.json()
        except ValueError:
            error_body = response.text[:2000]

        retry_delays = _retry_delays_for_response(
            response.status_code,
            error_body,
        )
        if retry_delays is not None and attempt < len(retry_delays):
            retry_after = None
            headers = getattr(response, "headers", {}) or {}
            raw_retry_after = headers.get("Retry-After")
            if raw_retry_after is not None:
                try:
                    retry_after = max(
                        0.0,
                        min(
                            float(raw_retry_after),
                            60.0 if response.status_code == 429 else 30.0,
                        ),
                    )
                except (TypeError, ValueError):
                    retry_after = None
            delay = (
                retry_after
                if retry_after is not None
                else retry_delays[attempt]
            )
            time.sleep(delay)
            attempt += 1
            continue

        raise OpenRouterCallError(
            f"OpenRouter HTTP {response.status_code} for model {model}: {error_body}",
            {
                "stage": "http_response",
                "model": model,
                "request_class": request_class,
                "request": payload,
                "attempts": attempt + 1,
                "status_code": response.status_code,
                "error_body": error_body,
            },
        )

    if response is None:
        raise OpenRouterCallError(
            f"OpenRouter request failed before receiving a response for model {model}: "
            f"{transport_error}",
            {
                "stage": "transport",
                "model": model,
                "request_class": request_class,
                "request": payload,
                "attempts": attempt + 1,
                "error": {
                    "type": type(transport_error).__name__ if transport_error else None,
                    "message": str(transport_error) if transport_error else None,
                },
            },
        )

    try:
        body = (
            _aggregate_openrouter_stream(response, model)
            if stream_enabled
            else response.json()
        )
    except Exception as exc:
        if isinstance(exc, OpenRouterCallError):
            raise
        raise OpenRouterCallError(
            f"OpenRouter response parsing failed for model {model}: {exc}",
            {
                "stage": "response_parse",
                "model": model,
                "request_class": request_class,
                "request": payload,
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            },
        ) from exc
    choices = body.get("choices") or []
    if not choices:
        raise OpenRouterCallError(
            "OpenRouter response contains no choices.",
            {
                "stage": "provider_response",
                "model": model,
                "request_class": request_class,
                "request": payload,
                "body": body,
                "raw_usage": body.get("usage") or {},
                "usage": parse_usage(body).model_dump(mode="json"),
                "cost": parse_cost(body).model_dump(mode="json"),
            },
        )

    choice = choices[0]
    message = choice.get("message") or {}
    content = _extract_text_content(message)
    if not content:
        usage = body.get("usage") or {}
        message_text = (
            "OpenRouter response did not contain story text. "
            f"finish_reason={choice.get('finish_reason')!r}, "
            f"completion_tokens={usage.get('completion_tokens')!r}, "
            f"reasoning_tokens={(usage.get('completion_tokens_details') or {}).get('reasoning_tokens')!r}, "
            f"content_type={type(message.get('content')).__name__}."
        )
        raise OpenRouterCallError(
            message_text,
            {
                "stage": "provider_response",
                "model": model,
                "request_class": request_class,
                "request": payload,
                "finish_reason": choice.get("finish_reason"),
                "body": body,
                "raw_usage": body.get("usage") or {},
                "usage": parse_usage(body).model_dump(mode="json"),
                "cost": parse_cost(body).model_dump(mode="json"),
            },
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


def count_words(text: str) -> int:
    return len(text.split())


def validate_generation(
    *,
    story: str,
    spec: StorySpec,
    finish_reason: str | None,
    min_word_ratio: float,
    max_word_ratio: float,
) -> TechnicalValidation:
    word_count = count_words(story)
    min_words = round(spec.target_words * min_word_ratio)
    max_words = round(spec.target_words * max_word_ratio)
    reasons: list[str] = []

    if finish_reason == "length":
        reasons.append("model_hit_output_token_limit")
    elif finish_reason not in (None, "stop"):
        reasons.append(f"unexpected_finish_reason:{finish_reason}")

    if word_count < min_words:
        reasons.append("below_minimum_word_count")
    if word_count > max_words:
        reasons.append("above_maximum_word_count")

    eligible_for_judge = not reasons
    return TechnicalValidation(
        status="complete" if eligible_for_judge else "incomplete",
        eligible_for_judge=eligible_for_judge,
        word_count=word_count,
        target_words=spec.target_words,
        min_words=min_words,
        max_words=max_words,
        finish_reason=finish_reason,
        reasons=reasons,
    )


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


def generate_one(
    config: dict[str, Any],
    spec: StorySpec,
    dry_run: bool = False,
    model_override: str | None = None,
) -> tuple[Path | None, TechnicalValidation | None]:
    teacher = config["teacher"]
    output = config["output"]
    story_config = config.get("story") or {}
    model_env = teacher.get("model_env", "TEACHER_MODEL")
    configured_model = model_override or os.getenv(model_env)
    api_key = os.getenv("OPENROUTER_API_KEY")

    if dry_run:
        model = configured_model or DRY_RUN_MODEL_PLACEHOLDER
    else:
        if not configured_model:
            raise RuntimeError(f"Missing model name in --model or environment variable {model_env}.")
        if not api_key:
            raise RuntimeError("Missing OPENROUTER_API_KEY.")
        model = configured_model

    system_prompt = load_teacher_prompt(Path("prompts/story_teacher.md"))
    user_prompt = build_user_prompt(spec)

    if dry_run:
        console.rule("Dry run")
        console.print(f"Model: {model}")
        console.print(f"Prompt version: {PROMPT_VERSION}")
        console.print(f"Model options: {build_model_options(model, config.get('seed'))}")
        console.print(user_prompt)
        return None, None

    story, body, request_payload = call_openrouter(
        api_key=api_key,
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=float(teacher.get("temperature", 0.8)),
        max_tokens=int(teacher.get("max_tokens", 7000)),
        seed=config.get("seed"),
    )

    choice = (body.get("choices") or [{}])[0]
    finish_reason = choice.get("finish_reason")
    technical_validation = validate_generation(
        story=story,
        spec=spec,
        finish_reason=finish_reason,
        min_word_ratio=float(story_config.get("min_word_ratio", 0.80)),
        max_word_ratio=float(story_config.get("max_word_ratio", 1.20)),
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
        technical_validation=technical_validation,
        request={
            "temperature": request_payload.get("temperature"),
            "max_tokens": request_payload.get("max_tokens"),
            "seed": request_payload.get("seed"),
            "reasoning": request_payload.get("reasoning"),
            "stream": request_payload.get("stream"),
        },
        response_meta={
            "openrouter_id": body.get("id"),
            "model": body.get("model"),
            "provider": body.get("provider"),
            "finish_reason": finish_reason,
        },
    )
    return save_record(record, raw_dir), technical_validation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic LUMI teacher stories via OpenRouter.")
    parser.add_argument("--spec", default="data/specifications/example_story.yaml")
    parser.add_argument("--config", default="configs/generation.yaml")
    parser.add_argument("--model", help="Override TEACHER_MODEL for this run without editing .env")
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
        output_path, validation = generate_one(
            config,
            spec,
            dry_run=args.dry_run,
            model_override=args.model,
        )
        if output_path and validation:
            status_style = "green" if validation.eligible_for_judge else "yellow"
            console.print(f"[{status_style}]Generated[/{status_style}] {output_path}")
            console.print(
                f"Technical gate: [{status_style}]{validation.status}[/{status_style}] | "
                f"words={validation.word_count}/{validation.target_words} | "
                f"finish_reason={validation.finish_reason} | "
                f"eligible_for_judge={validation.eligible_for_judge}"
            )
            if validation.reasons:
                console.print(f"Reasons: {', '.join(validation.reasons)}")
        elif args.dry_run:
            break
        if index + 1 < args.count:
            console.print(f"Completed {index + 1}/{args.count}")


if __name__ == "__main__":
    main()
