"""SERA v0.37 — multi-character SQLite scenario fixture over existing WorldStore.

One world-wide physical state stream can hold many characters. This module adds
only lab-scoped identities, story-run membership and a safe writer-facing view.
All versioned states, event CAS, rollback and hash-chain replay REUSE v0.2.
A fixture approval is not production semantic, G2 or world-write authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import sqlite3

from experiments.sera.world_state_v02 import (
    WorldStateError, canonical, entity_template, environment_template,
    fingerprint, initial_state, loadout,
)
from experiments.sera.world_store_v02 import WorldStore

SCHEMA = "sera.multi-character-scenario.v0.37"
RUN_KINDS = frozenset({"STORY", "ORIGIN", "SAGA"})


def require(ok, code):
    if not ok:
        raise WorldStateError(code)


def ident(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 255


def prepare(fixture):
    """Validate synthetic source in full before inserting any SQLite rows."""
    require(isinstance(fixture, dict) and set(fixture) == {
        "schema", "scenario_id", "world_id", "household_id", "universe_id",
        "profile_id", "characters", "objects", "locations", "routes",
    } and fixture["schema"] == SCHEMA, "V037_FIXTURE_SCHEMA_INVALID")
    for key in ("scenario_id", "world_id", "household_id",
                "universe_id", "profile_id"):
        require(ident(fixture[key]), "V037_FIXTURE_ID_INVALID")
    places = fixture["locations"]
    require(isinstance(places, list) and bool(places),
            "V037_LOCATIONS_REQUIRED")
    regions = {}
    for place in places:
        require(isinstance(place, dict) and set(place) == {"id"} and
                ident(place["id"]) and place["id"] not in regions,
                "V037_LOCATION_INVALID_OR_DUPLICATE")
        regions[place["id"]] = environment_template(weather="UNKNOWN")

    members = fixture["characters"]
    objects = fixture["objects"]
    require(isinstance(members, list) and bool(members) and
            isinstance(objects, list), "V037_CHARACTERS_REQUIRED")
    entities = {}
    identities = []
    for person in members:
        require(isinstance(person, dict) and set(person) == {
            "id", "profile_id", "name", "location_id", "knowledge", "traits",
            "origin_fixture_ref", "saga_fixture_ref",
        } and all(ident(person[key]) for key in
                  ("id", "profile_id", "name", "location_id")) and
                person["profile_id"] == fixture["profile_id"] and
                person["id"] not in entities and
                person["location_id"] in regions and
                isinstance(person["knowledge"], list) and
                isinstance(person["traits"], dict) and
                all(ref is None or ident(ref) for ref in
                    (person["origin_fixture_ref"], person["saga_fixture_ref"])),
                "V037_CHARACTER_SCOPE_OR_FIELDS_INVALID")
        require(len(person["knowledge"]) == len(set(person["knowledge"])) and
                all(ident(f) for f in person["knowledge"]),
                "V037_KNOWLEDGE_INVALID")
        entities[person["id"]] = entity_template(
            person["id"], "CHARACTER", person["location_id"],
            traits=person["traits"], knowledge=person["knowledge"],
        )
        identities.append((
            fixture["world_id"], person["id"], person["profile_id"],
            person["name"], person["origin_fixture_ref"],
            person["saga_fixture_ref"],
        ))
    for item in objects:
        require(isinstance(item, dict) and set(item) == {
            "id", "kind", "location_id", "owner_id", "holder_id", "worn_by_id",
        } and ident(item["id"]) and item["id"] not in entities and
                item["kind"] in ("OBJECT", "WEARABLE") and
                item["location_id"] in regions and
                all(x is None or ident(x) for x in
                    (item["owner_id"], item["holder_id"], item["worn_by_id"])),
                "V037_OBJECT_INVALID_OR_DUPLICATE")
        entities[item["id"]] = entity_template(
            item["id"], item["kind"], item["location_id"],
            owner=item["owner_id"], holder=item["holder_id"],
            worn_by=item["worn_by_id"],
        )
    # The existing WorldState graph validator catches incorrect possession,
    # nonexistent holders, worn/not-worn contradictions and invalid fields.
    world = initial_state(entities=entities, regions=regions)

    routes = fixture["routes"]
    require(isinstance(routes, list), "V037_ROUTES_INVALID")
    travel = {}
    for route in routes:
        require(isinstance(route, dict) and set(route) == {
            "from_id", "to_id", "min_minutes",
        } and route["from_id"] in regions and
                route["to_id"] in regions and
                route["from_id"] != route["to_id"] and
                type(route["min_minutes"]) is int and
                route["min_minutes"] > 0, "V037_ROUTE_INVALID")
        key = route["from_id"] + "->" + route["to_id"]
        require(key not in travel, "V037_DUPLICATE_ROUTE")
        travel[key] = route["min_minutes"]
    return world, travel, identities


class ScenarioLab:
    """WorldStore-owned SQLite persistence; never a real G2 physical attestor."""

    def __init__(self, path=":memory:"):
        self.store = WorldStore(path)
        self.db = self.store.db
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS lab_worlds (
                world_id TEXT PRIMARY KEY
                    REFERENCES world_streams(stream_id),
                scenario_id TEXT NOT NULL,
                household_id TEXT NOT NULL,
                universe_id TEXT NOT NULL,
                profile_id TEXT NOT NULL,
                source TEXT NOT NULL CHECK(source='SYNTHETIC_FIXTURE')
            );
            CREATE TABLE IF NOT EXISTS lab_characters (
                world_id TEXT NOT NULL REFERENCES lab_worlds(world_id),
                character_id TEXT NOT NULL,
                profile_id TEXT NOT NULL,
                display_name TEXT NOT NULL,
                origin_fixture_ref TEXT,
                saga_fixture_ref TEXT,
                PRIMARY KEY(world_id, character_id)
            );
            CREATE TABLE IF NOT EXISTS lab_runs (
                run_id TEXT PRIMARY KEY,
                world_id TEXT NOT NULL,
                character_id TEXT NOT NULL,
                kind TEXT NOT NULL CHECK(kind IN ('STORY','ORIGIN','SAGA')),
                status TEXT NOT NULL CHECK(status IN ('OPEN','COMPLETE')),
                start_revision INTEGER NOT NULL,
                FOREIGN KEY(world_id, character_id)
                    REFERENCES lab_characters(world_id, character_id)
            );
            CREATE TABLE IF NOT EXISTS lab_run_events (
                world_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                run_id TEXT NOT NULL REFERENCES lab_runs(run_id),
                revision INTEGER NOT NULL,
                PRIMARY KEY(world_id, event_id),
                FOREIGN KEY(world_id, event_id)
                    REFERENCES world_events(stream_id, event_id)
            );
            CREATE TRIGGER IF NOT EXISTS lab_event_link_immutable_update
                BEFORE UPDATE ON lab_run_events
                BEGIN SELECT RAISE(ABORT,'LAB_EVENT_LINK_IMMUTABLE'); END;
            CREATE TRIGGER IF NOT EXISTS lab_event_link_immutable_delete
                BEFORE DELETE ON lab_run_events
                BEGIN SELECT RAISE(ABORT,'LAB_EVENT_LINK_IMMUTABLE'); END;
        """)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        self.store.close()

    def seed(self, fixture):
        """One logical world, any number of characters, no model/DB writes outside lab."""
        initial, routes, identities = prepare(fixture)
        world_id = fixture["world_id"]
        # Validate the metadata keys before WorldStore's separately committed
        # stream initialization; a duplicate request does not touch the state.
        require(self.db.execute(
            "SELECT 1 FROM lab_worlds WHERE world_id=?", (world_id,)
        ).fetchone() is None and self.db.execute(
            "SELECT 1 FROM world_streams WHERE stream_id=?", (world_id,)
        ).fetchone() is None, "V037_WORLD_ALREADY_SEEDED")
        self.store.create(world_id, initial, travel_minutes=routes)
        try:
            self.db.execute("BEGIN IMMEDIATE")
            self.db.execute(
                "INSERT INTO lab_worlds VALUES (?,?,?,?,?,?)",
                (world_id, fixture["scenario_id"], fixture["household_id"],
                 fixture["universe_id"], fixture["profile_id"],
                 "SYNTHETIC_FIXTURE"),
            )
            self.db.executemany(
                "INSERT INTO lab_characters VALUES (?,?,?,?,?,?)", identities
            )
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            # No silent successful return from an incomplete fixture; this
            # orphaned stream is a visible setup error requiring a fresh DB.
            raise
        return {
            "status": "SYNTHETIC_WORLD_SEEDED_NONCANONICAL",
            "world_id": world_id,
            "character_ids": sorted(initial["entities"][key]["entity_id"]
                                    for key in initial["entities"]
                                    if initial["entities"][key]["kind"] == "CHARACTER"),
            "revision": 0,
            "canonical_commit_authorized": False,
            "production_db_writes": 0,
        }

    def _run(self, run_id):
        row = self.db.execute(
            "SELECT run_id,world_id,character_id,kind,status,start_revision "
            "FROM lab_runs WHERE run_id=?", (run_id,),
        ).fetchone()
        require(row is not None, "V037_RUN_UNKNOWN")
        return dict(zip(("run_id","world_id","character_id","kind",
                         "status","start_revision"), row))

    def begin_story(self, *, run_id, world_id, character_id):
        require(all(ident(v) for v in (run_id, world_id, character_id)),
                "V037_STORY_RUN_ID_INVALID")
        exists = self.db.execute(
            "SELECT 1 FROM lab_characters WHERE world_id=? AND character_id=?",
            (world_id, character_id),
        ).fetchone()
        require(exists is not None, "V037_CHARACTER_NOT_IN_WORLD")
        state = self.store.head(world_id)
        self.db.execute(
            "INSERT INTO lab_runs VALUES (?,?,?,?,?,?)",
            (run_id, world_id, character_id, "STORY", "OPEN", state["revision"]),
        )
        return self.context(run_id)

    def context(self, run_id):
        """Writer-facing view: never leaks other character's private knowledge."""
        run = self._run(run_id)
        require(run["kind"] == "STORY", "V037_FUTURE_STAGE_NOT_ACTIVE")
        state = self.store.head(run["world_id"])
        actor = state["entities"].get(run["character_id"])
        require(actor is not None and actor["kind"] == "CHARACTER",
                "V037_PRIMARY_CHARACTER_MISSING")
        pos = actor["location"]
        visible = []
        for eid, ent in sorted(state["entities"].items()):
            if eid == run["character_id"] or ent["location"] != pos or (
                ent["lifecycle"] == "DESTROYED"
            ):
                continue
            # No private traits, knowledge, inferred descriptions or facts
            # from any other character are ever exposed to the writer.
            visible.append({
                "id": eid, "kind": ent["kind"], "location": ent["location"],
                "holder": ent["holder"], "worn_by": ent["worn_by"],
                "owner": ent["owner"],
            })
        return {
            "schema": "sera.story-scene-context.v0.37",
            "source": "SYNTHETIC_SQLITE_WORLD",
            "run_id": run_id,
            "world_id": run["world_id"],
            "primary_character_id": run["character_id"],
            "location": pos,
            "revision": state["revision"],
            "state_sha256": sha256(canonical(state).encode()).hexdigest(),
            "loadout": loadout(state, run["character_id"]),
            "visible_entities": visible,
            "run_status": run["status"],
            "canonical_commit_authorized": False,
            "production_db_writes": 0,
            "g2_commit_request": None,
        }

    def commit_story_fixture(self, *, run_id, expected_revision, events,
                             fixture_approvals):
        """Only a consciously supplied test-fixture grant; not model authority."""
        run = self._run(run_id)
        require(run["kind"] == "STORY" and run["status"] == "OPEN",
                "V037_STORY_RUN_NOT_OPEN")
        require(isinstance(fixture_approvals, dict) and
                isinstance(events, list) and bool(events) and
                all(isinstance(e, dict) and
                    fixture_approvals.get(e.get("event_id")) == fingerprint(e)
                    for e in events),
                "V037_FIXTURE_GRANT_REQUIRED")
        # Disallow aliasing an existing event to a different character's run
        # even though WorldStore itself correctly handles event idempotency.
        for event in events:
            stored = self.db.execute(
                "SELECT run_id FROM lab_run_events "
                "WHERE world_id=? AND event_id=?",
                (run["world_id"], event["event_id"]),
            ).fetchone()
            require(stored is None or stored[0] == run_id,
                    "V037_EVENT_OWNED_BY_ANOTHER_RUN")

        def record(db, _before, _after, event, revision):
            db.execute(
                "INSERT INTO lab_run_events VALUES (?,?,?,?)",
                (run["world_id"], event["event_id"], run_id, revision),
            )

        new_state = self.store.commit(
            run["world_id"], expected_revision=expected_revision,
            events=events, approvals=fixture_approvals,
            on_event_committed=record,
        )
        return {
            "status": "STORY_FIXTURE_COMMITTED_TO_SIMULATION_ONLY",
            "world_id": run["world_id"],
            "run_id": run_id,
            "revision": new_state["revision"],
            "state_sha256": sha256(canonical(new_state).encode()).hexdigest(),
            "canonical_commit_authorized": False,
            "production_db_writes": 0,
            "g2_commit_request": None,
        }

    def head(self, world_id):
        self._world_exists(world_id)
        return self.store.head(world_id)

    def _world_exists(self, world_id):
        require(self.db.execute(
            "SELECT 1 FROM lab_worlds WHERE world_id=?", (world_id,)
        ).fetchone() is not None, "V037_LAB_WORLD_UNKNOWN")

    def finish_story(self, run_id):
        run = self._run(run_id)
        require(run["kind"] == "STORY" and run["status"] == "OPEN",
                "V037_STORY_RUN_NOT_OPEN")
        self.db.execute("UPDATE lab_runs SET status='COMPLETE' WHERE run_id=?",
                        (run_id,))
        return self.context(run_id)

    def reserved_stage(self, kind):
        require(kind in RUN_KINDS, "V037_RUN_KIND_INVALID")
        require(kind == "STORY", "V037_FUTURE_STAGE_NOT_ACTIVE")
        return "STORY"
