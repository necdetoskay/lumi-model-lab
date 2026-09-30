from __future__ import annotations

import time
from typing import Any

import requests

from src.generate import (
    OPENROUTER_RETRY_DELAYS_SECONDS,
    OPENROUTER_URL,
    OpenRouterCallError,
    _aggregate_openrouter_stream,
    _extract_text_content,
    _retry_delays_for_response,
    parse_cost,
    parse_usage,
)
from src.model_registry import normalize_openrouter_request


def call_openrouter(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int | None,
    seed: int | None,
    request_class: str = "teacher_story",
    structured_output: bool = False,
    response_format: dict[str, Any] | None = None,
    require_parameters: bool = False,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """
    v5-only OpenRouter transport that can carry an explicit strict JSON Schema
    without mutating the historical shared generate.py runtime.

    Existing model-runtime normalization still owns temperature, reasoning,
    max-token, seed, stream, and provider-routing policy.
    """
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
    if response_format is not None:
        payload["response_format"] = response_format

    payload = normalize_openrouter_request(
        model,
        payload,
        request_class=request_class,
        structured_output=structured_output and response_format is None,
    )

    if response_format is not None:
        # Explicit v5 strict-schema requests must survive generic json_object
        # normalization unchanged.
        payload["response_format"] = response_format

    if require_parameters:
        provider = dict(payload.get("provider") or {})
        provider["require_parameters"] = True
        payload["provider"] = provider

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
            if attempt >= len(OPENROUTER_RETRY_DELAYS_SECONDS):
                raise OpenRouterCallError(
                    (
                        "OpenRouter transport failed after "
                        f"{len(OPENROUTER_RETRY_DELAYS_SECONDS) + 1} attempts "
                        f"for model {model}: {exc}"
                    ),
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

        retry_delays = _retry_delays_for_response(response.status_code, error_body)
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
            delay = retry_after if retry_after is not None else retry_delays[attempt]
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
            f"OpenRouter request failed before receiving a response for model {model}: {transport_error}",
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
        raise OpenRouterCallError(
            (
                "OpenRouter response did not contain structured text. "
                f"finish_reason={choice.get('finish_reason')!r}, "
                f"completion_tokens={usage.get('completion_tokens')!r}."
            ),
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
