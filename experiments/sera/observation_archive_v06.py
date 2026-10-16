"""SERA v0.6 — immutable advisory/T2 observation archive (SQLite only).

This archive deliberately does NOT connect to a canonical WorldStore.
Saving a sighting does not create an Entity or accept an EventGraph mutation.
Persisting candidate evidence allows later promotion/review without
discarding the original quoted context.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import sqlite3

from experiments.sera.coverage import CoverageError
from experiments.sera.world_state_v02 import canonical


def check(ok, code):
    if not ok:
        raise CoverageError(code)


class ObservationArchive:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(str(path), isolation_level=None)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS inspection_archive (
                inspection_id TEXT PRIMARY KEY,
                stream_id TEXT NOT NULL,
                scene_id TEXT NOT NULL,
                prose_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL,
                result_status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS candidate_sightings (
                inspection_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                candidate_ref TEXT NOT NULL,
                tier TEXT NOT NULL,
                sentence_id TEXT NOT NULL,
                start_offset INTEGER NOT NULL,
                end_offset INTEGER NOT NULL,
                quote TEXT NOT NULL,
                PRIMARY KEY (inspection_id, sequence),
                FOREIGN KEY (inspection_id)
                    REFERENCES inspection_archive(inspection_id)
            );
            CREATE INDEX IF NOT EXISTS candidate_sightings_ref
              ON candidate_sightings(candidate_ref, inspection_id);
            CREATE TRIGGER IF NOT EXISTS inspection_archive_appendonly_u
              BEFORE UPDATE ON inspection_archive
              BEGIN SELECT RAISE(ABORT, 'OBSERVATION_ARCHIVE_IMMUTABLE'); END;
            CREATE TRIGGER IF NOT EXISTS inspection_archive_appendonly_d
              BEFORE DELETE ON inspection_archive
              BEGIN SELECT RAISE(ABORT, 'OBSERVATION_ARCHIVE_IMMUTABLE'); END;
            CREATE TRIGGER IF NOT EXISTS candidate_sightings_appendonly_u
              BEFORE UPDATE ON candidate_sightings
              BEGIN SELECT RAISE(ABORT, 'SIGHTINGS_IMMUTABLE'); END;
            CREATE TRIGGER IF NOT EXISTS candidate_sightings_appendonly_d
              BEFORE DELETE ON candidate_sightings
              BEGIN SELECT RAISE(ABORT, 'SIGHTINGS_IMMUTABLE'); END;
        """)
        self.db.execute("PRAGMA foreign_keys=ON")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.db.close()

    def save(self, *, inspection_id: str, stream_id: str,
             inspection: dict) -> dict:
        check(isinstance(inspection_id, str) and inspection_id and
              isinstance(stream_id, str) and stream_id and
              isinstance(inspection, dict) and
              inspection.get("schema") == "sera.scene-assurance.v0.6" and
              inspection.get("canonical_commit_authorized") is False and
              inspection.get("world_db_writes") == 0 and
              inspection.get("model_calls") == 0 and
              inspection.get("status") == "HOLD",
              "OBSERVATION_CANONICAL_WRITE_NOT_ALLOWED")
        content = canonical(inspection)
        digest = sha256(content.encode("utf-8")).hexdigest()
        previous = self.db.execute(
            "SELECT payload_sha256 FROM inspection_archive "
            "WHERE inspection_id=?", (inspection_id,),
        ).fetchone()
        if previous is not None:
            check(previous[0] == digest, "OBSERVATION_ID_REUSE_CONFLICT")
            return {"inspection_id": inspection_id, "status": "HOLD",
                    "idempotent": True, "canonical_db_writes": 0}
        sightings = inspection["t2_sightings"]
        units = {s["id"]: s for s in inspection["sentence_scan"]["sentences"]}
        check(isinstance(sightings, list), "OBSERVATION_SIGHTINGS_INVALID")
        for s in sightings:
            check(isinstance(s, dict) and s.get("tier") == "T2" and
                  s.get("canonical_entity_created") is False and
                  s.get("presence") == "UNDETERMINED" and
                  isinstance(s.get("ref"), str) and
                  s["ref"].startswith("candidate:") and
                  s.get("sentence_id") in units and
                  type(s.get("start")) is int and
                  type(s.get("end")) is int and
                  units[s["sentence_id"]]["start"] <= s["start"] and
                  s["end"] <= units[s["sentence_id"]]["end"] and
                  units[s["sentence_id"]]["quote"][
                      s["start"]-units[s["sentence_id"]]["start"]:
                      s["end"]-units[s["sentence_id"]]["start"]
                  ] == s["quote"], "OBSERVATION_EVIDENCE_INVALID")
        try:
            self.db.execute("BEGIN IMMEDIATE")
            self.db.execute(
                "INSERT INTO inspection_archive VALUES (?,?,?,?,?,?,?)",
                (inspection_id, stream_id, inspection["scene_key"],
                 inspection["prose_sha256"], content, digest, "HOLD"),
            )
            for i, item in enumerate(sightings):
                self.db.execute(
                    "INSERT INTO candidate_sightings VALUES (?,?,?,?,?,?,?,?)",
                    (inspection_id, i, item["ref"], "T2",
                     item["sentence_id"], item["start"],
                     item["end"], item["quote"]),
                )
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return {"inspection_id": inspection_id, "status": "HOLD",
                "idempotent": False, "canonical_db_writes": 0}

    def inspection(self, inspection_id: str) -> dict | None:
        row = self.db.execute(
            "SELECT payload_json,payload_sha256 FROM inspection_archive "
            "WHERE inspection_id=?", (inspection_id,),
        ).fetchone()
        if row is None:
            return None
        check(sha256(row[0].encode("utf-8")).hexdigest() == row[1],
              "OBSERVATION_ARCHIVE_HASH_INVALID")
        return json.loads(row[0])

    def sightings(self, *, stream_id: str, candidate_ref: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT a.scene_id,a.prose_sha256,s.sentence_id,s.start_offset,"
            "s.end_offset,s.quote FROM candidate_sightings s "
            "JOIN inspection_archive a ON a.inspection_id=s.inspection_id "
            "WHERE a.stream_id=? AND s.candidate_ref=? "
            "ORDER BY a.inspection_id,s.sequence", (stream_id, candidate_ref),
        ).fetchall()
        return [{
            "scene_id": s, "prose_sha256": sha, "sentence_id": sentence_id,
            "start": start, "end": end, "quote": quote, "tier": "T2",
            "canonical_entity_created": False,
        } for s, sha, sentence_id, start, end, quote in rows]
