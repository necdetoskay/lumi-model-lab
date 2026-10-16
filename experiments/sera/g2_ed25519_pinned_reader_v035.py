"""SERA v0.35: real Ed25519 verifier for Project_LUMI v0.34 signed GET.

Use the pinned PUBLIC key, its independently pinned RAW-SPKI-derived 32-byte
Ed25519 key SHA-256 fingerprint, and a fixed key ID. No model, transport,
database or response document may supply trusted key material.

The server owns its private key. The G2 HTTP client still enforces HTTPS,
scope, nonce, issuer, audience, freshness and one-time read binding.
This adapter authenticates ONLY a detached READ, never spending/commit.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import re

from experiments.sera.coverage import CoverageError
from experiments.sera.g2_authenticated_http_reader_v033 import create_reader


def require(ok, code):
    if not ok:
        raise CoverageError(code)


def pinned_verifier(*, public_key_pem, raw_public_key_sha256, key_id):
    """Return a signature verifier pinned to one Ed25519 public key.

    Key fingerprint = lowercase SHA-256 hex of the 32 raw Ed25519
    public-key bytes. It must be pinned OUTSIDE the HTTP response.
    """
    require(isinstance(public_key_pem, (str, bytes)) and public_key_pem and
            isinstance(key_id, str) and bool(key_id.strip()) and
            isinstance(raw_public_key_sha256, str) and
            re.fullmatch(r"[a-f0-9]{64}", raw_public_key_sha256) is not None,
            "V035_SIGNER_TRUST_CONFIG_INVALID")
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        key_bytes = (
            public_key_pem.encode("utf-8")
            if isinstance(public_key_pem, str) else public_key_pem
        )
        key = serialization.load_pem_public_key(key_bytes)
    except ImportError as exc:
        raise CoverageError("V035_CRYPTOGRAPHY_DEPENDENCY_MISSING") from exc
    except (ValueError, TypeError) as exc:
        raise CoverageError("V035_PINNED_PUBLIC_KEY_INVALID") from exc
    require(isinstance(key, Ed25519PublicKey),
            "V035_PINNED_KEY_NOT_ED25519")
    from cryptography.hazmat.primitives import serialization
    raw = key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    require(sha256(raw).hexdigest() == raw_public_key_sha256,
            "V035_PUBLIC_KEY_PIN_MISMATCH")

    def verify(message, signature, supplied_key_id):
        if (supplied_key_id != key_id or
            not isinstance(message, bytes) or
            not isinstance(signature, str)):
            return False
        try:
            # The Project_LUMI Node source emits base64 Ed25519 signatures,
            # never HMAC hex, base64url or unhashed model assertions.
            raw_sig = base64.b64decode(signature, validate=True)
            if len(raw_sig) != 64:
                return False
            key.verify(raw_sig, message)
            return True
        except Exception:
            # This callback is a boolean trust boundary. Never leak the
            # original signed source or secrets through exception text.
            return False

    return verify


def create_pinned_reader(*, endpoint, bearer_token, expected_scope,
                         issuer, audience, key_id,
                         public_key_pem, raw_public_key_sha256,
                         **reader_kwargs):
    """Return v0.33 (readonly_lookup, verify_source) with real asymmetric trust.

    No user-controlled key material or client-side signer is ever created.
    reader_kwargs is for injectable offline network/clock/nonce tests only.
    """
    verify = pinned_verifier(
        public_key_pem=public_key_pem,
        raw_public_key_sha256=raw_public_key_sha256,
        key_id=key_id,
    )
    require("verify_signature" not in reader_kwargs and
            "trusted_key_id" not in reader_kwargs,
            "V035_VERIFIER_OVERRIDE_FORBIDDEN")
    return create_reader(
        endpoint=endpoint, bearer_token=bearer_token,
        expected_scope=expected_scope, issuer=issuer,
        audience=audience, trusted_key_id=key_id,
        verify_signature=verify, **reader_kwargs,
    )
