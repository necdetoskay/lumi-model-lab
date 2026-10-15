"""P4.13: explicit NON-EQUIVALENT temperature omission, no live transport."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import test_story_harness_p411 as fixtures
import test_story_harness_p412 as p412_fixtures
from src.story_harness_p410 import canonical_json
from src.story_harness_p411 import (
    OneAttemptLedger, guarded_adapter_once, validate_callback,
)
from src.story_harness_p413 import adapt_wire, status
from src.story_harness_v1 import HarnessStop

ROOT = Path(__file__).resolve().parents[1]


def catalog():
    return p412_fixtures.catalog()


class P413TemperatureCompatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.P411SignedGrantAndTransportTests.setUpClass()

    def setUp(self):
        self.f = fixtures.P411SignedGrantAndTransportTests()
        self.f.setUp()
        self.initial_kwargs = self.f.kwargs()
        self.stage, self.preview = validate_callback(
            self.initial_kwargs, repo_root=ROOT,
        )

    def project(self, **kwargs):
        return adapt_wire(preview=self.preview, catalog=catalog(),
                          allow_sampling_semantics_change=True, **kwargs)

    def test_exact_initial_request_omits_only_temperature_with_disclosure(self):
        before = copy.deepcopy(self.preview)
        wire, info = self.project()
        self.assertEqual(self.preview, before)
        self.assertEqual(info["wire_temperature_parameter"], "OMITTED")
        self.assertFalse(info["sampling_semantics_equivalent"])
        self.assertFalse(info["catalog_is_authenticated_request_quote"])
        self.assertFalse(info["live_dispatch_allowed"])
        self.assertNotIn("temperature", wire)
        other = copy.deepcopy(wire)
        other["temperature"] = 0.0
        other["provider"].pop("max_price")
        self.assertEqual(other, self.preview["body"])
        self.assertEqual(
            info["exact_wire_sha256"], hashlib.sha256(canonical_json(wire)).hexdigest(),
        )
        self.assertEqual(info["other_request_parameters_preserved"], True)
        self.assertEqual(wire["provider"]["only"], ["Anthropic"])
        self.assertFalse(wire["provider"]["allow_fallbacks"])
        self.assertTrue(wire["provider"]["require_parameters"])
        self.assertTrue(wire["response_format"]["json_schema"]["strict"])

    def test_sampling_change_requires_explicit_offline_ack(self):
        with self.assertRaisesRegex(HarnessStop, "NON-EQUIVALENT"):
            adapt_wire(preview=self.preview, catalog=catalog())
        with self.assertRaises(HarnessStop):
            adapt_wire(preview=self.preview, catalog=catalog(),
                       allow_sampling_semantics_change="yes")

    def test_extra_missing_supported_parameter_is_rejected(self):
        for remove in ("max_tokens", "response_format", "structured_outputs"):
            c = catalog()
            c["data"]["endpoints"][0]["supported_parameters"].remove(remove)
            with self.subTest(remove=remove), self.assertRaises(HarnessStop):
                adapt_wire(preview=self.preview, catalog=c,
                           allow_sampling_semantics_change=True)

    def test_temperature_newly_supported_is_not_omitted(self):
        c = catalog()
        c["data"]["endpoints"][0]["supported_parameters"].append("temperature")
        with self.assertRaisesRegex(HarnessStop, "Exact sole compatibility"):
            adapt_wire(preview=self.preview, catalog=c,
                       allow_sampling_semantics_change=True)

    def test_price_increase_wrong_model_route_or_fallback_cannot_pass(self):
        changes = [
            lambda c: c["data"].update(id="wrong-model"),
            lambda c: c["data"]["endpoints"][0].update(provider_name="Other"),
            lambda c: c["data"]["endpoints"][0].update(tag="other"),
            lambda c: c["data"]["endpoints"][0]["pricing"].update(prompt="0.000003"),
        ]
        for changed in changes:
            c = catalog()
            changed(c)
            with self.subTest(change=str(changed)), self.assertRaises(HarnessStop):
                adapt_wire(preview=self.preview, catalog=c,
                           allow_sampling_semantics_change=True)
        p = copy.deepcopy(self.preview)
        p["body"]["provider"]["allow_fallbacks"] = True
        with self.assertRaises(HarnessStop):
            adapt_wire(preview=p, catalog=catalog(),
                       allow_sampling_semantics_change=True)

    def test_model_schema_or_generation_caps_cannot_change(self):
        for field, value in [("model", "wrong"),
                             ("max_tokens", 9999), ("stream", True)]:
            p = copy.deepcopy(self.preview)
            p["body"][field] = value
            with self.subTest(field=field), self.assertRaises(HarnessStop):
                adapt_wire(preview=p, catalog=catalog(),
                           allow_sampling_semantics_change=True)

    def test_initial_mock_only_and_ledger_records_exact_projected_body(self):
        with TemporaryDirectory() as td:
            ledger = OneAttemptLedger(td, self.f.verified())
            seen = []
            def post(**kw):
                seen.append(copy.deepcopy(kw["body"]))
                return self.f.fake_post(**kw)
            raw, body, request, failure = guarded_adapter_once(
                callback_kwargs=self.initial_kwargs, ledger=ledger,
                repo_root=ROOT, declared_input_ceiling_tokens=11000,
                fake_post=post, p413_catalog=catalog(), p413_sampling_ack=True,
            )
            self.assertEqual(raw["summary"], "mock")
            self.assertEqual(request["temperature"], None)
            self.assertNotIn("temperature", seen[0])
            self.assertEqual(len(seen), 1)
            reservation = json.loads((ledger.dir / "01-initial_audit.json").read_text())
            outcome = json.loads((ledger.dir / "01-initial_audit-outcome.json").read_text())
            wire_sha = hashlib.sha256(canonical_json(seen[0])).hexdigest()
            self.assertEqual(reservation["body_sha256"], wire_sha)
            self.assertEqual(outcome["body_sha256"], wire_sha)
            self.assertEqual(outcome["status"], "SETTLED")
            self.assertFalse(outcome["provider_dispatch_authorized"])
            self.assertNotIn("fake", (ledger.dir / "grant-consumed.json").read_text())

    def test_all_three_stages_compatibility_are_single_use_and_fake(self):
        with TemporaryDirectory() as td:
            ledger = OneAttemptLedger(td, self.f.verified())
            observed = []
            def post(**kw):
                observed.append(kw["stage"])
                self.assertNotIn("temperature", kw["body"])
                return self.f.fake_post(**kw)
            for stage in ("INITIAL_AUDIT", "SCENE_REPAIR", "FINAL_AUDIT"):
                guarded_adapter_once(
                    callback_kwargs=self.f.kwargs(stage),
                    ledger=ledger, repo_root=ROOT,
                    declared_input_ceiling_tokens=11000,
                    fake_post=post, p413_catalog=catalog(),
                    p413_sampling_ack=True,
                )
            self.assertEqual(observed, ["INITIAL_AUDIT", "SCENE_REPAIR", "FINAL_AUDIT"])
            self.assertEqual(ledger.settled, observed)
            self.assertLessEqual(ledger.actual, ledger.budget)
            self.assertEqual(len(list(ledger.dir.glob("*-outcome.json"))), 3)

    def test_no_ack_or_wrong_catalog_never_consumes_run_stage(self):
        with TemporaryDirectory() as td:
            ledger = OneAttemptLedger(td, self.f.verified())
            calls = []
            with self.assertRaises(HarnessStop):
                guarded_adapter_once(
                    callback_kwargs=self.initial_kwargs, ledger=ledger,
                    repo_root=ROOT, declared_input_ceiling_tokens=10000,
                    fake_post=lambda **_: calls.append(True),
                    p413_catalog=catalog(), p413_sampling_ack=False,
                )
            self.assertFalse(calls)
            self.assertEqual(ledger.stages, [])

    def test_bad_callback_source_sha_stops_before_ledger(self):
        with TemporaryDirectory() as td:
            ledger = OneAttemptLedger(td, self.f.verified())
            kw = self.f.kwargs()
            payload = json.loads(kw["user_prompt"])
            payload["source_story_sha256"] = "0" * 64
            kw["user_prompt"] = json.dumps(payload)
            with self.assertRaises(HarnessStop):
                guarded_adapter_once(
                    callback_kwargs=kw, ledger=ledger,
                    repo_root=ROOT, declared_input_ceiling_tokens=11000,
                    fake_post=self.f.fake_post, p413_catalog=catalog(),
                    p413_sampling_ack=True,
                )
            self.assertEqual(ledger.stages, [])

    def test_mock_transport_failure_exhausts_stage_without_retry(self):
        with TemporaryDirectory() as td:
            ledger = OneAttemptLedger(td, self.f.verified())
            invoked = []
            def fail(**kw):
                invoked.append(True)
                raise TimeoutError("fake timeout")
            with self.assertRaises(HarnessStop):
                guarded_adapter_once(
                    callback_kwargs=self.initial_kwargs, ledger=ledger,
                    repo_root=ROOT, declared_input_ceiling_tokens=11000,
                    fake_post=fail, p413_catalog=catalog(),
                    p413_sampling_ack=True,
                )
            self.assertEqual(len(invoked), 1)
            self.assertTrue(ledger.halted)
            with self.assertRaises(HarnessStop):
                guarded_adapter_once(
                    callback_kwargs=self.f.kwargs("SCENE_REPAIR"), ledger=ledger,
                    repo_root=ROOT, declared_input_ceiling_tokens=11000,
                    fake_post=fail, p413_catalog=catalog(),
                    p413_sampling_ack=True,
                )
            self.assertEqual(len(invoked), 1)

    def test_offline_report_never_upgrades_to_paid_or_accepted(self):
        report = status()
        self.assertEqual(report["provider_calls"], 0)
        self.assertEqual(report["cost_usd"], "0")
        self.assertFalse(report["live_dispatch_allowed"])
        self.assertFalse(report["quality_accepted"])
        self.assertFalse(report["sampling_semantics_equivalent"])
        self.assertFalse(report["q25_authorized"])
        self.assertFalse(report["state_write_authorized"])


if __name__ == "__main__":
    unittest.main()
