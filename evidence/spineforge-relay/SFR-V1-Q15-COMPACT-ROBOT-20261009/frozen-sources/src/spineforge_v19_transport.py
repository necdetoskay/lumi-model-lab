from __future__ import annotations

import json
from typing import Any

import requests

from src.generate import (
    OPENROUTER_URL,
    OpenRouterCallError,
    _aggregate_openrouter_stream,
    _extract_text_content,
    parse_cost,
    parse_usage,
)
from src.model_registry import normalize_openrouter_request
from src.spineforge_v6_json_schema import build_json_schema_response_format


STRICT_SCHEMA_MAX_BYTES = 4096


def schema_size_bytes(schema: dict[str, Any]) -> int:
    return len(
        json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    )


def _request_once(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int | None,
    seed: int | None,
    request_class: str,
    response_format: dict[str, Any] | None,
    require_parameters: bool,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    if request_class.startswith("spineforge_relay_v1"):
        from src.spineforge_relay_v1_lease_context import require_reserved_transport
        require_reserved_transport({
            "model": model, "system_prompt": system_prompt, "user_prompt": user_prompt,
            "temperature": temperature, "max_tokens": max_tokens, "seed": seed,
            "request_class": request_class, "response_format": response_format,
            "require_parameters": require_parameters,
        })
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
        structured_output=response_format is None,
    )

    if response_format is not None:
        payload["response_format"] = response_format
    if require_parameters:
        provider = dict(payload.get("provider") or {})
        provider["require_parameters"] = True
        payload["provider"] = provider

    stream_enabled = payload.get("stream") is True
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
    except (requests.Timeout, requests.ConnectionError) as exc:
        raise OpenRouterCallError(
            f"SpineForge v19 one-shot transport failed for {model}: {exc}",
            {
                "stage": "transport",
                "model": model,
                "request_class": request_class,
                "request": payload,
                "attempts": 1,
                "retry_suppressed": True,
                "retry_suppressed_reason": "spineforge_v19_qualification_one_shot",
                "error": {"type": type(exc).__name__, "message": str(exc)},
            },
        ) from exc

    if not response.ok:
        try:
            error_body: Any = response.json()
        except ValueError:
            error_body = response.text[:2000]
        raise OpenRouterCallError(
            f"OpenRouter HTTP {response.status_code} for model {model}: {error_body}",
            {
                "stage": "http_response",
                "model": model,
                "request_class": request_class,
                "request": payload,
                "attempts": 1,
                "status_code": response.status_code,
                "error_body": error_body,
                "retry_suppressed": True,
                "retry_suppressed_reason": "spineforge_v19_qualification_one_shot",
            },
        )

    try:
        body = (
            _aggregate_openrouter_stream(response, model)
            if stream_enabled
            else response.json()
        )
    except Exception as exc:
        raise OpenRouterCallError(
            f"SpineForge v19 response parsing failed for {model}: {exc}",
            {
                "stage": "response_parse",
                "model": model,
                "request_class": request_class,
                "request": payload,
                "attempts": 1,
                "retry_suppressed": True,
                "error": {"type": type(exc).__name__, "message": str(exc)},
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
                "attempts": 1,
                "body": body,
                "raw_usage": body.get("usage") or {},
                "usage": parse_usage(body).model_dump(mode="json"),
                "cost": parse_cost(body).model_dump(mode="json"),
                "retry_suppressed": True,
            },
        )

    message = (choices[0] or {}).get("message") or {}
    content = _extract_text_content(message)
    if not content:
        raise OpenRouterCallError(
            "OpenRouter response did not contain structured text.",
            {
                "stage": "provider_response",
                "model": model,
                "request_class": request_class,
                "request": payload,
                "attempts": 1,
                "body": body,
                "raw_usage": body.get("usage") or {},
                "usage": parse_usage(body).model_dump(mode="json"),
                "cost": parse_cost(body).model_dump(mode="json"),
                "retry_suppressed": True,
            },
        )
    return content, body, payload


def _parse_object(
    *,
    text: str,
    body: dict[str, Any],
    request: dict[str, Any],
    model: str,
    request_class: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OpenRouterCallError(
            "SpineForge v19 one-shot structured response is invalid JSON.",
            {
                "stage": "structured_parse",
                "model": model,
                "request_class": request_class,
                "request": request,
                "attempts": 1,
                "body": body,
                "raw_usage": body.get("usage") or {},
                "usage": parse_usage(body).model_dump(mode="json"),
                "cost": parse_cost(body).model_dump(mode="json"),
                "retry_suppressed": True,
            },
        ) from exc
    if not isinstance(parsed, dict):
        raise OpenRouterCallError(
            "SpineForge v19 structured response root must be an object.",
            {
                "stage": "structured_parse",
                "model": model,
                "request_class": request_class,
                "request": request,
                "attempts": 1,
                "body": body,
                "retry_suppressed": True,
            },
        )
    return parsed, body, request, []


def call_json_object_once(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int | None,
    seed: int | None,
    request_class: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    text, body, request = _request_once(
        api_key=api_key,
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        seed=seed,
        request_class=request_class,
        response_format=None,
        require_parameters=False,
    )
    return _parse_object(
        text=text,
        body=body,
        request=request,
        model=model,
        request_class=request_class,
    )


def call_strict_json_once(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int | None,
    seed: int | None,
    request_class: str,
    schema_name: str,
    schema: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    size = schema_size_bytes(schema)
    if size > STRICT_SCHEMA_MAX_BYTES:
        raise RuntimeError(
            f"SpineForge v19 strict schema too large: {size}>{STRICT_SCHEMA_MAX_BYTES}"
        )
    response_format = build_json_schema_response_format(name=schema_name, schema=schema)
    text, body, request = _request_once(
        api_key=api_key,
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        seed=seed,
        request_class=request_class,
        response_format=response_format,
        require_parameters=True,
    )
    return _parse_object(
        text=text,
        body=body,
        request=request,
        model=model,
        request_class=request_class,
    )
