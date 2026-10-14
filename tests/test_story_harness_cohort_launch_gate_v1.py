"""$20 aggregate cohort launch guard: offline crypto and budget negatives."""
import base64
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from src.story_harness_cohort_launch_gate_v1 import (
    GRANT_SCHEMA, RECONCILIATION_SCHEMA, launch_readiness,
    grant_payload, verify_signed_cohort_intent, reconcile_cumulative_budget
)
from src.story_harness_p410 import canonical_json
from src.story_harness_v1 import HarnessStop

NOW = datetime(2026, 10, 14, 19, 45, tzinfo=timezone.utc)
def stamp(n):
    return (NOW + timedelta(minutes=n)).isoformat().replace("+00:00", "Z")
def fake_ledger(**overrides):
    d = {
        "schema": RECONCILIATION_SCHEMA,
        "as_of_utc": stamp(0),
        "settled_total_usd": "1.000000",
        "previously_reserved_usd": "2.249558",
        "unknown_charge_hold_usd": "0",
        "historical_budget_evidence_sha256": "a" * 64,
        "all_existing_model_lab_key_spend_included": True,
        "other_spending_sources_excluded": True,
        "live_provider_reconciled": True,
        "externally_authenticated_by_finance_owner": True,
    }
    d.update(overrides)
    return d

class LaunchGateTests(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        self.key = base64.b64encode(self.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw)).decode()
        self.payload = grant_payload(repo_root=".",
                run_id="lumi-ten-offline99", issued_at=stamp(-1),
                expires_at=stamp(50))
    def envelope(self, payload=None):
        p = self.payload if payload is None else payload
        return {"payload": p, "signature_b64":
                base64.b64encode(self.private.sign(canonical_json(p))).decode()}
    def test_no_grant_or_provider_calls_by_default(self):
        report = launch_readiness(repo_root=".")
        self.assertEqual(report["status"], "BLOCKED_AWAITING_VERIFIED_LIVE_GATES")
        self.assertEqual(len(report["case_ids"]), 10)
        self.assertEqual(len(report["locked_harness_components"]), 11)
        self.assertEqual(report["new_real_provider_calls"], 0)
        self.assertFalse(report["paid_dispatch_authorized"])
        self.assertIn("EXTERNAL_SIGNED_COHORT_GRANT_MISSING", report["blockers"])
    def test_exact_signed_scope_binds_input_harness_and_zero_fix(self):
        r = verify_signed_cohort_intent(self.envelope(),
            independently_trusted_public_key_b64=self.key,now=NOW)
        self.assertTrue(r["signature_mathematically_verified"])
        self.assertEqual(r["paid_calls_authorized"],0)
        self.assertFalse(r["live_provider_post_allowed"])
        self.assertEqual(self.payload["case_ids"],
                         [f"B{i:02d}" for i in range(1,11)])
        self.assertTrue(self.payload["zero_model_retries"])
        self.assertTrue(self.payload["no_mid_cohort_modification"])
    def test_forged_grant_self_selected_key_or_invalid_signature_rejected(self):
        private2 = Ed25519PrivateKey.generate()
        otherkey = base64.b64encode(private2.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,format=serialization.PublicFormat.Raw)).decode()
        with self.assertRaises(HarnessStop):
            verify_signed_cohort_intent(self.envelope(),
                independently_trusted_public_key_b64=otherkey,now=NOW)
        wrong=self.envelope()
        wrong["payload"]=copy.deepcopy(wrong["payload"])
        wrong["payload"]["user_aggregate_cap_usd"]="25.00"
        with self.assertRaises(HarnessStop):
            verify_signed_cohort_intent(wrong,
                independently_trusted_public_key_b64=self.key,now=NOW)
    def test_signed_even_if_recomputed_cannot_change_case_or_ceiling(self):
        for field,value in [
            ("case_ids", ["B01"]),("max_new_baseline_reserved_usd","5.00"),
            ("harness_commit","0"*40),("memory_and_tools_locked",False),
            ("no_mid_cohort_modification",False),
            ("production_state_write_authorized",True)
        ]:
            p=copy.deepcopy(self.payload)
            p[field]=value
            with self.subTest(field=field),self.assertRaises(HarnessStop):
                verify_signed_cohort_intent(self.envelope(p),
                    independently_trusted_public_key_b64=self.key,now=NOW)
    def test_expiry_and_oversized_signature_window(self):
        with self.assertRaises(HarnessStop):
            verify_signed_cohort_intent(self.envelope(),
                independently_trusted_public_key_b64=self.key,
                now=NOW+timedelta(hours=2))
        p=copy.deepcopy(self.payload)
        p["expires_at"]=stamp(13*60)
        with self.assertRaises(HarnessStop):
            verify_signed_cohort_intent(self.envelope(p),
                independently_trusted_public_key_b64=self.key,now=NOW)
    def test_conservative_prior_floor_and_planning_envelope(self):
        result=reconcile_cumulative_budget(fake_ledger(),now=NOW)
        self.assertEqual(result["prior_conservative_exposure_usd"],"3.249558")
        self.assertEqual(result["first_ten_reserved_usd"],"4.400")
        self.assertEqual(result["next_twenty_planning_usd"],"8.800")
        self.assertEqual(result["all_thirty_total_reserved_usd"],"16.449558")
        self.assertEqual(result["headroom_after_thirty_usd"],"3.550442")
        self.assertFalse(result["external_financial_attestation_independently_verified"])
    def test_large_previous_cost_fails_closed_even_if_floor_would_fit(self):
        with self.assertRaises(HarnessStop):
            reconcile_cumulative_budget(fake_ledger(
                settled_total_usd="17.000000", previously_reserved_usd="0"),
                now=NOW)
    def test_ledger_missing_or_stale_not_fabricated(self):
        with self.assertRaises(HarnessStop):
            reconcile_cumulative_budget(fake_ledger(
                as_of_utc=stamp(-30)),now=NOW)
        with self.assertRaises(HarnessStop):
            reconcile_cumulative_budget(fake_ledger(
                unknown_charge_hold_usd="NaN"),now=NOW)
        with self.assertRaises(HarnessStop):
            reconcile_cumulative_budget(fake_ledger(
                previously_reserved_usd="-1"),now=NOW)
    def test_unknown_charge_blocks_live_even_if_budget_would_fit(self):
        r=reconcile_cumulative_budget(fake_ledger(
            unknown_charge_hold_usd="0.5"),now=NOW)
        self.assertFalse(r["all_required_ledger_claims_asserted"])
    def test_fake_ledger_approval_and_signature_can_never_unlock_post(self):
        report=launch_readiness(repo_root=".",envelope=self.envelope(),
            independently_trusted_public_key_b64=self.key,
            ledger_snapshot=fake_ledger(),now=NOW)
        self.assertTrue(report["signature_verified_offline"])
        self.assertTrue(report["budget_reconciliation_checked_offline"])
        self.assertFalse(report["paid_dispatch_authorized"])
        self.assertIn("EXTERNAL_LEDGER_AND_APPROVAL_TRUST_NOT_ESTABLISHED",
                      report["blockers"])
