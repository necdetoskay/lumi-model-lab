"""P4.12: no outbound requests in tests; no synthetic grant becomes live consent."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import test_story_harness_p411 as fixtures
from src import story_harness_p412 as p412
from src.story_harness_p411 import OneAttemptLedger, guarded_adapter_once, live_paid_dispatch
from src.story_harness_p410 import canonical_json
from src.story_harness_v1 import HarnessStop


def catalog():
    return {"data": {"id": p412.MODEL, "endpoints": [{
        "provider_name": "Anthropic", "tag": "anthropic", "status": 0,
        "model_id": p412.MODEL, "context_length": 1000000,
        "max_completion_tokens": 128000,
        "pricing": {"prompt": "0.000002", "completion": "0.00001"},
        "supported_parameters": ["max_tokens", "response_format", "structured_outputs"],
    }]}}


class P412Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.P411SignedGrantAndTransportTests.setUpClass()

    def setUp(self):
        self.f = fixtures.P411SignedGrantAndTransportTests()
        self.f.setUp()

    def call(self, ledger, stage="INITIAL_AUDIT", post=None):
        return guarded_adapter_once(callback_kwargs=self.f.kwargs(stage), ledger=ledger,
            repo_root=fixtures.ROOT, declared_input_ceiling_tokens=11000,
            fake_post=post or self.f.fake_post)

    def test_catalog_realistic_missing_temperature_is_blocker(self):
        result = p412.analyze_catalog(catalog())
        self.assertEqual(result["missing_request_parameters"], ["temperature"])
        self.assertEqual(result["prompt_usd_per_million"], "2.000000")
        self.assertFalse(result["request_input_tokens_verified"])
        self.assertFalse(result["catalog_context_is_request_token_quote"])

    def test_catalog_rejects_wrong_route_model_ambiguity_and_invalid_prices(self):
        for change in (lambda d: d.update(id="wrong"),
                       lambda d: d["endpoints"].append(copy.deepcopy(d["endpoints"][0])),
                       lambda d: d["endpoints"][0].update(tag="anthropic/other"),
                       lambda d: d["endpoints"][0].update(status=False),
                       lambda d: d["endpoints"][0]["pricing"].update(prompt="NaN"),
                       lambda d: d["endpoints"][0]["pricing"].update(completion="-1")):
            value = catalog()
            change(value["data"])
            with self.assertRaises(HarnessStop):
                p412.analyze_catalog(value)

    def test_price_and_output_cap_changes_block(self):
        value = catalog()
        value["data"]["endpoints"][0]["pricing"]["prompt"] = "0.000003"
        value["data"]["endpoints"][0]["max_completion_tokens"] = 2000
        result = p412.analyze_catalog(value)
        self.assertIn("ROUTE_PRICE_EXCEEDS_EXISTING_MAX_PRICE", result["blockers"])
        self.assertIn("PROVIDER_OUTPUT_LIMIT_TOO_SMALL", result["blockers"])

    def test_offline_default_never_fetches_or_claims_authority(self):
        with patch.object(p412, "fetch_catalog", side_effect=AssertionError("network")):
            result = p412.preflight(repo_root=fixtures.ROOT)
        self.assertIsNone(result["authorized_budget_usd"])
        self.assertFalse(result["grant_signature_verified"])
        self.assertFalse(result["provider_dispatch_authorized"])

    def test_refresh_is_observation_not_dispatch_or_token_quote(self):
        with patch.object(p412, "fetch_catalog", return_value=catalog()) as get:
            result = p412.preflight(repo_root=fixtures.ROOT, refresh_provider=True)
        get.assert_called_once_with()
        self.assertEqual(result["catalog_transport"], "HTTPS_GET")
        self.assertFalse(result["provider_dispatch_authorized"])
        self.assertIn("UNSUPPORTED_REQUEST_PARAMETERS:temperature", result["blockers"])

    def test_grant_is_reverified_and_not_consumed_or_live(self):
        now = datetime.now(timezone.utc)
        self.f.payload.update(issued_at=fixtures.z(now-timedelta(minutes=1)),
                              expires_at=fixtures.z(now+timedelta(minutes=2)))
        env = self.f.envelope()
        with self.assertRaises(HarnessStop):
            p412.preflight(repo_root=fixtures.ROOT, envelope=env)
        result = p412.preflight(repo_root=fixtures.ROOT, envelope=env,
                                trusted_public_key_b64=self.f.public)
        self.assertTrue(result["grant_signature_verified"])
        self.assertFalse(result["grant_consumed"])
        self.assertFalse(result["provider_dispatch_authorized"])
        with self.assertRaises(HarnessStop):
            live_paid_dispatch(grant=env)
        env["payload"]["budget_usd"] = "1"
        with self.assertRaises(HarnessStop):
            p412.preflight(repo_root=fixtures.ROOT, envelope=env,
                           trusted_public_key_b64=self.f.public)

    def test_expired_and_forged_verified_grant_preflight_rejected(self):
        with self.assertRaises(HarnessStop):
            p412.preflight(repo_root=fixtures.ROOT, envelope=self.f.verified(),
                           trusted_public_key_b64=self.f.public)
        self.f.payload.update(issued_at="2000-01-01T00:00:00Z", expires_at="2000-01-01T00:01:00Z")
        with self.assertRaises(HarnessStop):
            p412.preflight(repo_root=fixtures.ROOT, envelope=self.f.envelope(),
                           trusted_public_key_b64=self.f.public)

    def test_durable_totals_and_exact_wire_hash(self):
        with TemporaryDirectory() as td:
            ledger = OneAttemptLedger(td, self.f.verified())
            bodies = []
            def post(**kw):
                bodies.append(copy.deepcopy(kw["body"]))
                return self.f.fake_post(**kw)
            for stage in p412.STAGES:
                self.call(ledger, stage, post)
            rows = [json.loads(p.read_text()) for p in sorted(ledger.dir.glob('*-outcome.json'))]
            self.assertEqual([r["cumulative_reported_usd"] for r in rows], ["0.001", "0.002", "0.003"])
            self.assertEqual(rows[0]["body_sha256"], hashlib.sha256(canonical_json(bodies[0])).hexdigest())
            text = ''.join(p.read_text() for p in ledger.dir.glob('*.json'))
            self.assertNotIn('NOT_A_REAL_KEY', text)
            self.assertNotIn('Strict offline audit instructions', text)
            with self.assertRaises(FileExistsError):
                OneAttemptLedger(td, self.f.verified())

    def test_unknown_or_excess_usage_stops_next_stage_and_persists(self):
        for usage in ({"prompt_tokens": 1, "completion_tokens": 1},
                      {"prompt_tokens": 11001, "completion_tokens": 1, "cost": .001},
                      {"prompt_tokens": 1, "completion_tokens": 3001, "cost": .001},
                      {"prompt_tokens": 1, "completion_tokens": 1, "cost": .08}):
            with self.subTest(usage=usage), TemporaryDirectory() as td:
                ledger = OneAttemptLedger(td, self.f.verified())
                def post(**kw):
                    response = self.f.fake_post(**kw)
                    response["usage"] = usage
                    return response
                with self.assertRaises(HarnessStop):
                    self.call(ledger, post=post)
                row = json.loads(next(ledger.dir.glob('*-outcome.json')).read_text())
                self.assertEqual(row["status"], "STOP_UNKNOWN_OR_INVALID")
                with self.assertRaises(HarnessStop):
                    self.call(ledger, "SCENE_REPAIR", lambda **_: self.fail("called"))

    def test_transport_and_parse_failure_are_durable_and_redacted(self):
        for failure in (TimeoutError("SECRET"), {"bad": "SECRET"}):
            with TemporaryDirectory() as td:
                ledger = OneAttemptLedger(td, self.f.verified())
                def post(**kw):
                    if isinstance(failure, Exception):
                        raise failure
                    return failure
                with self.assertRaises(HarnessStop):
                    self.call(ledger, post=post)
                text = next(ledger.dir.glob('*-outcome.json')).read_text()
                self.assertNotIn('SECRET', text)
                self.assertIn('STOP_UNKNOWN_OR_INVALID', text)
                with self.assertRaises(HarnessStop):
                    self.call(ledger, 'SCENE_REPAIR')

    def test_disk_failure_after_response_blocks_all_continuation(self):
        with TemporaryDirectory() as td:
            ledger = OneAttemptLedger(td, self.f.verified())
            original = ledger._write_once
            def fail_write(name, receipt):
                if name.endswith('-outcome.json'):
                    raise OSError('disk unavailable')
                original(name, receipt)
            with patch.object(ledger, '_write_once', side_effect=fail_write):
                with self.assertRaises(OSError):
                    self.call(ledger)
            with self.assertRaises(HarnessStop):
                self.call(ledger, 'SCENE_REPAIR')
            with self.assertRaises(FileExistsError):
                OneAttemptLedger(td, self.f.verified())

    def test_run_path_escape_and_mutation_blocked(self):
        with TemporaryDirectory() as td:
            grant = self.f.verified()
            with self.assertRaises(HarnessStop):
                OneAttemptLedger(td, {**grant, 'run_id': '../escape'})
            ledger = OneAttemptLedger(td, grant)
            grant['provider_dispatch_authorized'] = True
            self.assertFalse(ledger.grant['provider_dispatch_authorized'])

    def test_catalog_redirect_and_network_error_fail_closed(self):
        with self.assertRaises(HarnessStop):
            p412._NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.test')
        with patch.object(p412.urllib.request, 'build_opener', side_effect=OSError('SECRET')):
            with self.assertRaisesRegex(HarnessStop, 'catalog unavailable') as err:
                p412.fetch_catalog()
            self.assertNotIn('SECRET', str(err.exception))


if __name__ == '__main__':
    unittest.main()
