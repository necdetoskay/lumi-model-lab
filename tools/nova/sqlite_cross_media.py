#!/usr/bin/env python3
"""Disposable SQLite index; canonical inputs are JSONL and authored JSON."""
import json
import sqlite3
from pathlib import Path
from validate_cross_media import ROOT, read_jsonl, check

def build(target=None):
    audit=check()
    if audit["status"]!="PASS":
        raise RuntimeError("Source-linkage gate failed: "+str(audit["errors"]))
    if target is None:
        target=ROOT/".nova-cache/nova-cross-media-v02.sqlite"
    target=Path(target)
    target.parent.mkdir(parents=True,exist_ok=True)
    staging=target.with_suffix(".tmp")
    if staging.exists():
        staging.unlink()
    db=sqlite3.connect(staging)
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
    CREATE TABLE works(
      work_id TEXT PRIMARY KEY, medium TEXT NOT NULL, payload TEXT NOT NULL
    );
    CREATE TABLE story_beats(
      work_id TEXT NOT NULL, beat_id TEXT NOT NULL, payload TEXT NOT NULL,
      PRIMARY KEY(work_id,beat_id), FOREIGN KEY(work_id) REFERENCES works(work_id)
    );
    CREATE TABLE mechanisms(
      mechanic_id TEXT PRIMARY KEY, work_id TEXT NOT NULL, payload TEXT NOT NULL,
      FOREIGN KEY(work_id) REFERENCES works(work_id)
    );
    CREATE TABLE sources(
      work_id TEXT NOT NULL, source_id TEXT NOT NULL, url TEXT NOT NULL, payload TEXT NOT NULL,
      PRIMARY KEY(work_id,source_id), FOREIGN KEY(work_id) REFERENCES works(work_id)
    );
    CREATE TABLE decisions(
      work_id TEXT NOT NULL, decision_id TEXT NOT NULL, decision_kind TEXT NOT NULL,
      payload TEXT NOT NULL, PRIMARY KEY(work_id,decision_id),
      FOREIGN KEY(work_id) REFERENCES works(work_id)
    );
    CREATE TABLE evidence(
      evidence_id TEXT PRIMARY KEY, work_id TEXT NOT NULL, mechanic_id TEXT NOT NULL,
      beat_id TEXT NOT NULL, payload TEXT NOT NULL,
      FOREIGN KEY(work_id,beat_id) REFERENCES story_beats(work_id,beat_id),
      FOREIGN KEY(mechanic_id) REFERENCES mechanisms(mechanic_id)
    );
    """)
    payload=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False)
    for x in read_jsonl("works"):
        db.execute("INSERT INTO works VALUES (?,?,?)",(x["work_id"],x["medium"],payload(x)))
    for x in read_jsonl("story_beats"):
        db.execute("INSERT INTO story_beats VALUES (?,?,?)",(x["work_id"],x["beat_id"],payload(x)))
    for x in read_jsonl("mechanisms"):
        db.execute("INSERT INTO mechanisms VALUES (?,?,?)",(x["mechanic_id"],x["work_id"],payload(x)))
    for x in read_jsonl("sources"):
        db.execute("INSERT INTO sources VALUES (?,?,?,?)",(x["work_id"],x["source_id"],x["url"],payload(x)))
    for x in read_jsonl("decisions"):
        db.execute("INSERT INTO decisions VALUES (?,?,?,?)",
                  (x["work_id"],x["decision_id"],x["decision_kind"],payload(x)))
    for x in read_jsonl("mechanic_evidence"):
        db.execute("INSERT INTO evidence VALUES (?,?,?,?,?)",
                  (x["evidence_id"],x["work_id"],x["mechanic_id"],x["beat_id"],payload(x)))
    assert not db.execute("PRAGMA foreign_key_check").fetchall()
    tables={t:db.execute("SELECT count(*) FROM "+t).fetchone()[0] for t in
            ["works","story_beats","mechanisms","sources","decisions","evidence"]}
    db.commit()
    db.close()
    staging.replace(target)
    return {"status":"PASS","tables":tables,"index_path":str(target),
            "note":"Disposable database, not LUMI production"}

if __name__=="__main__":
    print(json.dumps(build(),ensure_ascii=False,indent=2))
