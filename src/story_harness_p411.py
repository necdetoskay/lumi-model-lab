"""P4.11: independently signed ONE-run intent and guarded OpenRouter transport seam.

No configured trusted signing key, no provider token quote, no live dispatcher
authorization in this version. All tests use mock POST; never a paid model call.
"""
from __future__ import annotations

import base64
import copy
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from src.story_harness_p410 import (
    MODEL, PROVIDER, STAGES, ENDPOINT, request_preview, request_receipt,
    canonical_json, bounded_money,
)
from src.story_harness_p49 import STORY_SHA, SPINE, inspect, must
from src.story_harness_v1 import HarnessStop

GRANT_SCHEMA = "lumi.story-harness-p411-one-paid-attempt-grant.v1"
STAGE_BY_CLASS = {cls: stage for stage, (cls, _) in STAGES.items()}
OUTPUT_CAPS = {stage: cap for stage, (_, cap) in STAGES.items()}
RUN_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{3,47}$")
B64_PATTERN = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")
GRANT_FIELDS = {
    "schema", "run_id", "purpose", "story_sha256", "spine_sha256",
    "source_artifact_id", "model", "provider",
    "repair_first_span", "repair_last_span", "restricted_scope_acknowledged",
    "one_attempt_only", "max_calls", "max_repairs", "budget_usd",
    "issued_at", "expires_at", "human_approved",
}


def _decode_b64(value, *, size):
    must(type(value) is str and len(value) <= 128 and
         B64_PATTERN.fullmatch(value) is not None,
         "Malformed signature/public-key encoding")
    try:
        result = base64.b64decode(value, validate=True)
    except ValueError as exc:
        raise HarnessStop("Invalid signature/public-key encoding") from exc
    must(len(result) == size, "Invalid signature/public-key length")
    return result


def _time(value):
    must(type(value) is str and len(value) <= 40 and value.endswith("Z"),
         "Signed grant timestamps must be UTC Z")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HarnessStop("Invalid grant timestamp") from exc
    must(result.tzinfo is not None and result.utcoffset() == timedelta(0),
         "Grant timezone must be UTC")
    return result


def verify_one_time_grant(envelope, *, trusted_public_key_b64=None,
                          now=None, repo_root="."):
    """Validate Ed25519 over canonical exact payload; signer key is out-of-band.

    Caller MUST securely bind trusted_public_key_b64 to the human approver.
    A public key copied from the untrusted grant is NOT allowed.
    """
    must(type(envelope) is dict and set(envelope) == {"payload", "signature_b64"},
         "Grant envelope fields invalid")
    p = envelope["payload"]
    must(type(p) is dict and set(p) == GRANT_FIELDS, "Signed grant fields invalid")
    must(type(trusted_public_key_b64) is str and trusted_public_key_b64,
         "No configured external trusted human-approval key")
    key = _decode_b64(trusted_public_key_b64, size=32)
    signature = _decode_b64(envelope["signature_b64"], size=64)
    try:
        Ed25519PublicKey.from_public_bytes(key).verify(signature, canonical_json(p))
    except (ValueError, InvalidSignature) as exc:
        raise HarnessStop("Signature does not match trusted approval authority") from exc

    ready = inspect(repo_root=repo_root)
    expected = {
        "schema": GRANT_SCHEMA,
        "purpose": "one_real_bounded_story_quality_attempt",
        "story_sha256": STORY_SHA, "spine_sha256": SPINE,
        "source_artifact_id": ready["writer_artifact_id"],
        "model": MODEL, "provider": PROVIDER,
        "repair_first_span": "S167", "repair_last_span": "S203",
        "restricted_scope_acknowledged": True,
        "one_attempt_only": True, "max_calls": 3, "max_repairs": 1,
        "human_approved": True,
    }
    must(all(type(p.get(k)) is type(v) and p.get(k) == v
             for k, v in expected.items()), "Scope/source/authority grant mismatch")
    must(type(p["run_id"]) is str and RUN_PATTERN.fullmatch(p["run_id"]) is not None,
         "Invalid signed run ID")
    amount = bounded_money(p["budget_usd"])
    issued, expires = _time(p["issued_at"]), _time(p["expires_at"])
    if now is None:
        now = datetime.now(timezone.utc)
    must(isinstance(now, datetime) and now.tzinfo is not None and
         now.utcoffset() == timedelta(0), "Validation clock must be UTC")
    must(issued <= now < expires and
         expires - issued <= timedelta(minutes=20) and
         now - issued <= timedelta(minutes=20),
         "Grant expired/not yet active/oversized lifetime")
    return {
        "schema": "lumi.story-harness-p411-verified-grant.v1",
        "run_id": p["run_id"], "story_sha256": STORY_SHA,
        "budget_usd": format(amount, "f"),
        "grant_sha256": hashlib.sha256(canonical_json(p)).hexdigest(),
        "external_approval_key_sha256": hashlib.sha256(key).hexdigest(),
        "restricted_scope_acknowledged": True,
        "maximum_dispatch_attempts": 3, "maximum_repairs": 1,
        "signed_grant_verified": True,
        "provider_pricing_verified": False,
        "provider_token_upper_bound_verified": False,
        "provider_dispatch_authorized": False,
    }


def validate_callback(kwargs, *, repo_root):
    """Pin original v21 callback arguments without ever retaining its API key."""
    must(type(kwargs) is dict and set(kwargs) == {
        "api_key", "model", "system_prompt", "user_prompt", "temperature",
        "max_tokens", "seed", "request_class", "schema_name", "schema",
    }, "Original v21 callback signature changed")
    must(type(kwargs["api_key"]) is str, "Invalid API key type")
    stage = STAGE_BY_CLASS.get(kwargs["request_class"])
    must(stage is not None, "Unexpected stage callback")
    sanitized = dict(kwargs)
    sanitized["api_key"] = ""
    preview = request_preview(repo_root=repo_root, stage=stage,
                              callback_kwargs=sanitized)
    return stage, preview


class OneAttemptLedger:
    """Offline verified-grant reservation boundary; no real provider permission.

    Writes 0600 O_EXCL intent BEFORE any injected transport. No retry/reclaim.
    Sequential stages only. All receipts omit story prose, credentials and raw
    provider bodies. Filesystem permissions alone are not a tamper-proof store.
    """
    def __init__(self, root, verified_grant):
        must(type(verified_grant) is dict and
             verified_grant.get("schema") == "lumi.story-harness-p411-verified-grant.v1"
             and verified_grant.get("signed_grant_verified") is True
             and verified_grant.get("provider_dispatch_authorized") is False,
             "Not a source-bound externally signed test grant")
        supplied_root = Path(root).absolute()
        must(not any(p.is_symlink() for p in (supplied_root, *supplied_root.parents)),
             "Untrusted ledger root symlink")
        self.root = supplied_root.resolve(strict=True)
        must(self.root.is_dir(),
             "Untrusted ledger root")
        must(type(verified_grant.get("run_id")) is str and
             RUN_PATTERN.fullmatch(verified_grant["run_id"]) is not None,
             "Invalid ledger run ID")
        self.grant = copy.deepcopy(verified_grant)
        self.budget = bounded_money(verified_grant["budget_usd"])
        self.dir = self.root / verified_grant["run_id"]
        self.dir.mkdir(mode=0o700, exist_ok=False)
        self.reserved = Decimal("0")
        self.actual = Decimal("0")
        self.stages = []
        self.settled = []
        self.halted = False
        self.pending = None
        self._write_once("grant-consumed.json", {
            "schema": "lumi.story-harness-p411-local-claim.v1",
            "run_id": verified_grant["run_id"],
            "story_sha256": STORY_SHA,
            "grant_sha256": verified_grant["grant_sha256"],
            "signed_grant_verified": True,
            "provider_dispatch_authorized": False,
            "simulated_only": True,
        })
        self._sync_directory(self.root)

    @staticmethod
    def _sync_directory(path):
        # POSIX directory fsync persists O_EXCL names as well as file contents.
        # Windows requires deployment-specific ACL/storage qualification for live use.
        if os.name == "posix":
            fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)

    def _write_once(self, filename, receipt):
        path = self.dir / filename
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(canonical_json(receipt) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        self._sync_directory(self.dir)

    def consume_stage(self, stage, request, *, declared_input_ceiling_tokens, wire_body=None):
        must(not self.halted and self.stages == self.settled,
             "Unsettled/failed prior attempt; no further dispatch")
        must(stage in STAGES and len(self.stages) < 3 and
             stage not in self.stages, "Duplicate/unbounded stage")
        must((not self.stages and stage == "INITIAL_AUDIT") or
             (self.stages == ["INITIAL_AUDIT"] and
                 stage == "SCENE_REPAIR") or
             (self.stages == ["INITIAL_AUDIT", "SCENE_REPAIR"] and
                 stage == "FINAL_AUDIT"),
             "Invalid stage order, cannot retry")
        receipt = request_receipt(request, declared_input_ceiling_tokens)
        must(receipt["stage"] == stage
             and receipt["input_ceiling_provider_verified"] is False
             and receipt["request_time_provider_price_verified"] is False
             and receipt["live_dispatch_allowed"] is False,
             "Unexpected source or fabricated provider verification")
        exposure = bounded_money(receipt["conditional_exposure_usd"])
        default_wire = copy.deepcopy(request["body"])
        default_wire["provider"]["max_price"] = {"prompt": 2, "completion": 10}
        if wire_body is None:
            wire_body = default_wire
        else:
            # The only offline alternative is omission of temperature=0;
            # never admit arbitrary model, schema, prompt or routing changes.
            omitted = copy.deepcopy(default_wire)
            must(omitted.pop("temperature", None) == 0.0
                 and wire_body == omitted,
                 "Only exact temperature omission may change paid wire preview")
        must(self.reserved + exposure <= self.budget,
             "Signed total budget exceeded before dispatch")
        row = {
            "schema": "lumi.story-harness-p411-offline-stage-reservation.v1",
            "run_id": self.grant["run_id"], "stage": stage,
            "body_sha256": hashlib.sha256(canonical_json(wire_body)).hexdigest(),
            "source_sha256": STORY_SHA,
            "estimated_reserved_usd": format(exposure, "f"),
            "cumulative_estimated_usd": format(self.reserved + exposure, "f"),
            "provider_dispatch_count": 0,
            "actual_request_tokens_verified": False,
            "provider_pricing_verified": False,
            "simulated_only": True,
        }
        self._write_once(f"{len(self.stages)+1:02d}-{stage.lower()}.json", row)
        self.reserved += exposure
        self.stages.append(stage)
        self.pending = {"stage": stage, "exposure": exposure,
                        "input_cap": declared_input_ceiling_tokens,
                        "output_cap": OUTPUT_CAPS[stage], "body_sha256": row["body_sha256"]}
        return row

    def record_outcome(self, stage, *, usage=None, valid_response=False):
        """Persist redacted actual cost or UNKNOWN before allowing another stage.

        Reservations are never released; any uncertain result permanently stops
        this attempt. A new process cannot reclaim the already-created run ID.
        This remains a local simulation store, not externally trusted accounting.
        """
        must(not self.halted and self.pending is not None and
             self.pending["stage"] == stage, "No pending stage to settle")
        self.halted = True  # disk/validation failures also poison this attempt
        pending = self.pending
        cost, prompt, completion = None, None, None
        if type(usage) is dict:
            try:
                value = usage.get("cost")
                if type(value) in (str, int, float, Decimal):
                    parsed = Decimal(str(value))
                    if parsed.is_finite() and parsed >= 0:
                        cost = parsed
            except (InvalidOperation, ValueError):
                pass
            prompt, completion = usage.get("prompt_tokens"), usage.get("completion_tokens")
        tokens_valid = (type(prompt) is int and type(completion) is int
                        and 0 <= prompt <= pending["input_cap"]
                        and 0 <= completion <= pending["output_cap"])
        cumulative = self.actual + cost if cost is not None else None
        ok = (valid_response and tokens_valid and cost is not None
              and cost <= pending["exposure"] and cumulative <= self.budget)
        self._write_once(f"{len(self.stages):02d}-{stage.lower()}-outcome.json", {
            "schema": "lumi.story-harness-p412-offline-outcome.v1",
            "run_id": self.grant["run_id"], "stage": stage,
            "body_sha256": pending["body_sha256"],
            "status": "SETTLED" if ok else "STOP_UNKNOWN_OR_INVALID",
            "reported_cost_usd": format(cost, "f") if cost is not None else None,
            "cumulative_reported_usd": format(cumulative, "f") if cumulative is not None else None,
            "prompt_tokens": prompt if type(prompt) is int and prompt >= 0 else None,
            "completion_tokens": completion if type(completion) is int and completion >= 0 else None,
            "simulated_only": True, "provider_dispatch_authorized": False,
        })
        must(ok, "Unsettled/invalid usage or response; attempt stopped, no retry")
        self.actual = cumulative
        self.settled.append(stage)
        self.pending = None
        self.halted = False


def guarded_adapter_once(*, callback_kwargs, ledger, repo_root,
                         declared_input_ceiling_tokens, fake_post=None,
                         p413_catalog=None, p413_sampling_ack=False):
    """Exercise real adapter's request/response contract using FAKE POST only.

    Deliberate lack of a default network transport makes this impossible to
    use as a billable runner; a distinct reviewed live dispatch is required.
    """
    must(callable(fake_post) and
         ledger.grant["provider_dispatch_authorized"] is False,
         "P4.11 prohibits live transport")
    stage, preview = validate_callback(callback_kwargs, repo_root=repo_root)
    if p413_catalog is not None or p413_sampling_ack:
        must(p413_catalog is not None,
             "P4.13 sampling acknowledgement requires explicit provider catalog")
        # Dynamic import avoids circular dependency. The trust boundary is
        # still FAKE POST only; no original frozen adapter was changed.
        from src.story_harness_p413 import adapt_wire
        body, _disclosure = adapt_wire(
            preview=preview, catalog=p413_catalog,
            allow_sampling_semantics_change=p413_sampling_ack,
        )
    else:
        body = copy.deepcopy(preview["body"])
        body["provider"]["max_price"] = {"prompt": 2, "completion": 10}
    ledger.consume_stage(stage, preview,
                         declared_input_ceiling_tokens=declared_input_ceiling_tokens,
                         wire_body=body)
    try:
        response = fake_post(
            endpoint=ENDPOINT, headers={"Content-Type": "application/json"},
            body=body, stage=stage,
        )
    except Exception as exc:
        try:
            ledger.record_outcome(stage)
        except HarnessStop:
            pass
        raise HarnessStop("Provider transport unknown; intent consumed, no retry") from None
    try:
        result = _parse_fake_response(response, body, ledger)
    except Exception:
        try:
            ledger.record_outcome(stage, usage=(response.get("usage")
                                  if type(response) is dict else None))
        except HarnessStop:
            pass
        raise
    ledger.record_outcome(stage, usage=response["usage"], valid_response=True)
    return result


def _parse_fake_response(response, body, ledger):
    must(type(response) is dict
         and response.get("model") == MODEL
         and type(response.get("usage")) is dict
         and type(response["usage"].get("prompt_tokens")) is int
         and type(response["usage"].get("completion_tokens")) is int
         and response["usage"]["prompt_tokens"] >= 0
         and response["usage"]["completion_tokens"] >= 0,
         "Incomplete provider result; no retry")
    try:
        cost = Decimal(str(response["usage"]["cost"]))
    except (KeyError, ValueError, TypeError, InvalidOperation) as exc:
        raise HarnessStop("Missing actual usage/cost, no retry") from exc
    must(cost.is_finite() and cost >= 0 and
         cost <= ledger.budget, "Reported usage cost invalid/over approved total")
    choices = response.get("choices")
    must(type(choices) is list and len(choices) == 1 and
         type(choices[0].get("message", {}).get("content")) is str,
         "Provider returned invalid structured response")
    try:
        raw = json.loads(choices[0]["message"]["content"])
    except (ValueError, TypeError) as exc:
        raise HarnessStop("Malformed JSON response, no retry") from exc
    must(type(raw) is dict, "Structured response must be JSON object")
    # Original v21 adapter still owns strict schema/semantic verification.
    return raw, response, {
        "max_tokens": body["max_tokens"],
        "temperature": body.get("temperature"),
        "response_format": body["response_format"],
    }, []


def live_paid_dispatch(*args, **kwargs):
    raise HarnessStop("P411_PAID_DISPATCH_DISABLED_NO_VERIFIED_PROVIDER_TOKENS_OR_USER_GRANT")


def inspect_status(*, repo_root):
    p = inspect(repo_root=repo_root)
    return {
        "schema": "lumi.story-harness-p411-signed-grant-and-adapter.v1",
        "story_sha256": p["story_sha256"],
        "approved_spine_sha256": p["approved_spine_hash"],
        "writer_segments": p["full_story_segment_count"],
        "signed_grant_verifier_available": True,
        "external_trusted_human_key_configured": False,
        "provider_price_cap_shape": {"prompt": 2, "completion": 10},
        "provider_token_count_verified": False,
        "authentic_live_provider_route_verified": False,
        "real_paid_dispatch_possible": False,
        "fake_post_contract_available": True,
        "new_api_calls": 0, "new_api_cost_usd": "0",
        "story_quality_accepted": False,
        "english_master_authorized": False,
        "q25_authorized": False, "state_write_authorized": False,
        "stop_reason": "P411_SIGNED_GRANT_OFFLINE_TRANSPORT_ONLY_LIVE_STOP",
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    print(json.dumps(inspect_status(repo_root=args.repo_root),
                     ensure_ascii=False, sort_keys=True, indent=2))
