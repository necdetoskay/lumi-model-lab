"""P4.14 OpenRouter current-key spend-limit verification. NEVER model dispatch.

Read-only GET /api/v1/key and source-bound independently signed grant validation.
Metadata alone cannot prove exclusive ownership or a guaranteed per-request cap.
No API key creation, update, browser login, completion POST or ledger mutation.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
import json
import urllib.request

from src.story_harness_p411 import verify_one_time_grant
from src.story_harness_p49 import STORY_SHA, inspect, must
from src.story_harness_v1 import HarnessStop

KEY_URL = "https://openrouter.ai/api/v1/key"
MAX_REPLY_BYTES = 32768
SCHEMA = "lumi.story-harness-p414-key-limit-observation.v1"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HarnessStop("Current-key introspection redirect refused")


def read_current_key(*, api_key, opener=None):
    """One authenticated GET only, TLS verification by system default.

    Do not pass management keys or log full raw response/Authorization.
    Tests inject a fake opener, but that does NOT attest live key provisioning.
    """
    must(type(api_key) is str and api_key.startswith("sk-or-") and
         len(api_key) <= 256 and not any(ch.isspace() for ch in api_key),
         "Missing or malformed isolated OpenRouter inference key")
    req = urllib.request.Request(
        KEY_URL, method="GET",
        headers={"Authorization": "Bearer " + api_key,
                 "Accept": "application/json"},
    )
    try:
        with (opener or urllib.request.build_opener(_NoRedirect())).open(
            req, timeout=12
        ) as reply:
            must(reply.status == 200 and reply.geturl() == KEY_URL,
                 "Unexpected current-key HTTPS status/URL")
            raw = reply.read(MAX_REPLY_BYTES + 1)
            must(len(raw) <= MAX_REPLY_BYTES,
                 "Oversized key metadata response")
        body = json.loads(raw)
        must(type(body) is dict and type(body.get("data")) is dict,
             "Invalid current-key response shape")
        return body
    except HarnessStop:
        raise
    except Exception:
        # No error body, response headers, URL with credentials or exception
        # traces are allowed in failure receipts.
        raise HarnessStop("Authenticated current-key metadata unavailable; no dispatch") from None


def money(value, field):
    must(type(value) in (int, float, str, Decimal)
         and type(value) is not bool and len(str(value)) <= 32,
         "Missing/invalid current-key " + field)
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise HarnessStop("Non-decimal current-key " + field) from exc
    must(n.is_finite() and n >= 0 and n <= Decimal("1000000"),
         "Nonfinite/negative current-key " + field)
    return n


def analyze_key_metadata(snapshot, *, signed_budget_usd, now=None):
    """Analyze current-key response WITHOUT claiming it was fetched live."""
    must(type(snapshot) is dict and type(snapshot.get("data")) is dict,
         "Invalid provider current-key metadata envelope")
    data = snapshot["data"]
    grant_limit = money(signed_budget_usd, "signed_budget_usd")
    must(Decimal("0") < grant_limit <= Decimal("1"),
         "Invalid signed-budget upper bound")
    limit = money(data.get("limit"), "limit")
    remain = money(data.get("limit_remaining"), "limit_remaining")
    usage = money(data.get("usage"), "usage")
    byok = money(data.get("byok_usage"), "byok_usage")
    must(data.get("is_management_key") is False
         and data.get("is_provisioning_key") is False
         and data.get("is_free_tier") is False,
         "Not a standalone paid inference key")
    must(data.get("limit_reset", "MISSING") is None,
         "Resettable/missing key limit forbidden for one paid attempt")
    must(data.get("include_byok_in_limit") is True,
         "BYOK spend not included in limited-key budget")
    must(Decimal("0") < limit <= grant_limit
         and remain == limit and usage == 0 and byok == 0,
         "Key not fresh/dedicated or exceeds signed budget")
    if now is None:
        now = datetime.now(timezone.utc)
    must(isinstance(now, datetime) and now.tzinfo is not None
         and now.utcoffset() == timedelta(0), "Non-UTC verification clock")
    expiry = data.get("expires_at")
    if expiry is not None:
        must(type(expiry) is str and expiry.endswith("Z") and len(expiry) <= 40,
             "Invalid inference key expiry")
        try:
            expires = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HarnessStop("Malformed inference key expiry") from exc
        must(expires > now + timedelta(minutes=20),
             "Inference key expires too soon")
    # Neither the raw key, the hash, its label nor account identifiers are
    # copied into the persisted report.
    return {
        "schema": SCHEMA,
        "source_story_sha256": STORY_SHA,
        "configured_key_limit_usd": format(limit, "f"),
        "remaining_key_limit_usd": format(remain, "f"),
        "observed_key_usage_usd": format(usage, "f"),
        "observed_byok_usage_usd": format(byok, "f"),
        "key_limit_reset": None,
        "byok_included_in_limit": True,
        "key_type": "non_management_inference",
        "key_policy_structurally_valid": True,
        "authenticated_live_provider_observation": False,
        "user_key_provisioned_by_project": False,
        "exclusivity_and_inflight_spend_guaranteed": False,
        "external_human_grant_consumed": False,
        "live_dispatch_allowed": False,
    }


def validate_signed_key_preflight(*, repo_root, envelope,
                                  trusted_public_key_b64,
                                  api_key, opener=None, now=None):
    """Read a key only AFTER independently verifying the exact original grant.

    Even a valid grant and genuine authenticated metadata are INSUFFICIENT to
    permit live dispatch: sampling exception, token quote, single-use authority
    and in-flight spending bounds are not proven by this function.
    """
    ready = inspect(repo_root=repo_root)
    grant = verify_one_time_grant(
        envelope, trusted_public_key_b64=trusted_public_key_b64,
        now=now, repo_root=repo_root,
    )
    must(grant["story_sha256"] == ready["story_sha256"] == STORY_SHA
         and grant["signed_grant_verified"] is True
         and grant["provider_dispatch_authorized"] is False,
         "Signed approval or story integrity unavailable")
    snapshot = read_current_key(api_key=api_key, opener=opener)
    result = analyze_key_metadata(
        snapshot, signed_budget_usd=grant["budget_usd"], now=now,
    )
    # No caller-visible raw usage metadata or bearer secret. Mock openers used
    # by unit tests cannot be interpreted as live provider authentication.
    result["external_grant_signature_verified"] = True
    result["grant_sha256"] = grant["grant_sha256"]
    result["live_metadata_path_exercised"] = opener is None
    result["authenticated_live_provider_observation"] = opener is None
    result["provider_dispatch_authorized"] = False
    result["stop_reason"] = "P414_AUTHENTICATED_KEY_OBSERVATION_NOT_LIVE_DISPATCH"
    return result


def status(*, repo_root):
    source = inspect(repo_root=repo_root)
    return {
        "schema": SCHEMA,
        "source_story_sha256": source["story_sha256"],
        "current_key_endpoint": KEY_URL,
        "key_management_mutations_supported": False,
        "read_only_key_metadata_verifier_implemented": True,
        "key_provisioned": False,
        "key_limit_verified_on_user_account": False,
        "external_trust_anchor_provisioned": False,
        "authenticated_signed_user_grant_consumed": False,
        "non_equivalent_temperature_change_user_approved": False,
        "authoritative_request_token_ceiling_verified": False,
        "independent_live_spending_lock_provisioned": False,
        "live_dispatch_allowed": False,
        "model_calls": 0,
        "api_cost_usd": "0",
        "story_quality_accepted": False,
        "english_master_authorized": False,
        "q25_authorized": False,
        "state_write_authorized": False,
        "stop_reason": "P414_USER_KEY_LIMIT_AND_GRANT_NOT_PROVISIONED_LIVE_STOP",
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    options = parser.parse_args()
    print(json.dumps(status(repo_root=options.repo_root),
                     ensure_ascii=False, sort_keys=True, indent=2))
