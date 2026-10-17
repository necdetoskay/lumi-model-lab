"""SERA v0.52 paid-grant signer pin: trusted deployment config only.

The signed approval cannot supply its own trust root or fingerprint.
The expected lowercase SHA-256 of the raw 32-byte Ed25519 public key MUST
be provisioned independently from the signed approval (protected deployment
config / runner trust store). Signing keys never enter this module.
"""
from __future__ import annotations

from hashlib import sha256
import re
from experiments.sera.provider_grant_journal_v052 import JournalBlocked


def verify_pinned_paid_issuer(*, public_key, trusted_raw_key_sha256):
    """Fail before provider/journal creation on invalid or substituted signer."""
    if (not isinstance(trusted_raw_key_sha256, str) or
        re.fullmatch(r"[a-f0-9]{64}", trusted_raw_key_sha256) is None):
        raise JournalBlocked("V052_PAID_ISSUER_PIN_CONFIG_MISSING")
    if not isinstance(public_key, bytes) or len(public_key) != 32:
        raise JournalBlocked("V052_PAID_ISSUER_PUBLIC_KEY_INVALID")
    if sha256(public_key).hexdigest() != trusted_raw_key_sha256:
        raise JournalBlocked("V052_PAID_ISSUER_PIN_MISMATCH")
    return public_key
