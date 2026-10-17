"""Verify independent Ed25519 single-run paid authorization, never sign here.

The signing private key must be outside the runner/repository. An approval is
not generated from `authorized=True` and cannot be inherited from Aion.
"""
import base64
import time
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from experiments.sera.provider_grant_journal_v052 import JournalBlocked, _canonical

def verify_approval(*, approval, trusted_public_key, source_sha256,
                    world_sha256, scene_key, policy_sha256, approved_models,
                    grants, now=None):
    if not isinstance(approval, dict) or set(approval) != {"manifest","signature"}:
        raise JournalBlocked("V052_SIGNED_APPROVAL_REQUIRED")
    manifest = approval["manifest"]
    expected = dict(scope="SERA_V052_MARA_NONCANONICAL_PAID",
                    source_sha256=source_sha256,world_sha256=world_sha256,
                    scene_key=scene_key,policy_sha256=policy_sha256,
                    approved_models=approved_models,grants=grants)
    if not isinstance(manifest,dict) or any(manifest.get(k) != v for k,v in expected.items()):
        raise JournalBlocked("V052_APPROVAL_SCOPE_OR_BINDING_DRIFT")
    if set(manifest) != set(expected) | {"expires_at","approval_id"}:
        raise JournalBlocked("V052_APPROVAL_FIELDS_INVALID")
    if not isinstance(manifest["approval_id"],str) or not manifest["approval_id"]:
        raise JournalBlocked("V052_APPROVAL_ID_REQUIRED")
    expires=manifest["expires_at"]
    if type(expires) is not int or expires <= (time.time() if now is None else now):
        raise JournalBlocked("V052_APPROVAL_EXPIRED")
    try:
        if not isinstance(trusted_public_key,bytes) or len(trusted_public_key)!=32:
            raise ValueError("untrusted public key")
        signature=base64.b64decode(approval["signature"],validate=True)
        Ed25519PublicKey.from_public_bytes(trusted_public_key).verify(
            signature,_canonical(manifest).encode("utf-8"))
    except (InvalidSignature,TypeError,ValueError) as exc:
        raise JournalBlocked("V052_APPROVAL_SIGNATURE_INVALID") from exc
    if len({item["grant_id"] for item in grants.values()}) != len(grants) or len(
        {item["request_id"] for item in grants.values()}) != len(grants):
        raise JournalBlocked("V052_DUPLICATE_GRANT_OR_REQUEST_ID")
    return True
