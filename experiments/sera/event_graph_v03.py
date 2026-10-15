"""SERA EventGraph v0.3: typed narrative-event DAG + atomic world effects.

Experimental, standard-library-only. A model's story/event proposal is NEVER
authority to approve a v0.2 state mutation. Effects are derived from the Python
world reducer; model-supplied before/after values are deliberately not accepted.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

from experiments.sera.world_state_v02 import (
    WorldStateError, canonical, check, event_contract, fingerprint, validate,
)
from experiments.sera.world_store_v02 import WorldStore

SCHEMA = "sera.narrative-event.v0.3"
P_FIELDS = frozenset({
    "schema", "event_id", "event_type", "scene_id", "location",
    "epistemic", "participants", "objects", "time",
    "caused_by", "preconditions", "evidence", "world_event",
})
ROLES = frozenset({"ACTOR", "SPEAKER", "LISTENER", "WITNESS", "AFFECTED",
                   "RECIPIENT", "REMOTE_WITNESS"})
OBJECT_ROLES = frozenset({"EVIDENCE", "TOPIC", "TOOL", "AFFECTED"})
EPISTEMIC = frozenset({"OBSERVED_ACTION", "REPORTED_CLAIM",
                       "HYPOTHESIS", "NARRATOR_FACT"})
KINDS = frozenset({"TESTIMONY", "DISCOVERY", "TRANSFER", "OBSERVATION",
                   "MOVEMENT", "DECISION", "INTERACTION", "WORLD_CHANGE",
                   "STORY_BEAT"})
EXACT_ROLE = frozenset({"id", "role"})
EXACT_TIME = frozenset({"ordinal", "earliest_minute", "latest_minute",
                        "exact_minute"})
EXACT_PRECONDITION = frozenset({"scope", "id", "path", "equals"})
EXACT_EVIDENCE = frozenset({"prose_sha256", "start", "end", "quote"})
REVIEW_FIELDS = frozenset({"decision", "authority", "event_hash",
                           "prose_sha256", "reason"})


def require_shape(value, names, code):
    check(isinstance(value, dict) and set(value) == names, code)


def digest_obj(obj) -> str:
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def _get(root, path):
    check(isinstance(path, list) and path and all(
        isinstance(part, str) and part and
        not part.startswith("_") and part not in ("events",)
        for part in path), "EVENT_PRECONDITION_PATH_INVALID")
    value = root
    for part in path:
        check(isinstance(value, dict) and part in value,
              "EVENT_PRECONDITION_FIELD_UNKNOWN")
        value = value[part]
    return value


def _diff(before, after, path=()):
    """Full typed leaf changes. No diff if an object's value was unchanged."""
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        results = []
        for name in sorted(set(before) | set(after)):
            if name in before and name in after:
                results += _diff(before[name], after[name], path + (name,))
            else:
                results.append({
                    "path": list(path + (name,)),
                    "before": deepcopy(before.get(name)),
                    "after": deepcopy(after.get(name)),
                })
        return results
    return [{
        "path": list(path),
        "before": deepcopy(before),
        "after": deepcopy(after),
    }]


def world_effects(before, after) -> list[dict]:
    """Calculate effects from the actual v0.2 reducer output, never from text."""
    effects = []
    for scope, collection in (("ENTITY", "entities"), ("REGION", "regions")):
        keys = sorted(set(before[collection]) | set(after[collection]))
        for key in keys:
            for difference in _diff(
                before[collection].get(key), after[collection].get(key)
            ):
                effects.append({"scope": scope, "id": key, **difference})
    return effects


def validate_proposal(proposal: dict, *, prose: str, state: dict) -> None:
    """Validate stable IDs, exact evidence, related physical entities and time."""
    validate(state)
    require_shape(proposal, P_FIELDS, "NARRATIVE_SCHEMA_INVALID")
    check(proposal["schema"] == SCHEMA, "NARRATIVE_SCHEMA_VERSION_INVALID")
    check(all(isinstance(proposal[k], str) and proposal[k].strip()
              for k in ("event_id", "event_type", "scene_id", "location")),
          "NARRATIVE_HEADER_INVALID")
    check(proposal["event_type"] in KINDS, "NARRATIVE_TYPE_INVALID")
    check(proposal["epistemic"] in EPISTEMIC, "NARRATIVE_EPISTEMIC_INVALID")
    check(isinstance(proposal["participants"], list) and
          isinstance(proposal["objects"], list), "NARRATIVE_ROLES_INVALID")
    seen_people = set()
    for person in proposal["participants"]:
        require_shape(person, EXACT_ROLE, "PARTICIPANT_SCHEMA_INVALID")
        ident, role = person["id"], person["role"]
        check(isinstance(ident, str) and ident in state["entities"] and
              state["entities"][ident]["kind"] == "CHARACTER",
              f"NARRATIVE_CHARACTER_UNKNOWN:{ident}")
        check(role in ROLES and (ident, role) not in seen_people,
              "PARTICIPANT_ROLE_INVALID")
        seen_people.add((ident, role))
        if role not in ("REMOTE_WITNESS", "AFFECTED"):
            check(state["entities"][ident]["location"] == proposal["location"],
                  f"PARTICIPANT_LOCATION_MISMATCH:{ident}")
    seen_objects = set()
    for obj in proposal["objects"]:
        require_shape(obj, EXACT_ROLE, "OBJECT_RELATION_SCHEMA_INVALID")
        ident, role = obj["id"], obj["role"]
        check(isinstance(ident, str) and ident and
              role in OBJECT_ROLES and (ident, role) not in seen_objects,
              "OBJECT_RELATION_INVALID")
        seen_objects.add((ident, role))
        target = state["entities"].get(ident)
        check(target is not None or (
            proposal["world_event"]["type"] == "INTRODUCE_ENTITY"
            and proposal["world_event"]["payload"].get("entity_id") == ident
        ), f"OBJECT_RELATION_UNKNOWN:{ident}")
        if target is not None:
            check(target["kind"] != "CHARACTER",
                  f"CHARACTER_NOT_PHYSICAL_OBJECT:{ident}")
            if role in ("TOOL", "AFFECTED"):
                check(target["location"] == proposal["location"],
                      f"OBJECT_LOCATION_MISMATCH:{ident}")
    require_shape(proposal["time"], EXACT_TIME, "NARRATIVE_TIME_SCHEMA_INVALID")
    t = proposal["time"]
    check(type(t["ordinal"]) is int and t["ordinal"] >= 1,
          "NARRATIVE_ORDINAL_INVALID")
    for name in ("earliest_minute", "latest_minute", "exact_minute"):
        v = t[name]
        check(v is None or (type(v) is int and v >= 0),
              "NARRATIVE_TIME_VALUE_INVALID")
    if t["earliest_minute"] is not None and t["latest_minute"] is not None:
        check(t["earliest_minute"] <= t["latest_minute"],
              "NARRATIVE_TIME_RANGE_INVALID")
    if t["exact_minute"] is not None:
        check(all(bound is None or (
            t["exact_minute"] >= bound if key == "earliest_minute"
            else t["exact_minute"] <= bound
        ) for key, bound in (
            ("earliest_minute", t["earliest_minute"]),
            ("latest_minute", t["latest_minute"]),
        )), "NARRATIVE_EXACT_TIME_OUT_OF_RANGE")
        check(proposal["world_event"]["at_minute"] == t["exact_minute"],
              "NARRATIVE_WORLD_TIME_MISMATCH")
    else:
        # No fake exact minute: the v0.2 mutation cursor is an application
        # resolution timestamp, NOT a claim that the prose specifies it.
        minute = proposal["world_event"]["at_minute"]
        check(t["earliest_minute"] is None or
              minute >= t["earliest_minute"],
              "NARRATIVE_EVENT_BEFORE_WINDOW")
        check(t["latest_minute"] is None or
              minute <= t["latest_minute"],
              "NARRATIVE_EVENT_AFTER_WINDOW")
    check(isinstance(proposal["caused_by"], list) and all(
        isinstance(dep, str) and dep for dep in proposal["caused_by"]
    ) and len(set(proposal["caused_by"])) == len(proposal["caused_by"]),
          "NARRATIVE_DEPENDENCIES_INVALID")
    check(proposal["event_id"] not in proposal["caused_by"],
          "NARRATIVE_SELF_CAUSATION")
    check(isinstance(proposal["preconditions"], list),
          "NARRATIVE_PRECONDITIONS_INVALID")
    for cond in proposal["preconditions"]:
        require_shape(cond, EXACT_PRECONDITION,
                      "NARRATIVE_PRECONDITION_SCHEMA_INVALID")
        check(cond["scope"] in ("ENTITY", "REGION"), "PRECONDITION_SCOPE_INVALID")
        group = ("entities" if cond["scope"] == "ENTITY" else "regions")
        check(isinstance(cond["id"], str) and cond["id"] in state[group],
              "PRECONDITION_ENTITY_UNKNOWN")
        check(_get(state[group][cond["id"]], cond["path"]) == cond["equals"],
              f"NARRATIVE_PRECONDITION_FAILED:{cond['id']}")
    require_shape(proposal["evidence"], EXACT_EVIDENCE,
                  "NARRATIVE_EVIDENCE_SCHEMA_INVALID")
    ev = proposal["evidence"]
    check(isinstance(prose, str) and prose,
          "NARRATIVE_PROSE_MISSING")
    check(ev["prose_sha256"] == hashlib.sha256(
        prose.encode("utf-8")).hexdigest(), "NARRATIVE_PROSE_HASH_MISMATCH")
    start, end = ev["start"], ev["end"]
    check(type(start) is int and type(end) is int and
          0 <= start < end <= len(prose) and
          isinstance(ev["quote"], str) and
          ev["quote"] == prose[start:end],
          "NARRATIVE_EVIDENCE_SPAN_INVALID")
    event_contract(proposal["world_event"])
    event = proposal["world_event"]
    check(event["event_id"] == proposal["event_id"],
          "NARRATIVE_WORLD_EVENT_ID_MISMATCH")
    if proposal["epistemic"] in ("HYPOTHESIS",):
        check(event["type"] in ("INTERACT_ENTITY", "ADVANCE_SCENE"),
              "HYPOTHESIS_CANNOT_MUTATE_WORLD")
    if proposal["epistemic"] == "REPORTED_CLAIM" and event["type"] == "LEARN_FACT":
        check(event["payload"]["fact_id"].startswith("claim:"),
              "REPORTED_CLAIM_MUST_REMAIN_ATTRIBUTED")
    if proposal["epistemic"] == "REPORTED_CLAIM":
        check(event["type"] in ("LEARN_FACT", "INTERACT_ENTITY",
                                "ADVANCE_SCENE"),
              "REPORTED_CLAIM_CANNOT_BECOME_WORLD_FACT")

    people = {p["id"] for p in proposal["participants"]}
    related_objects = {o["id"] for o in proposal["objects"]}
    payload = event["payload"]
    for name in ("actor_id", "character_id", "from_id", "to_id"):
        ident = payload.get(name)
        if ident is not None:
            check(ident in people, f"EVENT_ACTOR_NOT_LINKED:{ident}")
    for name in ("entity_id", "object_id"):
        ident = payload.get(name)
        if ident is not None:
            check(ident in related_objects, f"EVENT_OBJECT_NOT_LINKED:{ident}")


def validate_review(review: dict, proposal: dict):
    """Trusted application-adjudication metadata, NOT an LLM signature."""
    require_shape(review, REVIEW_FIELDS, "NARRATIVE_REVIEW_SCHEMA_INVALID")
    check(review["decision"] == "APPROVED" and
          review["authority"] == "APPLICATION" and
          isinstance(review["reason"], str) and review["reason"].strip() and
          review["event_hash"] == digest_obj(proposal) and
          review["prose_sha256"] == proposal["evidence"]["prose_sha256"],
          "NARRATIVE_NOT_APPROVED")


class EventGraphStore:
    """Separate event metadata sharing the SAME SQLite transaction as WorldStore."""

    def __init__(self, path=":memory:"):
        self.world = WorldStore(path)
        self.db = self.world.db
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS narrative_events (
          stream_id TEXT NOT NULL, event_id TEXT NOT NULL,
          revision INTEGER NOT NULL, scene_id TEXT NOT NULL,
          ordinal INTEGER NOT NULL, event_type TEXT NOT NULL,
          epistemic TEXT NOT NULL, location TEXT NOT NULL,
          proposal_json TEXT NOT NULL, proposal_sha TEXT NOT NULL,
          review_json TEXT NOT NULL, PRIMARY KEY(stream_id,event_id),
          UNIQUE(stream_id,scene_id,ordinal),
          FOREIGN KEY(stream_id,revision)
            REFERENCES world_events(stream_id,revision)
        );
        CREATE TABLE IF NOT EXISTS narrative_participants (
          stream_id TEXT NOT NULL, event_id TEXT NOT NULL,
          entity_id TEXT NOT NULL, role TEXT NOT NULL,
          PRIMARY KEY(stream_id,event_id,entity_id,role),
          FOREIGN KEY(stream_id,event_id)
            REFERENCES narrative_events(stream_id,event_id)
        );
        CREATE TABLE IF NOT EXISTS narrative_objects (
          stream_id TEXT NOT NULL, event_id TEXT NOT NULL,
          entity_id TEXT NOT NULL, role TEXT NOT NULL,
          PRIMARY KEY(stream_id,event_id,entity_id,role),
          FOREIGN KEY(stream_id,event_id)
            REFERENCES narrative_events(stream_id,event_id)
        );
        CREATE TABLE IF NOT EXISTS narrative_dependencies (
          stream_id TEXT NOT NULL, event_id TEXT NOT NULL,
          caused_by TEXT NOT NULL,
          PRIMARY KEY(stream_id,event_id,caused_by),
          FOREIGN KEY(stream_id,event_id)
            REFERENCES narrative_events(stream_id,event_id),
          FOREIGN KEY(stream_id,caused_by)
            REFERENCES narrative_events(stream_id,event_id)
        );
        CREATE TABLE IF NOT EXISTS narrative_effects (
          stream_id TEXT NOT NULL, event_id TEXT NOT NULL,
          ordinal INTEGER NOT NULL,
          scope TEXT NOT NULL, entity_id TEXT NOT NULL,
          path_json TEXT NOT NULL, before_json TEXT NOT NULL,
          after_json TEXT NOT NULL,
          PRIMARY KEY(stream_id,event_id,ordinal),
          FOREIGN KEY(stream_id,event_id)
            REFERENCES narrative_events(stream_id,event_id)
        );
        CREATE TABLE IF NOT EXISTS narrative_lifecycle (
          stream_id TEXT NOT NULL, event_id TEXT NOT NULL,
          sequence INTEGER NOT NULL,
          status TEXT NOT NULL, rationale TEXT NOT NULL,
          PRIMARY KEY(stream_id,event_id,sequence),
          FOREIGN KEY(stream_id,event_id)
            REFERENCES narrative_events(stream_id,event_id)
        );
        CREATE INDEX IF NOT EXISTS narrative_entity_object_index
          ON narrative_objects(stream_id,entity_id);
        CREATE INDEX IF NOT EXISTS narrative_entity_person_index
          ON narrative_participants(stream_id,entity_id);
        CREATE INDEX IF NOT EXISTS narrative_causes_index
          ON narrative_dependencies(stream_id,caused_by);
        """)
        for name in (
            "narrative_events", "narrative_participants", "narrative_objects",
            "narrative_dependencies", "narrative_effects",
            "narrative_lifecycle"
        ):
            for action in ("UPDATE", "DELETE"):
                self.db.execute(
                    f"CREATE TRIGGER IF NOT EXISTS guard_{name}_{action.lower()} "
                    f"BEFORE {action} ON {name} BEGIN "
                    "SELECT RAISE(ABORT, 'NARRATIVE_LEDGER_IMMUTABLE'); END"
                )

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.world.close()

    def create(self, *args, **kwargs):
        return self.world.create(*args, **kwargs)

    def head(self, stream_id):
        return self.world.head(stream_id)

    def _prior(self, stream_id, event_id):
        row = self.db.execute(
            "SELECT proposal_json, revision FROM narrative_events "
            "WHERE stream_id=? AND event_id=?", (stream_id, event_id)
        ).fetchone()
        return row

    def commit(self, *, stream_id: str, proposal: dict, prose: str,
               review: dict, approved_world_events: dict,
               expected_revision: int) -> dict:
        """One reviewed narrative event/world event transaction.

        This API must only be called by trusted application orchestration
        after separate extractor/JEV/human validation. It does not run a JEV
        model and a hash is not an unforgeable authority token.
        """
        check(isinstance(stream_id, str) and stream_id,
              "NARRATIVE_STREAM_ID_INVALID")
        state = self.head(stream_id)
        validate_review(review, proposal)
        # Reject mutated/forged replays without rewriting any history.
        previous = self._prior(stream_id, proposal["event_id"])
        if previous is not None:
            check(previous[0] == canonical(proposal),
                  "NARRATIVE_ID_CONFLICT")
            return {"status": "COMMITTED", "revision": previous[1],
                    "event_id": proposal["event_id"], "idempotent": True,
                    "effects": self.effects(stream_id, proposal["event_id"])}
        check(state["revision"] == expected_revision,
              "NARRATIVE_REVISION_CONFLICT")
        validate_proposal(proposal, prose=prose, state=state)
        # Strict only-prior causal references => no self-loops or forward edges,
        # thus acyclic within one stream.
        for dep in proposal["caused_by"]:
            check(self._prior(stream_id, dep) is not None,
                  f"NARRATIVE_CAUSE_NOT_COMMITTED:{dep}")
        last = self.db.execute(
            "SELECT ordinal FROM narrative_events "
            "WHERE stream_id=? AND scene_id=? ORDER BY ordinal DESC LIMIT 1",
            (stream_id, proposal["scene_id"]),
        ).fetchone()
        if last is not None:
            check(proposal["time"]["ordinal"] > last[0],
                  "NARRATIVE_SCENE_ORDER_INVALID")

        def graph_hook(db, before, after, event, revision):
            check(event["event_id"] == proposal["event_id"],
                  "NARRATIVE_ATOMIC_EVENT_MISMATCH")
            effects = world_effects(before, after)
            declared_people = {p["id"] for p in proposal["participants"]}
            declared_objects = {p["id"] for p in proposal["objects"]}
            # Every changed character and object must be linked in the graph;
            # this includes a carried object that moved with the character.
            for effect in effects:
                if effect["scope"] == "ENTITY":
                    ident = effect["id"]
                    ent = after["entities"].get(ident) or before["entities"].get(ident)
                    check(ident in (
                        declared_people if ent["kind"] == "CHARACTER"
                        else declared_objects
                    ), f"NARRATIVE_EFFECT_ENTITY_NOT_LINKED:{ident}")
                elif effect["scope"] == "REGION":
                    check(effect["id"] == proposal["location"],
                          "NARRATIVE_ENVIRONMENT_NOT_LINKED")
            db.execute(
                "INSERT INTO narrative_events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (stream_id, proposal["event_id"], revision,
                 proposal["scene_id"], proposal["time"]["ordinal"],
                 proposal["event_type"], proposal["epistemic"],
                 proposal["location"], canonical(proposal),
                 digest_obj(proposal), canonical(review)),
            )
            for item in proposal["participants"]:
                db.execute(
                    "INSERT INTO narrative_participants VALUES (?,?,?,?)",
                    (stream_id, proposal["event_id"], item["id"], item["role"])
                )
            for item in proposal["objects"]:
                db.execute(
                    "INSERT INTO narrative_objects VALUES (?,?,?,?)",
                    (stream_id, proposal["event_id"], item["id"], item["role"])
                )
            for dep in proposal["caused_by"]:
                db.execute(
                    "INSERT INTO narrative_dependencies VALUES (?,?,?)",
                    (stream_id, proposal["event_id"], dep),
                )
            for i, effect in enumerate(effects):
                db.execute(
                    "INSERT INTO narrative_effects VALUES (?,?,?,?,?,?,?,?)",
                    (stream_id, proposal["event_id"], i, effect["scope"],
                     effect["id"], canonical(effect["path"]),
                     canonical(effect["before"]), canonical(effect["after"])),
                )
            for step, (status, reason) in enumerate((
                ("PROPOSED", "Typed proposal received by trusted application"),
                ("VERIFIED", review["reason"]),
                ("COMMITTED", "Atomic world reducer + narrative graph commit"),
            )):
                db.execute(
                    "INSERT INTO narrative_lifecycle VALUES (?,?,?,?,?)",
                    (stream_id, proposal["event_id"], step, status, reason),
                )

        self.world.commit(
            stream_id, expected_revision=expected_revision,
            events=[proposal["world_event"]],
            approvals=approved_world_events,
            on_event_committed=graph_hook,
        )
        return {
            "status": "COMMITTED", "idempotent": False,
            "revision": expected_revision + 1,
            "event_id": proposal["event_id"],
            "effects": self.effects(stream_id, proposal["event_id"]),
        }

    def effects(self, stream_id, event_id) -> list[dict]:
        return [{
            "scope": scope, "id": ident,
            "path": json.loads(path),
            "before": json.loads(old), "after": json.loads(new),
        } for scope, ident, path, old, new in self.db.execute(
            "SELECT scope,entity_id,path_json,before_json,after_json "
            "FROM narrative_effects WHERE stream_id=? AND event_id=? "
            "ORDER BY ordinal", (stream_id, event_id),
        )]

    def get(self, stream_id, event_id):
        row = self._prior(stream_id, event_id)
        if row is None:
            return None
        item = json.loads(row[0])
        item["revision"] = row[1]
        item["status"] = "COMMITTED"
        item["effects"] = self.effects(stream_id, event_id)
        return item

    def history(self, stream_id, entity_id):
        """All events mentioning a character/object or changing its state."""
        ids = [
            item[0] for item in self.db.execute(
                "SELECT event_id FROM narrative_participants "
                "WHERE stream_id=? AND entity_id=? UNION "
                "SELECT event_id FROM narrative_objects "
                "WHERE stream_id=? AND entity_id=? UNION "
                "SELECT event_id FROM narrative_effects "
                "WHERE stream_id=? AND entity_id=? AND scope='ENTITY'",
                (stream_id, entity_id, stream_id, entity_id,
                 stream_id, entity_id),
            )
        ]
        return sorted((self.get(stream_id, ident) for ident in ids),
                      key=lambda p: p["revision"])

    def descendants(self, stream_id, event_id):
        check(self._prior(stream_id, event_id) is not None,
              "NARRATIVE_ROOT_UNKNOWN")
        # Standard recursive CTE; graph is committed-prior DAG, no cycles.
        rows = self.db.execute(
            """WITH RECURSIVE children(event_id) AS (
                 SELECT event_id FROM narrative_dependencies
                 WHERE stream_id=? AND caused_by=?
                 UNION
                 SELECT dep.event_id FROM narrative_dependencies dep
                 JOIN children c ON dep.caused_by=c.event_id
                 WHERE dep.stream_id=?
               )
               SELECT ne.event_id FROM children c
               JOIN narrative_events ne ON ne.stream_id=? AND ne.event_id=c.event_id
               ORDER BY ne.revision""",
            (stream_id, event_id, stream_id, stream_id),
        ).fetchall()
        return [row[0] for row in rows]

    def timeline(self, stream_id, scene_id):
        rows = self.db.execute(
            "SELECT event_id FROM narrative_events "
            "WHERE stream_id=? AND scene_id=? ORDER BY ordinal",
            (stream_id, scene_id),
        ).fetchall()
        return [self.get(stream_id, row[0]) for row in rows]

    def lifecycle(self, stream_id, event_id):
        return [{
            "status": status, "rationale": rationale,
        } for status, rationale in self.db.execute(
            "SELECT status,rationale FROM narrative_lifecycle "
            "WHERE stream_id=? AND event_id=? ORDER BY sequence",
            (stream_id, event_id),
        )]

    def verify(self, stream_id):
        """Replay underlying world and verify each graph effect against it."""
        check(self.world.verify_replay(stream_id), "NARRATIVE_WORLD_REPLAY_FAILED")
        world_ids = self.db.execute(
            "SELECT revision,event_id FROM world_events WHERE stream_id=? "
            "ORDER BY revision", (stream_id,),
        ).fetchall()
        narrative_ids = self.db.execute(
            "SELECT revision,event_id FROM narrative_events WHERE stream_id=? "
            "ORDER BY revision", (stream_id,),
        ).fetchall()
        check(world_ids == narrative_ids,
              "NARRATIVE_WORLD_EVENT_COVERAGE_MISMATCH")
        for event_id, revision, serialized, sha in self.db.execute(
            "SELECT event_id,revision,proposal_json,proposal_sha "
            "FROM narrative_events WHERE stream_id=? ORDER BY revision",
            (stream_id,),
        ):
            check(digest_obj(json.loads(serialized)) == sha,
                  "NARRATIVE_PROPOSAL_HASH_MISMATCH")
            before = self.world.snapshot(stream_id, revision - 1)
            after = self.world.snapshot(stream_id, revision)
            expected = world_effects(before, after)
            check(expected == self.effects(stream_id, event_id),
                  "NARRATIVE_EFFECT_REPLAY_MISMATCH")
            proposal = json.loads(serialized)
            check(proposal["event_id"] == event_id and
                  after["events"][-1] == proposal["world_event"],
                  "NARRATIVE_EVENT_REPLAY_MISMATCH")
            for dep in proposal["caused_by"]:
                row = self._prior(stream_id, dep)
                check(row is not None and row[1] < revision,
                      "NARRATIVE_CAUSAL_REPLAY_INVALID")
        return True
