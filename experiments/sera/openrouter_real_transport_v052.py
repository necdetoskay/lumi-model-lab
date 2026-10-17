"""SERA v0.52 real OpenRouter wire transport (inert until an approved callback).

ONE HTTP POST, no retry, no provider fallback, no implicit paid authorization.
It must be invoked ONLY behind the signed-approval + durable journal bridge.
The provider response envelope is returned whole for persistence BEFORE parsing
by the v0.21/v0.22 stage adapters. Transport errors propagate so a STARTED
journal record prevents blind rebilling. No output-token limit is added.
"""
from __future__ import annotations

import base64
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
            # Archive the exact non-2xx response bytes too; a model response
            # must never be confused with a completed story-stage result.
            return {"wire_payload_b64": base64.b64encode(exc.read()).decode("ascii"),
                    "http_status": exc.code,
                    "duration_ms": round((time.monotonic() - started) * 1000)}
        # Persist the EXACT received response bytes before JSON decode. The
        # journal is responsible for durable RECEIPTED-before-parse semantics.
        # Network/timeouts propagate as UNKNOWN-INFLIGHT, never auto-resend.
        return {"wire_payload_b64": base64.b64encode(raw_bytes).decode("ascii"),
                "http_status": 200,
                "duration_ms": round((time.monotonic() - started) * 1000)}
    return one_post



def decode_receipted_wire(envelope):
    """Only invoke AFTER ProviderJournal persisted the exact response bytes."""
    if not isinstance(envelope, dict) or set(envelope) != {
        "wire_payload_b64", "http_status", "duration_ms"
    }:
        raise JournalBlocked("V052_WIRE_RECEIPT_FORMAT_INVALID")
    try:
        raw = base64.b64decode(envelope["wire_payload_b64"], validate=True)
    except (ValueError, TypeError) as exc:
        raise JournalBlocked("V052_WIRE_RECEIPT_CORRUPT") from exc
    status = envelope["http_status"]
    if type(status) is not int:
        raise JournalBlocked("V052_HTTP_STATUS_INVALID")
    if status != 200:
        return {"raw": None, "error": "HTTP_" + str(status),
                "duration_ms": envelope["duration_ms"]}
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JournalBlocked("V052_RECEIPTED_MODEL_JSON_INVALID") from exc
    if not isinstance(data, dict):
        raise JournalBlocked("V052_RECEIPTED_ENVELOPE_INVALID")
    return {"raw": data, "error": None,
            "duration_ms": envelope["duration_ms"]}
