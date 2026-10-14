"""Versioned JSONL authority with a disposable, transactionally built SQLite index."""
from __future__ import annotations

import json
from contextlib import closing
from pathlib import Path
import re
import sqlite3
import unicodedata

from experiments.narrative_mechanics import core as nml

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RELEASE_SHA256 = "88dadf252ba075ea60367d6a3eb07fce07abb0f31306c16edb2c000fe3f7d1e0"
AXES = (*nml.AXES, "dramatic_opening", "outcome", "series_arc", "novelty")


def tokens(text):
    folded = unicodedata.normalize("NFKC", text).casefold().replace("ı", "i").replace("\u0307", "")
    return re.findall(r"[^\W_]+", folded)


def normalized(text):
    return " ".join(tokens(text))


def duplicate_report(records):
    exact, near = [], []
    for i, a in enumerate(records):
        for b in records[i + 1:]:
            ta, tb = set(tokens(a["abstract"])), set(tokens(b["abstract"]))
            similarity = len(ta & tb) / max(1, len(ta | tb))
            pair = [a["id"], b["id"]]
            if normalized(a["abstract"]) == normalized(b["abstract"]):
                exact.append(pair)
            elif similarity >= 0.65:
                near.append({"ids": pair, "jaccard": round(similarity, 4)})
    return {"exact": exact, "near_review_required": near,
            "semantic_duplicates_certified_absent": False}


def load(root=nml.ROOT):
    upstream = nml.load_release(root)
    if nml.sha((DATA / "release.v1.json").read_bytes()) != RELEASE_SHA256:
        raise nml.Invalid("NOVA_RELEASE_CHANGED")
    release = nml.read_json(DATA / "release.v1.json")
    if release["upstream_release"] != nml.RELEASE_SHA256:
        raise nml.Invalid("UPSTREAM_RELEASE_CHANGED")
    for name, digest in release["files"].items():
        if nml.sha(nml.safe_path(HERE, name).read_bytes()) != digest:
            raise nml.Invalid("NOVA_ARTIFACT_CHANGED")
    rows = []
    for line in (DATA / "vault.v1.jsonl").read_bytes().splitlines():
        row = json.loads(line, object_pairs_hook=nml._pairs)
        nml.validate(row, nml.read_json(HERE / "schemas/mechanic.schema.json"))
        rows.append(row)
    identities = [(x["id"], x["version"]) for x in rows]
    if len(identities) != len(set(identities)) or len({x["id"] for x in rows}) != len(rows):
        raise nml.Invalid("DUPLICATE_MECHANIC_ID")
    if duplicate_report(rows)["exact"]:
        raise nml.Invalid("DUPLICATE_MECHANIC_CONTENT")
    by_id = {x["id"]: x for x in upstream["cards"]}
    episodes = {x["id"]: x for x in upstream["archive"]["episodes"]}
    for row in rows:
        card = by_id[row["upstream_id"]]
        if row["upstream_sha256"] != nml.fingerprint(card):
            raise nml.Invalid("MECHANIC_LINEAGE_CHANGED")
        if row["status"] != card["status"]:
            raise nml.Invalid("WITHHELD_STATUS_CHANGED")
        if row["normalized_sha256"] != nml.sha(normalized(row["abstract"]).encode()):
            raise nml.Invalid("NORMALIZATION_MISMATCH")
        if set(row["analysis"]) != set(AXES):
            raise nml.Invalid("MISSING_ANALYSIS_AXIS")
        for axis in row["analysis"].values():
            if axis["epistemic"] == "UNKNOWN":
                if axis["evidence"]:
                    raise nml.Invalid("UNKNOWN_WITH_EVIDENCE")
            elif not axis["evidence"]:
                raise nml.Invalid("CLAIM_WITHOUT_EVIDENCE")
            for evidence in axis["evidence"]:
                source = episodes.get(evidence["source_id"])
                if not source or evidence["source_id"] not in row["source_ids"]:
                    raise nml.Invalid("UNKNOWN_SOURCE")
                data = nml.safe_path(root, source["path"]).read_bytes()
                start, end = evidence["start_byte"], evidence["end_byte"]
                if evidence["source_sha256"] != source["sha256"] or not 0 <= start < end <= len(data):
                    raise nml.Invalid("SOURCE_BINDING")
                try:
                    data[:start].decode("utf-8")
                    data[start:end].decode("utf-8")
                except UnicodeError as exc:
                    raise nml.Invalid("UTF8_BOUNDARY") from exc
                if nml.sha(data[start:end]) != evidence["span_sha256"]:
                    raise nml.Invalid("SOURCE_SPAN_CHANGED")
        if any(p["age_min"] > p["age_max"] for p in row["profiles"]):
            raise nml.Invalid("PROFILE_AGE_RANGE")
    return rows, upstream, release


def record_usage(directory, audit, brief):
    events = [{"schema": "nova.usage.v1", "id": mid, "ordinal": brief["ordinal"],
               "state_sha256": audit["state_sha256"], "selection_sha256": nml.fingerprint(audit)}
              for mid in audit["selected_ids"]]
    for event in events:
        nml.validate(event, nml.read_json(HERE / "schemas/usage.schema.json"))
    # One immutable batch per selection, preserving previous history and provenance.
    return nml.freeze(directory, "usage", events)


def load_usage(path):
    path = Path(path)
    paths = sorted(path.glob("usage-*.json")) if path.is_dir() else [path]
    events = []
    for item in paths:
        if item.is_symlink() or item.name != "usage-" + nml.sha(item.read_bytes()) + ".json":
            raise nml.Invalid("USAGE_ARTIFACT_CHANGED")
        batch = nml.read_json(item)
        if not isinstance(batch, list):
            raise nml.Invalid("USAGE_SCHEMA")
        for event in batch:
            nml.validate(event, nml.read_json(HERE / "schemas/usage.schema.json"))
        events.extend(batch)
    return events


def build_index(path, rows, release):
    """Create only; never delete or overwrite an existing vault/index."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb"):
        pass
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript("""
          CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
          CREATE TABLE mechanics(id TEXT PRIMARY KEY, version INTEGER NOT NULL,
            digest TEXT NOT NULL UNIQUE, status TEXT NOT NULL, record TEXT NOT NULL);
          CREATE TABLE sources(mechanic_id TEXT NOT NULL REFERENCES mechanics(id),
            source_id TEXT NOT NULL, PRIMARY KEY(mechanic_id, source_id));
          CREATE INDEX sources_by_episode ON sources(source_id);
        """)
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("INSERT INTO metadata VALUES (?,?)", ("release_sha256", nml.fingerprint(release)))
        for row in rows:
            db.execute("INSERT INTO mechanics VALUES (?,?,?,?,?)",
                       (row["id"], row["version"], row["normalized_sha256"], row["status"],
                        nml.canonical(row).decode()))
            db.executemany("INSERT INTO sources VALUES (?,?)", [(row["id"], s) for s in row["source_ids"]])
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise nml.Invalid("SQLITE_INTEGRITY")
    verify_index(path, rows, release)


def verify_index(path, rows, release):
    uri = Path(path).resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        if db.execute("SELECT value FROM metadata WHERE key='release_sha256'").fetchone() != (nml.fingerprint(release),):
            raise nml.Invalid("STALE_INDEX")
        actual = db.execute("SELECT id,version,digest,status,record FROM mechanics ORDER BY id").fetchall()
        expected = [(r["id"], r["version"], r["normalized_sha256"], r["status"], nml.canonical(r).decode())
                    for r in sorted(rows, key=lambda x: x["id"])]
        links = db.execute("SELECT mechanic_id,source_id FROM sources ORDER BY mechanic_id,source_id").fetchall()
        if actual != expected or links != sorted((r["id"], s) for r in rows for s in r["source_ids"]):
            raise nml.Invalid("INDEX_DRIFT")
