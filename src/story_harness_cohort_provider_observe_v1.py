"""Read-only OpenRouter isolated-key readiness for LUMI Frozen Cohort.

No provider POST, no paid model, no secrets in output. This code does not
establish financial approval or key exclusivity merely because a key GET
succeeds. Requires a separately provisioned NEW isolated inference key.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import os

from src.story_harness_p414 import read_current_key
from src.story_harness_p412 import fetch_catalog, analyze_catalog
from src.story_harness_cohort_launch_gate_v1 import utc, usd, must
from src.story_harness_frozen_cohort_v1 import TRIAL_CAP, CAP
from src.story_harness_p417_live_pilot import MODEL, PROVIDER
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-cohort-key-read-only-v1"
KEY_ENV = "LUMI_STORY_COHORT_ISOLATED_OPENROUTER_KEY"
BASELINE_KEY_CAP = Decimal("4.40")

def analyze_isolated_key(snapshot, *, now=None):
    """Untrusted supplied metadata; validates the desired fresh key shape."""
    must(type(snapshot) is dict and type(snapshot.get("data")) is dict,
         "PROVIDER_KEY_ENVELOPE")
    row = snapshot["data"]
    must(type(row.get("is_management_key")) is bool and
         row["is_management_key"] is False and
         row.get("is_provisioning_key") is False and
         row.get("is_free_tier") is False and
         row.get("include_byok_in_limit") is True and
         "limit_reset" in row and row["limit_reset"] is None,
         "KEY_NOT_ISOLATED_INFERENCE")
    lim = usd(str(row.get("limit")))
    left = usd(str(row.get("limit_remaining")))
    used = usd(str(row.get("usage")))
    byok = usd(str(row.get("byok_usage")))
    must(lim == BASELINE_KEY_CAP and left == BASELINE_KEY_CAP and
         used == 0 and byok == 0,
         "KEY_NOT_FRESH_EXACT_LIMIT")
    if now is None:
        now = datetime.now(timezone.utc)
    must(now.utcoffset() == timedelta(0), "CLOCK_NOT_UTC")
    expires = row.get("expires_at")
    if expires is not None:
        must(utc(expires) >= now + timedelta(hours=3), "KEY_EXPIRES_DURING_BATCH")
    # Values here are redacted; raw response, key identity and labels omitted.
    return {
        "schema": SCHEMA,
        "provider": "openrouter",
        "expected_model": MODEL,
        "expected_upstream": PROVIDER,
        "key_fresh_limited_nonresetting": True,
        "configured_limit_usd": format(lim, "f"),
        "remaining_limit_usd": format(left, "f"),
        "baseline_total_reserved_usd": format(10 * TRIAL_CAP, "f"),
        "key_exclusivity_independently_proven": False,
        "real_live_key_provenance": False,
        "provider_dispatch_authorized": False,
        "real_model_calls": 0,
    }

def observe_provider_read_only(*, api_key, now=None, key_fetch=None,
                               catalog_fetch=None):
    """Explicit 2 GETs only; fake injected GET callbacks remain UNAUTHENTICATED."""
    must(type(api_key) is str and api_key.startswith("sk-or-") and
         len(api_key) <= 256 and not any(c.isspace() for c in api_key),
         "ISOLATED_KEY_MISSING")
    key_fetch = key_fetch or read_current_key
    catalog_fetch = catalog_fetch or fetch_catalog
    snapshot = key_fetch(api_key=api_key)
    key = analyze_isolated_key(snapshot, now=now)
    catalog = analyze_catalog(catalog_fetch())
    must(type(catalog["blockers"]) is list and
         not catalog["blockers"] and
         catalog["model"] == MODEL and
         catalog["provider"] == PROVIDER and
         Decimal(catalog["max_completion_tokens"]) >= 6500,
         "LIVE_MODEL_ROUTE_NOT_QUALIFIED")
    key["catalog_sha256"] = catalog["catalog_sha256"]
    key["catalog_route_parameter_blockers"] = catalog["blockers"]
    key["key_get_attempted"] = True
    key["catalog_get_attempted"] = True
    key["real_live_key_provenance"] = (
        key_fetch is read_current_key and catalog_fetch is fetch_catalog
    )
    # Caller still cannot assume that some *other* workflow is not using the
    # same key; signed approval, aggregate spent reconciliation and key owner
    # attestation are separate necessities.
    key["provider_dispatch_authorized"] = False
    return key

def offline_status():
    return {
        "schema": SCHEMA,
        "status": "WAITING_FOR_DEDICATED_COHORT_KEY_AND_EXTERNAL_LEDGER",
        "required_secret_name": KEY_ENV,
        "new_10_case_key_limit_usd": "4.40",
        "live_key_observed": False,
        "paid_model_calls": 0,
        "provider_dispatch_authorized": False,
    }

if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-get-only", action="store_true",
                        help="Observe a dedicated key and public route via GET only")
    args = parser.parse_args()
    if not args.live_get_only:
        print(json.dumps(offline_status(), sort_keys=True))
    else:
        secret = os.environ.get(KEY_ENV, "")
        must(bool(secret), "DEDICATED_SECRET_NOT_CONFIGURED")
        report = observe_provider_read_only(api_key=secret)
        print(json.dumps(report, sort_keys=True, ensure_ascii=False))
