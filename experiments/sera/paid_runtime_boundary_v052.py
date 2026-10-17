"""SERA v0.52 owner-provisioned single-host paid runtime boundary.

LIVE provider calls may use only a separately provisioned protected trust
file and pre-existing journal with an exact inode/device/host binding. This
never provisions a signer, never signs a grant and never sends HTTP requests.
SQLite is permitted ONLY for same-host workers on a LOCAL filesystem; never
pretend this is multi-host distributed coordination.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
from urllib.parse import quote

from experiments.sera.provider_grant_journal_v052 import JournalBlocked, ProviderJournal

SCHEMA="sera.v052-paid-local-runtime-trust"
TABLE="paid_runtime_identity"
RUNTIME_KEYS=frozenset({"schema","trusted_raw_key_sha256","journal_path",
                         "journal_id","host_id_sha256",
                         "revoked_approval_ids"})
IDENTITY_KEYS=("journal_id","journal_path","host_id_sha256","device","inode")


def _host_identity():
    try:
        raw=Path("/etc/machine-id").read_bytes().strip()
        if len(raw)<16:
            raise ValueError("missing host identity")
        return sha256(raw).hexdigest()
    except (OSError,ValueError) as exc:
        raise JournalBlocked("V052_PAID_HOST_ID_UNAVAILABLE") from exc


def _safe_owned_file(path):
    p=Path(path)
    if not p.is_absolute():
        raise JournalBlocked("V052_PAID_TRUST_PATH_NOT_ABSOLUTE")
    parent=p.parent
    try:
        parent_info=os.lstat(parent)
        if (not stat.S_ISDIR(parent_info.st_mode) or
            parent_info.st_uid not in (0,os.geteuid()) or
            parent_info.st_mode & (stat.S_IWGRP|stat.S_IWOTH)):
            raise JournalBlocked("V052_PAID_TRUST_PARENT_INSECURE")
        if p.resolve(strict=True)!=p:
            raise JournalBlocked("V052_PAID_TRUST_SYMLINKED_PATH")
        fd=os.open(p,os.O_RDONLY | getattr(os,"O_NOFOLLOW",0)
                   | getattr(os,"O_CLOEXEC",0))
        try:
            info=os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or
                info.st_uid not in (0,os.geteuid()) or
                info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
                raise JournalBlocked("V052_PAID_TRUST_FILE_INSECURE")
            if info.st_size>8192:
                raise JournalBlocked("V052_PAID_TRUST_FILE_OVERSIZED")
            data=os.read(fd,8193)
        finally:
            os.close(fd)
    except (OSError,ValueError) as exc:
        raise JournalBlocked("V052_PAID_TRUST_FILE_UNREADABLE") from exc
    return data


def read_protected_runtime_config(path):
    """Read only independent owner-protected JSON, never an approval field."""
    try:
        cfg=json.loads(_safe_owned_file(path))
    except (UnicodeDecodeError,ValueError,TypeError) as exc:
        raise JournalBlocked("V052_PAID_TRUST_CONFIG_INVALID") from exc
    if not isinstance(cfg,dict) or set(cfg)!=RUNTIME_KEYS or (
        cfg["schema"]!=SCHEMA):
        raise JournalBlocked("V052_PAID_TRUST_CONFIG_SCHEMA_INVALID")
    pin=cfg["trusted_raw_key_sha256"]
    if not isinstance(pin,str) or re.fullmatch("[a-f0-9]{64}",pin) is None:
        raise JournalBlocked("V052_PAID_TRUST_PIN_INVALID")
    journal=cfg["journal_path"]
    if (not isinstance(journal,str) or not Path(journal).is_absolute() or
        journal.endswith("/") or ".." in Path(journal).parts):
        raise JournalBlocked("V052_PAID_JOURNAL_PATH_UNSAFE")
    if (not isinstance(cfg["journal_id"],str) or
        re.fullmatch("[a-f0-9]{64}",cfg["journal_id"]) is None):
        raise JournalBlocked("V052_PAID_JOURNAL_ID_INVALID")
    revoked=cfg["revoked_approval_ids"]
    if (not isinstance(revoked,list) or len(revoked)>1000 or
        len(set(str(x) for x in revoked))!=len(revoked) or
        any(not isinstance(x,str) or not x or len(x)>256 for x in revoked)):
        raise JournalBlocked("V052_PAID_APPROVAL_REVOCATION_CONFIG_INVALID")
    if cfg["host_id_sha256"] != _host_identity():
        raise JournalBlocked("V052_PAID_HOST_MISMATCH")
    return cfg


def verify_shared_local_journal(cfg):
    """Verify an existing SINGLE local journal, without creating it."""
    p=Path(cfg["journal_path"])
    try:
        parent=os.lstat(p.parent)
        if (not stat.S_ISDIR(parent.st_mode) or
            parent.st_uid not in (0,os.geteuid()) or
            parent.st_mode & (stat.S_IWGRP|stat.S_IWOTH)):
            raise JournalBlocked("V052_PAID_JOURNAL_PARENT_INSECURE")
        if p.resolve(strict=True)!=p:
            raise JournalBlocked("V052_PAID_JOURNAL_SYMLINKED_PATH")
        info=os.lstat(p)
        if (not stat.S_ISREG(info.st_mode) or
            info.st_uid not in (0,os.geteuid()) or
            info.st_mode & (stat.S_IWGRP|stat.S_IWOTH)):
            raise JournalBlocked("V052_PAID_JOURNAL_FILE_INSECURE")
        # SQLite over NFS/multiple hosts does not provide this guarantee.
        uri="file:"+quote(str(p))+"?mode=ro"
        with sqlite3.connect(uri,uri=True) as db:
            row=db.execute(
                "SELECT journal_id,journal_path,host_id_sha256,device,inode "
                "FROM paid_runtime_identity WHERE singleton=1").fetchone()
        expected=(cfg["journal_id"],str(p),cfg["host_id_sha256"],
                  info.st_dev,info.st_ino)
        if row != expected:
            raise JournalBlocked("V052_PAID_JOURNAL_IDENTITY_OR_COPY_DRIFT")
        return str(p)
    except sqlite3.Error as exc:
        raise JournalBlocked("V052_PAID_JOURNAL_NOT_PROVISIONED") from exc
    except OSError as exc:
        raise JournalBlocked("V052_PAID_JOURNAL_MISSING") from exc


def provision_local_journal(*, path):
    """Admin bootstrap only: create empty local journal, return fixed ID.

    NEVER invoke from a paid story worker. Provisioned journal UUID must be
    pinned independently in a protected deployment config before any run.
    """
    p=Path(path)
    if not p.is_absolute() or p.is_symlink() or p.exists():
        raise JournalBlocked("V052_PAID_BOOTSTRAP_REQUIRES_NEW_ABSOLUTE_PATH")
    parent=p.parent
    if (not parent.is_dir() or parent.is_symlink() or
        (parent.stat().st_mode & (stat.S_IWOTH | stat.S_IWGRP))):
        raise JournalBlocked("V052_PAID_BOOTSTRAP_PARENT_UNTRUSTED")
    oldmask=os.umask(0o077)
    try:
        j=ProviderJournal(p)
        info=p.stat()
        journal_id=secrets.token_hex(32)
        host=_host_identity()
        with j._connect() as db:
            db.execute("""CREATE TABLE paid_runtime_identity (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                journal_id TEXT NOT NULL, journal_path TEXT NOT NULL,
                host_id_sha256 TEXT NOT NULL,
                device INTEGER NOT NULL, inode INTEGER NOT NULL)""")
            db.execute("INSERT INTO paid_runtime_identity VALUES (1,?,?,?,?,?)",
                       (journal_id,str(p),host,info.st_dev,info.st_ino))
        return {"journal_id":journal_id,"host_id_sha256":host,
                "journal_path":str(p)}
    finally:
        os.umask(oldmask)


def assert_paid_approval_active(*, config_path, original_config, approval_id):
    """Check protected owner revocations immediately before a new model POST.

    This is not an external revocation service: deployment owner must update
    and distribute the protected config atomically to the dedicated host.
    A changed trust root or journal identity cannot migrate an active run.
    """
    fresh=read_protected_runtime_config(config_path)
    original={k:v for k,v in original_config.items()
              if k!="revoked_approval_ids"}
    current={k:v for k,v in fresh.items()
             if k!="revoked_approval_ids"}
    if current!=original:
        raise JournalBlocked("V052_PAID_RUNTIME_TRUST_CHANGED")
    if approval_id in fresh["revoked_approval_ids"]:
        raise JournalBlocked("V052_PAID_APPROVAL_REVOKED")
    verify_shared_local_journal(fresh)
    return True
