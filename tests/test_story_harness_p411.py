"""P4.11 offline negative proofs: signed human-intent format, stage reservation, mock POST."""
from __future__ import annotations

import base64
import copy
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from src.story_harness_p411 import (
    GRANT_SCHEMA, MODEL, PROVIDER, STAGES, OneAttemptLedger,
    canonical_json, guarded_adapter_once, inspect_status, live_paid_dispatch,
    verify_one_time_grant,
)
from src.story_harness_p49 import exact_file, PROFILE_PATH
from src.story_harness_v1 import HarnessStop

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["summary"],
    "properties": {"summary": {"type": "string"}},
}
FIXED_TIME = datetime(2026, 10, 13, 10, 0, tzinfo=timezone.utc)


def b64(value):
    return base64.b64encode(value).decode("ascii")


def z(ts):
    return ts.isoformat().replace("+00:00", "Z")


class P411SignedGrantAndTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads(exact_file(ROOT, PROFILE_PATH))
        cls.writer = json.loads(exact_file(ROOT, cls.profile["source_story"]["artifact_path"]))
        cls.story = exact_file(ROOT, cls.writer["repaired_story_path"]).decode().rstrip("\n")
        spans, cursor = [], 0
        for row in cls.writer["repaired_segments"]:
            ix = cls.story.find(row["repaired_text"], cursor)
            if ix < cursor:
                raise AssertionError("P4.11 Writer source segment mismatch")
            spans.append([row["span_id"], cls.story[cursor:ix], row["repaired_text"]])
            cursor = ix + len(row["repaired_text"])
        cls.wire_spans = {"spans": spans, "trailing_whitespace": cls.story[cursor:]}

    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        self.public = b64(self.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ))
        self.payload = {
            "schema": GRANT_SCHEMA,
            "run_id": "p411_one1",
            "purpose": "one_real_bounded_story_quality_attempt",
            "story_sha256": self.profile["source_story"]["story_sha256"],
            "spine_sha256": self.profile["approved_spine_hash"],
            "source_artifact_id": self.writer["artifact_id"],
            "model": MODEL, "provider": PROVIDER,
            "repair_first_span": "S167", "repair_last_span": "S203",
            "restricted_scope_acknowledged": True,
            "one_attempt_only": True, "max_calls": 3, "max_repairs": 1,
            "budget_usd": "0.25",
            "issued_at": z(FIXED_TIME - timedelta(minutes=2)),
            "expires_at": z(FIXED_TIME + timedelta(minutes=7)),
            "human_approved": True,
        }

    def envelope(self, payload=None):
        p = self.payload if payload is None else payload
        return {"payload": p, "signature_b64": b64(self.private.sign(canonical_json(p)))}

    def verified(self, envelope=None, key=None, now=FIXED_TIME):
        return verify_one_time_grant(
            envelope if envelope is not None else self.envelope(),
            trusted_public_key_b64=self.public if key is None else key,
            now=now, repo_root=ROOT,
        )

    def kwargs(self, stage="INITIAL_AUDIT"):
        request_class, max_tokens = STAGES[stage]
        schema_name = {
            "INITIAL_AUDIT": "spineforge_v21_initial_blocking_audit_v1",
            "SCENE_REPAIR": "spineforge_v21_scene_repair_v1",
            "FINAL_AUDIT": "spineforge_v21_targeted_final_audit_v1",
        }[stage]
        payload = {"source_story_sha256": self.profile["source_story"]["story_sha256"]}
        if stage == "INITIAL_AUDIT":
            payload.update({
                "approved_spine_hash": self.profile["approved_spine_hash"],
                "reader_profile": {"exact_age": 12},
                "story_segments": self.wire_spans,
            })
        if stage == "SCENE_REPAIR":
            payload.update({
                "scene_cluster": {"start_span_id": "S167", "end_span_id": "S203"},
                "entry_boundary": {"span_id": "S166"},
                "exit_boundary": {"span_id": "S204"},
                "source_scene_segments": {
                    "spans": self.wire_spans["spans"][166:203],
                    "trailing_whitespace": "",
                },
            })
        if stage == "FINAL_AUDIT":
            payload["routing_policy"] = {"scope": "REPAIRED_SCENE_PLUS_BOUNDARIES"}
        return {
            "api_key": "NOT_A_REAL_KEY", "model": MODEL,
            "system_prompt": "Strict offline audit instructions",
            "user_prompt": json.dumps(payload, ensure_ascii=False),
            "temperature": 0.0, "max_tokens": max_tokens, "seed": None,
            "request_class": request_class, "schema_name": schema_name,
            "schema": copy.deepcopy(SCHEMA),
        }

    def fake_post(self, *, endpoint, headers, body, stage):
        self.assertEqual(body["model"], MODEL)
        self.assertEqual(body["provider"]["only"], ["Anthropic"])
        self.assertFalse(body["provider"]["allow_fallbacks"])
        self.assertTrue(body["provider"]["require_parameters"])
        self.assertEqual(body["provider"]["max_price"], {"prompt": 2, "completion": 10})
        self.assertNotIn("Authorization", headers)
        self.assertIn("messages", body)
        return {
            "model": MODEL,
            "usage": {"prompt_tokens": 120, "completion_tokens": 40,
                      "total_tokens": 160, "cost": 0.001},
            "choices": [{"message": {"content": json.dumps({"summary": "mock"})}}],
        }

    def test_success_signed_grant_but_no_live_permission(self):
        grant = self.verified()
        self.assertTrue(grant["signed_grant_verified"])
        self.assertFalse(grant["provider_dispatch_authorized"])
        self.assertFalse(grant["provider_pricing_verified"])
        self.assertEqual(grant["budget_usd"], "0.25")
        self.assertTrue(grant["restricted_scope_acknowledged"])
        self.assertEqual(grant["story_sha256"], self.profile["source_story"]["story_sha256"])

    def test_no_external_trusted_key_is_hard_stop(self):
        with self.assertRaisesRegex(HarnessStop, "No configured external"):
            verify_one_time_grant(self.envelope(), repo_root=ROOT, now=FIXED_TIME)

    def test_self_supplied_or_wrong_public_key_fails(self):
        evil = Ed25519PrivateKey.generate().public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw,
        )
        with self.assertRaises(HarnessStop):
            self.verified(key=b64(evil))

    def test_payload_tampering_with_old_signature_rejected(self):
        env = self.envelope()
        env["payload"]["budget_usd"] = "1.00"
        with self.assertRaises(HarnessStop):
            self.verified(env)

    def test_signed_wrong_story_spine_model_or_approval_is_rejected(self):
        for k, v in (
            ("story_sha256", "f"*64), ("spine_sha256", "f"*64),
            ("model", "anthropic/claude-3.5-sonnet"),
            ("restricted_scope_acknowledged", False),
            ("human_approved", False),
            ("max_calls", 4),
            ("repair_first_span", "S162"),
            ("one_attempt_only", False),
        ):
            p = {**self.payload, k: v}
            with self.subTest(k=k), self.assertRaises(HarnessStop):
                self.verified(self.envelope(p))

    def test_expired_future_and_long_lived_grants_denied(self):
        for now in (FIXED_TIME + timedelta(hours=1),
                    FIXED_TIME - timedelta(hours=1)):
            with self.assertRaises(HarnessStop):
                self.verified(now=now)
        p = dict(self.payload)
        p["expires_at"] = z(FIXED_TIME + timedelta(hours=5))
        with self.assertRaises(HarnessStop):
            self.verified(self.envelope(p))

    def test_forged_issuer_key_or_extra_payload_field_blocked(self):
        env = self.envelope()
        env["public_key_b64"] = self.public
        with self.assertRaises(HarnessStop):
            self.verified(env)
        p = dict(self.payload)
        p["force_live"] = True
        with self.assertRaises(HarnessStop):
            self.verified(self.envelope(p))

    def test_atomic_one_time_run_claim_prevents_duplicate_run(self):
        with TemporaryDirectory() as td:
            grant = self.verified()
            ledger = OneAttemptLedger(td, grant)
            self.assertTrue((ledger.dir / "grant-consumed.json").is_file())
            with self.assertRaises(FileExistsError):
                OneAttemptLedger(td, grant)

    def test_signed_approval_does_not_enable_non_mock_network(self):
        with TemporaryDirectory() as td:
            ledger = OneAttemptLedger(td, self.verified())
            with self.assertRaises(HarnessStop):
                guarded_adapter_once(
                    callback_kwargs=self.kwargs(), ledger=ledger,
                    repo_root=ROOT, declared_input_ceiling_tokens=10000,
                )
            with self.assertRaisesRegex(HarnessStop, "PAID_DISPATCH_DISABLED"):
                live_paid_dispatch(api_key="fake", grant=self.envelope())

    def test_fake_transport_valid_request_and_response(self):
        with TemporaryDirectory() as td:
            ledger = OneAttemptLedger(td, self.verified())
            raw, body, request, failures = guarded_adapter_once(
                callback_kwargs=self.kwargs(), ledger=ledger,
                repo_root=ROOT, declared_input_ceiling_tokens=11000,
                fake_post=self.fake_post,
            )
            self.assertEqual(raw["summary"], "mock")
            self.assertEqual(request["max_tokens"], 3000)
            self.assertEqual(body["model"], MODEL)
            self.assertEqual(failures, [])
            self.assertEqual(ledger.stages, ["INITIAL_AUDIT"])
            content = (ledger.dir / "01-initial_audit.json").read_text()
            self.assertNotIn("NOT_A_REAL_KEY", content)
            self.assertNotIn("Strict offline audit instructions", content)
            self.assertNotIn("mock", content)
            self.assertIn('"simulated_only":true', content)

    def test_all_three_fake_stages_and_duplicate_denial(self):
        with TemporaryDirectory() as td:
            ledger = OneAttemptLedger(td, self.verified())
            for stage, n in zip(STAGES, (10000, 5500, 5500)):
                guarded_adapter_once(
                    callback_kwargs=self.kwargs(stage), ledger=ledger,
                    repo_root=ROOT, declared_input_ceiling_tokens=n,
                    fake_post=self.fake_post,
                )
            self.assertEqual(ledger.stages, list(STAGES))
            with self.assertRaises(HarnessStop):
                guarded_adapter_once(
                    callback_kwargs=self.kwargs("FINAL_AUDIT"),
                    ledger=ledger, repo_root=ROOT,
                    declared_input_ceiling_tokens=1000,
                    fake_post=self.fake_post,
                )

    def test_out_of_order_stage_never_calls_provider(self):
        with TemporaryDirectory() as td:
            ledger = OneAttemptLedger(td, self.verified())
            called = []
            with self.assertRaises(HarnessStop):
                guarded_adapter_once(
                    callback_kwargs=self.kwargs("FINAL_AUDIT"),
                    ledger=ledger, repo_root=ROOT,
                    declared_input_ceiling_tokens=1000,
                    fake_post=lambda **_: called.append(True),
                )
            self.assertEqual(called, [])

    def test_failed_transport_consumes_stage_without_retry(self):
        with TemporaryDirectory() as td:
            ledger = OneAttemptLedger(td, self.verified())
            calls = []
            def fail(**kwargs):
                calls.append("attempt")
                raise TimeoutError("synthetic failure")
            with self.assertRaisesRegex(HarnessStop, "intent consumed"):
                guarded_adapter_once(
                    callback_kwargs=self.kwargs(), ledger=ledger,
                    repo_root=ROOT, declared_input_ceiling_tokens=10000,
                    fake_post=fail,
                )
            self.assertEqual(calls, ["attempt"])
            with self.assertRaises(HarnessStop):
                guarded_adapter_once(
                    callback_kwargs=self.kwargs(), ledger=ledger,
                    repo_root=ROOT, declared_input_ceiling_tokens=10000,
                    fake_post=fail,
                )
            self.assertEqual(calls, ["attempt"])

    def test_missing_cost_or_malformed_response_fails_closed(self):
        with TemporaryDirectory() as td:
            ledger = OneAttemptLedger(td, self.verified())
            fake = lambda **_: {"model": MODEL, "usage": {
                "prompt_tokens": 12, "completion_tokens": 1},
                "choices": [{"message": {"content": "{}"}}]}
            with self.assertRaisesRegex(HarnessStop, "Missing actual usage"):
                guarded_adapter_once(
                    callback_kwargs=self.kwargs(), ledger=ledger,
                    repo_root=ROOT, declared_input_ceiling_tokens=10000,
                    fake_post=fake,
                )

    def test_wrong_model_request_rejected_before_reserve_or_transport(self):
        with TemporaryDirectory() as td:
            ledger = OneAttemptLedger(td, self.verified())
            kw = self.kwargs()
            kw["model"] = "not-the-signed-model"
            called = []
            with self.assertRaises(HarnessStop):
                guarded_adapter_once(
                    callback_kwargs=kw, ledger=ledger,
                    repo_root=ROOT, declared_input_ceiling_tokens=10000,
                    fake_post=lambda **_: called.append(True),
                )
            self.assertEqual(called, [])
            self.assertFalse((ledger.dir / "01-initial_audit.json").exists())

    def test_status_reports_zero_calls_and_unaccepted_quality(self):
        info = inspect_status(repo_root=ROOT)
        self.assertEqual(info["stop_reason"], "P411_SIGNED_GRANT_OFFLINE_TRANSPORT_ONLY_LIVE_STOP")
        self.assertFalse(info["external_trusted_human_key_configured"])
        self.assertFalse(info["real_paid_dispatch_possible"])
        self.assertFalse(info["story_quality_accepted"])
        self.assertEqual(info["new_api_calls"], 0)
        self.assertEqual(info["new_api_cost_usd"], "0")


if __name__ == "__main__":
    unittest.main()
