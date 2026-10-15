"""P4.14 credential-bound OpenRouter current-key checks: fake GET only, no model."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_story_harness_p411 as grant_fixtures
from src.story_harness_p414 import (
    KEY_URL, analyze_key_metadata, read_current_key,
    validate_signed_key_preflight, status,
)
from src.story_harness_v1 import HarnessStop

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 13, 11, 30, tzinfo=timezone.utc)
TEST_BEARER = "sk-or-offline-p414-test-only-unique-nonexistent"


def data(**overrides):
    original = {
        "is_management_key": False,
        "is_provisioning_key": False,
        "is_free_tier": False,
        "limit": 0.25,
        "limit_remaining": 0.25,
        "limit_reset": None,
        "include_byok_in_limit": True,
        "usage": 0,
        "byok_usage": 0,
        "expires_at": "2026-10-13T13:00:00Z",
        "label": "PRIVATE_TEST_LABEL_SHOULD_NOT_LOG",
        "creator_user_id": "PRIVATE_USER_ID_SHOULD_NOT_LOG",
        "hash": "PRIVATE_HASH_SHOULD_NOT_LOG",
    }
    original.update(overrides)
    return {"data": original}


class FakeReply:
    def __init__(self, value, *, status=200, url=KEY_URL):
        self.body = json.dumps(value).encode()
        self.status = status
        self.url = url
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def geturl(self):
        return self.url
    def read(self, n):
        return self.body[:n]


class FakeOpener:
    def __init__(self, value, **kwargs):
        self.response = FakeReply(value, **kwargs)
        self.calls = []
    def open(self, request, timeout=None):
        self.calls.append((request, timeout))
        return self.response


class P414Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        grant_fixtures.P411SignedGrantAndTransportTests.setUpClass()

    def setUp(self):
        self.f = grant_fixtures.P411SignedGrantAndTransportTests()
        self.f.setUp()
        self.f.payload["issued_at"] = "2026-10-13T11:29:00Z"
        self.f.payload["expires_at"] = "2026-10-13T11:39:00Z"

    def verify(self, opener):
        return validate_signed_key_preflight(
            repo_root=ROOT, envelope=self.f.envelope(),
            trusted_public_key_b64=self.f.public,
            api_key=TEST_BEARER, now=NOW, opener=opener,
        )

    def test_fresh_nonreset_isolated_key_matches_signed_budget(self):
        report = analyze_key_metadata(data(), signed_budget_usd="0.25", now=NOW)
        self.assertTrue(report["key_policy_structurally_valid"])
        self.assertEqual(report["remaining_key_limit_usd"], "0.25")
        self.assertFalse(report["authenticated_live_provider_observation"])
        self.assertFalse(report["live_dispatch_allowed"])
        message = json.dumps(report)
        self.assertNotIn("PRIVATE_", message)
        self.assertNotIn("sk-or-", message)

    def test_budget_limit_stricter_than_signed_grant_allowed(self):
        report = analyze_key_metadata(
            data(limit="0.20", limit_remaining="0.20"),
            signed_budget_usd="0.25", now=NOW)
        self.assertEqual(report["configured_key_limit_usd"], "0.20")

    def test_no_limit_reset_daily_weekly_monthly_or_missing(self):
        for reset in ("daily", "weekly", "monthly", "none"):
            with self.subTest(reset=reset), self.assertRaises(HarnessStop):
                analyze_key_metadata(data(limit_reset=reset),
                                     signed_budget_usd="0.25", now=NOW)
        row = data()
        del row["data"]["limit_reset"]
        with self.assertRaises(HarnessStop):
            analyze_key_metadata(row, signed_budget_usd="0.25", now=NOW)

    def test_unlimited_and_oversized_limit_fail(self):
        for val in (None, 0, -1, 0.251, "NaN", "Infinity", True, "9"):
            with self.subTest(val=val), self.assertRaises(HarnessStop):
                analyze_key_metadata(data(limit=val),
                                     signed_budget_usd="0.25", now=NOW)

    def test_previously_used_or_not_full_remaining_key_fail(self):
        for change in (
            {"usage": 0.001, "limit_remaining": 0.249},
            {"limit_remaining": 0.24},
            {"byok_usage": 0.001},
        ):
            with self.subTest(change=change), self.assertRaises(HarnessStop):
                analyze_key_metadata(data(**change),
                                     signed_budget_usd="0.25", now=NOW)

    def test_management_provisioning_and_free_key_fail(self):
        for name in ("is_management_key", "is_provisioning_key", "is_free_tier"):
            with self.subTest(name=name), self.assertRaises(HarnessStop):
                analyze_key_metadata(data(**{name: True}),
                                     signed_budget_usd="0.25", now=NOW)

    def test_byok_must_be_counted_in_limit(self):
        for val in (False, None, "yes"):
            with self.subTest(value=val), self.assertRaises(HarnessStop):
                analyze_key_metadata(data(include_byok_in_limit=val),
                                     signed_budget_usd="0.25", now=NOW)

    def test_expiring_key_fail_and_missing_expiry_allowed(self):
        with self.assertRaises(HarnessStop):
            analyze_key_metadata(data(expires_at="2026-10-13T11:45:00Z"),
                                 signed_budget_usd="0.25", now=NOW)
        r = analyze_key_metadata(data(expires_at=None),
                                 signed_budget_usd="0.25", now=NOW)
        self.assertFalse(r["live_dispatch_allowed"])

    def test_bad_shape_nonfinite_grant_and_missing_usage_fail(self):
        for invalid in (None, {}, {"data": []}, {"data": {}}):
            with self.subTest(value=invalid), self.assertRaises(HarnessStop):
                analyze_key_metadata(invalid, signed_budget_usd="0.25", now=NOW)
        with self.assertRaises(HarnessStop):
            analyze_key_metadata(data(), signed_budget_usd="NaN", now=NOW)
        with self.assertRaises(HarnessStop):
            analyze_key_metadata(data(usage=None),
                                 signed_budget_usd="0.25", now=NOW)

    def test_fake_get_is_one_request_and_never_completion_post(self):
        transport = FakeOpener(data())
        reply = read_current_key(api_key=TEST_BEARER, opener=transport)
        self.assertEqual(reply["data"]["limit_remaining"], 0.25)
        self.assertEqual(len(transport.calls), 1)
        req, timeout = transport.calls[0]
        self.assertEqual(req.full_url, KEY_URL)
        self.assertEqual(req.get_method(), "GET")
        self.assertEqual(timeout, 12)
        self.assertEqual(req.get_header("Authorization"), "Bearer " + TEST_BEARER)
        self.assertNotIn("chat/completions", req.full_url)

    def test_fake_response_wrong_status_redirect_or_size_stops(self):
        for options in ({"status": 401}, {"status": 302},
                        {"url": "https://other.example/steal"}):
            with self.subTest(option=options), self.assertRaises(HarnessStop):
                read_current_key(api_key=TEST_BEARER,
                                 opener=FakeOpener(data(), **options))
        transport = FakeOpener({"data": {"label": "x" * 50000}})
        with self.assertRaises(HarnessStop):
            read_current_key(api_key=TEST_BEARER, opener=transport)

    def test_secret_is_not_released_in_failure_exception(self):
        secret = "sk-or-FORBIDDEN_TEST_SECRET"
        class BadOpener:
            def open(self, *args, **kwargs):
                raise RuntimeError(secret)
        with self.assertRaises(HarnessStop) as cm:
            read_current_key(api_key=secret, opener=BadOpener())
        self.assertNotIn(secret, str(cm.exception))

    def test_signed_grant_verified_before_any_get_and_no_live_dispatch(self):
        op = FakeOpener(data())
        result = self.verify(op)
        self.assertTrue(result["external_grant_signature_verified"])
        self.assertFalse(result["live_metadata_path_exercised"])
        self.assertFalse(result["authenticated_live_provider_observation"])
        self.assertFalse(result["provider_dispatch_authorized"])
        self.assertFalse(result["external_human_grant_consumed"]
                         if "external_human_grant_consumed" in result else False)
        self.assertEqual(len(op.calls), 1)
        self.assertEqual(result["source_story_sha256"], self.f.payload["story_sha256"])
        self.assertNotIn(TEST_BEARER, json.dumps(result))
        self.assertNotIn("PRIVATE_", json.dumps(result))

    def test_invalid_signature_does_not_fetch_key(self):
        op = FakeOpener(data())
        env = self.f.envelope()
        env["payload"]["budget_usd"] = "0.99"
        with self.assertRaises(HarnessStop):
            validate_signed_key_preflight(
                repo_root=ROOT, envelope=env,
                trusted_public_key_b64=self.f.public,
                api_key=TEST_BEARER, now=NOW, opener=op,
            )
        self.assertEqual(op.calls, [])

    def test_expired_grant_or_untrusted_key_never_fetch_key(self):
        op = FakeOpener(data())
        with self.assertRaises(HarnessStop):
            validate_signed_key_preflight(
                repo_root=ROOT, envelope=self.f.envelope(),
                trusted_public_key_b64=None,
                api_key=TEST_BEARER, now=NOW, opener=op)
        with self.assertRaises(HarnessStop):
            validate_signed_key_preflight(
                repo_root=ROOT, envelope=self.f.envelope(),
                trusted_public_key_b64=self.f.public,
                api_key=TEST_BEARER, now=NOW + timedelta(hours=1), opener=op)
        self.assertEqual(op.calls, [])

    def test_no_credential_requested_by_status_and_no_spend_claim(self):
        report = status(repo_root=ROOT)
        self.assertFalse(report["key_provisioned"])
        self.assertFalse(report["key_limit_verified_on_user_account"])
        self.assertFalse(report["external_trust_anchor_provisioned"])
        self.assertFalse(report["live_dispatch_allowed"])
        self.assertFalse(report["story_quality_accepted"])
        self.assertEqual(report["model_calls"], 0)
        self.assertEqual(report["api_cost_usd"], "0")
        self.assertEqual(report["stop_reason"],
                         "P414_USER_KEY_LIMIT_AND_GRANT_NOT_PROVISIONED_LIVE_STOP")


if __name__ == "__main__":
    unittest.main()
