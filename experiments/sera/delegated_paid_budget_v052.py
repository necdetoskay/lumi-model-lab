"""SERA v0.52: finite, signed *delegated* paid-call authority (LAB ONLY).

A signer may preapprove a finite set of ROLE capacities for as-yet-unknown
writer-generated revisions. Each exact request is allocated once by a shared
SQLite journal under BEGIN IMMEDIATE; every new request requires all earlier
allocations to have complete, priced receipts. STARTED/unknown or unpriced
results block further spend. No blind POST, output-token cap, or canon writes.

This is an OBSERVED cost guard, NOT a guaranteed provider charge ceiling.
No signing key or real provider credentials are created or loaded here.
"""
from __future__ import annotations

import base64
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import sqlite3
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from experiments.sera.coverage import prose_hash
from experiments.sera.provider_grant_journal_v052 import (
    JournalBlocked, _canonical, _hash)
from experiments.sera.request_policy import enforce_no_output_token_limit

ROLES = frozenset({"extraction", "semantic", "typed", "writer"})
SCOPE = "SERA_V052_MARA_DELEGATED_NONCANONICAL_PAID"
SCHEMA = "sera.v052-delegated-paid-budget"


def _money(value):
    if not isinstance(value, str):
        raise JournalBlocked("V052_DELEGATED_MONEY_MUST_BE_DECIMAL_STRING")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise JournalBlocked("V052_DELEGATED_MONEY_INVALID") from exc
    if not amount.is_finite() or amount <= 0:
        raise JournalBlocked("V052_DELEGATED_MONEY_INVALID")
    return amount


def verify_delegated_approval(*, approval, trusted_public_key,
                              source_sha256, world_sha256, scene_key,
                              policy_sha256, approved_models, max_rewrites,
                              now=None):
    """Only a trusted, separately pinned Ed25519 key authorizes billable scope."""
    if not isinstance(approval, dict) or set(approval) != {"manifest", "signature"}:
        raise JournalBlocked("V052_DELEGATED_SIGNED_APPROVAL_REQUIRED")
    m = approval["manifest"]
    required = {"schema", "scope", "approval_id", "expires_at",
                "source_sha256", "world_sha256", "scene_key",
                "policy_sha256", "approved_models", "max_rewrites",
                "max_posts", "max_posts_per_role", "max_observed_usd"}
    if not isinstance(m, dict) or set(m) != required:
        raise JournalBlocked("V052_DELEGATED_MANIFEST_FIELDS_INVALID")
    expected = {"schema":SCHEMA, "scope":SCOPE,
                "source_sha256":source_sha256, "world_sha256":world_sha256,
                "scene_key":scene_key, "policy_sha256":policy_sha256,
                "approved_models":approved_models, "max_rewrites":max_rewrites}
    if any(m[k] != v for k,v in expected.items()):
        raise JournalBlocked("V052_DELEGATED_SCOPE_DRIFT")
    if not isinstance(m["approval_id"],str) or not m["approval_id"].strip():
        raise JournalBlocked("V052_DELEGATED_APPROVAL_ID_INVALID")
    if type(m["expires_at"]) is not int or m["expires_at"] <= (
        time.time() if now is None else now):
        raise JournalBlocked("V052_DELEGATED_EXPIRED")
    if not isinstance(approved_models,dict) or set(approved_models) != ROLES or (
        len(set(approved_models.values())) != 4):
        raise JournalBlocked("V052_DELEGATED_MODEL_ALLOWLIST_INVALID")
    if any(not isinstance(v,str) or not v or v.startswith("synthetic/")
           for v in approved_models.values()):
        raise JournalBlocked("V052_DELEGATED_MODEL_ALLOWLIST_INVALID")
    if type(max_rewrites) is not int or not 0 <= max_rewrites <= 2:
        raise JournalBlocked("V052_DELEGATED_REWRITE_POLICY_INVALID")
    limit=m["max_posts"]
    per_role=m["max_posts_per_role"]
    if (type(limit) is not int or not 1 <= limit <= 100 or
        not isinstance(per_role,dict) or set(per_role) != ROLES or
        any(type(n) is not int or not 0 <= n <= limit for n in per_role.values()) or
        sum(per_role.values()) < 1):
        raise JournalBlocked("V052_DELEGATED_CALL_POLICY_INVALID")
    _money(m["max_observed_usd"])
    try:
        if not isinstance(trusted_public_key, bytes) or len(trusted_public_key) != 32:
            raise ValueError("no pinned trust root")
        Ed25519PublicKey.from_public_bytes(trusted_public_key).verify(
            base64.b64decode(approval["signature"],validate=True),
            _canonical(m).encode("utf-8"))
    except (InvalidSignature,ValueError,TypeError) as exc:
        raise JournalBlocked("V052_DELEGATED_SIGNATURE_INVALID") from exc
    return m


def _raw_envelope(envelope):
    """Parse only a RECEIPTED envelope; no provider I/O."""
    if not isinstance(envelope,dict):
        raise JournalBlocked("V052_DELEGATED_RECEIPT_CORRUPT")
    if "wire_payload_b64" in envelope:
        if envelope.get("http_status") != 200:
            raise JournalBlocked("V052_DELEGATED_NON_SUCCESS_RECEIPT_HOLD")
        try:
            return json.loads(base64.b64decode(
                envelope["wire_payload_b64"],validate=True).decode("utf-8"))
        except (TypeError,ValueError,UnicodeDecodeError) as exc:
            raise JournalBlocked("V052_DELEGATED_WIRE_UNPARSEABLE") from exc
    if envelope.get("error") is not None:
        raise JournalBlocked("V052_DELEGATED_PROVIDER_ERROR_HOLD")
    return envelope.get("raw")


def _priced(envelope):
    body=_raw_envelope(envelope)
    if not isinstance(body,dict) or not isinstance(body.get("id"),str) or (
        not body["id"]) or not isinstance(body.get("usage"),dict):
        raise JournalBlocked("V052_DELEGATED_PROVIDER_RECEIPT_INCOMPLETE")
    usage=body["usage"]
    try:
        cost=Decimal(str(usage["cost"]))
    except (KeyError,ValueError,InvalidOperation,TypeError) as exc:
        raise JournalBlocked("V052_DELEGATED_PROVIDER_PRICE_MISSING") from exc
    if not cost.is_finite() or cost < 0:
        raise JournalBlocked("V052_DELEGATED_PROVIDER_PRICE_INVALID")
    return body,cost


class DelegatedBudget:
    """Use the SAME SQLite file as ProviderJournal; one worker cohort only."""

    def __init__(self, journal, *, approval, trusted_public_key,
                 source_sha256, world_sha256, scene_key, policy_sha256,
                 approved_models, max_rewrites):
        self.journal=journal
        self.manifest=verify_delegated_approval(
            approval=approval,trusted_public_key=trusted_public_key,
            source_sha256=source_sha256,world_sha256=world_sha256,
            scene_key=scene_key,policy_sha256=policy_sha256,
            approved_models=approved_models,max_rewrites=max_rewrites)
        self.approval_id=self.manifest["approval_id"]
        self.initial_sha=source_sha256
        self.world_sha=world_sha256
        self.scene_key=scene_key
        self.policy_sha=policy_sha256
        self.models=dict(approved_models)
        self.digest=_hash(self.manifest)
        with journal._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS delegated_approvals (
                approval_id TEXT PRIMARY KEY, manifest_sha TEXT NOT NULL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS delegated_requests (
                approval_id TEXT NOT NULL, request_fingerprint TEXT NOT NULL,
                grant_id TEXT NOT NULL UNIQUE, request_id TEXT NOT NULL UNIQUE,
                stage TEXT NOT NULL, revision_sha TEXT NOT NULL,
                PRIMARY KEY(approval_id,request_fingerprint)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS delegated_revisions (
                approval_id TEXT NOT NULL, revision_sha TEXT NOT NULL,
                parent_sha TEXT, writer_fingerprint TEXT,
                PRIMARY KEY(approval_id,revision_sha)
            )""")
            db.execute("BEGIN IMMEDIATE")
            prior=db.execute(
                "SELECT manifest_sha FROM delegated_approvals WHERE approval_id=?",
                (self.approval_id,)).fetchone()
            if prior and prior[0] != self.digest:
                raise JournalBlocked("V052_DELEGATED_APPROVAL_ID_REUSED")
            if prior is None:
                db.execute("INSERT INTO delegated_approvals VALUES (?,?)",
                           (self.approval_id,self.digest))
                db.execute("INSERT INTO delegated_revisions VALUES (?,?,NULL,NULL)",
                           (self.approval_id,self.initial_sha))

    def _request_hash(self, *, role, revision_sha, model, payload):
        if role not in ROLES or model != self.models[role]:
            raise JournalBlocked("V052_DELEGATED_MODEL_OR_ROLE_DRIFT")
        enforce_no_output_token_limit(payload)
        return _hash({
            "approval_id":self.approval_id,"role":role,
            "revision_sha":revision_sha,"model":model,"request":payload,
            "source_sha256":self.initial_sha,
            "world_sha256":self.world_sha,
            "scene_key":self.scene_key,"policy_sha256":self.policy_sha})

    def _binding(self, role, revision_sha, model, fingerprint):
        return dict(source_sha256=self.initial_sha,revision_sha256=revision_sha,
                    world_sha256=self.world_sha,scene_key=self.scene_key,
                    policy_sha256=self.policy_sha,model=model,stage=role,
                    request_fingerprint=fingerprint,approval_id=self.approval_id)

    def _find(self, db, fingerprint):
        return db.execute("""SELECT grant_id,request_id,stage,revision_sha
                             FROM delegated_requests
                             WHERE approval_id=? AND request_fingerprint=?""",
                          (self.approval_id,fingerprint)).fetchone()

    def _observed(self, db):
        total=Decimal("0")
        rows=db.execute("""SELECT r.grant_id,r.stage,r.request_id,c.status,
                                 c.envelope_json,c.envelope_sha
                          FROM delegated_requests r
                          LEFT JOIN calls c ON c.grant_id=r.grant_id
                          WHERE r.approval_id=?""",(self.approval_id,)).fetchall()
        for grant_id,stage,request_id,status,raw,checksum in rows:
            if status != "RECEIPTED":
                raise JournalBlocked("V052_DELEGATED_PREVIOUS_REQUEST_NOT_RECEIPTED")
            try:
                envelope=json.loads(raw)
                if _hash(envelope) != checksum:
                    raise ValueError("tampered")
            except (TypeError,ValueError) as exc:
                raise JournalBlocked("V052_DELEGATED_ARCHIVE_CORRUPT") from exc
            _,cost=_priced(envelope)
            total+=cost
        return rows,total

    def allocate(self, *, role, revision_sha, model, payload):
        """Atomically allocate one exact request; no external POST here."""
        fingerprint=self._request_hash(
            role=role,revision_sha=revision_sha,model=model,payload=payload)
        with self.journal._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            exists=self._find(db,fingerprint)
            if exists:
                return fingerprint,exists[0],exists[1]
            if int(time.time()) >= self.manifest["expires_at"]:
                raise JournalBlocked("V052_DELEGATED_EXPIRED")
            if db.execute("""SELECT 1 FROM delegated_revisions
                             WHERE approval_id=? AND revision_sha=?""",
                          (self.approval_id,revision_sha)).fetchone() is None:
                raise JournalBlocked("V052_DELEGATED_UNPROVEN_REVISION")
            rows,total=self._observed(db)
            if total >= _money(self.manifest["max_observed_usd"]):
                raise JournalBlocked("V052_DELEGATED_OBSERVED_COST_GUARD")
            if len(rows) >= self.manifest["max_posts"]:
                raise JournalBlocked("V052_DELEGATED_POST_COUNT_EXHAUSTED")
            if sum(1 for row in rows if row[1] == role) >= (
                self.manifest["max_posts_per_role"][role]):
                raise JournalBlocked("V052_DELEGATED_ROLE_COUNT_EXHAUSTED")
            unique=_hash({"approval_id":self.approval_id,"request":fingerprint})
            grant_id="v052-delegated-"+unique
            request_id="v052-request-"+unique
            db.execute("""INSERT INTO delegated_requests VALUES (?,?,?,?,?,?)""",
                       (self.approval_id,fingerprint,grant_id,request_id,
                        role,revision_sha))
            return fingerprint,grant_id,request_id

    def completed(self, *, role, revision_sha, model, payload):
        """No allocation; read an existing priced or unpriced receipt."""
        fingerprint=self._request_hash(
            role=role,revision_sha=revision_sha,model=model,payload=payload)
        with self.journal._connect() as db:
            row=self._find(db,fingerprint)
        if not row:
            raise JournalBlocked("V052_DELEGATED_RECOVERY_UNKNOWN_REQUEST")
        return self.journal.read_completed(
            grant_id=row[0],request_id=row[1],
            binding=self._binding(role,revision_sha,model,fingerprint),
            model=model,payload=payload)

    def invoke(self, *, role, revision_sha, model, payload, transport):
        fingerprint,grant_id,request_id=self.allocate(
            role=role,revision_sha=revision_sha,model=model,payload=payload)
        binding=self._binding(role,revision_sha,model,fingerprint)
        # Validated signed scope was checked at construction and allocation.
        self.journal.register_grant(
            grant_id=grant_id,binding=binding,authorized=True)
        return self.journal.execute_once(
            grant_id=grant_id,binding=binding,request_id=request_id,
            model=model,payload=payload,transport=transport)

    def register_model_revision(self, *, parent_prose, revised_prose,
                                writer_payload, writer_response_id):
        """Only a durable writer receipt can introduce a new SHA.

        This cannot be invoked with a hand-edited output: exact revised scene
        bytes and previous source SHA must match the receipted writer reply.
        """
        parent=prose_hash(parent_prose)
        revised=prose_hash(revised_prose)
        if revised == parent:
            raise JournalBlocked("V052_DELEGATED_NO_CHANGED_REVISION")
        with self.journal._connect() as db:
            if not db.execute("""SELECT 1 FROM delegated_revisions
                 WHERE approval_id=? AND revision_sha=?""",
                 (self.approval_id,parent)).fetchone():
                raise JournalBlocked("V052_DELEGATED_UNKNOWN_PARENT")
        envelope=self.completed(
            role="writer",revision_sha=parent,model=self.models["writer"],
            payload=writer_payload)
        body,_=_priced(envelope)
        if body["id"] != writer_response_id or body.get("model") != self.models["writer"]:
            raise JournalBlocked("V052_DELEGATED_WRITER_RECEIPT_ID_MISMATCH")
        choices=body.get("choices")
        if not isinstance(choices,list) or len(choices)!=1 or (
            choices[0].get("finish_reason") != "stop"):
            raise JournalBlocked("V052_DELEGATED_WRITER_INCOMPLETE")
        from experiments.sera.openrouter_scene_writer_v021 import _parse
        data=_parse(choices[0].get("message",{}).get("content"))
        if data["source_prose_sha256"] != parent or data["revised_scene_prose"] != revised_prose:
            raise JournalBlocked("V052_DELEGATED_WRITER_REVISION_UNPROVEN")
        with self.journal._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing=db.execute("""SELECT parent_sha,writer_fingerprint
                 FROM delegated_revisions WHERE approval_id=? AND revision_sha=?""",
                (self.approval_id,revised)).fetchone()
            fingerprint=self._request_hash(
                role="writer",revision_sha=parent,
                model=self.models["writer"],payload=writer_payload)
            expected=(parent,fingerprint)
            if existing and existing != expected:
                raise JournalBlocked("V052_DELEGATED_REVISION_REBIND")
            if not existing:
                db.execute("""INSERT INTO delegated_revisions VALUES (?,?,?,?)""",
                           (self.approval_id,revised,parent,fingerprint))
        return revised
