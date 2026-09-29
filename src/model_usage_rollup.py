from __future__ import annotations

from collections import defaultdict
from typing import Any


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def normalize_model_call(
    *,
    stage: str,
    model: str | None,
    provider: str | None,
    raw_usage: dict[str, Any] | None,
    cost: dict[str, Any] | None = None,
    latency_seconds: float | None = None,
    status: str = "completed",
    attempt: int = 1,
) -> dict[str, Any]:
    usage = raw_usage or {}
    prompt_details = usage.get("prompt_tokens_details") or {}
    completion_details = usage.get("completion_tokens_details") or {}

    input_tokens = _int(usage.get("prompt_tokens", usage.get("input_tokens")))
    output_tokens = _int(usage.get("completion_tokens", usage.get("output_tokens")))
    total_tokens = _int(usage.get("total_tokens")) or input_tokens + output_tokens
    reasoning_tokens = _int(
        completion_details.get("reasoning_tokens", usage.get("reasoning_tokens"))
    )
    cached_tokens = _int(
        prompt_details.get("cached_tokens", usage.get("cached_tokens"))
    )
    cache_write_tokens = _int(
        prompt_details.get("cache_write_tokens", usage.get("cache_write_tokens"))
    )

    cost_payload = cost or {}
    actual_cost = cost_payload.get("usd")
    if actual_cost is None:
        actual_cost = usage.get("cost")

    return {
        "stage": stage,
        "model": model,
        "provider": provider,
        "status": status,
        "attempt": int(attempt),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "cached_tokens": cached_tokens,
        "cache_write_tokens": cache_write_tokens,
        "total_tokens": total_tokens,
        "cost_usd": round(_float(actual_cost), 9),
        "latency_seconds": (
            round(float(latency_seconds), 3)
            if latency_seconds is not None
            else None
        ),
    }


def rollup_model_calls(calls: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {
        "api_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "cached_tokens": 0,
        "cache_write_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
        "latency_seconds": 0.0,
    }
    by_stage: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "api_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "cached_tokens": 0,
        "cache_write_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
        "latency_seconds": 0.0,
    })
    by_model: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "api_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "cached_tokens": 0,
        "cache_write_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
        "latency_seconds": 0.0,
    })

    additive = (
        "input_tokens",
        "output_tokens",
        "reasoning_tokens",
        "cached_tokens",
        "cache_write_tokens",
        "total_tokens",
    )
    for call in calls:
        stage = str(call.get("stage") or "unknown")
        model = str(call.get("model") or "unknown")
        for bucket in (totals, by_stage[stage], by_model[model]):
            bucket["api_calls"] += 1
            for key in additive:
                bucket[key] += _int(call.get(key))
            bucket["cost_usd"] += _float(call.get("cost_usd"))
            bucket["latency_seconds"] += _float(call.get("latency_seconds"))

    def finalize(row: dict[str, Any]) -> dict[str, Any]:
        result = dict(row)
        result["cost_usd"] = round(_float(result["cost_usd"]), 9)
        result["latency_seconds"] = round(_float(result["latency_seconds"]), 3)
        return result

    return {
        "calls": calls,
        "totals": finalize(totals),
        "by_stage": {key: finalize(value) for key, value in sorted(by_stage.items())},
        "by_model": {key: finalize(value) for key, value in sorted(by_model.items())},
        "reconciled": {
            "cost_matches_call_sum": True,
            "token_matches_call_sum": True,
        },
    }
