"""External single-attempt guard for frozen Final V3 Spine; not a V3 runtime change.

A successful Spine logically authorizes exactly two distinct calls (architect then
gate). A fault stops before any downstream call. One HTTPS POST per logical call.
This guard is a new qualification policy, not evidence of frozen V3 equivalence.
"""
from __future__ import annotations

import hashlib
import json
import os
from contextlib import ExitStack, contextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path
from unittest.mock import patch

SPINE_MODELS = ("anthropic/claude-sonnet-5.5", "openai/gpt-5.6-luna")
FROZEN_V3_SHA = "63e1e3ce82c244bc5bb02b0463a9a1a6715c941b"


class SafetyStop(RuntimeError):
    """A guardrail stopped the trial; no automated resumption is permitted."""


def _safe_cost(body):
    usage = body.get("usage") if isinstance(body, dict) else None
    value = usage.get("cost") if isinstance(usage, dict) else None
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise SafetyStop("PROVIDER_COST_MISSING_OR_INVALID")
    try:
        d = Decimal(str(value))
    except InvalidOperation as exc:
        raise SafetyStop("PROVIDER_COST_MISSING_OR_INVALID") from exc
    if not d.is_finite() or d < 0:
        raise SafetyStop("PROVIDER_COST_MISSING_OR_INVALID")
    return d


class SingleAttemptSpineGuard:
    def __init__(self, evidence_dir: Path, max_cost_usd: Decimal):
        if not max_cost_usd.is_finite() or max_cost_usd <= 0:
            raise ValueError("Invalid grant ceiling")
        self.evidence_dir = evidence_dir
        self.max_cost = max_cost_usd
        self.spent = Decimal("0")
        self.calls = 0
        self._event_number = 0
        self._post = None

    def event(self, kind, **safe_fields):
        # Atomic, exclusively created, fsynced event files. Never log request,
        # response, prompt, token, provider error body or credentials here.
        payload = dict(schema="v3-single-attempt-evidence.v1", kind=kind, **safe_fields)
        self._event_number += 1
        path = self.evidence_dir / f"{self._event_number:03d}-{kind.lower()}.json"
        data = (json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n").encode()
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            raise

    def _one_post(self, url, **kwargs):
        # All outgoing POST operations must go through the monitored provider.
        from src import generate as g
        if url != g.OPENROUTER_URL:
            self.event("POLICY_STOP", reason="POST_DESTINATION_NOT_ALLOWED")
            raise SafetyStop("POST_DESTINATION_NOT_ALLOWED")
        payload = kwargs.get("json")
        if not isinstance(payload, dict):
            self.event("POLICY_STOP", reason="NON_JSON_PROVIDER_POST")
            raise SafetyStop("NON_JSON_PROVIDER_POST")
        model = payload.get("model")
        if self.calls >= len(SPINE_MODELS):
            self.event("POLICY_STOP", reason="EXTRA_PROVIDER_POST_BLOCKED")
            raise SafetyStop("EXTRA_PROVIDER_POST_BLOCKED")
        if model != SPINE_MODELS[self.calls]:
            self.event("POLICY_STOP", reason="WRONG_MODEL_OR_UNEXPECTED_RETRY")
            raise SafetyStop("WRONG_MODEL_OR_UNEXPECTED_RETRY")
        self.calls += 1
        wire_hash = hashlib.sha256(json.dumps(payload, sort_keys=True,
                    separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        self.event("POST_INTENT", call_number=self.calls, model=model,
                   canonical_payload_sha256=wire_hash)
        try:
            response = self._post(url, **kwargs)
        except Exception as exc:
            self.event("TRANSPORT_FAULT", call_number=self.calls,
                       exception_type=type(exc).__name__)
            raise
        self.event("HTTP_OBSERVED", call_number=self.calls,
                   status_code=int(getattr(response, "status_code", 0)))
        return response

    def _observed_call(self, **kwargs):
        from src import english_story_pipeline as p
        output = self._original_call(**kwargs)
        _, body, _ = output
        if not isinstance(body, dict):
            self.event("PROVIDER_FAULT", reason="INVALID_COMPLETION_BODY")
            raise SafetyStop("INVALID_COMPLETION_BODY")
        cost = _safe_cost(body)
        generation_id = body.get("id")
        if not isinstance(generation_id, str) or not generation_id.startswith("gen-") or len(generation_id) > 140:
            self.event("PROVIDER_FAULT", reason="GENERATION_ID_MISSING_OR_INVALID")
            raise SafetyStop("GENERATION_ID_MISSING_OR_INVALID")
        usage = body.get("usage") or {}
        self.event("PROVIDER_OBSERVED", call_number=self.calls,
                   model=kwargs.get("model"), generation_id=generation_id,
                   reported_cost_usd=str(cost),
                   input_tokens=usage.get("prompt_tokens") if isinstance(usage.get("prompt_tokens"), int) else None,
                   output_tokens=usage.get("completion_tokens") if isinstance(usage.get("completion_tokens"), int) else None)
        self.spent += cost
        if self.spent > self.max_cost:
            self.event("POLICY_STOP", reason="CUMULATIVE_COST_CEILING_REACHED",
                       observed_cost_usd=str(self.spent))
            raise SafetyStop("CUMULATIVE_COST_CEILING_REACHED")
        return output

    def _no_parse_retry(self, **kwargs):
        # Keep original V3 parser and prompts; override only retry count.
        kwargs["max_parse_attempts"] = 1
        return self._original_structured(**kwargs)

    @contextmanager
    def installed(self):
        from src import generate as g
        from src import english_story_pipeline as p
        from src import episode_spine_v2_generate as s
        import requests
        self._post = requests.post
        self._original_call = p.call_openrouter
        self._original_structured = p.call_structured_json_with_retry
        with ExitStack() as stack:
            stack.enter_context(patch.object(requests, "post", self._one_post))
            # Transport timeout, HTTP 429/5xx and malformed JSON cannot retry.
            stack.enter_context(patch.object(g, "OPENROUTER_RETRY_DELAYS_SECONDS", ()))
            stack.enter_context(patch.object(g, "_retry_delays_for_response",
                                            lambda *args, **kwargs: None))
            stack.enter_context(patch.object(p, "call_openrouter", self._observed_call))
            stack.enter_context(patch.object(s, "call_structured_json_with_retry", self._no_parse_retry))
            self.event("GUARD_INSTALLED", permitted_models=list(SPINE_MODELS),
                       provider_post_limit=2, attempts_per_model=1)
            yield self
