"""Read-only paid-dispatch preflight. Public metadata GET only; never model POST.

Catalog observations are not a token quote, user consent, or a spending cap.
Reuse P4.11 signature verification and accounting instead of another runner.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import urllib.request

from src.story_harness_p410 import MODEL, PROVIDER, STAGES, canonical_json
from src.story_harness_p411 import verify_one_time_grant
from src.story_harness_p49 import inspect, must
from src.story_harness_v1 import HarnessStop

CATALOG_URL = f"https://openrouter.ai/api/v1/models/{MODEL}/endpoints"
REQUIRED_PARAMETERS = {"temperature", "max_tokens", "response_format", "structured_outputs"}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HarnessStop("Catalog redirect refused")


def fetch_catalog():
    """One bounded HTTPS GET, default certificate validation, no keys or retries."""
    request = urllib.request.Request(CATALOG_URL, method="GET",
                                     headers={"Accept": "application/json"})
    try:
        with urllib.request.build_opener(_NoRedirect()).open(request, timeout=20) as reply:
            must(reply.status == 200 and reply.geturl() == CATALOG_URL,
                 "Unexpected catalog response")
            raw = reply.read(1_000_001)
            must(len(raw) <= 1_000_000, "Oversized catalog response")
        return json.loads(raw)
    except HarnessStop:
        raise
    except Exception:
        raise HarnessStop("Public provider catalog unavailable; no dispatch") from None


def _price(value):
    must(type(value) is str and len(value) < 40, "Missing decimal catalog price")
    try:
        price = Decimal(value)
    except InvalidOperation:
        raise HarnessStop("Invalid catalog price") from None
    must(price.is_finite() and 0 <= price <= 1, "Nonfinite/invalid catalog price")
    return price


def analyze_catalog(catalog):
    """Pure analysis; supplied JSON cannot assert authenticated provenance."""
    must(type(catalog) is dict and type(catalog.get("data")) is dict,
         "Invalid provider catalog")
    data = catalog["data"]
    must(data.get("id") == MODEL and type(data.get("endpoints")) is list,
         "Wrong catalog model")
    routes = [r for r in data["endpoints"] if type(r) is dict and
              r.get("provider_name") == PROVIDER and r.get("tag") == "anthropic"]
    must(len(routes) == 1, "Missing/ambiguous exact Anthropic route")
    route = routes[0]
    must(route.get("model_id") == MODEL and type(route.get("status")) is int
         and route["status"] == 0, "Wrong/unavailable provider route")
    params = route.get("supported_parameters")
    must(type(params) is list and all(type(p) is str for p in params),
         "Missing provider parameter support")
    prices = route.get("pricing")
    must(type(prices) is dict, "Missing route pricing")
    prompt, completion = _price(prices.get("prompt")), _price(prices.get("completion"))
    must(prompt > 0 and completion > 0, "Unexpected free route")
    context, output = route.get("context_length"), route.get("max_completion_tokens")
    must(type(context) is int and context > 0 and type(output) is int and output > 0,
         "Missing route token limits")
    blockers = []
    missing = sorted(REQUIRED_PARAMETERS - set(params))
    if missing:
        blockers.append("UNSUPPORTED_REQUEST_PARAMETERS:" + ",".join(missing))
    if prompt > Decimal("0.000002") or completion > Decimal("0.00001"):
        blockers.append("ROUTE_PRICE_EXCEEDS_EXISTING_MAX_PRICE")
    if output < max(cap for _, cap in STAGES.values()):
        blockers.append("PROVIDER_OUTPUT_LIMIT_TOO_SMALL")
    # Catalog context capacity is not the actual request's billed token ceiling.
    return {
        "model": MODEL, "provider": PROVIDER, "route_tag": "anthropic",
        "catalog_sha256": hashlib.sha256(canonical_json(catalog)).hexdigest(),
        "prompt_usd_per_million": format(prompt * 1_000_000, "f"),
        "completion_usd_per_million": format(completion * 1_000_000, "f"),
        "context_length": context, "max_completion_tokens": output,
        "missing_request_parameters": missing, "blockers": blockers,
        "request_input_tokens_verified": False,
        "catalog_context_is_request_token_quote": False,
    }


def preflight(*, repo_root=".", refresh_provider=False, envelope=None,
              trusted_public_key_b64=None):
    """Reverify original signed envelope now, never trust a verified-grant dict.

    The key must be supplied by the operator's out-of-band trust configuration.
    This read-only check does not consume a grant or reserve money.
    """
    source = inspect(repo_root=repo_root)
    blockers = ["PAID_DISPATCH_DISABLED", "NO_VERIFIED_BILLED_INPUT_TOKEN_CEILING",
                "LIVE_ACCOUNTING_STORE_NOT_PROVISIONED"]
    grant = None
    if envelope is None:
        blockers.extend(["NO_EXTERNALLY_AUTHENTICATED_USER_GRANT",
                         "RESTRICTED_S167_S203_SCOPE_NOT_USER_REAPPROVED"])
    else:
        grant = verify_one_time_grant(envelope, repo_root=repo_root,
                                     trusted_public_key_b64=trusted_public_key_b64)
    catalog = None
    if refresh_provider:
        catalog = analyze_catalog(fetch_catalog())
        blockers.extend(catalog["blockers"])
    else:
        blockers.append("CURRENT_PROVIDER_CATALOG_NOT_FETCHED")
    return {
        "schema": "lumi.story-harness-p412-preflight.v1",
        "status": "BLOCKED", "story_sha256": source["story_sha256"],
        "catalog": catalog, "catalog_observed_at": (
            datetime.now(timezone.utc).isoformat() if refresh_provider else None),
        "catalog_source": CATALOG_URL if refresh_provider else None,
        "catalog_transport": "HTTPS_GET" if refresh_provider else None,
        "grant_signature_verified": grant is not None,
        "grant_consumed": False,
        "authorized_budget_usd": grant["budget_usd"] if grant else None,
        "request_token_quote_verified": False,
        "provider_dispatch_authorized": False,
        "story_quality_accepted": False,
        "english_master_authorized": False, "q25_authorized": False,
        "state_write_authorized": False,
        "blockers": blockers,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--refresh-provider", action="store_true",
                        help="One free public metadata GET; no model request")
    args = parser.parse_args()
    try:
        report = preflight(repo_root=args.repo_root, refresh_provider=args.refresh_provider)
    except HarnessStop as exc:
        report = {"status": "BLOCKED", "provider_dispatch_authorized": False,
                  "blockers": [str(exc)]}
    print(json.dumps(report, sort_keys=True, indent=2))
    raise SystemExit(2)
