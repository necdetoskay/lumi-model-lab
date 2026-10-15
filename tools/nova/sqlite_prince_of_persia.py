#!/usr/bin/env python3
"""Build disposable SQLite index with strong FK checks for NOVA PoP v0.3."""
import json
import sqlite3
import sys
from pathlib import Path
from validate_prince_of_persia import ROOT, BASE, validate, jsonl

def build(dest=ROOT/".nova-cache/nova-prince-of-persia-v03.sqlite"):
    gate=validate()
    if gate["status"]!="PASS":raise ValueError("source corpus not valid: "+str(gate["errors"]))
    path=Path(dest);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(".building.sqlite")
    if temp.exists():temp.unlink()
    conn=sqlite3.connect(temp)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
CREATE TABLE works(id TEXT PRIMARY KEY, title TEXT NOT NULL, family TEXT NOT NULL, raw TEXT NOT NULL);
CREATE TABLE sources(id TEXT PRIMARY KEY, url TEXT NOT NULL, raw TEXT NOT NULL);
CREATE TABLE work_sources(work_id TEXT NOT NULL REFERENCES works(id), source_id TEXT NOT NULL REFERENCES sources(id),PRIMARY KEY(work_id,source_id));
CREATE TABLE anchors(id TEXT PRIMARY KEY, work_id TEXT NOT NULL REFERENCES works(id), kind TEXT NOT NULL, raw TEXT NOT NULL);
CREATE TABLE locations(id TEXT PRIMARY KEY, raw TEXT NOT NULL);
CREATE TABLE time_edges(edge_id TEXT PRIMARY KEY, from_id TEXT NOT NULL REFERENCES anchors(id),to_id TEXT NOT NULL REFERENCES anchors(id),relation TEXT NOT NULL,raw TEXT NOT NULL);
CREATE TABLE ending_branches(id TEXT PRIMARY KEY, work_id TEXT NOT NULL REFERENCES works(id),canonical INTEGER NOT NULL, raw TEXT NOT NULL);
CREATE TABLE mechanics(id TEXT PRIMARY KEY, label TEXT NOT NULL,raw TEXT NOT NULL);
CREATE TABLE mechanism_evidence(id TEXT PRIMARY KEY, mechanic_id TEXT NOT NULL REFERENCES mechanics(id),anchor_id TEXT NOT NULL REFERENCES anchors(id),raw TEXT NOT NULL);
CREATE TABLE evidence_sources(evidence_id TEXT NOT NULL REFERENCES mechanism_evidence(id),source_id TEXT NOT NULL REFERENCES sources(id),PRIMARY KEY(evidence_id,source_id));
CREATE TABLE prior_v02_mechanics(id TEXT PRIMARY KEY);
CREATE TABLE cross_corpus_links(id TEXT PRIMARY KEY,mechanic_id TEXT NOT NULL REFERENCES mechanics(id),old_mechanic_id TEXT NOT NULL REFERENCES prior_v02_mechanics(id));
CREATE TABLE supplementary_releases(id TEXT PRIMARY KEY, raw TEXT NOT NULL);
CREATE INDEX ix_mechanic_evidence ON mechanism_evidence(mechanic_id);
CREATE INDEX ix_work_sources ON work_sources(source_id);
CREATE INDEX ix_anchor_work ON anchors(work_id);
""")
    def encode(x):return json.dumps(x,ensure_ascii=False,sort_keys=True)
    for w in jsonl("works"):
        conn.execute("INSERT INTO works VALUES(?,?,?,?)",
                     (w["work_id"],w["title"],w["family"],encode(w)))
    for s in jsonl("sources"):conn.execute("INSERT INTO sources VALUES(?,?,?)",(s["source_id"],s["url"],encode(s)))
    for w in jsonl("works"):
        for sid in w["source_ids"]:
            conn.execute("INSERT INTO work_sources VALUES(?,?)",(w["work_id"],sid))
    for row in jsonl("story_beats"):
        conn.execute("INSERT INTO anchors VALUES(?,?,?,?)",(row["beat_id"],row["work_id"],"story_beat",encode(row)))
    for row in jsonl("temporal_events"):
        conn.execute("INSERT INTO anchors VALUES(?,?,?,?)",(row["event_id"],"WW-2004","temporal_event",encode(row)))
    for row in jsonl("temporal_locations"):
        conn.execute("INSERT INTO locations VALUES(?,?)",(row["location_id"],encode(row)))
    for n,row in enumerate(jsonl("temporal_edges"),1):
        conn.execute("INSERT INTO time_edges VALUES(?,?,?,?,?)",
                     ("TE"+str(n),row["from_event_id"],row["to_event_id"],row["relation"],encode(row)))
    for row in jsonl("ending_branches"):
        conn.execute("INSERT INTO ending_branches VALUES(?,?,?,?)",
                     (row["branch_id"],"WW-2004",int(row["canonical_for_next_game"]),encode(row)))
    for row in jsonl("mechanics"):
        conn.execute("INSERT INTO mechanics VALUES(?,?,?)",(row["mechanic_id"],row["label_tr"],encode(row)))
    for row in jsonl("mechanic_evidence"):
        conn.execute("INSERT INTO mechanism_evidence VALUES(?,?,?,?)",
                     (row["evidence_id"],row["mechanic_id"],row["anchor_id"],encode(row)))
        for sid in row["source_ids"]:
            conn.execute("INSERT INTO evidence_sources VALUES(?,?)",(row["evidence_id"],sid))
    original=[json.loads(s) for s in (ROOT/"data/nova/v0.2/mechanisms.jsonl").read_text(encoding="utf8").splitlines() if s.strip()]
    for row in original:conn.execute("INSERT INTO prior_v02_mechanics VALUES(?)",(row["mechanic_id"],))
    for n,row in enumerate(jsonl("cross_corpus_links"),1):
        conn.execute("INSERT INTO cross_corpus_links VALUES(?,?,?)",
                     ("XL"+str(n),row["from_id"],row["to_existing_id"]))
    for row in jsonl("supplementary_releases"):
        conn.execute("INSERT INTO supplementary_releases VALUES(?,?)",(row["release_id"],encode(row)))
    violations=conn.execute("PRAGMA foreign_key_check").fetchall()
    if violations:raise ValueError("Broken SQLite FK refs: "+str(violations))
    names=("works","sources","work_sources","anchors","locations","time_edges","ending_branches",
           "mechanics","mechanism_evidence","evidence_sources","prior_v02_mechanics",
           "cross_corpus_links","supplementary_releases")
    counts={n:conn.execute("SELECT COUNT(*) FROM "+n).fetchone()[0] for n in names}
    expected={"works":19,"sources":29,"anchors":113,"locations":7,"time_edges":34,
              "ending_branches":2,"mechanics":22,"mechanism_evidence":72,
              "prior_v02_mechanics":35,"cross_corpus_links":27,"supplementary_releases":8}
    for key,val in expected.items():
        if counts[key]!=val:raise ValueError("Wrong SQL materialization "+key+" "+str(counts[key]))
    conn.commit();conn.close()
    temp.replace(path)
    return {"status":"PASS","index_path":str(path),"counts":counts,
            "foreign_key_violations":len(violations),"production_modified":False,"new_paid_calls":0}

if __name__=="__main__":
    try:r=build(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/".nova-cache/nova-prince-of-persia-v03.sqlite")
    except Exception as e:r={"status":"FAIL","error":repr(e)}
    print(json.dumps(r,ensure_ascii=False,indent=2))
    sys.exit(0 if r["status"]=="PASS" else 1)
