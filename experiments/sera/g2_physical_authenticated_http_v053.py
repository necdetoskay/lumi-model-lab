"""SERA v0.53 — proposed *read-only* HTTPS G2 physical registry client.

This is a consumer contract, NOT proof the endpoint is deployed. There is
no G2 POST, provider POST, DB mutation, fallback-to-prose or self-signature.
Authenticated v0.32 authority must be resolved independently first. A fresh
per-request nonce is generated here and verified by the app-pinned v0.36
Ed25519 reader, using an app-owned durable nonce-consumer callback.

The external G2 app MUST implement a consistent signed physical snapshot.
"""
from __future__ import annotations

import secrets
import time
from urllib.parse import quote, urlsplit

from experiments.sera.coverage import CoverageError
from experiments.sera.g2_authenticated_http_reader_v033 import (
    _get_json, MAX_BODY_BYTES,
)
from experiments.sera.g2_physical_projection_v033 import SCHEMA as PHYSICAL_SCHEMA
from experiments.sera.g2_readonly_scope_bridge_v032 import _uuid
from experiments.sera.signed_physical_reconciliation_v053 import (
    reconcile_signed_physical_source,
)

API_PATH="/api/internal/sera/g2-physical-readonly"
PERMISSION="g2.physical_registry.readonly"


def need(ok,code):
    if not ok:
        raise CoverageError(code)


def physical_https_origin(endpoint):
    """Pin a single HTTPS hostname+path; no localhost/IP/redirect/credentials."""
    need(isinstance(endpoint,str),"V053_PHYSICAL_ENDPOINT_INVALID")
    try:
        parts=urlsplit(endpoint)
        # Reject byte-level alias tricks before handing hostname to resolver.
        host=parts.hostname
        port=parts.port
    except ValueError as exc:
        raise CoverageError("V053_PHYSICAL_ENDPOINT_INVALID") from exc
    need(
        parts.scheme=="https" and host is not None and
        parts.username is None and parts.password is None and
        not parts.query and not parts.fragment and
        parts.path==API_PATH and port in (None,443) and
        host==host.lower() and host!="localhost" and
        ":" not in host and
        not host.replace(".","").isdigit() and
        all(ch.isascii() and (ch.islower() or ch.isdigit()
            or ch in ".-") for ch in host) and
        "." in host and ".." not in host and
        not host.startswith(".") and not host.endswith("."),
        "V053_PHYSICAL_ENDPOINT_NOT_PINNED_HTTPS")
    return endpoint


def create_physical_reader(
    *,endpoint,bearer_token,public_key_pem,raw_public_key_sha256,
    key_id,issuer,audience,consume_nonce,
    transport=_get_json,nonce_factory=lambda:secrets.token_urlsafe(32),
    clock=time.time,
):
    """Return read-and-reconcile callback; caller supplies independent G2.

    public_key_pem/key fingerprint, bearer token and consume_nonce must be
    deployment-owned, never copied from response, user text or story model.
    """
    physical_https_origin(endpoint)
    need(isinstance(bearer_token,str) and
         20<=len(bearer_token)<=8192 and
         not any(ch in bearer_token for ch in "\r\n"),
         "V053_PHYSICAL_READ_CREDENTIAL_INVALID")
    need(all(isinstance(x,str) and x.strip() for x in (
         public_key_pem,raw_public_key_sha256,key_id,issuer,audience)) and
         callable(consume_nonce) and callable(transport) and
         callable(nonce_factory) and callable(clock),
         "V053_PHYSICAL_TRUST_NOT_CONFIGURED")

    def read_and_reconcile(
        *,contract_id,authority,prose,scene_key,
        registry,candidate_lexicon,model_report=None,
    ):
        need(_uuid(contract_id) and isinstance(authority,dict) and
             authority.get("authenticated_source_preflight") is True and
             authority.get("g2_contract_id")==contract_id and
             authority.get("canonical_commit_authorized") is False and
             authority.get("world_db_writes")==0 and
             authority.get("g2_commit_request") is None,
             "V053_G2_AUTHORITY_NOT_AUTHENTICATED")
        nonce=nonce_factory()
        need(isinstance(nonce,str) and 24<=len(nonce)<=180 and
             all(ch.isascii() and (ch.isalnum() or ch in "_-")
                 for ch in nonce),
             "V053_PHYSICAL_NONCE_INVALID")
        url=(endpoint+"?contractId="+quote(contract_id,safe="")+
             "&nonce="+quote(nonce,safe=""))
        packet=transport(
            url=url,authorization=bearer_token,timeout=15,
            max_bytes=MAX_BODY_BYTES)
        need(isinstance(packet,dict) and set(packet)=={
             "schema","snapshot","provenance"} and
             packet["schema"]==PHYSICAL_SCHEMA and
             isinstance(packet["snapshot"],dict) and
             isinstance(packet["provenance"],dict),
             "V053_PHYSICAL_HTTP_DOCUMENT_INVALID")
        # Never trust self-declared packet keys, source, scope or time.
        # This single v0.36 verification also consumes the owner-managed
        # nonce ONCE, only after signature and snapshot invariants pass.
        return reconcile_signed_physical_source(
            prose=prose,scene_key=scene_key,
            chronology=None,registry=registry,
            candidate_lexicon=candidate_lexicon,
            authority=authority,projection=packet,
            public_key_pem=public_key_pem,
            raw_public_key_sha256=raw_public_key_sha256,
            key_id=key_id,issuer=issuer,audience=audience,
            expected_nonce=nonce,consume_nonce=consume_nonce,
            now=clock(),model_report=model_report)
    return read_and_reconcile
