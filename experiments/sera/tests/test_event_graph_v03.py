"""SERA EventGraph v0.3 offline acceptance/negative controls.

Mara prose is HAND-AUTHORED SYNTHETIC fixture, not the live 243-word scene.
The authority/review values are supplied only by this test harness.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.tests.test_world_state_v02 import (
    base, event, approved, ROUTES
)
from experiments.sera.event_graph_v03 import (
    EventGraphStore, WorldStateError, SCHEMA, digest_obj,
    validate_proposal, world_effects,
)

SCENE = (
    "On the platform, Vane examined his pocket watch. "
    "Vane told Mara that his pocket watch had stopped at 02:07. "
    "Mara examined her notebook, considering what Vane had claimed."
)
MOVE_SCENE = "Mara walked from the station to the archive with her notebook and coat."
WEATHER_SCENE = "The station sky became cloudy."
SOURCE_TYPE = "SYNTHETIC_GOLD_NOT_LIVE_MARA"


def proposal(id, typ, at, quote, *, scene="hook_empty_platform",
             prose=SCENE, location="station", ordinal=1,
             people=(), objects=(), causes=(), conditions=(),
             epistemic="OBSERVED_ACTION", time_exact=None, earliest=135,
             latest=200, **payload):
    start = prose.index(quote)
    return {
        "schema": SCHEMA,
        "event_id": id,
        "event_type": typ,
        "scene_id": scene,
        "location": location,
        "epistemic": epistemic,
        "participants": [{"id": ident, "role": role} for ident, role in people],
        "objects": [{"id": ident, "role": role} for ident, role in objects],
        "time": {"ordinal": ordinal, "earliest_minute": earliest,
                 "latest_minute": latest, "exact_minute": time_exact},
        "caused_by": list(causes),
        "preconditions": list(conditions),
        "evidence": {
            "prose_sha256": sha256(prose.encode("utf-8")).hexdigest(),
            "start": start, "end": start + len(quote), "quote": quote,
        },
        "world_event": event(id, {
            "TESTIMONY": "LEARN_FACT",
            "OBSERVATION": "INTERACT_ENTITY",
            "INTERACTION": "INTERACT_ENTITY",
            "MOVEMENT": "MOVE_CHARACTER",
            "WORLD_CHANGE": "SET_WEATHER",
            "TRANSFER": "TRANSFER_HOLDER",
            "STORY_BEAT": "ADVANCE_SCENE",
        }[typ], at, **payload),
    }


def review(proposal):
    return {
        "decision": "APPROVED", "authority": "APPLICATION",
        "event_hash": digest_obj(proposal),
        "prose_sha256": proposal["evidence"]["prose_sha256"],
        "reason": "Synthetic controlled verifier in offline tests",
    }


def commit(store, p, prose=SCENE):
    return store.commit(
        stream_id="mara", proposal=p, prose=prose,
        review=review(p),
        approved_world_events=approved(p["world_event"]),
        expected_revision=store.head("mara")["revision"],
    )


def look():
    return proposal(
        "evt_vane_observes", "OBSERVATION", 137,
        "Vane examined his pocket watch.",
        people=(("vane", "ACTOR"),),
        objects=(("vane_watch", "TOOL"),),
        interaction="LOOK_AT", entity_id="vane_watch", actor_id="vane",
        conditions=({"scope": "ENTITY", "id": "vane_watch",
                     "path": ["condition", "functional"], "equals": "STOPPED"},),
    )


def tell():
    return proposal(
        "evt_vane_claim", "TESTIMONY", 140,
        "Vane told Mara that his pocket watch had stopped at 02:07.",
        ordinal=2, causes=("evt_vane_observes",),
        people=(("vane", "SPEAKER"), ("mara", "LISTENER")),
        objects=(("vane_watch", "TOPIC"),),
        epistemic="REPORTED_CLAIM", character_id="mara",
        fact_id="claim:vane_watch_stopped_0207",
        conditions=({"scope": "ENTITY", "id": "mara",
                     "path": ["location"], "equals": "station"},),
    )


def record():
    return proposal(
        "evt_mara_notebook", "INTERACTION", 141,
        "Mara examined her notebook",
        ordinal=3, causes=("evt_vane_claim",),
        people=(("mara", "ACTOR"),),
        objects=(("mara_notebook", "TOOL"),),
        interaction="LOOK_AT", actor_id="mara", entity_id="mara_notebook",
    )


def move():
    return proposal(
        "evt_walk_to_archive", "MOVEMENT", 155,
        "Mara walked from the station to the archive with her notebook and coat.",
        scene="archive_log_check", prose=MOVE_SCENE, ordinal=1,
        people=(("mara", "ACTOR"),),
        objects=(("mara_notebook", "AFFECTED"),
                 ("mara_coat", "AFFECTED")),
        causes=("evt_mara_notebook",),
        to_location="archive", character_id="mara",
    )


def weather():
    return proposal(
        "evt_weather", "WORLD_CHANGE", 160,
        WEATHER_SCENE, prose=WEATHER_SCENE, ordinal=4,
        people=(), objects=(), location="station",
        region_id="station", old_weather="CLEAR",
        new_weather="CLOUDY", temperature_c=12, wind_kph=6,
        cloud_cover_pct=70, precip_mm_h=0, ground_wet=False,
        exception_rule_id=None,
    )


class EventGraphTests(unittest.TestCase):
    def fail(self, prefix, fn):
        with self.assertRaises(WorldStateError) as ctx:
            fn()
        self.assertTrue(ctx.exception.code.startswith(prefix),
                        f"{prefix} vs {ctx.exception.code}")

    def test_mara_narrative_claim_and_causes_without_false_truth(self):
        self.assertEqual(SOURCE_TYPE, "SYNTHETIC_GOLD_NOT_LIVE_MARA")
        with EventGraphStore() as g:
            g.create("mara", base(), travel_minutes=ROUTES)
            a, b, c = look(), tell(), record()
            ra = commit(g, a)
            rb = commit(g, b)
            rc = commit(g, c)
            self.assertEqual([ra["status"],rb["status"],rc["status"]],
                             ["COMMITTED"]*3)
            self.assertEqual(ra["effects"], [])
            self.assertEqual(rb["effects"][0]["scope"], "ENTITY")
            self.assertEqual(rb["effects"][0]["id"], "mara")
            self.assertEqual(rb["effects"][0]["path"], ["knowledge"])
            self.assertIn("claim:vane_watch_stopped_0207",
                          rb["effects"][0]["after"])
            self.assertEqual(g.head("mara")["entities"]["vane_watch"]
                             ["condition"]["functional"], "STOPPED")
            self.assertNotIn("train_41_physically_arrived",
                             g.head("mara")["entities"]["mara"]["knowledge"])
            self.assertEqual(g.descendants("mara", "evt_vane_observes"),
                             ["evt_vane_claim", "evt_mara_notebook"])
            self.assertEqual([v["event_id"] for v in
                              g.history("mara","vane_watch")],
                             ["evt_vane_observes", "evt_vane_claim"])
            self.assertEqual([x["status"] for x in
                              g.lifecycle("mara","evt_vane_claim")],
                             ["PROPOSED","VERIFIED","COMMITTED"])
            self.assertEqual(len(g.timeline("mara","hook_empty_platform")),3)
            self.assertTrue(g.verify("mara"))

    def test_move_includes_all_indirectly_carried_objects(self):
        with EventGraphStore() as g:
            g.create("mara", base(), travel_minutes=ROUTES)
            for p in (look(),tell(),record()):
                commit(g,p)
            result = commit(g,move(),MOVE_SCENE)
            self.assertEqual(result["status"],"COMMITTED")
            affected = {x["id"] for x in result["effects"]
                        if x["scope"]=="ENTITY"}
            self.assertEqual(affected,
                             {"mara","mara_coat","mara_notebook"})
            self.assertEqual(g.head("mara")["entities"]["mara_coat"]["location"],
                             "archive")
            self.assertEqual(g.head("mara")["entities"]["vane_watch"]["location"],
                             "station")
            self.assertEqual(g.descendants("mara","evt_vane_claim"),
                             ["evt_mara_notebook","evt_walk_to_archive"])
            self.assertTrue(g.verify("mara"))

    def test_missing_impacted_wearable_rolls_back_world_and_graph(self):
        with EventGraphStore() as g:
            g.create("mara", base(), travel_minutes=ROUTES)
            for p in (look(),tell(),record()):
                commit(g,p)
            bad=move()
            bad["objects"]=[{"id":"mara_notebook","role":"AFFECTED"}]
            before=g.head("mara")
            self.fail("NARRATIVE_EFFECT_ENTITY_NOT_LINKED",
                      lambda: commit(g,bad,MOVE_SCENE))
            self.assertEqual(g.head("mara"),before)
            self.assertIsNone(g.get("mara","evt_walk_to_archive"))
            self.assertEqual(g.world.entity_history("mara","mara_coat"),[])
            self.assertTrue(g.verify("mara"))

    def test_weather_graph_uses_derived_region_effects(self):
        with EventGraphStore() as g:
            g.create("mara", base())
            p=weather()
            committed=commit(g,p,WEATHER_SCENE)
            self.assertTrue(committed["effects"])
            self.assertEqual({x["scope"] for x in committed["effects"]},
                             {"REGION"})
            self.assertIn("station",{x["id"] for x in committed["effects"]})
            self.assertTrue(g.verify("mara"))

    def test_wrong_precondition_and_world_state_never_written(self):
        with EventGraphStore() as g:
            g.create("mara",base())
            p=look()
            p["preconditions"][0]["equals"]="WORKING"
            self.fail("NARRATIVE_PRECONDITION_FAILED",
                      lambda: commit(g,p))
            self.assertEqual(g.head("mara")["revision"],0)
            self.assertEqual(g.timeline("mara","hook_empty_platform"),[])

    def test_unauthorized_review_and_world_event_grant_fail_closed(self):
        with EventGraphStore() as g:
            g.create("mara",base())
            p=look()
            invalid=review(p)
            invalid["authority"]="JEV"
            self.fail("NARRATIVE_NOT_APPROVED",
                      lambda: g.commit(
                          stream_id="mara",proposal=p,prose=SCENE,
                          review=invalid,approved_world_events=approved(
                              p["world_event"]),expected_revision=0,
                      ))
            self.fail("EVENT_NOT_APPROVED",
                      lambda: g.commit(
                          stream_id="mara",proposal=p,prose=SCENE,
                          review=review(p),approved_world_events={},
                          expected_revision=0,
                      ))
            self.assertEqual(g.head("mara")["revision"],0)

    def test_reported_claim_cannot_mutate_physical_object(self):
        with EventGraphStore() as g:
            g.create("mara",base())
            p=proposal(
                "evt_false_change","INTERACTION",140,
                "Vane examined his pocket watch.",
                people=(("vane","ACTOR"),),
                objects=(("vane_watch","AFFECTED"),),
                epistemic="REPORTED_CLAIM",
                entity_id="vane_watch",
                field="color",old="SILVER",new="RED",
            )
            p["world_event"]["type"]="CHANGE_APPEARANCE"
            self.fail("REPORTED_CLAIM_CANNOT_BECOME_WORLD_FACT",
                      lambda: commit(g,p))
            self.assertEqual(g.head("mara")["entities"]
                             ["vane_watch"]["appearance"]["color"],"SILVER")

    def test_reported_claim_must_be_attributed(self):
        with EventGraphStore() as g:
            g.create("mara",base())
            p=tell()
            p["world_event"]["payload"]["fact_id"]="train_arrived"
            self.fail("REPORTED_CLAIM_MUST_REMAIN_ATTRIBUTED",
                      lambda: commit(g,p))

    def test_missing_cause_and_self_causation_are_rejected(self):
        with EventGraphStore() as g:
            g.create("mara",base())
            p=look()
            p["caused_by"]=["not_committed"]
            self.fail("NARRATIVE_CAUSE_NOT_COMMITTED",
                      lambda: commit(g,p))
            p["caused_by"]=["evt_vane_observes"]
            self.fail("NARRATIVE_SELF_CAUSATION",
                      lambda: commit(g,p))

    def test_source_quote_and_sha_cannot_be_forged(self):
        with EventGraphStore() as g:
            g.create("mara",base())
            p=look()
            p["evidence"]["quote"]="A different action occurred"
            self.fail("NARRATIVE_EVIDENCE_SPAN_INVALID",
                      lambda: commit(g,p))
            p=look()
            p["evidence"]["prose_sha256"]="0"*64
            self.fail("NARRATIVE_PROSE_HASH_MISMATCH",
                      lambda: commit(g,p))

    def test_bogus_model_supplied_after_state_is_schema_invalid(self):
        with EventGraphStore() as g:
            g.create("mara",base())
            p=look()
            p["after"]={"vane_watch":{"appearance":{"color":"RED"}}}
            self.fail("NARRATIVE_SCHEMA_INVALID",
                      lambda: commit(g,p))

    def test_duplicate_exact_idempotent_but_mutated_event_rejected(self):
        with EventGraphStore() as g:
            g.create("mara",base())
            p=look()
            first=commit(g,p)
            same=commit(g,p)
            self.assertFalse(first["idempotent"])
            self.assertTrue(same["idempotent"])
            self.assertEqual(g.head("mara")["revision"],1)
            changed=deepcopy(p)
            changed["event_type"]="DISCOVERY"
            self.fail("NARRATIVE_ID_CONFLICT",
                      lambda: commit(g,changed))
            self.assertTrue(g.verify("mara"))

    def test_scene_event_order_never_moves_backward(self):
        with EventGraphStore() as g:
            g.create("mara",base())
            commit(g,look())
            p=proposal(
                "evt_another", "OBSERVATION", 140,
                "Vane examined his pocket watch.",
                ordinal=1,
                people=(("vane","ACTOR"),),
                objects=(("vane_watch","TOOL"),),
                entity_id="vane_watch",actor_id="vane",interaction="OBSERVE",
            )
            self.fail("NARRATIVE_SCENE_ORDER_INVALID",
                      lambda: commit(g,p))

    def test_typed_people_and_objects_linked_to_world_event(self):
        with EventGraphStore() as g:
            g.create("mara",base())
            p=look()
            p["participants"]=[]
            self.fail("EVENT_ACTOR_NOT_LINKED",lambda: commit(g,p))
            p=look()
            p["objects"]=[]
            self.fail("EVENT_OBJECT_NOT_LINKED",lambda: commit(g,p))

    def test_character_cannot_be_used_as_physical_object(self):
        with EventGraphStore() as g:
            g.create("mara",base())
            p=look()
            p["objects"]=[{"id":"mara","role":"TOOL"}]
            self.fail("CHARACTER_NOT_PHYSICAL_OBJECT",
                      lambda: commit(g,p))

    def test_nested_precondition_unknown_field_fails_closed(self):
        with EventGraphStore() as g:
            g.create("mara",base())
            p=look()
            p["preconditions"][0]["path"]=["appearance","missing_color"]
            self.fail("EVENT_PRECONDITION_FIELD_UNKNOWN",
                      lambda: commit(g,p))

    def test_unsupported_narrative_status_and_time_bounds(self):
        with EventGraphStore() as g:
            g.create("mara",base())
            p=look()
            p["epistemic"]="DEFINITELY_TRUE_BY_MODEL"
            self.fail("NARRATIVE_EPISTEMIC_INVALID",lambda: commit(g,p))
            p=look()
            p["time"]["exact_minute"]=139
            self.fail("NARRATIVE_WORLD_TIME_MISMATCH",
                      lambda: commit(g,p))
            p=look()
            p["time"]["earliest_minute"]=145
            self.fail("NARRATIVE_EVENT_BEFORE_WINDOW",
                      lambda: commit(g,p))

    def test_implicit_time_kept_null_not_fabricated(self):
        with EventGraphStore() as g:
            g.create("mara",base())
            p=look()
            self.assertIsNone(p["time"]["exact_minute"])
            commit(g,p)
            old=g.get("mara",p["event_id"])
            self.assertIsNone(old["time"]["exact_minute"])
            self.assertEqual(old["world_event"]["at_minute"],137)
            # Internal world cursor 137 does NOT claim the prose says 02:17.
            self.assertTrue(g.verify("mara"))

    def test_sqlite_history_immutable_and_persists_across_reopen(self):
        with TemporaryDirectory() as tmp:
            name=Path(tmp)/"eventgraph.sqlite"
            with EventGraphStore(name) as g:
                g.create("mara",base())
                commit(g,look())
                with self.assertRaises(sqlite3.DatabaseError):
                    g.db.execute("DELETE FROM narrative_events")
                self.assertTrue(g.verify("mara"))
            with EventGraphStore(name) as g:
                self.assertEqual(g.get("mara","evt_vane_observes")["status"],
                                 "COMMITTED")
                self.assertTrue(g.verify("mara"))

    def test_effect_history_matches_replay_and_corrupted_row_is_blocked(self):
        with EventGraphStore() as g:
            g.create("mara",base())
            commit(g,look())
            commit(g,tell())
            self.assertTrue(g.verify("mara"))
            with self.assertRaises(sqlite3.DatabaseError):
                g.db.execute("UPDATE narrative_effects SET after_json='null'")
            self.assertTrue(g.verify("mara"))

    def test_object_history_and_narrative_event_history_both_available(self):
        with EventGraphStore() as g:
            g.create("mara",base())
            commit(g,look())
            commit(g,tell())
            # Non-mutating watch interaction is in object history and graph.
            watch=g.world.entity_history("mara","vane_watch")
            self.assertEqual(len(watch),1)
            self.assertEqual(watch[0]["before"],watch[0]["after"])
            self.assertEqual(len(g.history("mara","vane_watch")),2)

    def test_graph_atomicity_when_sqlite_insert_is_rejected(self):
        with EventGraphStore() as g:
            g.create("mara",base())
            p=look()
            # An existing narrative-only ID collides with another stream? No.
            # Instead force a DB constraint to fail inside graph_hook.
            g.db.execute("""
                CREATE TRIGGER force_graph_fail BEFORE INSERT
                ON narrative_events BEGIN
                  SELECT RAISE(ABORT,'FAIL_GRAPH_WRITE');
                END
            """)
            with self.assertRaises(sqlite3.DatabaseError):
                commit(g,p)
            self.assertEqual(g.head("mara")["revision"],0)
            self.assertIsNone(g.get("mara","evt_vane_observes"))
            self.assertTrue(g.world.verify_replay("mara"))


if __name__ == "__main__":
    unittest.main()
