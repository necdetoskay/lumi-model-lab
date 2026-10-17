"""SERA v0.52 delegated paid authorization: source-lineage-bound, bounded, durable.

A signer grants a finite number of calls across a single frozen Mara lineage,
NOT arbitrary source text or an output token ceiling. No keys/network here.
Existing ProviderJournal remains the only POST path. Never re-POST unknown calls.
The trusted issuer public key MUST be pinned independently by deployment.
"""
from __future__ import annotations

import base64
from decimal import Decimal, InvalidOperation
import hashlib
import json
import sqlite3
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from experiments.sera.provider_grant_journal_v052 import (
    ProviderJournal, JournalBlocked, _canonical, _hash)
from experiments.sera.request_policy import enforce_no_output_token_limit
from experiments.sera.openrouter_real_transport_v052 import decode_receipted_wire
from experiments.sera.coverage import prose_hash
from experiments.sera.openrouter_scene_writer_v021 import _parse as parse_writer
from experiments.sera.world_state_v02 import canonical

ROLES = frozenset({"extraction", "semantic", "typed", "writer"})
SCOPE = "SERA_V052_MARA_DELEGATED_NONCANONICAL_PAID"
MAX_CALLS_POLICY = 100
MAX_REWRITES_POLICY = 2


def _usd(value):
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise JournalBlocked("V052_DELEGATED_BUDGET_INVALID") from exc
    if not n.is_finite() or n <= 0:
        raise JournalBlocked("V052_DELEGATED_BUDGET_INVALID")
    return n


def verify_delegation(*, approval, trusted_public_key, source_sha256,
                      world_sha256, scene_key, policy_sha256, models, now=None):
    if not isinstance(approval, dict) or set(approval) != {"manifest", "signature"}:
        raise JournalBlocked("V052_DELEGATED_SIGNED_APPROVAL_REQUIRED")
    m = approval["manifest"]
    keys = {"scope", "approval_id", "expires_at", "source_sha256",
            "world_sha256", "scene_key", "policy_sha256", "approved_models",
            "max_calls", "max_rewrites", "observed_spend_guard_usd"}
    if not isinstance(m, dict) or set(m) != keys:
        raise JournalBlocked("V052_DELEGATED_MANIFEST_FIELDS_INVALID")
    expected = dict(scope=SCOPE, source_sha256=source_sha256,
                    world_sha256=world_sha256, scene_key=scene_key,
                    policy_sha256=policy_sha256, approved_models=models)
    if any(m[k] != v for k, v in expected.items()):
        raise JournalBlocked("V052_DELEGATED_BINDING_DRIFT")
    if (not isinstance(m["approval_id"], str) or not m["approval_id"] or
        type(m["expires_at"]) is not int or
        m["expires_at"] <= (time.time() if now is None else now)):
        raise JournalBlocked("V052_DELEGATED_EXPIRED_OR_ID_INVALID")
    if (not isinstance(models, dict) or set(models) != ROLES or
        len(set(models.values())) != len(ROLES) or
        any(not isinstance(model, str) or not model or
            model.startswith("synthetic/") for model in models.values())):
        raise JournalBlocked("V052_DELEGATED_MODEL_ALLOWLIST_INVALID")
    if (type(m["max_calls"]) is not int or
        not 1 <= m["max_calls"] <= MAX_CALLS_POLICY or
        type(m["max_rewrites"]) is not int or
        not 0 <= m["max_rewrites"] <= MAX_REWRITES_POLICY):
        raise JournalBlocked("V052_DELEGATED_CALL_OR_REVISION_LIMIT_INVALID")
    _usd(m["observed_spend_guard_usd"])
    try:
        if not isinstance(trusted_public_key, bytes) or len(trusted_public_key) != 32:
            raise ValueError("unpinned Ed25519 trust anchor")
        sig = base64.b64decode(approval["signature"], validate=True)
        Ed25519PublicKey.from_public_bytes(trusted_public_key).verify(
            sig, _canonical(m).encode("utf-8"))
    except (ValueError, TypeError, InvalidSignature) as exc:
        raise JournalBlocked("V052_DELEGATED_SIGNATURE_INVALID") from exc
    return m


class DelegatedSceneBudget:
    """One journal/DB for every cooperating worker, with atomic reservations.

    Every new source revision must be proven by a previously RECEIPTED writer
    generation with a source SHA and the exact returned revised_scene_prose.
    Reservation is atomic across workers; a crash never frees a billed slot.
    """

    def __init__(self, *, db_path, approval, trusted_public_key,
                 source_sha256, world_sha256, scene_key, policy_sha256, models):
        self.manifest = verify_delegation(
            approval=approval, trusted_public_key=trusted_public_key,
            source_sha256=source_sha256, world_sha256=world_sha256,
            scene_key=scene_key, policy_sha256=policy_sha256, models=models)
        self.models = dict(models)
        self.journal = ProviderJournal(db_path)
        self.approval_id = self.manifest["approval_id"]
        self.approval_hash = _hash(approval)
        self.root_sha = source_sha256
        self.world_sha = world_sha256
        self.scene_key = scene_key
        self.policy_sha = policy_sha256
        with self.journal._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS delegated_approvals (
                approval_id TEXT PRIMARY KEY, approval_sha TEXT NOT NULL,
                root_sha TEXT NOT NULL, world_sha TEXT NOT NULL,
                policy_sha TEXT NOT NULL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS delegated_revisions (
                approval_id TEXT NOT NULL, revision INTEGER NOT NULL,
                source_sha TEXT NOT NULL, parent_sha TEXT,
                writer_fingerprint TEXT,
                PRIMARY KEY(approval_id,revision),
                UNIQUE(approval_id,source_sha)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS delegated_requests (
                fingerprint TEXT PRIMARY KEY, approval_id TEXT NOT NULL,
                revision INTEGER NOT NULL, source_sha TEXT NOT NULL,
                role TEXT NOT NULL, model TEXT NOT NULL,
                grant_id TEXT NOT NULL UNIQUE, request_id TEXT NOT NULL UNIQUE
            )""")
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT approval_sha,root_sha,world_sha,policy_sha "
                "FROM delegated_approvals WHERE approval_id=?",
                (self.approval_id,)).fetchone()
            expected = (self.approval_hash, self.root_sha,
                        self.world_sha, self.policy_sha)
            if existing and existing != expected:
                raise JournalBlocked("V052_DELEGATED_APPROVAL_ID_REUSED")
            if not existing:
                db.execute("INSERT INTO delegated_approvals VALUES (?,?,?,?,?)",
                           (self.approval_id, *expected))
                db.execute("INSERT INTO delegated_revisions VALUES (?,?,?,?,?)",
                           (self.approval_id, 0, self.root_sha, None, None))

    def _binding(self, *, fingerprint, role, model, source_sha):
        return dict(source_sha256=source_sha, world_sha256=self.world_sha,
                    scene_key=self.scene_key, policy_sha256=self.policy_sha,
                    model=model, stage=role, request_fingerprint=fingerprint,
                    root_source_sha256=self.root_sha,
                    delegated_approval_id=self.approval_id)

    def _fingerprint(self, *, source_sha, role, model, request):
        return _hash(dict(source_sha256=source_sha,
                          root_source_sha256=self.root_sha,
                          world_sha256=self.world_sha, scene_key=self.scene_key,
                          policy_sha256=self.policy_sha, stage=role,
                          model=model, request=request))

    def _existing_receipt_cost(self, db):
        """Fail closed on unknown money. HTTP rejections are not assumed free."""
        rows = db.execute("""SELECT c.status,c.envelope_json
            FROM delegated_requests d LEFT JOIN calls c ON c.grant_id=d.grant_id
            WHERE d.approval_id=?""", (self.approval_id,)).fetchall()
        total = Decimal("0")
        for status, encoded in rows:
            if status != "RECEIPTED" or not encoded:
                raise JournalBlocked("V052_DELEGATED_UNSETTLED_CALL")
            try:
                envelope = json.loads(encoded)
                if "wire_payload_b64" in envelope:
                    envelope = decode_receipted_wire(envelope)
                if envelope.get("error") is not None:
                    raise JournalBlocked("V052_DELEGATED_COST_UNKNOWN")
                usage = envelope["raw"]["usage"]
                price = Decimal(str(usage["cost"]))
                if not price.is_finite() or price < 0:
                    raise ValueError("invalid observed cost")
            except (ValueError, TypeError, KeyError, AttributeError, InvalidOperation):
                raise JournalBlocked("V052_DELEGATED_COST_UNKNOWN") from None
            total += price
        return total

    def _reserve(self, *, source_sha, role, model, request, recovery_only=False):
        enforce_no_output_token_limit(request)
        if role not in ROLES or model != self.models[role]:
            raise JournalBlocked("V052_DELEGATED_MODEL_OR_ROLE_DRIFT")
        fingerprint = self._fingerprint(
            source_sha=source_sha, role=role, model=model, request=request)
        grant_id = "sera-del-" + hashlib.sha256(
            (self.approval_id + ":" + fingerprint).encode()).hexdigest()
        request_id = "sera-req-" + hashlib.sha256(
            (self.approval_id + ":post:" + fingerprint).encode()).hexdigest()
        with self.journal._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            revision = db.execute(
                "SELECT revision FROM delegated_revisions "
                "WHERE approval_id=? AND source_sha=?",
                (self.approval_id,source_sha)).fetchone()
            if revision is None:
                raise JournalBlocked("V052_DELEGATED_UNPROVEN_SOURCE_REVISION")
            existing = db.execute(
                "SELECT approval_id,revision,source_sha,role,model,grant_id,request_id "
                "FROM delegated_requests WHERE fingerprint=?",
                (fingerprint,)).fetchone()
            wanted = (self.approval_id,revision[0],source_sha,role,model,
                      grant_id,request_id)
            if existing:
                if existing != wanted:
                    raise JournalBlocked("V052_DELEGATED_REQUEST_REBIND")
                return fingerprint,grant_id,request_id
            if recovery_only:
                raise JournalBlocked("V052_DELEGATED_RECOVERY_ONLY_NO_NEW_GRANT")
            if time.time() >= self.manifest["expires_at"]:
                raise JournalBlocked("V052_DELEGATED_AUTHORIZATION_EXPIRED")
            count = db.execute(
                "SELECT count(*) FROM delegated_requests WHERE approval_id=?",
                (self.approval_id,)).fetchone()[0]
            if count >= self.manifest["max_calls"]:
                raise JournalBlocked("V052_DELEGATED_CALL_BUDGET_EXHAUSTED")
            if self._existing_receipt_cost(db) >= _usd(
                    self.manifest["observed_spend_guard_usd"]):
                raise JournalBlocked("V052_DELEGATED_OBSERVED_BUDGET_EXHAUSTED")
            db.execute("""INSERT INTO delegated_requests
                VALUES (?,?,?,?,?,?,?,?)""",
                (fingerprint,self.approval_id,revision[0],source_sha,role,
                 model,grant_id,request_id))
        return fingerprint,grant_id,request_id

    def call(self, *, source_sha, role, model, request, transport):
        if not callable(transport) or not isinstance(request, dict):
            raise JournalBlocked("V052_DELEGATED_TRANSPORT_OR_REQUEST_INVALID")
        fingerprint,grant_id,request_id = self._reserve(
            source_sha=source_sha,role=role,model=model,request=request)
        binding = self._binding(fingerprint=fingerprint,role=role,
                                model=model,source_sha=source_sha)
        self.journal.register_grant(
            grant_id=grant_id,binding=binding,authorized=True)
        receipt = self.journal.execute_once(
            grant_id=grant_id,binding=binding,request_id=request_id,
            model=model,payload=request,transport=transport)
        return decode_receipted_wire(receipt) if "wire_payload_b64" in receipt else receipt

    def recover_completed(self, *, source_sha, role, model, request):
        fingerprint,grant_id,request_id = self._reserve(
            source_sha=source_sha,role=role,model=model,request=request,
            recovery_only=True)
        receipt=self.journal.read_completed(
            grant_id=grant_id,
            binding=self._binding(fingerprint=fingerprint,role=role,
                                  model=model,source_sha=source_sha),
            request_id=request_id,model=model,payload=request)
        return decode_receipted_wire(receipt) if "wire_payload_b64" in receipt else receipt

    def accept_writer_revision(self, *, parent_sha, revised_prose,
                               writer_request, generation_id):
        """Advance only from a completed, source-bound writer generation."""
        if not isinstance(revised_prose,str) or not revised_prose.strip():
            raise JournalBlocked("V052_DELEGATED_REVISED_PROSE_INVALID")
        if not isinstance(writer_request,dict):
            raise JournalBlocked("V052_DELEGATED_WRITER_REQUEST_INVALID")
        new_sha=prose_hash(revised_prose)
        if new_sha == parent_sha:
            raise JournalBlocked("V052_DELEGATED_REWRITE_DID_NOT_CHANGE")
        model=self.models["writer"]
        fingerprint=self._fingerprint(source_sha=parent_sha,role="writer",
                                      model=model,request=writer_request)
        with self.journal._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            parent=db.execute(
                "SELECT revision FROM delegated_revisions "
                "WHERE approval_id=? AND source_sha=?",
                (self.approval_id,parent_sha)).fetchone()
            if parent is None:
                raise JournalBlocked("V052_DELEGATED_PARENT_SOURCE_UNKNOWN")
            next_revision=parent[0]+1
            if next_revision > self.manifest["max_rewrites"]:
                raise JournalBlocked("V052_DELEGATED_REWRITE_BUDGET_EXHAUSTED")
            row=db.execute("""SELECT c.status,c.envelope_json
                FROM delegated_requests d JOIN calls c ON c.grant_id=d.grant_id
                WHERE d.approval_id=? AND d.fingerprint=? AND d.role='writer'
                  AND d.source_sha=?""",
                (self.approval_id,fingerprint,parent_sha)).fetchone()
            if not row or row[0]!="RECEIPTED":
                raise JournalBlocked("V052_DELEGATED_WRITER_RECEIPT_REQUIRED")
            try:
                saved=json.loads(row[1])
                envelope=(decode_receipted_wire(saved) if
                          "wire_payload_b64" in saved else saved)
                body=envelope["raw"]
                choice=body["choices"][0]
                data=parse_writer(choice["message"]["content"])
                if (body["id"]!=generation_id or choice["finish_reason"]!="stop"
                    or data["source_prose_sha256"]!=parent_sha
                    or data["revised_scene_prose"]!=revised_prose):
                    raise ValueError("writer receipt does not prove requested revision")
            except (TypeError,KeyError,IndexError,ValueError) as exc:
                raise JournalBlocked("V052_DELEGATED_WRITER_LINEAGE_INVALID") from exc
            previous=db.execute(
                "SELECT source_sha,parent_sha,writer_fingerprint "
                "FROM delegated_revisions WHERE approval_id=? AND revision=?",
                (self.approval_id,next_revision)).fetchone()
            expected=(new_sha,parent_sha,fingerprint)
            if previous:
                if previous!=expected:
                    raise JournalBlocked("V052_DELEGATED_REVISION_FORK_BLOCKED")
                return new_sha
            db.execute("INSERT INTO delegated_revisions VALUES (?,?,?,?,?)",
                       (self.approval_id,next_revision,*expected))
        return new_sha
