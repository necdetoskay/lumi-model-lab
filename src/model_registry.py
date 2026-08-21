from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def model_slug(model: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "__", model.strip())
    return value.strip("_.-") or "model"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_fingerprint(model: str, qualification_config: dict[str, Any]) -> tuple[str, dict[str, str]]:
    files = [Path(str(item)) for item in qualification_config.get("fingerprint_files") or []]
    hashes: dict[str, str] = {}
    for path in files:
        if not path.exists():
            raise RuntimeError(f"Fingerprint file does not exist: {path}")
        hashes[str(path)] = file_sha256(path)

    payload = {
        "model": model,
        "qualification_name": qualification_config.get("name"),
        "files": hashes,
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest(), hashes


def load_registry(path: Path) -> dict[str, Any]:
    return load_json(path, {"version": 1, "entries": []})


def find_by_fingerprint(registry: dict[str, Any], fingerprint: str) -> dict[str, Any] | None:
    for entry in registry.get("entries") or []:
        if entry.get("fingerprint") == fingerprint:
            return entry
    return None


def upsert_entry(path: Path, entry: dict[str, Any]) -> dict[str, Any]:
    registry = load_registry(path)
    entries = list(registry.get("entries") or [])
    replaced = False
    for index, current in enumerate(entries):
        if current.get("fingerprint") == entry.get("fingerprint"):
            entries[index] = entry
            replaced = True
            break
    if not replaced:
        entries.append(entry)
    registry["entries"] = entries
    registry["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_json(path, registry)
    return registry
