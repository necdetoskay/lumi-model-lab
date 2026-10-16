"""SERA v0.2 isolated SQLite event store and historical state reconstruction.

Experimental SQLite ONLY; never uses Project LUMI databases or migrations.
Accepted mutations require caller-supplied app authorization fingerprints.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import sqlite3

from experiments.sera.world_state_v02 import (
    WorldStateError, apply_event, canonical, check, fingerprint, validate,
)


def digest(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


class WorldStore:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(str(path), isolation_level=None)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS world_streams (
                stream_id TEXT PRIMARY KEY,
                revision INTEGER NOT NULL,
                initial_json TEXT NOT NULL,
                initial_sha TEXT NOT NULL,
                head_json TEXT NOT NULL,
                head_sha TEXT NOT NULL,
                rules_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS world_snapshots (
                stream_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                state_json TEXT NOT NULL,
                state_sha TEXT NOT NULL,
                PRIMARY KEY(stream_id, revision),
                FOREIGN KEY(stream_id) REFERENCES world_streams(stream_id)
            );
            CREATE TABLE IF NOT EXISTS world_events (
                stream_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                event_id TEXT NOT NULL,
                event_json TEXT NOT NULL,
                event_sha TEXT NOT NULL,
                previous_sha TEXT NOT NULL,
                PRIMARY KEY(stream_id, revision),
                UNIQUE(stream_id, event_id),
                FOREIGN KEY(stream_id) REFERENCES world_streams(stream_id)
            );
            CREATE TABLE IF NOT EXISTS world_entity_history (
                stream_id TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                event_id TEXT NOT NULL,
                before_json TEXT,
                after_json TEXT,
                PRIMARY KEY(stream_id, entity_id, revision),
                FOREIGN KEY(stream_id, revision)
                    REFERENCES world_events(stream_id, revision)
            );
            CREATE TABLE IF NOT EXISTS world_environment_history (
                stream_id TEXT NOT NULL,
                region_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                event_id TEXT NOT NULL,
                before_json TEXT,
                after_json TEXT,
                PRIMARY KEY(stream_id, region_id, revision),
                FOREIGN KEY(stream_id, revision)
                    REFERENCES world_events(stream_id, revision)
            );
            CREATE INDEX IF NOT EXISTS entity_history_lookup
                ON world_entity_history(stream_id, entity_id, revision);
            CREATE INDEX IF NOT EXISTS environment_history_lookup
                ON world_environment_history(stream_id, region_id, revision);
            CREATE TRIGGER IF NOT EXISTS world_events_immutable_update
                BEFORE UPDATE ON world_events
                BEGIN SELECT RAISE(ABORT, 'EVENT_LOG_IMMUTABLE'); END;
            CREATE TRIGGER IF NOT EXISTS world_events_immutable_delete
                BEFORE DELETE ON world_events
                BEGIN SELECT RAISE(ABORT, 'EVENT_LOG_IMMUTABLE'); END;
            CREATE TRIGGER IF NOT EXISTS snapshots_immutable_update
                BEFORE UPDATE ON world_snapshots
                BEGIN SELECT RAISE(ABORT, 'SNAPSHOT_IMMUTABLE'); END;
            CREATE TRIGGER IF NOT EXISTS snapshots_immutable_delete
                BEFORE DELETE ON world_snapshots
                BEGIN SELECT RAISE(ABORT, 'SNAPSHOT_IMMUTABLE'); END;
            CREATE TRIGGER IF NOT EXISTS entity_history_immutable_update
                BEFORE UPDATE ON world_entity_history
                BEGIN SELECT RAISE(ABORT, 'ENTITY_HISTORY_IMMUTABLE'); END;
            CREATE TRIGGER IF NOT EXISTS entity_history_immutable_delete
                BEFORE DELETE ON world_entity_history
                BEGIN SELECT RAISE(ABORT, 'ENTITY_HISTORY_IMMUTABLE'); END;
            CREATE TRIGGER IF NOT EXISTS environment_history_immutable_update
                BEFORE UPDATE ON world_environment_history
                BEGIN SELECT RAISE(ABORT, 'ENVIRONMENT_HISTORY_IMMUTABLE'); END;
            CREATE TRIGGER IF NOT EXISTS environment_history_immutable_delete
                BEFORE DELETE ON world_environment_history
                BEGIN SELECT RAISE(ABORT, 'ENVIRONMENT_HISTORY_IMMUTABLE'); END;
        """)

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _row(self, stream_id):
        row = self.db.execute(
            "SELECT revision, initial_json, initial_sha, head_json, head_sha, "
            "rules_json FROM world_streams WHERE stream_id=?",
            (stream_id,),
        ).fetchone()
        check(row is not None, "WORLD_STREAM_UNKNOWN")
        return row

    def create(self, stream_id, initial, *, travel_minutes=None,
               world_rules=(), on_stream_created=None):
        validate(initial)
        check(initial["revision"] == 0 and initial["events"] == [],
              "INITIAL_STATE_MUST_BE_UNCOMMITTED")
        check(isinstance(stream_id, str) and stream_id,
              "STREAM_ID_INVALID")
        routes = dict(travel_minutes or {})
        rules = tuple(sorted(set(world_rules)))
        check(all(isinstance(key, str) and type(v) is int and v >= 0
                  for key, v in routes.items()), "TRAVEL_RULES_INVALID")
        check(all(isinstance(rule, str) and rule for rule in rules),
              "WORLD_RULES_INVALID")
        config = canonical({"routes": routes, "rules": rules})
        state_json = canonical(initial)
        state_hash = digest(state_json)
        try:
            self.db.execute("BEGIN IMMEDIATE")
            self.db.execute(
                "INSERT INTO world_streams VALUES (?,?,?,?,?,?,?)",
                (stream_id, 0, state_json, state_hash,
                 state_json, state_hash, config),
            )
            self.db.execute(
                "INSERT INTO world_snapshots VALUES (?,?,?,?)",
                (stream_id, 0, state_json, state_hash),
            )
            # Optional fixture metadata must be part of the SAME atomic seed.
            # No nested BEGIN/COMMIT in the callback; failure rolls back all.
            if on_stream_created is not None:
                on_stream_created(self.db)
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def head(self, stream_id):
        revision, _initial, _sha, state, recorded_sha, _rules = self._row(stream_id)
        check(digest(state) == recorded_sha, "HEAD_HASH_MISMATCH")
        decoded = json.loads(state)
        check(decoded["revision"] == revision, "HEAD_REVISION_MISMATCH")
        validate(decoded)
        return decoded

    def snapshot(self, stream_id, revision):
        check(type(revision) is int and revision >= 0, "REVISION_INVALID")
        row = self.db.execute(
            "SELECT state_json,state_sha FROM world_snapshots "
            "WHERE stream_id=? AND revision=?", (stream_id, revision),
        ).fetchone()
        check(row is not None, "SNAPSHOT_REVISION_UNKNOWN")
        check(digest(row[0]) == row[1], "SNAPSHOT_HASH_MISMATCH")
        state = json.loads(row[0])
        validate(state)
        return state

    def entity_at(self, stream_id, entity_id, *, revision=None, story_minute=None):
        check(not (revision is not None and story_minute is not None),
              "HISTORY_QUERY_AMBIGUOUS")
        if story_minute is not None:
            check(type(story_minute) is int and story_minute >= 0,
                  "HISTORY_TIME_INVALID")
            row = self.db.execute(
                "SELECT revision FROM world_snapshots "
                "WHERE stream_id=? AND json_extract(state_json,'$.minute')<=? "
                "ORDER BY revision DESC LIMIT 1",
                (stream_id, story_minute),
            ).fetchone()
            check(row is not None, "HISTORY_TIME_OUT_OF_RANGE")
            revision = row[0]
        state = (self.head(stream_id) if revision is None
                 else self.snapshot(stream_id, revision))
        return deepcopy(state["entities"].get(entity_id))

    def entity_history(self, stream_id, entity_id):
        self._row(stream_id)
        rows = self.db.execute(
            "SELECT revision,event_id,before_json,after_json "
            "FROM world_entity_history WHERE stream_id=? AND entity_id=? "
            "ORDER BY revision", (stream_id, entity_id),
        ).fetchall()
        return [
            {"revision": r, "event_id": eid,
             "before": json.loads(before) if before is not None else None,
             "after": json.loads(after) if after is not None else None}
            for r, eid, before, after in rows
        ]

    def environment_history(self, stream_id, region_id):
        self._row(stream_id)
        rows = self.db.execute(
            "SELECT revision,event_id,before_json,after_json "
            "FROM world_environment_history WHERE stream_id=? AND region_id=? "
            "ORDER BY revision", (stream_id, region_id),
        ).fetchall()
        return [
            {"revision": rev, "event_id": eid,
             "before": json.loads(before) if before else None,
             "after": json.loads(after) if after else None}
            for rev, eid, before, after in rows
        ]

    def commit(self, stream_id, *, expected_revision: int,
               events: list[dict], approvals: dict[str, str],
               on_event_committed=None):
        """One transactional batch; optimistic concurrency and idempotency.

        All events are validated before any persistent commit. An exact
        all-repeated batch is idempotent; mixed old/new or mutated IDs fail.
        """
        check(type(expected_revision) is int and expected_revision >= 0,
              "EXPECTED_REVISION_INVALID")
        check(isinstance(events, list) and bool(events), "EMPTY_EVENT_BATCH")
        check(isinstance(approvals, dict), "APPROVALS_INVALID")
        try:
            self.db.execute("BEGIN IMMEDIATE")
            rev, _base, _base_sha, state_json, head_sha, rules_json = self._row(stream_id)
            persisted = self.db.execute(
                "SELECT event_id,event_json FROM world_events WHERE stream_id=?",
                (stream_id,),
            ).fetchall()
            existing = dict(persisted)
            repeat_count = sum(e.get("event_id") in existing for e in events
                               if isinstance(e, dict))
            if repeat_count:
                for e in events:
                    eid = e.get("event_id")
                    check(eid in existing and existing[eid] == canonical(e),
                          f"EVENT_ID_CONFLICT:{eid}")
                check(repeat_count == len(events), "PARTIAL_REPLAY_FORBIDDEN")
                self.db.execute("COMMIT")
                return json.loads(state_json)
            check(rev == expected_revision, "OPTIMISTIC_REVISION_CONFLICT")
            check(digest(state_json) == head_sha, "HEAD_HASH_MISMATCH")
            state = json.loads(state_json)
            config = json.loads(rules_json)
            last = self.db.execute(
                "SELECT event_sha FROM world_events WHERE stream_id=? "
                "ORDER BY revision DESC LIMIT 1", (stream_id,),
            ).fetchone()
            previous = last[0] if last else "0" * 64
            for event in events:
                # No event from a model has authority to supply its own grant.
                before = state
                state = apply_event(
                    state, event, approvals=approvals,
                    travel_minutes=config["routes"],
                    world_rules=frozenset(config["rules"]),
                )
                event_json = canonical(event)
                rev = state["revision"]
                event_sha = digest(previous + "|" + str(rev) +
                                   "|" + event_json)
                self.db.execute(
                    "INSERT INTO world_events VALUES (?,?,?,?,?,?)",
                    (stream_id, rev, event["event_id"], event_json,
                     event_sha, previous),
                )
                ids = set(before["entities"]) | set(state["entities"])
                for entity_id in ids:
                    old = before["entities"].get(entity_id)
                    new = state["entities"].get(entity_id)
                    touched = (event["type"] == "INTERACT_ENTITY" and
                               event["payload"]["entity_id"] == entity_id)
                    if old != new or touched:
                        self.db.execute(
                            "INSERT INTO world_entity_history VALUES (?,?,?,?,?,?)",
                            (stream_id, entity_id, rev, event["event_id"],
                             canonical(old) if old is not None else None,
                             canonical(new) if new is not None else None),
                        )
                for region in set(before["regions"]) | set(state["regions"]):
                    old = before["regions"].get(region)
                    new = state["regions"].get(region)
                    if old != new:
                        self.db.execute(
                            "INSERT INTO world_environment_history VALUES "
                            "(?,?,?,?,?,?)",
                            (stream_id, region, rev, event["event_id"],
                             canonical(old) if old is not None else None,
                             canonical(new) if new is not None else None),
                        )
                snapshot_json = canonical(state)
                self.db.execute(
                    "INSERT INTO world_snapshots VALUES (?,?,?,?)",
                    (stream_id, rev, snapshot_json, digest(snapshot_json)),
                )
                # Optional trusted integration callback executes within the
                # SAME SQLite transaction, after each validated world mutation.
                # It must not COMMIT/ROLLBACK or modify existing ledger rows.
                # Any exception fails closed and rolls back both ledgers.
                if on_event_committed is not None:
                    on_event_committed(
                        self.db, deepcopy(before), deepcopy(state),
                        deepcopy(event), rev,
                    )
                previous = event_sha
            final_json = canonical(state)
            self.db.execute(
                "UPDATE world_streams SET revision=?,head_json=?,head_sha=? "
                "WHERE stream_id=? AND revision=?",
                (rev, final_json, digest(final_json), stream_id,
                 expected_revision),
            )
            check(self.db.execute("SELECT changes()").fetchone()[0] == 1,
                  "OPTIMISTIC_REVISION_CONFLICT")
            self.db.execute("COMMIT")
            return deepcopy(state)
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def verify_replay(self, stream_id):
        """Replay all signed-identity events and compare every checkpoint."""
        head_revision, original, original_sha, head_json, head_sha, rules_json = (
            self._row(stream_id)
        )
        check(digest(original) == original_sha, "INITIAL_HASH_MISMATCH")
        initial = json.loads(original)
        state = self.snapshot(stream_id, 0)
        check(state == initial, "INITIAL_SNAPSHOT_MISMATCH")
        config = json.loads(rules_json)
        previous = "0" * 64
        rows = self.db.execute(
            "SELECT revision,event_id,event_json,event_sha,previous_sha "
            "FROM world_events WHERE stream_id=? ORDER BY revision",
            (stream_id,),
        ).fetchall()
        for rev, eid, json_event, h, prev in rows:
            check(prev == previous and
                  h == digest(previous + "|" + str(rev) + "|" + json_event),
                  "EVENT_HASH_CHAIN_INVALID")
            event = json.loads(json_event)
            check(event["event_id"] == eid, "EVENT_ID_INTEGRITY_INVALID")
            state = apply_event(
                state, event, approvals={eid: fingerprint(event)},
                travel_minutes=config["routes"],
                world_rules=frozenset(config["rules"]),
            )
            check(state["revision"] == rev and
                  state == self.snapshot(stream_id, rev),
                  "EVENT_REPLAY_SNAPSHOT_MISMATCH")
            previous = h
        check(head_revision == state["revision"] and
              digest(head_json) == head_sha and
              state == json.loads(head_json),
              "EVENT_REPLAY_HEAD_MISMATCH")
        return True
