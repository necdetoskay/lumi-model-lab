from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Callable

from src.generate import OpenRouterCallError, call_openrouter, count_words, parse_cost, parse_usage
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls


WRITER_MODEL = "aion-labs/aion-3.5-mini"


WriterCall = Callable[..., tuple[str, dict[str, Any], dict[str, Any]]]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_writer_handoff(handoff: dict[str, Any]) -> None:
    if handoff.get("schema") != "spineforge-v20-writer-handoff.v1":
        raise RuntimeError("Writer handoff schema mismatch.")
    if handoff.get("status") != "WRITER_READY":
        raise RuntimeError("Writer handoff is not WRITER_READY.")
    if handoff.get("writer_model") != WRITER_MODEL:
        raise RuntimeError("Writer model mismatch.")
    if not handoff.get("approval_id"):
        raise RuntimeError("Writer handoff missing approval_id.")
    if not handoff.get("spine_hash"):
        raise RuntimeError("Writer handoff missing spine_hash.")
    if not handoff.get("context_fingerprint"):
        raise RuntimeError("Writer handoff missing context_fingerprint.")
    if (handoff.get("human_review") or {}).get("verdict") != "APPROVE":
        raise RuntimeError("Writer handoff requires human APPROVE.")
    if (handoff.get("human_review") or {}).get("story_writer_authorized") is not True:
        raise RuntimeError("Writer handoff is not authorized by human review.")
    if int(handoff.get("target_words_min") or 0) != 1600:
        raise RuntimeError("Writer minimum word authority mismatch.")
    if int(handoff.get("target_words_max") or 0) != 2500:
        raise RuntimeError("Writer maximum word authority mismatch.")
    if not isinstance(handoff.get("writer_input"), dict):
        raise RuntimeError("Writer handoff missing writer_input.")


def execute_writer_once(
    *,
    handoff: dict[str, Any],
    api_key: str,
    system_prompt: str,
    call_fn: WriterCall = call_openrouter,
) -> dict[str, Any]:
    validate_writer_handoff(handoff)
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required.")

    require_qualification_runtime_profile(WRITER_MODEL)

    started = time.perf_counter()
    started_at = _now_iso()
    call_started = time.perf_counter()

    try:
        story, body, request = call_fn(
            api_key=api_key,
            model=WRITER_MODEL,
            system_prompt=system_prompt,
            user_prompt=json.dumps(handoff["writer_input"], ensure_ascii=False),
            temperature=0.76,
            max_tokens=7000,
            seed=2026100101,
            request_class="spineforge_v20_story_writer",
            structured_output=False,
        )
    except OpenRouterCallError as exc:
        latency = round(time.perf_counter() - call_started, 3)
        trace = getattr(exc, "trace", None) or {}
        failure_call = normalize_model_call(
            stage="spineforge_v20_writer",
            model=WRITER_MODEL,
            provider=runtime_profile_identity(WRITER_MODEL).get("provider"),
            raw_usage=trace.get("raw_usage") or {},
            cost=trace.get("cost") or {},
            latency_seconds=latency,
            status="failed",
        )
        return {
            "schema": "spineforge-v20-writer-evidence.v1",
            "status": "writer_provider_failure",
            "approval_id": handoff["approval_id"],
            "context_fingerprint": handoff["context_fingerprint"],
            "spine_hash": handoff["spine_hash"],
            "writer_model": WRITER_MODEL,
            "started_at": started_at,
            "completed_at": _now_iso(),
            "latency_seconds": round(time.perf_counter() - started, 3),
            "failure": {
                "type": type(exc).__name__,
                "message": str(exc),
                "stage": trace.get("stage"),
                "finish_reason": trace.get("finish_reason"),
                "generation_id": (trace.get("body") or {}).get("id"),
            },
            "writer_usage_rollup": rollup_model_calls([failure_call]),
            "automatic_retry_executed": False,
            "editor_authorized": False,
            "judge_authorized": False,
            "repair_authorized": False,
            "translation_authorized": False,
            "state_commit_authorized": False,
        }

    latency = round(time.perf_counter() - call_started, 3)
    words = count_words(story)
    title = next((line.strip() for line in story.splitlines() if line.strip()), "")
    min_words = int(handoff["target_words_min"])
    max_words = int(handoff["target_words_max"])

    writer_call = normalize_model_call(
        stage="spineforge_v20_writer",
        model=WRITER_MODEL,
        provider=runtime_profile_identity(WRITER_MODEL).get("provider"),
        raw_usage=body.get("usage") or {},
        cost=parse_cost(body).model_dump(mode="json"),
        latency_seconds=latency,
    )
    checks = {
        "non_empty": bool(story.strip()),
        "title_present": bool(title),
        "word_count": words,
        "target_words_min": min_words,
        "target_words_max": max_words,
        "preferred_words_min": int(handoff["preferred_words_min"]),
        "preferred_words_max": int(handoff["preferred_words_max"]),
        "length_pass": min_words <= words <= max_words,
        "preferred_length_hit": int(handoff["preferred_words_min"]) <= words <= int(handoff["preferred_words_max"]),
    }
    writer_usage = rollup_model_calls([writer_call])

    return {
        "schema": "spineforge-v20-writer-evidence.v1",
        "status": (
            "writer_generated"
            if checks["non_empty"] and checks["title_present"] and checks["length_pass"]
            else "writer_generated_deterministic_check_failed"
        ),
        "approval_id": handoff["approval_id"],
        "context_pack_id": handoff["context_pack_id"],
        "context_fingerprint": handoff["context_fingerprint"],
        "spine_hash": handoff["spine_hash"],
        "writer_model": WRITER_MODEL,
        "started_at": started_at,
        "completed_at": _now_iso(),
        "latency_seconds": round(time.perf_counter() - started, 3),
        "deterministic_checks": checks,
        "story": story,
        "writer_call": {
            "usage": parse_usage(body).model_dump(mode="json"),
            "cost": parse_cost(body).model_dump(mode="json"),
            "latency_seconds": latency,
            "request": {
                "temperature": request.get("temperature"),
                "max_tokens": request.get("max_tokens"),
                "reasoning": request.get("reasoning"),
                "response_format": request.get("response_format"),
            },
        },
        "writer_usage_rollup": writer_usage,
        "writer_cost_usd": writer_usage["totals"]["cost_usd"],
        "automatic_retry_executed": False,
        "editor_authorized": False,
        "judge_authorized": False,
        "repair_authorized": False,
        "translation_authorized": False,
        "state_commit_authorized": False,
    }
