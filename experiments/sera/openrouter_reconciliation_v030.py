"""SERA v0.30: read-only OpenRouter known-generation response recovery.

This resolver NEVER sends a chat completion. It uses only the documented
GET /api/v1/generation and GET /api/v1/generation/content endpoints.
Critically, those GETs require a GEN ID. A lost reply with no trustworthy
generation ID CANNOT be rediscovered from a local request SHA.

An independent application-owned, authenticated binding must attest
(generation_id, request_sha256, model); this module NEVER trusts a
model-supplied id or guesses it. The returned stored source messages
must exactly match the already frozen original request, metadata must
match the pinned model, and cost must be finite/nonnegative. A verified
read-only recovery still grants NO canon/WorldStore authority.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from experiments.sera.coverage import CoverageError
from experiments.sera.world_state_v02 import canonical
from hashlib import sha256

SCHEMA = "sera.openrouter-known-generation-recovery.v0.30"
BASE = "https://openrouter.ai/api/v1"
MAX_READ_BYTES = 2_000_000


def _must(ok, code):
    if not ok:
        raise CoverageError(code)


def fingerprint(*, model, request):
    _must(isinstance(model, str) and model.strip() and
          isinstance(request, dict), "V030_REQUEST_OR_MODEL_INVALID")
    return sha256(canonical({
        "model": model, "request": request,
    }).encode("utf-8")).hexdigest()


def read_generation(*, api_key, generation_id, part):
    """Authenticated provider GET only, never POST; no retry or fallback."""
    _must(isinstance(api_key, str) and api_key.strip(),
          "V030_PROVIDER_CREDENTIAL_REQUIRED")
    _must(isinstance(generation_id, str) and generation_id.strip() and
          len(generation_id) <= 180 and
          all(c.isalnum() or c in "-_" for c in generation_id),
          "V030_GENERATION_ID_INVALID")
    _must(part in ("metadata", "content"), "V030_LOOKUP_TYPE_INVALID")
    path = "/generation" if part == "metadata" else "/generation/content"
    url = BASE + path + "?" + urlencode({"id": generation_id})
    req = Request(url, headers={
        "Authorization": "Bearer " + api_key,
        "Accept": "application/json",
        "HTTP-Referer": "https://github.com/necdetoskay/lumi-model-lab",
    }, method="GET")
    try:
        with urlopen(req, timeout=20) as response:
            body = response.read(MAX_READ_BYTES + 1)
    except Exception as exc:
        raise CoverageError("V030_PROVIDER_READ_UNAVAILABLE") from exc
    _must(len(body) <= MAX_READ_BYTES, "V030_PROVIDER_READ_TOO_LARGE")
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise CoverageError("V030_PROVIDER_READ_JSON_INVALID") from exc


def recover(*, model, request, api_key, binding_lookup,
            verify_binding, get_generation=read_generation):
    """Read a trusted known-generation completion without charging again.

    binding_lookup(model, request_sha256) returns a signed/app-owned map.
    verify_binding(binding) must validate full authenticity independently.
    The default provider GET is read-only and never called if ID is unknown.
    """
    sig = fingerprint(model=model, request=request)
    _must(callable(binding_lookup) and callable(verify_binding) and
          callable(get_generation),
          "V030_AUTHENTICATED_LOOKUP_REQUIRED")
    binding = binding_lookup(model=model, request_sha256=sig)
    if binding is None:
        # No generation ID => NO defensible provider lookup. Do not retry.
        raise CoverageError("V030_GENERATION_ID_UNAVAILABLE_NO_RESEND")
    _must(isinstance(binding, dict) and set(binding) == {
        "schema", "model", "request_sha256", "generation_id",
        "evidence_source",
    } and binding["schema"] == SCHEMA and
          binding["model"] == model and
          binding["request_sha256"] == sig and
          binding["evidence_source"] == "AUTHENTICATED_PROVIDER_GENERATION" and
          isinstance(binding["generation_id"], str) and
          callable(verify_binding) and
          verify_binding(deepcopy(binding)) is True,
          "V030_GENERATION_BINDING_UNTRUSTED")
    gid = binding["generation_id"]
    _must(gid and len(gid) <= 180 and
          all(c.isalnum() or c in "-_" for c in gid),
          "V030_GENERATION_ID_INVALID")
    metadata = get_generation(
        api_key=api_key, generation_id=gid, part="metadata",
    )
    content = get_generation(
        api_key=api_key, generation_id=gid, part="content",
    )
    _must(isinstance(metadata, dict) and
          isinstance(metadata.get("data"), dict) and
          isinstance(content, dict) and isinstance(content.get("data"), dict),
          "V030_PROVIDER_READ_ENVELOPE_INVALID")
    info, stored = metadata["data"], content["data"]
    _must(info.get("id") == gid and info.get("model") == model and
          info.get("finish_reason") == "stop" and
          isinstance(stored.get("input"), dict) and
          isinstance(stored.get("output"), dict) and
          stored["input"].get("messages") == request.get("messages"),
          "V030_PROVIDER_PROVENANCE_MISMATCH")
    answer = stored["output"].get("completion")
    _must(isinstance(answer, str) and answer.strip(),
          "V030_COMPLETION_CONTENT_NOT_STORED")
    try:
        cost = Decimal(str(info["total_cost"]))
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise CoverageError("V030_GENERATION_COST_UNAVAILABLE") from exc
    _must(cost.is_finite() and cost >= 0,
          "V030_GENERATION_COST_UNAVAILABLE")
    return {
        "error": None,
        "raw": {
            "id": gid, "model": model,
            "usage": {"cost": str(cost)},
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": answer},
            }],
        },
        "read_only_recovery": {
            "schema": SCHEMA,
            "request_sha256": sig,
            "generation_id": gid,
            "provider_read_operations": 2,
            "provider_post_operations": 0,
            "response_content_verified_against_source_messages": True,
            "canonical_commit_authorized": False,
            "world_db_writes": 0,
            "requires_manual_intervention": False,
        },
    }


def make_reconciler(*, api_key, binding_lookup, verify_binding,
                    get_generation=read_generation):
    def reconcile(*, model, request, request_sha256):
        _must(fingerprint(model=model, request=request) == request_sha256,
              "V030_RECOVERY_REQUEST_DIGEST_MISMATCH")
        return recover(
            model=model, request=request, api_key=api_key,
            binding_lookup=binding_lookup,
            verify_binding=verify_binding, get_generation=get_generation,
        )
    return reconcile
