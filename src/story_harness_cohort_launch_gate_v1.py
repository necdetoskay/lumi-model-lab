"""LUMI $20 ten-story cohort: signed intent and aggregate budget preflight.

OFFLINE ONLY. No model POST, no credential loading, no provider key fetch.
A valid Ed25519 signature is not, by itself, proof of human ownership:
the trusted public-key anchor must be provisioned independently out-of-band.
Old P4.x $10 grants cannot authorize the $20 cohort.
"""
from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from src.story_harness_p410 import canonical_json
from src.story_harness_frozen_cohort_v1 import (
    preflight, IDS, CAP, DOCUMENTED_RESERVATION, TRIAL_CAP
)
from src.story_harness_frozen_round_v1 import (
    simulate_seal, check_lock, COMPONENT_FILES
)
from src.story_harness_readiness_v1 import offline_readiness
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-cohort-launch-offline-preflight.v1"
GRANT_SCHEMA = "lumi.story-harness-cohort-ten-once-grant.v1"
RECONCILIATION_SCHEMA = "lumi.story-harness-cohort-aggregate-reconciliation.v1"
REG = re.compile(r"^lumi-ten-[a-z0-9]{6,28}$")
HEX = re.compile(r"^[a-f0-9]{64}$")
GRANT_FIELDS = {
    "schema", "purpose", "run_id", "round", "harness_commit",
    "harness_runtime_sha256", "cohort_seal_sha256",
    "case_input_sha256", "case_ids", "user_aggregate_cap_usd",
    "max_new_baseline_reserved_usd", "one_attempt_per_case",
    "no_mid_cohort_modification", "zero_model_retries",
    "memory_and_tools_locked", "same_model_and_prompt_per_case",
    "production_state_write_authorized", "issued_at", "expires_at",
}
SPENT_FIELDS = {
    "schema", "as_of_utc", "settled_total_usd", "previously_reserved_usd",
    "unknown_charge_hold_usd", "historical_budget_evidence_sha256",
    "all_existing_model_lab_key_spend_included",
    "other_spending_sources_excluded", "live_provider_reconciled",
    "externally_authenticated_by_finance_owner",
}
ALL_ROUNDS = 30
BASELINE = 10
REMAINING = 20

def must(condition, message):
    if not condition:
        raise HarnessStop("COHORT_LAUNCH_STOP_" + message)

def usd(value):
    must(type(value) is str and 1 <= len(value) <= 25,
         "INVALID_CURRENCY_FORMAT")
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError):
        raise HarnessStop("COHORT_LAUNCH_STOP_NON_DECIMAL_CURRENCY") from None
    must(amount.is_finite() and amount >= 0 and
         amount.as_tuple().exponent >= -6, "INVALID_CURRENCY")
    return amount

def utc(value):
    must(type(value) is str and value.endswith("Z") and
         len(value) <= 40, "BAD_UTC_TIME")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HarnessStop("COHORT_LAUNCH_STOP_BAD_UTC_TIME") from None
    must(result.utcoffset() == timedelta(0), "BAD_UTC_OFFSET")
    return result

def sha_obj(value):
    return hashlib.sha256(canonical_json(value)).hexdigest()

def grant_payload(*, repo_root=".", run_id, issued_at, expires_at):
    """Build an unsigned exact-scope preview. NEVER signs human approval."""
    policy = preflight(repo_root)
    lock = simulate_seal(repo_root)
    check_lock(repo_root, lock)
    must(type(run_id) is str and REG.fullmatch(run_id) is not None,
         "RUN_ID")
    must(utc(issued_at) < utc(expires_at), "TIME_ORDER")
    return {
        "schema": GRANT_SCHEMA,
        "purpose": "one_immutable_ten_case_baseline_no_mid_cohort_fixes",
        "run_id": run_id,
        "round": "BASELINE",
        "harness_commit": lock["harness_commit"],
        "harness_runtime_sha256": policy["case_matrix_sha256"] and
            lock["files_sha256"]["configs/story_harness_runtime_v1.json"],
        "cohort_seal_sha256": sha_obj(lock),
        "case_input_sha256": policy["case_input_sha256"],
        "case_ids": list(IDS),
        "user_aggregate_cap_usd": "20.00",
        "max_new_baseline_reserved_usd": format(BASELINE * TRIAL_CAP, "f"),
        "one_attempt_per_case": True,
        "no_mid_cohort_modification": True,
        "zero_model_retries": True,
        "memory_and_tools_locked": True,
        "same_model_and_prompt_per_case": True,
        "production_state_write_authorized": False,
        "issued_at": issued_at,
        "expires_at": expires_at,
    }

def verify_signed_cohort_intent(envelope, *, independently_trusted_public_key_b64,
                                now=None, repo_root="."):
    """Verify exact signed scope, still OFFLINE; does NOT authorize a POST."""
    must(type(envelope) is dict and set(envelope) ==
         {"payload", "signature_b64"}, "GRANT_ENVELOPE")
    p = envelope["payload"]
    must(type(p) is dict and set(p) == GRANT_FIELDS,
         "GRANT_FIELDS")
    must(type(independently_trusted_public_key_b64) is str and
         type(envelope["signature_b64"]) is str, "TRUST_KEY_MISSING")
    try:
        key = base64.b64decode(independently_trusted_public_key_b64, validate=True)
        sig = base64.b64decode(envelope["signature_b64"], validate=True)
    except (ValueError, binascii.Error):
        raise HarnessStop("COHORT_LAUNCH_STOP_BAD_SIGNED_ENCODING") from None
    must(len(key) == 32 and len(sig) == 64, "BAD_SIGNATURE_LENGTH")
    try:
        Ed25519PublicKey.from_public_bytes(key).verify(sig, canonical_json(p))
    except (InvalidSignature, ValueError):
        raise HarnessStop("COHORT_LAUNCH_STOP_UNTRUSTED_SIGNATURE") from None
    fresh = grant_payload(repo_root=repo_root, run_id=p["run_id"],
                          issued_at=p["issued_at"], expires_at=p["expires_at"])
    must(p == fresh, "SIGNED_SCOPE_OR_COHORT_DRIFT")
    if now is None:
        now = datetime.now(timezone.utc)
    must(isinstance(now, datetime) and now.tzinfo is not None and
         now.utcoffset() == timedelta(0), "UNTRUSTED_CLOCK")
    issued, expires = utc(p["issued_at"]), utc(p["expires_at"])
    must(issued <= now < expires and now - issued <= timedelta(minutes=15)
         and expires - issued <= timedelta(hours=12),
         "GRANT_EXPIRED_OR_EXCESSIVE_LIFETIME")
    return {
        "signature_mathematically_verified": True,
        "trust_anchor_out_of_band_required": True,
        "cohort_seal_sha256": p["cohort_seal_sha256"],
        "payload_sha256": sha_obj(p),
        "run_id": p["run_id"],
        "paid_calls_authorized": 0,
        "live_provider_post_allowed": False,
    }

def reconcile_cumulative_budget(snapshot, *, now=None):
    """Pure math over externally supplied figures; claims are not authenticated."""
    must(type(snapshot) is dict and set(snapshot) == SPENT_FIELDS,
         "RECONCILIATION_FIELDS")
    must(snapshot["schema"] == RECONCILIATION_SCHEMA and
         type(snapshot["all_existing_model_lab_key_spend_included"]) is bool and
         type(snapshot["other_spending_sources_excluded"]) is bool and
         type(snapshot["live_provider_reconciled"]) is bool and
         type(snapshot["externally_authenticated_by_finance_owner"]) is bool and
         type(snapshot["historical_budget_evidence_sha256"]) is str and
         HEX.fullmatch(snapshot["historical_budget_evidence_sha256"]),
         "RECONCILIATION_UNVERIFIED_SHAPE")
    if now is None:
        now = datetime.now(timezone.utc)
    stamp = utc(snapshot["as_of_utc"])
    must(timedelta(0) <= now - stamp <= timedelta(minutes=15),
         "STALE_FINANCIAL_OBSERVATION")
    settled = usd(snapshot["settled_total_usd"])
    held = usd(snapshot["previously_reserved_usd"])
    unknown = usd(snapshot["unknown_charge_hold_usd"])
    # Never reduce historical exposure below previously documented hold.
    prior = max(DOCUMENTED_RESERVATION, settled + held + unknown)
    baseline = BASELINE * TRIAL_CAP
    post_baseline = (ALL_ROUNDS - BASELINE) * TRIAL_CAP
    total = prior + baseline + post_baseline
    must(prior + baseline <= CAP, "BASELINE_UNDERFUNDED")
    must(total <= CAP, "THIRTY_CASE_ENVELOPE_UNDERFUNDED")
    externally_sufficient = all([
        snapshot["all_existing_model_lab_key_spend_included"],
        snapshot["other_spending_sources_excluded"],
        snapshot["live_provider_reconciled"],
        snapshot["externally_authenticated_by_finance_owner"],
        unknown == 0,
    ])
    return {
        "prior_conservative_exposure_usd": format(prior, "f"),
        "first_ten_reserved_usd": format(baseline, "f"),
        "next_twenty_planning_usd": format(post_baseline, "f"),
        "all_thirty_total_reserved_usd": format(total, "f"),
        "headroom_after_thirty_usd": format(CAP - total, "f"),
        "all_required_ledger_claims_asserted": externally_sufficient,
        "external_financial_attestation_independently_verified": False,
        "provider_charges_independently_fetched": False,
        "live_dispatch_authorized": False,
    }

def launch_readiness(*, repo_root=".", envelope=None,
                     independently_trusted_public_key_b64=None,
                     ledger_snapshot=None, now=None):
    """Report immutable dry gate without secrets/network/POST. ALWAYS BLOCKED."""
    policy = preflight(repo_root)
    original = offline_readiness(repo_root)
    locked = simulate_seal(repo_root)
    must(original["run_commit"] == locked["harness_commit"] and
         len(locked["component_sha256"]) == len(COMPONENT_FILES) == 11,
         "PARTIAL_RUNTIME_FREEZE")
    report = {
        "schema": SCHEMA,
        "status": "BLOCKED_AWAITING_VERIFIED_LIVE_GATES",
        "run_commit": locked["harness_commit"],
        "case_ids": list(IDS),
        "locked_harness_components": sorted(COMPONENT_FILES),
        "cohort_seal_sha256": sha_obj(locked),
        "budget_ceiling_usd": format(CAP, "f"),
        "baseline_reservation_usd": format(BASELINE * TRIAL_CAP, "f"),
        "signature_verified_offline": False,
        "budget_reconciliation_checked_offline": False,
        "new_real_provider_calls": 0,
        "paid_dispatch_authorized": False,
        "baseline_started": False,
        "production_writes_authorized": False,
        "blockers": [],
    }
    if envelope is None or not independently_trusted_public_key_b64:
        report["blockers"].append("EXTERNAL_SIGNED_COHORT_GRANT_MISSING")
    else:
        grant = verify_signed_cohort_intent(
            envelope, independently_trusted_public_key_b64=
            independently_trusted_public_key_b64,
            now=now, repo_root=repo_root)
        report["signature_verified_offline"] = grant[
            "signature_mathematically_verified"]
        report["grant_payload_sha256"] = grant["payload_sha256"]
    if ledger_snapshot is None:
        report["blockers"].append("AUTHENTICATED_LIVE_LEDGER_RECONCILIATION_MISSING")
    else:
        math = reconcile_cumulative_budget(ledger_snapshot, now=now)
        report["budget_reconciliation_checked_offline"] = True
        report["conditional_budget_math"] = math
        if not math["all_required_ledger_claims_asserted"]:
            report["blockers"].append("AGGREGATE_LEDGER_CLAIMS_NOT_SATISFIED")
    report["blockers"].extend([
        "LIVE_PROVIDER_KEY_EXCLUSIVITY_AND_CREDIT_NOT_VERIFIED",
        "EXTERNAL_LEDGER_AND_APPROVAL_TRUST_NOT_ESTABLISHED",
        "PAID_TEN_CASE_BATCH_EXECUTOR_NOT_QUALIFIED",
    ])
    must(report["paid_dispatch_authorized"] is False, "UNEXPECTED_LIVE_AUTH")
    return report

if __name__ == "__main__":
    import json
    print(json.dumps(launch_readiness(), sort_keys=True, ensure_ascii=False))
