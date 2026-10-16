"""v0.36: independently pinned physical-source signature gate (LAB ONLY).

A signed accepted G2 story is not proof of where a character/object is.
Accept a physical snapshot only from an independently provisioned Ed25519
public key and challenge, then delegate to the v0.33 fail-closed projector.
There is deliberately no service URL, fallback to prose, or canon write.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import re
import time

from experiments.sera.coverage import CoverageError
from experiments.sera.g2_ed25519_pinned_reader_v035 import pinned_verifier
from experiments.sera.g2_physical_projection_v033 import SCHEMA, project
from experiments.sera.g2_readonly_scope_bridge_v032 import _uuid, digest
from experiments.sera.world_state_v02 import canonical

DOMAIN = "sera-g2-physical-readonly-v036"
PERMISSION = "g2.physical_registry.readonly"
EXPECTED_PROOF_KEYS = {
    "source", "snapshot_sha256", "g2_authority_sha256",
    "snapshot_id", "nonce", "issuer", "audience", "key_id",
    "permission", "issued_at", "expires_at", "signature",
}


def require(condition, code):
    if not condition:
        raise CoverageError(code)


def project_pinned_physical(
    *, authority, projection, public_key_pem, raw_public_key_sha256,
    key_id, issuer, audience, expected_nonce, consume_nonce, now=None,
):
    """Return a NONCANONICAL projection; require trusted one-use nonce store.

    consume_nonce must atomically mark a nonce consumed, returning True only
    the first time. In deployment this MUST be an app-owned durable store,
    never a caller-controlled lambda. now override is for offline tests only.
    """
    require(isinstance(projection, dict) and
            set(projection) == {"schema", "snapshot", "provenance"} and
            projection.get("schema") == SCHEMA and
            isinstance(projection.get("snapshot"), dict) and
            isinstance(projection.get("provenance"), dict),
            "V036_PHYSICAL_SOURCE_NOT_AVAILABLE")
    require(isinstance(expected_nonce, str) and
            re.fullmatch(r"[A-Za-z0-9_-]{24,180}", expected_nonce) is not None and
            callable(consume_nonce) and
            isinstance(issuer, str) and bool(issuer.strip()) and
            isinstance(audience, str) and bool(audience.strip()),
            "V036_PHYSICAL_TRUST_CONFIG_INVALID")

    snap = deepcopy(projection["snapshot"])
    proof = deepcopy(projection["provenance"])
    require(set(proof) == EXPECTED_PROOF_KEYS and
            proof.get("source") == "PROJECT_LUMI_G2_PHYSICAL_READONLY" and
            proof.get("permission") == PERMISSION and
            proof.get("nonce") == expected_nonce and
            proof.get("issuer") == issuer and
            proof.get("audience") == audience and
            proof.get("key_id") == key_id and
            _uuid(proof.get("snapshot_id")) and
            isinstance(proof.get("snapshot_sha256"), str) and
            re.fullmatch(r"[a-f0-9]{64}", proof["snapshot_sha256"]) is not None and
            isinstance(proof.get("g2_authority_sha256"), str) and
            re.fullmatch(r"[a-f0-9]{64}", proof["g2_authority_sha256"]) is not None and
            isinstance(authority, dict) and
            proof.get("g2_authority_sha256") == digest(authority) and
            proof.get("snapshot_sha256") == digest(snap),
            "V036_PHYSICAL_SCOPE_OR_PROOF_MISMATCH")
    issued = proof.get("issued_at")
    expires = proof.get("expires_at")
    clock = time.time() if now is None else now
    require(type(issued) in (int, float) and
            type(expires) in (int, float) and
            type(clock) in (int, float) and
            0 < issued <= clock + 5 and issued - 5 <= clock < expires and
            0 < expires - issued <= 60,
            "V036_PHYSICAL_EVIDENCE_EXPIRED")
    unsigned = {k: v for k, v in proof.items() if k != "signature"}
    message = canonical({
        "domain": DOMAIN,
        "snapshot_sha256": proof["snapshot_sha256"],
        "provenance": unsigned,
    }).encode("utf-8")
    verify = pinned_verifier(
        public_key_pem=public_key_pem,
        raw_public_key_sha256=raw_public_key_sha256,
        key_id=key_id,
    )
    require(verify(message, proof["signature"], proof["key_id"]),
            "V036_PHYSICAL_SIGNATURE_INVALID")

    # Re-evaluate all physical graph and G2 scope invariants, even after
    # signature verification. A valid signature does not prove completeness.
    result = project(
        authority=authority,
        projection={"schema": SCHEMA, "snapshot": snap, "provenance": proof},
        verify_projection=lambda _s, _p: True,
    )
    # Only after all checks may the app-owned anti-replay store consume the
    # challenge. Never make this result an accepted WorldState write token.
    require(consume_nonce(expected_nonce) is True,
            "V036_PHYSICAL_NONCE_REPLAY")
    require(result["canonical_commit_authorized"] is False and
            result["world_db_writes"] == 0 and
            result["g2_commit_request"] is None,
            "V036_NONCANONICAL_GUARD_VIOLATED")
    return {
        **result,
        "physical_source_verified": True,
        "physical_key_id": key_id,
        "physical_signed_message_sha256": sha256(message).hexdigest(),
        "physical_source_status": "SIGNED_READONLY_SHADOW_ONLY",
    }
