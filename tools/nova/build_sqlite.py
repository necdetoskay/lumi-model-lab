#!/usr/bin/env python3
"""Rebuild disposable offline NOVA SQLite index from canonical versioned JSONL."""
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from validate import ROOT, BASE, read_jsonl, validate

def build(destination=None):
    verdict = validate()
    if verdict["status"] != "PASS":
        raise RuntimeError(f"NOVA schema gate failed: {verdict['errors']}")
    if destination is None:
        destination = ROOT / ".nova-cache/nova-v0.1.sqlite"
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp.sqlite")
    if temp.exists():
        temp.unlink()
    con = sqlite3.connect(temp)
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript("""
        CREATE TABLE works (
          work_id TEXT PRIMARY KEY,
          payload_json TEXT NOT NULL
        );
        CREATE TABLE episodes (
          episode_id TEXT PRIMARY KEY,
          work_id TEXT NOT NULL REFERENCES works(work_id),
          season INTEGER NOT NULL,
          episode INTEGER NOT NULL,
          payload_json TEXT NOT NULL,
          UNIQUE(work_id, season, episode)
        );
        CREATE TABLE analyses (
          analysis_id TEXT PRIMARY KEY,
          episode_id TEXT NOT NULL UNIQUE REFERENCES episodes(episode_id),
          payload_json TEXT NOT NULL
        );
        CREATE TABLE mechanics (
          mechanic_id TEXT PRIMARY KEY,
          payload_json TEXT NOT NULL
        );
        CREATE TABLE mechanic_evidence (
          evidence_id TEXT PRIMARY KEY,
          episode_id TEXT NOT NULL REFERENCES episodes(episode_id),
          mechanic_id TEXT NOT NULL REFERENCES mechanics(mechanic_id),
          analysis_id TEXT NOT NULL REFERENCES analyses(analysis_id),
          payload_json TEXT NOT NULL
        );
    """)
    def payload(row):
        return json.dumps(row, sort_keys=True, ensure_ascii=False)
    for x in read_jsonl("works.jsonl"):
        con.execute("INSERT INTO works VALUES (?, ?)", (x["work_id"], payload(x)))
    for x in read_jsonl("episodes.jsonl"):
        con.execute("INSERT INTO episodes VALUES (?, ?, ?, ?, ?)",
                    (x["episode_id"], x["work_id"], x["season"], x["episode"], payload(x)))
    for x in read_jsonl("analyses.jsonl"):
        con.execute("INSERT INTO analyses VALUES (?, ?, ?)",
                    (x["analysis_id"], x["episode_id"], payload(x)))
    for x in read_jsonl("mechanics.jsonl"):
        con.execute("INSERT INTO mechanics VALUES (?, ?)", (x["mechanic_id"], payload(x)))
    for x in read_jsonl("mechanic_evidence.jsonl"):
        con.execute("INSERT INTO mechanic_evidence VALUES (?, ?, ?, ?, ?)",
                    (x["evidence_id"], x["episode_id"], x["mechanic_id"], x["analysis_id"], payload(x)))
    foreign_errors = con.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_errors:
        raise RuntimeError(f"SQLite foreign key errors: {foreign_errors}")
    counts = {table: con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
              for table in ("works", "episodes", "analyses", "mechanics", "mechanic_evidence")}
    con.commit()
    con.close()
    temp.replace(path)
    return {"status": "PASS", "database": str(path), "tables": counts}

if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
