"""SERA v0.33: hardened authenticated HTTPS GET for a future Project_LUMI G2 source.

This is a client contract, NOT a deployed Project_LUMI endpoint. The
existing /stories/latest GET lacks frozen world and character heads,
while /production POST MUTATES story and cannot be used for preflight.

No database access, POST, outbound model call, or canonical write.
An external G2 service must implement an authenticated READ-ONLY endpoint,
a single consistent head snapshot, and a trusted signing key. The client
pins issuer/audience/key and verifies freshness + single-use nonce before
v0.32 is allowed to accept any G2 rows.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import secrets
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import (
    HTTPSHandler, HTTPRedirectHandler, Request, build_opener,
)

from experiments.sera.coverage import CoverageError
from experiments.sera.g2_readonly_scope_bridge_v032 import (
    SCHEMA, SCOPE, _uuid, digest,
)
from experiments.sera.world_state_v02 import canonical

API_PATH = "/api/internal/sera/g2-authority-readonly"
READ_PERMISSION = "g2.story_authority.readonly"
MAX_BODY_BYTES = 1_500_000
CLOCK_SKEW_SECONDS = 30


def require(ok, code):
    if not ok:
        raise CoverageError(code)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CoverageError("V033_HTTP_REDIRECT_FORBIDDEN")


def _origin(endpoint):
    require(isinstance(endpoint, str), "V033_ENDPOINT_INVALID")
    parts = urlsplit(endpoint)
    require(parts.scheme == "https" and parts.hostname and
            parts.username is None and parts.password is None and
            parts.query == "" and parts.fragment == "" and
            parts.path == API_PATH and
            parts.port in (None, 443) and
            parts.hostname == parts.hostname.lower() and
            not parts.hostname.replace(".", "").isdigit() and
            ":" not in parts.hostname and
            parts.hostname != "localhost",
            "V033_ENDPOINT_NOT_PINNED_HTTPS")
    # A trusted operator must configure a hostname, not an arbitrary
    # user supplied URL/IP with credentials or a redirect.
    return parts


def _get_json(*, url, authorization, timeout, max_bytes):
    opener = build_opener(HTTPSHandler(context=ssl.create_default_context()),
                          _NoRedirect())
    req = Request(url, headers={
        "Authorization": "Bearer " + authorization,
        "Accept": "application/json",
        "Cache-Control": "no-store",
    }, method="GET")
    try:
        with opener.open(req, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
            require(len(raw) <= max_bytes, "V033_RESPONSE_TOO_LARGE")
            require(response.status == 200, "V033_SOURCE_HTTP_NOT_200")
            require(response.headers.get("Content-Type", "").split(";")[0] ==
                    "application/json",
                    "V033_SOURCE_MEDIA_TYPE_INVALID")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise CoverageError("V033_G2_READ_UNAVAILABLE") from exc
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise CoverageError("V033_G2_JSON_INVALID") from exc
    return obj


def signed_message(rows, provenance):
    """Exact JSON message that the APP server MUST sign with its private key.

    Only public verifier material is present on the SERA client. The
    signature field itself is excluded; the full provenance is covered.
    """
    require(isinstance(provenance, dict), "V033_PROVENANCE_INVALID")
    without_signature = {
        k: v for k, v in provenance.items() if k != "signature"
    }
    return canonical({
        "domain": "sera-g2-authority-readonly-v033",
        "rows_sha256": digest(rows),
        "provenance": without_signature,
    }).encode("utf-8")


def create_reader(*, endpoint, bearer_token, expected_scope,
                  issuer, audience, trusted_key_id, verify_signature,
                  transport=_get_json, clock=time.time,
                  nonce_factory=lambda: secrets.token_urlsafe(32)):
    """Returns (readonly_lookup, verify_source) suitable for v0.32.

    A new nonce is created per GET and consumed at verification. This
    prevents signed stale data from being recycled into another job.
    For production, verify_signature MUST use an app-pinned asymmetric
    public key; model-supplied keys and HMAC fixture keys are forbidden.
    """
    _origin(endpoint)
    require(isinstance(bearer_token, str) and
            20 <= len(bearer_token) <= 8192 and
            all(c not in bearer_token for c in "\r\n"),
            "V033_READONLY_CREDENTIAL_INVALID")
    require(isinstance(expected_scope, dict) and
            set(expected_scope) == set(SCOPE) and
            all(_uuid(expected_scope[k]) for k in SCOPE),
            "V033_EXPECTED_G2_SCOPE_INVALID")
    require(all(isinstance(v, str) and v.strip()
                for v in (issuer, audience, trusted_key_id)) and
            callable(verify_signature) and callable(transport) and
            callable(clock) and callable(nonce_factory),
            "V033_TRUST_BOUNDARY_UNCONFIGURED")
    pending = {}

    def readonly_lookup(*, contract_id):
        require(_uuid(contract_id), "V033_CONTRACT_ID_INVALID")
        nonce = nonce_factory()
        require(isinstance(nonce, str) and
                len(nonce) >= 24 and len(nonce) <= 180 and
                all(ch.isalnum() or ch in "_-" for ch in nonce),
                "V033_NONCE_INVALID")
        url = (endpoint + "?contractId=" + quote(contract_id, safe="") +
               "&nonce=" + quote(nonce, safe=""))
        pending[contract_id] = {"nonce": nonce, "received_at": clock()}
        document = transport(
            url=url, authorization=bearer_token, timeout=15,
            max_bytes=MAX_BODY_BYTES,
        )
        require(isinstance(document, dict) and
                document.get("schema") == SCHEMA and
                isinstance(document.get("rows"), dict) and
                isinstance(document.get("provenance"), dict),
                "V033_G2_HTTP_DOCUMENT_INVALID")
        return deepcopy(document)

    def verify_source(rows, provenance):
        contract_id = provenance.get("contract_id")
        state = pending.pop(contract_id, None)
        require(isinstance(state, dict),
                "V033_READ_NOT_REQUESTED_OR_ALREADY_CONSUMED")
        now = clock()
        require(provenance.get("source") == "PROJECT_LUMI_G2_READONLY" and
                provenance.get("contract_id") == contract_id and
                provenance.get("nonce") == state["nonce"] and
                provenance.get("issuer") == issuer and
                provenance.get("audience") == audience and
                provenance.get("key_id") == trusted_key_id and
                provenance.get("rows_sha256") == digest(rows) and
                provenance.get("scope_sha256") == digest(expected_scope) and
                provenance.get("permission") == READ_PERMISSION and
                isinstance(provenance.get("snapshot_id"), str) and
                provenance["snapshot_id"].strip() and
                isinstance(provenance.get("signature"), str) and
                provenance["signature"] and
                type(provenance.get("issued_at")) in (float, int) and
                type(provenance.get("expires_at")) in (float, int) and
                state["received_at"] - CLOCK_SKEW_SECONDS <=
                    provenance["issued_at"] <=
                    now + CLOCK_SKEW_SECONDS and
                provenance["expires_at"] > now and
                provenance["expires_at"] -
                    provenance["issued_at"] <= 120 and
                now - state["received_at"] <= 30,
                "V033_SIGNED_SCOPE_FRESHNESS_OR_PERMISSION_INVALID")
        try:
            valid = verify_signature(
                signed_message(rows, provenance),
                provenance["signature"], trusted_key_id,
            )
        except Exception as exc:
            raise CoverageError("V033_G2_SOURCE_SIGNATURE_INVALID") from exc
        require(valid is True, "V033_G2_SOURCE_SIGNATURE_INVALID")
        return True

    return readonly_lookup, verify_source
