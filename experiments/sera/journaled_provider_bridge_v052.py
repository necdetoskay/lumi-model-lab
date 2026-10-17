"""SERA v0.52 P0/P1 bridge: journal-backed callback for existing model adapters.

No network client and no authorization creation in this module. Every distinct
billable model request needs its OWN pre-authorized grant. Inject a verified
grant resolver and transport; missing authorization always fails closed.
"""
from __future__ import annotations

from hashlib import sha256
import json

from experiments.sera.provider_grant_journal_v052 import JournalBlocked, _hash
from experiments.sera.request_policy import enforce_no_output_token_limit
from experiments.sera.signed_paid_approval_v052 import verify_approval

STAGES = frozenset({"extraction", "semantic", "typed", "writer"})


def create_journaled_provider(*, journal, source_sha256, world_sha256,
                              scene_key, policy_sha256, approved_models,
                              grants, transport, authorization_verified=False,
                              approval=None, trusted_public_key=None):
    """Return adapter matching provider_call(key=, model=, prepared=).

    grants: immutable mapping request fingerprint -> {"grant_id","request_id"}.
    Grant registration is forbidden here. Do not bind unknown/new source SHA
    to a previous grant after a rewrite: launch a fresh authorized grant set.
    """
    # A boolean assertion by the caller is NOT authorization.
    if authorization_verified is True and approval is None:
        raise JournalBlocked("V052_SIGNED_APPROVAL_REQUIRED")
    if not isinstance(approved_models, dict) or set(approved_models) != STAGES:
        raise JournalBlocked("V052_MODEL_ROLE_ALLOWLIST_INVALID")
    if len(set(approved_models.values())) != 4 or any(
        not isinstance(m, str) or not m.strip() or m.startswith("synthetic/")
        for m in approved_models.values()
    ):
        raise JournalBlocked("V052_MODEL_ROLE_ALLOWLIST_INVALID")
    if not isinstance(grants, dict) or not callable(transport):
        raise JournalBlocked("V052_GRANTS_OR_TRANSPORT_INVALID")
    for value in (source_sha256, world_sha256, policy_sha256):
        if not isinstance(value, str) or len(value) != 64 or any(
            c not in "0123456789abcdef" for c in value):
            raise JournalBlocked("V052_FINGERPRINT_INVALID")
    if not isinstance(scene_key, str) or not scene_key.strip():
        raise JournalBlocked("V052_SCENE_KEY_INVALID")
    verify_approval(approval=approval, trusted_public_key=trusted_public_key,
                    source_sha256=source_sha256,world_sha256=world_sha256,
                    scene_key=scene_key,policy_sha256=policy_sha256,
                    approved_models=approved_models,grants=grants)
    models = dict(approved_models)

    def provider_call(*, key, model, prepared):
        # Key is intentionally not read or saved by this layer. The transport
        # owns secure key handling; no credential is written to journal.
        if not isinstance(prepared, dict) or not isinstance(prepared.get("request"), dict):
            raise JournalBlocked("V052_MODEL_REQUEST_INVALID")
        request = prepared["request"]
        enforce_no_output_token_limit(request)
        stage = next((s for s, m in models.items() if m == model), None)
        if stage is None:
            raise JournalBlocked("V052_MODEL_NOT_ALLOWLISTED")
        signature = _hash({"stage":stage,"model":model,"request":request,
                           "source_sha256":source_sha256,
                           "world_sha256":world_sha256,
                           "scene_key":scene_key,"policy_sha256":policy_sha256})
        grant = grants.get(signature)
        if not isinstance(grant, dict) or set(grant) != {"grant_id","request_id"}:
            raise JournalBlocked("V052_REQUEST_SPECIFIC_GRANT_MISSING")
        binding = dict(source_sha256=source_sha256,world_sha256=world_sha256,
                       scene_key=scene_key,policy_sha256=policy_sha256,
                       model=model,stage=stage,request_fingerprint=signature)
        # Pre-registered approval must bind this exact request+model+source.
        return journal.execute_once(
            grant_id=grant["grant_id"], binding=binding,
            request_id=grant["request_id"], model=model,payload=request,
            transport=transport)
    return provider_call


def fingerprint_for_request(*, stage, model, request, source_sha256,
                            world_sha256, scene_key, policy_sha256):
    """Pure planning only: fingerprint an expected request, no provider POST."""
    if stage not in STAGES or not isinstance(request,dict):
        raise JournalBlocked("V052_REQUEST_PLAN_INVALID")
    enforce_no_output_token_limit(request)
    return _hash(dict(stage=stage,model=model,request=request,
                      source_sha256=source_sha256,world_sha256=world_sha256,
                      scene_key=scene_key,policy_sha256=policy_sha256))
