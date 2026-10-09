"""Verify the actual source version a historical artifact froze, not new code."""
import hashlib
import json
from pathlib import Path


def verify_historical_source(row):
    path = Path(row["path"])
    expected = row["sha256"]
    if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected:
        return
    root = Path("evidence/spineforge-relay/frozen-sources")
    registry = json.loads((root/"registry.json").read_text(encoding="utf-8"))
    if registry.get("schema") != "spineforge-relay.frozen-source-registry.v1":
        raise RuntimeError("Invalid frozen source registry")
    matches = [entry for entry in registry["entries"]
               if (entry["source_path"], entry["sha256"]) == (row["path"], expected)]
    if len(matches) != 1:
        raise RuntimeError("Saved Relay evidence mismatch: frozen source bytes")
    archive = Path(matches[0]["archive_path"])
    if not archive.resolve().is_relative_to(root.resolve()) or hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise RuntimeError("Saved Relay evidence mismatch: corrupt frozen source snapshot")
