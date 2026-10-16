"""v0.35 actual Node crypto.sign ↔ Python Ed25519 interoperability tests.

All rows, UUIDs, dates and keys are synthetic. No service, DB, network,
model provider or production secret is contacted.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import subprocess
from urllib.parse import parse_qs, urlsplit
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa

from experiments.sera.coverage import CoverageError
from experiments.sera.g2_ed25519_pinned_reader_v035 import (
    create_pinned_reader, pinned_verifier,
)
from experiments.sera.g2_authenticated_http_reader_v033 import (
    API_PATH, READ_PERMISSION,
)
from experiments.sera.g2_readonly_scope_bridge_v032 import (
    SCHEMA, SCOPE, digest, resolve,
)
from experiments.sera.tests.test_g2_readonly_scope_v032 import (
    IDS, synthetic_rows, req,
)
from experiments.sera.tests.test_storyforge_bridge_v028 import fake_result
from experiments.sera.tests.test_world_state_v02 import base

ENDPOINT = "https://authority.project-lumi.example" + API_PATH
T0 = 1792159200.125
KEY_ID = "g2-source-signer-v035"
NODE = r"""
const fs = require('node:fs');
const crypto = require('node:crypto');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
function g2Canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(g2Canonical).join(',') + ']';
  if (value !== null && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map(k =>
      JSON.stringify(k) + ':' + g2Canonical(value[k])).join(',') + '}';
  }
  if (value === undefined || typeof value === 'function')
    throw new Error('NOT_SERIALIZABLE');
  return JSON.stringify(value);
}
const hash = value => crypto.createHash('sha256')
  .update(g2Canonical(value)).digest('hex');
const rows = input.rows;
const prov = {...input.provenance, rows_sha256: hash(rows)};
const msg = g2Canonical({
  domain: 'sera-g2-authority-readonly-v033',
  rows_sha256: hash(rows),
  provenance: prov,
});
const signature = crypto.sign(null, Buffer.from(msg, 'utf8'),
  crypto.createPrivateKey(input.private_key_pem)).toString('base64');
process.stdout.write(JSON.stringify({
  schema: 'sera.project-lumi-g2-readonly-binding.v0.32',
  rows, provenance: {...prov,signature},
}));
"""


def keypair():
    secret = ed25519.Ed25519PrivateKey.generate()
    pem = secret.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    public = secret.public_key()
    pub_pem = public.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    pin = sha256(public.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )).hexdigest()
    return pem, pub_pem, pin


def scope():
    return {k: IDS[k] for k in SCOPE}


def signed_by_real_node_crypto(*, rows, provenance, secret):
    result = subprocess.run(
        ["node", "-e", NODE],
        input=json.dumps({
            "rows": rows, "provenance": provenance,
            "private_key_pem": secret,
        }, ensure_ascii=False),
        text=True, capture_output=True, timeout=8, check=True,
    )
    return json.loads(result.stdout)


def service(*, mutate_signed=None, mutate_unsigned=None):
    secret, pub_pem, pin = keypair()
    requests = []
    def transport(*, url, authorization, timeout, max_bytes):
        assert url.startswith(ENDPOINT + "?")
        assert authorization == "synthetic-readonly-service-token"
        assert timeout == 15
        assert max_bytes == 1_500_000
        requests.append(url)
        query = parse_qs(urlsplit(url).query)
        rows = synthetic_rows()
        provenance = {
            "source": "PROJECT_LUMI_G2_READONLY",
            "contract_id": IDS["contractId"],
            "snapshot_id": "synthetic-node-signed-transaction",
            "scope_sha256": digest(scope()),
            "permission": READ_PERMISSION,
            "nonce": query["nonce"][0],
            "issuer": "project-lumi-server",
            "audience": "sera-internal-reader",
            "key_id": KEY_ID,
            "issued_at": T0,
            "expires_at": T0 + 60,
        }
        if mutate_signed is not None:
            mutate_signed(rows, provenance)
        document = signed_by_real_node_crypto(
            rows=rows, provenance=provenance, secret=secret,
        )
        if mutate_unsigned is not None:
            mutate_unsigned(document)
        return document
    return pub_pem, pin, transport, requests


def reader(*, pub_pem, pin, transport):
    return create_pinned_reader(
        endpoint=ENDPOINT,
        bearer_token="synthetic-readonly-service-token",
        expected_scope=scope(),
        issuer="project-lumi-server", audience="sera-internal-reader",
        key_id=KEY_ID,
        public_key_pem=pub_pem,
        raw_public_key_sha256=pin,
        transport=transport,
        clock=lambda: T0,
        nonce_factory=lambda: "unique-synthetic-node-nonce-32chars",
    )


def resolve_once(getter, check):
    return resolve(
        contract_id=IDS["contractId"], expected_scope=scope(),
        request=req(), result=fake_result(), world=base(),
        readonly_lookup=getter, verify_source=check,
    )


class PinnedEd25519V035Tests(unittest.TestCase):
    def test_real_node_signature_validates_full_v032_g2_readonly_chain(self):
        pem, pin, transport, sent = service()
        getter, verifier = reader(
            pub_pem=pem, pin=pin, transport=transport,
        )
        result = resolve_once(getter, verifier)
        self.assertTrue(result["authenticated_source_preflight"])
        self.assertEqual(result["scope"], scope())
        self.assertEqual(len(sent), 1)
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(result["world_db_writes"], 0)
        self.assertIsNone(result["g2_commit_request"])

    def test_byte_for_byte_post_signature_tampering_denied(self):
        def alter(doc):
            doc["rows"]["accepted_story"]["storyText"] += " forged"
        pem, pin, transport, _ = service(mutate_unsigned=alter)
        getter, verifier = reader(pub_pem=pem, pin=pin, transport=transport)
        with self.assertRaisesRegex(
            CoverageError, "V033_SIGNED_SCOPE_FRESHNESS_OR_PERMISSION_INVALID"
        ):
            # Rows SHA mismatch is detected before Ed25519 verification.
            resolve_once(getter, verifier)

    def test_signed_wrong_scope_or_issuer_denied_before_structure(self):
        for mutate in (
            lambda rows, p: p.update(scope_sha256="0" * 64),
            lambda rows, p: p.update(issuer="attacker"),
            lambda rows, p: p.update(permission="story.commit"),
        ):
            with self.subTest(mutate=mutate):
                pem, pin, transport, _ = service(mutate_signed=mutate)
                getter, verifier = reader(
                    pub_pem=pem, pin=pin, transport=transport,
                )
                with self.assertRaisesRegex(
                    CoverageError, "V033_SIGNED_SCOPE_FRESHNESS_OR_PERMISSION_INVALID"
                ):
                    resolve_once(getter, verifier)

    def test_wrong_key_or_independent_pin_cannot_bootstrap_trust(self):
        secret1, public1, pin1 = keypair()
        _, public2, pin2 = keypair()
        with self.assertRaisesRegex(
            CoverageError, "V035_PUBLIC_KEY_PIN_MISMATCH"
        ):
            pinned_verifier(
                public_key_pem=public1,
                raw_public_key_sha256=pin2,
                key_id=KEY_ID,
            )
        verify = pinned_verifier(
            public_key_pem=public1, raw_public_key_sha256=pin1,
            key_id=KEY_ID,
        )
        self.assertFalse(verify(b"story", "AAAA", "wrong-key-id"))
        self.assertFalse(verify(b"story", "not base64 !!", KEY_ID))
        self.assertFalse(verify(b"story", "AAAA", KEY_ID))
        self.assertNotEqual(public1, public2)

    def test_reject_non_ed25519_public_key_and_private_pem(self):
        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = private.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        with self.assertRaisesRegex(
            CoverageError, "V035_PINNED_KEY_NOT_ED25519"
        ):
            pinned_verifier(
                public_key_pem=pem,
                raw_public_key_sha256="0" * 64, key_id=KEY_ID,
            )
        secret, _, pin = keypair()
        with self.assertRaisesRegex(
            CoverageError, "V035_PINNED_PUBLIC_KEY_INVALID"
        ):
            pinned_verifier(
                public_key_pem=secret, raw_public_key_sha256=pin,
                key_id=KEY_ID,
            )

    def test_verify_callback_override_forbidden(self):
        _, public, pin = keypair()
        with self.assertRaisesRegex(
            CoverageError, "V035_VERIFIER_OVERRIDE_FORBIDDEN"
        ):
            create_pinned_reader(
                endpoint=ENDPOINT,
                bearer_token="synthetic-readonly-service-token",
                expected_scope=scope(),
                issuer="project-lumi-server", audience="sera-internal-reader",
                key_id=KEY_ID, public_key_pem=public,
                raw_public_key_sha256=pin,
                verify_signature=lambda *args: True,
            )

    def test_replayed_ed25519_signed_read_proof_is_one_use(self):
        pem, pin, transport, _ = service()
        getter, verifier = reader(pub_pem=pem, pin=pin, transport=transport)
        doc = getter(contract_id=IDS["contractId"])
        self.assertTrue(verifier(doc["rows"], doc["provenance"]))
        with self.assertRaisesRegex(
            CoverageError, "V033_READ_NOT_REQUESTED_OR_ALREADY_CONSUMED"
        ):
            verifier(doc["rows"], doc["provenance"])


if __name__ == "__main__":
    unittest.main()
