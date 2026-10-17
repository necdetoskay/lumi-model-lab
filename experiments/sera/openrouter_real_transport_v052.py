"""SERA v0.52 real OpenRouter wire transport (inert until an approved callback).

ONE HTTP POST, no retry, no provider fallback, no implicit paid authorization.
It must be invoked ONLY behind the signed-approval + durable journal bridge.
The provider response envelope is returned whole for persistence BEFORE parsing
by the v0.21/v0.22 stage adapters. Transport errors propagate so a STARTED
journal record prevents blind rebilling. No output-token limit is added.
"""
from __future__ import annotations

import json
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from experiments.sera.provider_grant_journal_v052 import JournalBlocked
from experiments.sera.request_policy import enforce_no_output_token_limit

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
TITLE = "SERA v0.52 Qualified Shadow — Noncanonical"


def make_openrouter_transport(*, api_key, opener=None, timeout_seconds=180):
    """Construct a dormant callable for the signed/journaled provider bridge.

    This function never reads environment secrets and never makes HTTP calls.
    A trusted runtime supplies its credential. `opener` is test injectable.
    Response shape is compatible with v0.21/v0.22: {"raw": ..., "error": ...}.
    """
    if not isinstance(api_key, str) or not api_key.strip():
        raise JournalBlocked("V052_PROVIDER_CREDENTIAL_REQUIRED")
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 600:
        raise JournalBlocked("V052_TRANSPORT_TIMEOUT_INVALID")
    send = opener if opener is not None else urlopen
    if not callable(send):
        raise JournalBlocked("V052_TRANSPORT_OPENER_INVALID")

    def one_post(*, model, payload, request_id):
        if not isinstance(model, str) or not model.strip():
            raise JournalBlocked("V052_TRANSPORT_MODEL_REQUIRED")
        if not isinstance(request_id, str) or not request_id.strip():
            raise JournalBlocked("V052_TRANSPORT_REQUEST_ID_REQUIRED")
        enforce_no_output_token_limit(payload)
        if "model" in payload and payload["model"] != model:
            raise JournalBlocked("V052_TRANSPORT_MODEL_DRIFT")
        if "stream" in payload and payload["stream"] is not False:
            raise JournalBlocked("V052_STREAMED_UNRECEIPTED_CALL_FORBIDDEN")
        # Preserve original stage messages/schema; do not invent generation caps.
        body = dict(payload, model=model, stream=False)
        enforce_no_output_token_limit(body)
        request = Request(
            ENDPOINT, method="POST",
            headers={
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/necdetoskay/lumi-model-lab",
                "X-Title": TITLE,
                # Correlation only. Never assume this makes POST idempotent.
                "X-Request-ID": request_id,
            },
            data=json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8"),
        )
        started = time.monotonic()
        try:
            with send(request, timeout=timeout_seconds) as response:
                raw_bytes = response.read()
        except HTTPError as exc:
            # Received HTTP rejection is a durable response, not a valid
            # generated scene; do not leak potentially sensitive error text.
            return {"raw": None, "error": "HTTP_" + str(exc.code),
                    "duration_ms": round((time.monotonic() - started) * 1000)}
        # Network/timeout/JSON errors MUST propagate into UNKNOWN-INFLIGHT:
        # the journal will not send another POST for this request.
        result = json.loads(raw_bytes.decode("utf-8"))
        if not isinstance(result, dict):
            raise JournalBlocked("V052_PROVIDER_ENVELOPE_NOT_OBJECT")
        return {"raw": result, "error": None,
                "duration_ms": round((time.monotonic() - started) * 1000)}
    return one_post
