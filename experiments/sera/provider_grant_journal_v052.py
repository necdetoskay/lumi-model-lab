"""SERA v0.52 P0: durable single-use authorization and provider POST journal.

This is a safety primitive, NOT an authorization grant and NOT a paid runner.
Callers must never infer consent from credentials or a different experiment.
A started-but-unreceipted POST remains unknown and is never retried.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import sqlite3
import time
from pathlib import Path

from experiments.sera.request_policy import enforce_no_output_token_limit

SCHEMA = "sera.v052-paid-post-journal"
class JournalBlocked(RuntimeError):
    pass


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _hash(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


class ProviderJournal:
    """Shared local SQLite journal; use one durable DB for all worker processes."""

    def __init__(self, db_path, *, expected_file_identity=None):
        self.path = Path(db_path)
        # Legacy isolated/offline lab journals may bootstrap themselves.
        # LIVE paid lane must bind an already-provisioned device+inode.
        self._expected_file_identity = expected_file_identity
        if expected_file_identity is not None:
            if (not isinstance(expected_file_identity, tuple) or
                len(expected_file_identity)!=2 or
                any(type(v) is not int or v < 0 for v in expected_file_identity)
                or not self.path.is_absolute()):
                raise JournalBlocked("V052_PAID_JOURNAL_EXPECTED_IDENTITY_INVALID")
            self._assert_bound_file()
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            if expected_file_identity is not None:
                tables={row[0] for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
                if not {"grants","calls","paid_runtime_identity"} <= tables:
                    raise JournalBlocked("V052_PAID_JOURNAL_SCHEMA_OR_HISTORY_MISSING")
                return
            db.execute("""CREATE TABLE IF NOT EXISTS grants (
                grant_id TEXT PRIMARY KEY, binding_sha TEXT NOT NULL,
                authorized INTEGER NOT NULL CHECK(authorized = 1),
                consumed INTEGER NOT NULL DEFAULT 0 CHECK(consumed IN (0,1))
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS calls (
                request_id TEXT PRIMARY KEY, grant_id TEXT NOT NULL UNIQUE,
                request_sha TEXT NOT NULL, binding_sha TEXT NOT NULL,
                model TEXT NOT NULL, status TEXT NOT NULL,
                started_at REAL NOT NULL, completed_at REAL,
                envelope_json TEXT, envelope_sha TEXT,
                FOREIGN KEY(grant_id) REFERENCES grants(grant_id)
            )""")

    def _assert_bound_file(self):
        if self._expected_file_identity is None:
            return
        try:
            info = os.lstat(self.path)
        except OSError as exc:
            raise JournalBlocked("V052_PAID_JOURNAL_FILE_MISSING_OR_REPLACED") from exc
        if (not stat.S_ISREG(info.st_mode) or
            (info.st_dev,info.st_ino) != self._expected_file_identity):
            raise JournalBlocked("V052_PAID_JOURNAL_FILE_IDENTITY_CHANGED")

    def _connect(self):
        self._assert_bound_file()
        # mode=rw forbids silent replacement/creation in the protected lane.
        if self._expected_file_identity is None:
            db = sqlite3.connect(str(self.path), timeout=30, isolation_level=None)
        else:
            from urllib.parse import quote
            uri="file:"+quote(str(self.path))+"?mode=rw"
            try:
                db=sqlite3.connect(uri, uri=True,timeout=30,isolation_level=None)
            except sqlite3.Error as exc:
                raise JournalBlocked("V052_PAID_JOURNAL_OPEN_FAILED") from exc
        try:
            self._assert_bound_file()
            db.execute("PRAGMA busy_timeout=30000")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA foreign_keys=ON")
            return db
        except BaseException:
            db.close()
            raise

    def register_grant(self, *, grant_id, binding, authorized=False):
        """Authorization must be explicitly supplied by a separate human-approved control."""
        if not authorized or not isinstance(grant_id, str) or not grant_id.strip():
            raise JournalBlocked("V052_EXPLICIT_SERA_PAID_AUTHORIZATION_REQUIRED")
        if not isinstance(binding, dict) or not binding:
            raise JournalBlocked("V052_GRANT_BINDING_REQUIRED")
        required = {"source_sha256", "world_sha256", "scene_key",
                    "policy_sha256", "model"}
        if not required <= set(binding) or any(not isinstance(binding[k], str)
                                                or not binding[k] for k in required):
            raise JournalBlocked("V052_GRANT_BINDING_INCOMPLETE")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT binding_sha FROM grants WHERE grant_id=?",
                                  (grant_id,)).fetchone()
            fingerprint = _hash(binding)
            if existing:
                if existing[0] != fingerprint:
                    raise JournalBlocked("V052_GRANT_REBIND_FORBIDDEN")
                return
            db.execute("INSERT INTO grants VALUES (?, ?, 1, 0)",
                       (grant_id, fingerprint))

    def execute_once(self, *, grant_id, binding, request_id, model, payload, transport):
        """Persist STARTED atomically before POST; persist full envelope before parsing.

        transport(model=..., payload=..., request_id=...) performs exactly one POST.
        A crash after STARTED cannot silently repeat billable work.
        """
        if not isinstance(payload, dict) or not callable(transport):
            raise JournalBlocked("V052_TRANSPORT_INVALID")
        enforce_no_output_token_limit(payload)
        if not isinstance(request_id, str) or not request_id.strip():
            raise JournalBlocked("V052_REQUEST_ID_REQUIRED")
        if not isinstance(model, str) or model != binding.get("model"):
            raise JournalBlocked("V052_MODEL_NOT_ALLOWED")
        binding_sha, request_sha = _hash(binding), _hash({"model":model,"payload":payload})
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            grant = db.execute("SELECT binding_sha,consumed FROM grants WHERE grant_id=?",
                               (grant_id,)).fetchone()
            if not grant or grant[0] != binding_sha:
                raise JournalBlocked("V052_GRANT_MISSING_OR_DRIFT")
            prior = db.execute("""SELECT request_id,request_sha,binding_sha,status,
                                         envelope_json,envelope_sha FROM calls
                                  WHERE grant_id=?""", (grant_id,)).fetchone()
            if prior:
                if prior[:3] != (request_id,request_sha,binding_sha):
                    raise JournalBlocked("V052_GRANT_ALREADY_SPENT")
                if prior[3] != "RECEIPTED":
                    raise JournalBlocked("V052_UNKNOWN_INFLIGHT_NO_REPOST")
                if _hash(json.loads(prior[4])) != prior[5]:
                    raise JournalBlocked("V052_RECEIPT_CORRUPT")
                return json.loads(prior[4])
            if grant[1]:
                raise JournalBlocked("V052_GRANT_ALREADY_SPENT")
            db.execute("UPDATE grants SET consumed=1 WHERE grant_id=?", (grant_id,))
            db.execute("""INSERT INTO calls
                (request_id,grant_id,request_sha,binding_sha,model,status,started_at)
                VALUES (?,?,?,?,?,'STARTED',?)""",
                (request_id,grant_id,request_sha,binding_sha,model,time.time()))
        # Never persist credentials; caller must use a transport that redacts secrets.
        envelope = transport(model=model, payload=payload, request_id=request_id)
        if not isinstance(envelope, dict):
            raise JournalBlocked("V052_RESPONSE_NOT_AN_ENVELOPE")
        encoded = _canonical(envelope)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status FROM calls WHERE request_id=?",
                             (request_id,)).fetchone()
            if not row or row[0] != "STARTED":
                raise JournalBlocked("V052_RECEIPT_STATE_DRIFT")
            db.execute("""UPDATE calls SET status='RECEIPTED',completed_at=?,
                          envelope_json=?,envelope_sha=? WHERE request_id=?""",
                       (time.time(), encoded, _hash(envelope), request_id))
        return envelope

    def status(self, grant_id):
        with self._connect() as db:
            row = db.execute("SELECT status FROM calls WHERE grant_id=?",
                             (grant_id,)).fetchone()
            return row[0] if row else "NOT_STARTED"

    def read_completed(self, *, grant_id, binding, request_id, model, payload):
        """GET-only local receipt; NEVER creates a grant or calls a provider."""
        enforce_no_output_token_limit(payload)
        binding_sha = _hash(binding)
        request_sha = _hash({"model": model, "payload": payload})
        with self._connect() as db:
            row = db.execute(
                """SELECT request_id,request_sha,binding_sha,model,status,
                          envelope_json,envelope_sha FROM calls WHERE grant_id=?""",
                (grant_id,)).fetchone()
        if row is None:
            raise JournalBlocked("V052_RECOVERY_NO_PRIOR_POST")
        if row[:4] != (request_id, request_sha, binding_sha, model):
            raise JournalBlocked("V052_RECOVERY_REQUEST_OR_MODEL_DRIFT")
        if row[4] != "RECEIPTED":
            raise JournalBlocked("V052_RECOVERY_UNKNOWN_INFLIGHT_NO_REPOST")
        try:
            envelope = json.loads(row[5])
            if not isinstance(envelope, dict) or _hash(envelope) != row[6]:
                raise ValueError("incorrect receipt hash")
        except (ValueError, TypeError, OSError) as exc:
            raise JournalBlocked("V052_RECOVERY_RECEIPT_CORRUPT") from exc
        return envelope
