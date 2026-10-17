"""SERA physical-read nonce ledger: SINGLE LOCAL HOST, no G2/world writes.

Provisioning is infra-only. The story worker must use a pre-existing DB and
can never recreate a lost store. Local SQLite transactions serialize nonce
consumption across processes; do not use on NFS/multiple hosts.
"""
from __future__ import annotations
import os
from pathlib import Path
import re
import sqlite3
import stat
from urllib.parse import quote
from experiments.sera.coverage import CoverageError

PATTERN=re.compile(r"[A-Za-z0-9_-]{24,180}\Z")


def require(ok,code):
    if not ok:
        raise CoverageError(code)


def identity(path):
    p=Path(path)
    require(p.is_absolute(),"V053_NONCE_PATH_NOT_ABSOLUTE")
    try:
        directory=os.lstat(p.parent)
        file=os.lstat(p)
    except OSError as exc:
        raise CoverageError("V053_NONCE_STORE_MISSING") from exc
    require(stat.S_ISDIR(directory.st_mode) and
            directory.st_uid in (0,os.geteuid()) and
            not directory.st_mode & (stat.S_IWGRP|stat.S_IWOTH),
            "V053_NONCE_PARENT_INSECURE")
    require(stat.S_ISREG(file.st_mode) and not p.is_symlink() and
            file.st_uid in (0,os.geteuid()) and
            not file.st_mode & (stat.S_IWGRP|stat.S_IWOTH),
            "V053_NONCE_FILE_INSECURE")
    return (file.st_dev,file.st_ino)


def provision_nonce_store(path):
    """One-time explicit infrastructure action, forbidden in a story run."""
    p=Path(path)
    require(p.is_absolute() and not p.exists() and not p.is_symlink(),
            "V053_NONCE_BOOTSTRAP_REQUIRES_NEW_PATH")
    try:
        parent=os.lstat(p.parent)
        require(stat.S_ISDIR(parent.st_mode) and
                parent.st_uid in (0,os.geteuid()) and
                not parent.st_mode & (stat.S_IWGRP|stat.S_IWOTH),
                "V053_NONCE_PARENT_INSECURE")
    except OSError as exc:
        raise CoverageError("V053_NONCE_PARENT_MISSING") from exc
    mask=os.umask(0o077)
    try:
        fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        os.close(fd)
        with sqlite3.connect(str(p)) as db:
            db.execute("CREATE TABLE physical_nonce_claim ("
                       "nonce TEXT PRIMARY KEY NOT NULL,"
                       "consumed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
                       " WITHOUT ROWID")
    finally:
        os.umask(mask)
    return identity(p)


class LocalPhysicalNonceStore:
    def __init__(self,path):
        self.path=Path(path)
        self.file_identity=identity(self.path)
        with self.connect() as db:
            rows=db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='physical_nonce_claim'").fetchall()
            require(len(rows)==1,"V053_NONCE_SCHEMA_MISSING")

    def connect(self):
        require(identity(self.path)==self.file_identity,
                "V053_NONCE_STORE_REPLACED")
        try:
            db=sqlite3.connect("file:"+quote(str(self.path))+"?mode=rw",
                               uri=True,timeout=30,isolation_level=None)
            require(identity(self.path)==self.file_identity,
                    "V053_NONCE_STORE_REPLACED")
            db.execute("PRAGMA busy_timeout=30000")
            db.execute("PRAGMA synchronous=FULL")
            return db
        except BaseException:
            if "db" in locals():
                db.close()
            raise

    def consume(self,nonce):
        require(isinstance(nonce,str) and PATTERN.fullmatch(nonce) is not None,
                "V053_NONCE_VALUE_INVALID")
        with self.connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                cursor=db.execute(
                    "INSERT OR IGNORE INTO physical_nonce_claim(nonce) VALUES (?)",
                    (nonce,))
                accepted=cursor.rowcount==1
                db.execute("COMMIT")
                return accepted
            except sqlite3.Error as exc:
                try: db.execute("ROLLBACK")
                except sqlite3.Error: pass
                raise CoverageError("V053_NONCE_ATOMIC_INSERT_FAILED") from exc

    __call__=consume
