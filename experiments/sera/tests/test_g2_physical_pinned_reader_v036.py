"""v0.36: authentic Ed25519 physical projection is still NONCANONICAL."""
import base64
from copy import deepcopy
from hashlib import sha256
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from experiments.sera.coverage import CoverageError
from experiments.sera.g2_physical_projection_v033 import SCHEMA
from experiments.sera.g2_physical_pinned_reader_v036 import (
    DOMAIN, PERMISSION, project_pinned_physical,
)
from experiments.sera.g2_readonly_scope_bridge_v032 import digest
from experiments.sera.world_state_v02 import canonical
from experiments.sera.tests.test_g2_physical_projection_v033 import (
    BOX, LOC_B, data,
)
from experiments.sera.tests.test_g2_readonly_scope_v032 import verified

NOW = 1792159200
NONCE = "physical-challenge-nonce-unique-00001"
KEY_ID = "g2-physical-key-v1"
ISSUER = "project-lumi-g2-physical"
AUDIENCE = "sera-physical-lab"
SNAPSHOT_ID = "30000000-0000-4000-8000-000000000004"


class PinnedPhysicalTests(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        public = self.private.public_key()
        self.pem = public.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()
        raw = public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.fingerprint = sha256(raw).hexdigest()
        self.authority = verified()
        self.used = set()

    def consume(self, nonce):
        if nonce in self.used:
            return False
        self.used.add(nonce)
        return True

    def signed(self, *, mutate=None, update_proof=None, bad_signature=False):
        snap = data(self.authority)
        if mutate:
            mutate(snap)
        proof = {
            "source": "PROJECT_LUMI_G2_PHYSICAL_READONLY",
            "snapshot_sha256": digest(snap),
            "g2_authority_sha256": digest(self.authority),
            "snapshot_id": SNAPSHOT_ID,
            "nonce": NONCE, "issuer": ISSUER, "audience": AUDIENCE,
            "key_id": KEY_ID, "permission": PERMISSION,
            "issued_at": NOW, "expires_at": NOW + 60,
        }
        if update_proof:
            update_proof(proof)
        message = canonical({
            "domain": DOMAIN,
            "snapshot_sha256": proof["snapshot_sha256"],
            "provenance": proof,
        }).encode("utf-8")
        signature = self.private.sign(message)
        if bad_signature:
            signature = bytes([signature[0] ^ 1]) + signature[1:]
        return {
            "schema": SCHEMA,
            "snapshot": snap,
            "provenance": {
                **proof, "signature": base64.b64encode(signature).decode(),
            },
        }

    def evaluate(self, projection=None, **changes):
        args = dict(
            authority=self.authority,
            projection=projection if projection is not None else self.signed(),
            public_key_pem=self.pem, raw_public_key_sha256=self.fingerprint,
            key_id=KEY_ID, issuer=ISSUER, audience=AUDIENCE,
            expected_nonce=NONCE, consume_nonce=self.consume, now=NOW + 1,
        )
        args.update(changes)
        return project_pinned_physical(**args)

    def test_signed_physical_source_is_shadow_only_and_replay_is_denied(self):
        packet = self.signed()
        before = deepcopy(self.authority)
        result = self.evaluate(packet)
        self.assertTrue(result["physical_source_verified"])
        self.assertEqual(result["physical_source_status"],
                         "SIGNED_READONLY_SHADOW_ONLY")
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(result["world_db_writes"], 0)
        self.assertIsNone(result["g2_commit_request"])
        self.assertEqual(before, self.authority)
        self.assertEqual(result["world"]["entities"][BOX]["location"],
                         packet["snapshot"]["entities"][1]["locationId"])
        with self.assertRaisesRegex(CoverageError,
                                    "V036_PHYSICAL_NONCE_REPLAY"):
            self.evaluate(packet)

    def test_absent_registry_untrusted_key_or_broken_signature(self):
        with self.assertRaisesRegex(CoverageError,
                                    "V036_PHYSICAL_SOURCE_NOT_AVAILABLE"):
            self.evaluate(projection={})
        with self.assertRaisesRegex(CoverageError,
                                    "V035_PUBLIC_KEY_PIN_MISMATCH"):
            self.evaluate(raw_public_key_sha256="f" * 64)
        with self.assertRaisesRegex(CoverageError,
                                    "V036_PHYSICAL_SIGNATURE_INVALID"):
            self.evaluate(self.signed(bad_signature=True))
        self.assertEqual(self.used, set())

    def test_tamper_is_not_authenticated(self):
        packet = self.signed()
        packet["snapshot"]["entities"][1]["locationId"] = LOC_B
        with self.assertRaisesRegex(CoverageError,
                                    "V036_PHYSICAL_SCOPE_OR_PROOF_MISMATCH"):
            self.evaluate(packet)
        self.assertEqual(self.used, set())

    def test_expired_wrong_nonce_permission_issuer_or_audience(self):
        changes = (
            {"expires_at": NOW},
            {"nonce": "another-physical-nonce-unique-00002"},
            {"permission": "g2.story_outcome.commit"},
            {"issuer": "untrusted"},
            {"audience": "untrusted"},
            {"key_id": "attacker"},
            {"g2_authority_sha256": "f" * 64},
        )
        for change in changes:
            with self.subTest(change=change):
                packet = self.signed(update_proof=lambda p: p.update(change))
                with self.assertRaises(CoverageError):
                    self.evaluate(packet)
        self.assertEqual(self.used, set())

    def test_wrong_world_and_custody_do_not_pass_even_valid_signature(self):
        for mutate in (
            lambda p: p.update(worldFingerprint="f" * 64),
            lambda p: p["entities"][1].update(locationId=LOC_B),
            lambda p: p["entities"][1].update(holderId="30000000-0000-4000-8000-000000000099"),
            lambda p: p["entities"][0].update(locationId="30000000-0000-4000-8000-000000000099"),
        ):
            with self.subTest(mutate=mutate):
                packet = self.signed(mutate=mutate)
                with self.assertRaises(Exception):
                    self.evaluate(packet)
        self.assertEqual(self.used, set())

    def test_missing_trusted_nonce_store_is_rejected(self):
        with self.assertRaisesRegex(CoverageError,
                                    "V036_PHYSICAL_TRUST_CONFIG_INVALID"):
            self.evaluate(consume_nonce=None)
        self.assertEqual(self.used, set())

    def test_proof_unknown_keys_are_rejected(self):
        packet = self.signed()
        packet["provenance"]["public_key"] = self.pem
        with self.assertRaisesRegex(CoverageError,
                                    "V036_PHYSICAL_SCOPE_OR_PROOF_MISMATCH"):
            self.evaluate(packet)
        self.assertEqual(self.used, set())


if __name__ == "__main__":
    unittest.main()
