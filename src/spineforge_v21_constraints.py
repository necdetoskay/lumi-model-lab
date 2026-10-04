"""Exact projection of approved prose fields, never inferred semantic facts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def digest_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select(source: Any, pointer: str) -> Any:
    if not pointer.startswith("/"):
        raise RuntimeError("Constraint requires an absolute JSON pointer")
    for part in pointer[1:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        try:
            source = source[int(part)] if isinstance(source, list) else source[part]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise RuntimeError(f"Missing approved Spine constraint: {pointer}") from exc
    return source


def derive_constraints(approval: dict, selection: dict, *, approval_file_sha256: str) -> dict:
    spine = approval.get("approved_spine")
    spine_hash = digest_json(spine)
    if (approval.get("gate_decision") != "ACCEPT"
            or approval.get("human_review", {}).get("verdict") != "APPROVE"
            or approval.get("spine_hash") != spine_hash
            or selection.get("approved_spine_hash") != spine_hash):
        raise RuntimeError("Approved Spine approval/hash binding failed")
    rows = []
    for row in selection["selectors"]:
        value = select(spine, row["pointer"])
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError("Constraint must project nonempty approved text")
        rows.append({"source_pointer": row["pointer"], "role": row["role"], "text": value})
    if not rows or len({r["source_pointer"] for r in rows}) != len(rows):
        raise RuntimeError("Missing or duplicate constraint selection")
    payload = {
        "schema": "spineforge-v21-approved-constraints.v1",
        "derivation": "EXACT_APPROVED_FIELD_PROJECTION_NOT_SEMANTIC_EXTRACTION",
        "approval_id": approval["approval_id"],
        "context_fingerprint": approval["context_fingerprint"],
        "approved_spine_hash": spine_hash,
        "approval_file_sha256": approval_file_sha256,
        "selection_sha256": digest_json(selection),
        "scene_scope": selection["scene_scope"],
        "constraints": rows,
    }
    payload["artifact_sha256"] = digest_json(payload)
    return payload


def load_constraints(profile: dict) -> dict:
    source = profile["approved_spine"]
    approval_path, selection_path = Path(source["artifact_path"]), Path(source["selection_path"])
    derived = derive_constraints(json.loads(approval_path.read_text()),
                                 json.loads(selection_path.read_text()),
                                 approval_file_sha256=sha_file(approval_path))
    saved = json.loads(Path(source["constraints_path"]).read_text())
    if saved != derived or derived["artifact_sha256"] != source["constraints_sha256"]:
        raise RuntimeError("Approved Spine constraints drift")
    if derived["approved_spine_hash"] != profile["source_story"]["approved_spine_hash"]:
        raise RuntimeError("Source story/Spine hash mismatch")
    return derived
