"""SERA v0.52 signed delegated model callback with verified source lineage.

This callback is ONLY for an isolated, single-scene synchronous LAB lane.
It does not create a signer, supply credentials, or launch provider calls by
itself. Revision changes are accepted ONLY after the model writer's durable
receipt matches exact rewritten prose. Unknown in-flight spends block new work.
"""
from __future__ import annotations

from hashlib import sha256

from experiments.sera.coverage import prose_hash
from experiments.sera.provider_grant_journal_v052 import JournalBlocked
from experiments.sera.request_policy import enforce_no_output_token_limit
from experiments.sera.openrouter_real_transport_v052 import decode_receipted_wire
from experiments.sera.world_state_v02 import canonical


def create_delegated_provider(*, budget, transport):
    if not callable(transport):
        raise JournalBlocked("V052_DELEGATED_TRANSPORT_MISSING")
    active=[budget.initial_sha]
    models=budget.models

    def use_source(prose):
        sha=prose_hash(prose)
        if not budget.revision_registered(sha):
            raise JournalBlocked("V052_DELEGATED_SOURCE_LINEAGE_NOT_PROVEN")
        active[0]=sha
        return sha

    def provider_call(*, key, model, prepared):
        if not isinstance(prepared,dict) or not isinstance(prepared.get("request"),dict):
            raise JournalBlocked("V052_DELEGATED_REQUEST_INVALID")
        request=prepared["request"]
        enforce_no_output_token_limit(request)
        role=next((r for r,v in models.items() if v==model),None)
        if role is None:
            raise JournalBlocked("V052_DELEGATED_MODEL_NOT_ALLOWLISTED")
        receipt=budget.invoke(role=role,revision_sha=active[0],model=model,
                              payload=request,transport=transport)
        return (decode_receipted_wire(receipt) if "wire_payload_b64" in receipt
                else receipt)

    def recover_completed(*, model, request, request_sha256):
        if not isinstance(request,dict):
            raise JournalBlocked("V052_DELEGATED_RECOVERY_REQUEST_INVALID")
        expected=sha256(canonical({"model":model,"request":request})
                        .encode("utf-8")).hexdigest()
        if expected != request_sha256:
            raise JournalBlocked("V052_DELEGATED_RECOVERY_REQUEST_DRIFT")
        role=next((r for r,v in models.items() if v==model),None)
        if role is None:
            raise JournalBlocked("V052_DELEGATED_RECOVERY_MODEL_INVALID")
        receipt=budget.completed(role=role,revision_sha=active[0],
                                 model=model,payload=request)
        return (decode_receipted_wire(receipt) if "wire_payload_b64" in receipt
                else receipt)

    provider_call.use_source=use_source
    provider_call.recover_completed=recover_completed
    return provider_call
