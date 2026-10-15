"""SERA v0.2: deterministic object/character/weather/SQLite history tests.

All storage is isolated SQLite in memory or tempfile. No paid model calls.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from experiments.sera.world_state_v02 import (
    WorldStateError, apply_event, entity_template, environment_template,
    fingerprint, initial_state, loadout, validate,
)
from experiments.sera.world_store_v02 import WorldStore

ROUTES = {
    "station->archive": 10,
    "archive->station": 10,
}
RULES = ("authorized_magic_size", "authorized_magic_storm")


def base():
    entities = {
        "mara": entity_template(
            "mara", "CHARACTER", "station", size="M",
            color="BROWN", traits={
                "hair_color": "BROWN", "eye_color": "GREEN",
                "goal": "Investigate the missing train",
            }, knowledge=["manifest_records_0210"], last_action_minute=135,
        ),
        "vane": entity_template(
            "vane", "CHARACTER", "station", size="L",
            traits={"goal": "Give a bounded witness statement"},
            knowledge=["watch_stopped_0207"], last_action_minute=135,
        ),
        "mara_coat": entity_template(
            "mara_coat", "WEARABLE", "station",
            owner="mara", worn_by="mara", color="BLUE",
            material="WOOL", width_cm=45, height_cm=70, depth_cm=4,
            mass_kg=1.0, size="M", age="OLD", integrity_pct=82,
            functional="WORKING",
        ),
        "vane_watch": entity_template(
            "vane_watch", "OBJECT", "station",
            owner="vane", holder="vane", color="SILVER",
            width_cm=4, height_cm=4, depth_cm=1.0,
            mass_kg=0.1, functional="STOPPED",
            age="OLD", integrity_pct=75,
        ),
        "mara_notebook": entity_template(
            "mara_notebook", "OBJECT", "station",
            owner="mara", holder="mara",
            color="BROWN", age="USED",
        ),
        "bench": entity_template(
            "bench", "OBJECT", "station",
            color="BROWN", material="WOOD", width_cm=150,
            height_cm=50, depth_cm=40, mass_kg=35,
        ),
        "pencil": entity_template(
            "pencil", "OBJECT", "station",
            color="YELLOW", material="WOOD", width_cm=0.7,
            height_cm=18, depth_cm=0.7, mass_kg=0.01,
        ),
    }
    return initial_state(
        entities=entities, minute=135,
        regions={
            "station": environment_template(
                "CLEAR", temperature_c=12, wind_kph=6,
                cloud_cover_pct=5, precip_mm_h=0, ground_wet=False,
                last_change_minute=135,
            ),
            "archive": environment_template(
                "CLOUDY", temperature_c=11, wind_kph=4,
                cloud_cover_pct=60, precip_mm_h=0, ground_wet=False,
                last_change_minute=135,
            ),
        },
    )


def event(event_id, type, minute, **payload):
    return {
        "event_id": event_id, "type": type, "at_minute": minute,
        "reason": "Verified scene action with cause",
        "evidence_ref": f"scene-1#span-{event_id}",
        "payload": payload,
    }


def approved(ev):
    return {ev["event_id"]: fingerprint(ev)}


def single(state, ev, rules=()):
    return apply_event(state, ev, approvals=approved(ev),
                       travel_minutes=ROUTES, world_rules=frozenset(rules))


class WorldStateV02Tests(unittest.TestCase):
    def assert_error(self, expected, action):
        with self.assertRaises(WorldStateError) as ctx:
            action()
        self.assertTrue(ctx.exception.code.startswith(expected),
                        f"expected {expected}, got {ctx.exception.code}")

    def test_full_frozen_properties_and_derived_outfit(self):
        s = base()
        self.assertEqual(s["entities"]["vane_watch"]["appearance"]["color"], "SILVER")
        self.assertEqual(s["entities"]["vane_watch"]["dimensions"]["width_cm"], 4)
        self.assertEqual(s["entities"]["vane_watch"]["condition"]["functional"], "STOPPED")
        outfit = loadout(s, "mara")
        self.assertEqual(outfit["worn"], ["mara_coat"])
        self.assertIn("mara_notebook", outfit["held"])
        self.assertIn("mara_coat", outfit["owned"])
        self.assertIn("manifest_records_0210", outfit["knowledge"])

    def test_ten_scenes_do_not_change_object_clothing_or_weather(self):
        with WorldStore() as store:
            store.create("mara_world", base(), travel_minutes=ROUTES)
            original = deepcopy(store.head("mara_world"))
            for i in range(10):
                e = event(f"scene-{i+1}", "ADVANCE_SCENE",
                          140 + i*5, scene_key=f"scene-{i+1}")
                store.commit("mara_world", expected_revision=i,
                             events=[e], approvals=approved(e))
            final = store.head("mara_world")
            self.assertEqual(final["scene_index"], 10)
            self.assertEqual(original["entities"], final["entities"])
            for region in original["regions"]:
                self.assertEqual(original["regions"][region],
                                 final["regions"][region])
            self.assertEqual(store.entity_at("mara_world", "vane_watch",
                                             revision=0),
                             store.entity_at("mara_world", "vane_watch",
                                             revision=10))
            self.assertEqual(loadout(final, "mara")["worn"], ["mara_coat"])
            self.assertTrue(store.verify_replay("mara_world"))

    def test_color_requires_approved_event_and_history_reconstructs(self):
        with WorldStore() as store:
            store.create("story", base())
            change = event(
                "paint-watch", "CHANGE_APPEARANCE", 145,
                entity_id="vane_watch", field="color",
                old="SILVER", new="BLUE",
            )
            self.assert_error(
                "EVENT_NOT_APPROVED",
                lambda: store.commit("story", expected_revision=0,
                                     events=[change], approvals={}),
            )
            self.assertEqual(store.head("story")["revision"], 0)
            after = store.commit(
                "story", expected_revision=0,
                events=[change], approvals=approved(change),
            )
            self.assertEqual(after["entities"]["vane_watch"]["appearance"]["color"],
                             "BLUE")
            self.assertEqual(store.entity_at("story", "vane_watch",
                                             revision=0)["appearance"]["color"], "SILVER")
            self.assertEqual(store.entity_at("story", "vane_watch",
                                             revision=1)["appearance"]["color"], "BLUE")
            hist = store.entity_history("story", "vane_watch")
            self.assertEqual(len(hist), 1)
            self.assertEqual(hist[0]["event_id"], "paint-watch")
            self.assertEqual(hist[0]["before"]["appearance"]["color"], "SILVER")
            self.assertEqual(hist[0]["after"]["appearance"]["color"], "BLUE")
            self.assertEqual(hist[0]["after"]["dimensions"]["width_cm"], 4)
            self.assertTrue(store.verify_replay("story"))

    def test_unknown_properties_stay_unknown(self):
        s = base()
        self.assertIsNone(s["entities"]["mara_notebook"]["dimensions"]["width_cm"])
        self.assertEqual(s["entities"]["mara_notebook"]["condition"]["functional"], "UNKNOWN")
        later = single(s, event("s1", "ADVANCE_SCENE", 145, scene_key="s1"))
        self.assertIsNone(later["entities"]["mara_notebook"]["dimensions"]["width_cm"])

    def test_invalid_color_and_unauthorized_mutation(self):
        s = base()
        e = event("paint", "CHANGE_APPEARANCE", 145, entity_id="vane_watch",
                  field="color", old="SILVER", new="ULTRAVIOLET")
        self.assert_error("APPEARANCE_INVALID", lambda: single(s, e))
        good = event("paint", "CHANGE_APPEARANCE", 145, entity_id="vane_watch",
                     field="color", old="SILVER", new="BLUE")
        self.assert_error("EVENT_NOT_APPROVED",
                          lambda: apply_event(s, good, approvals={}))
        wrong = event("paint", "CHANGE_APPEARANCE", 145, entity_id="vane_watch",
                      field="color", old="RED", new="BLUE")
        self.assert_error("APPEARANCE_CAS_MISMATCH", lambda: single(s, wrong))
        self.assertEqual(s["entities"]["vane_watch"]["appearance"]["color"],
                         "SILVER")

    def test_implicit_size_change_requires_world_rule(self):
        s = base()
        e = event("sudden-growth", "CHANGE_DIMENSION", 145,
                  entity_id="vane_watch", field="width_cm",
                  old=4, new=400, world_rule_id="authorized_magic_size")
        self.assert_error("DIMENSION_CHANGE_WORLD_RULE_REQUIRED",
                          lambda: single(s, e))
        change = single(s, e, rules=("authorized_magic_size",))
        self.assertEqual(change["entities"]["vane_watch"]["dimensions"]["width_cm"], 400)
        self.assertEqual(s["entities"]["vane_watch"]["dimensions"]["width_cm"], 4)

    def test_impossible_clothing_size_and_ownership(self):
        s = base()
        s["entities"]["mara_coat"]["size"] = "XL"
        self.assert_error("CLOTHING_SIZE_MISMATCH", lambda: validate(s))
        bad = event("transfer", "TRANSFER_HOLDER", 140,
                    entity_id="vane_watch", from_id="mara", to_id="vane")
        self.assert_error("TRANSFER_SOURCE_INVALID",
                          lambda: single(base(), bad))

    def test_clothing_wear_remove_and_character_movement(self):
        s = base()
        removed = event("remove-coat", "REMOVE_WEAR", 136,
                        entity_id="mara_coat", character_id="mara")
        s = single(s, removed)
        self.assertEqual(loadout(s, "mara")["worn"], [])
        self.assertEqual(s["entities"]["mara_coat"]["holder"], "mara")
        wear = event("wear-coat", "WEAR", 137,
                     entity_id="mara_coat", character_id="mara")
        s = single(s, wear)
        move = event("walk-to-archive", "MOVE_CHARACTER", 150,
                     character_id="mara", to_location="archive")
        s = single(s, move)
        self.assertEqual(s["entities"]["mara_coat"]["location"], "archive")
        self.assertEqual(s["entities"]["mara_notebook"]["location"], "archive")
        self.assertEqual(s["entities"]["vane_watch"]["location"], "station")
        self.assertEqual(loadout(s, "mara")["worn"], ["mara_coat"])
        self.assertEqual(s["entities"]["mara_coat"]["appearance"]["color"], "BLUE")

    def test_teleport_rejected_and_state_unchanged(self):
        s = base()
        e = event("teleport", "MOVE_CHARACTER", 137,
                  character_id="mara", to_location="archive")
        self.assert_error("MOVE_TRAVEL_TOO_FAST", lambda: single(s, e))
        self.assertEqual(s["entities"]["mara"]["location"], "station")

    def test_weather_cannot_jump_without_elapsed_time(self):
        s = base()
        p = {
            "region_id": "station", "old_weather": "CLEAR",
            "new_weather": "RAIN", "temperature_c": 11,
            "wind_kph": 7, "cloud_cover_pct": 90,
            "precip_mm_h": 3, "ground_wet": True,
            "exception_rule_id": None,
        }
        early = event("rain-immediately", "SET_WEATHER", 138, **p)
        self.assert_error("WEATHER_CHANGE_TOO_ABRUPT",
                          lambda: single(s, early))
        legit = event("rain-after-time", "SET_WEATHER", 155, **p)
        after = single(s, legit)
        self.assertEqual(after["regions"]["station"]["weather"], "RAIN")
        self.assertEqual(s["regions"]["station"]["weather"], "CLEAR")

    def test_weather_temperature_jump_and_invalid_ground(self):
        s = base()
        p = dict(region_id="station", old_weather="CLEAR",
                 new_weather="STORM", temperature_c=-20,
                 wind_kph=70, cloud_cover_pct=100,
                 precip_mm_h=50, ground_wet=True, exception_rule_id=None)
        e = event("storm", "SET_WEATHER", 160, **p)
        self.assert_error("WEATHER_TEMPERATURE_JUMP", lambda: single(s, e))
        p["temperature_c"] = 11
        p["ground_wet"] = False
        storm = event("storm", "SET_WEATHER", 160, **p)
        self.assert_error("RAIN_REQUIRES_WET_GROUND", lambda: single(s, storm))
        p["exception_rule_id"] = "authorized_magic_storm"
        storm = event("magic-storm", "SET_WEATHER", 140, **p)
        self.assert_error("WEATHER_EXCEPTION_NOT_AUTHORIZED",
                          lambda: single(s, storm))

    def test_weather_history_old_new(self):
        with WorldStore() as store:
            store.create("world", base())
            e = event("clouds", "SET_WEATHER", 155,
                      region_id="station", old_weather="CLEAR",
                      new_weather="CLOUDY", temperature_c=12,
                      wind_kph=6, cloud_cover_pct=70,
                      precip_mm_h=0, ground_wet=False,
                      exception_rule_id=None)
            store.commit("world", expected_revision=0,
                         events=[e], approvals=approved(e))
            hist = store.environment_history("world", "station")
            self.assertEqual(hist[0]["before"]["weather"], "CLEAR")
            self.assertEqual(hist[0]["after"]["weather"], "CLOUDY")
            self.assertTrue(store.verify_replay("world"))

    def test_destroyed_object_never_deleted(self):
        with WorldStore() as store:
            store.create("world", base())
            e = event("break-bench", "RETIRE_ENTITY", 150, entity_id="bench")
            store.commit("world", expected_revision=0,
                         events=[e], approvals=approved(e))
            self.assertIn("bench", store.head("world")["entities"])
            self.assertEqual(
                store.entity_at("world", "bench", revision=1)["lifecycle"],
                "DESTROYED",
            )
            self.assertEqual(
                store.entity_at("world", "bench", revision=0)["lifecycle"],
                "ACTIVE",
            )
            self.assertEqual(len(store.entity_history("world", "bench")), 1)

    def test_ancestors_and_identity_preserved_on_new_object(self):
        with WorldStore() as store:
            store.create("world", base())
            piece = entity_template(
                "piece1", "OBJECT", "station", parent_id="bench",
                color="BROWN", material="WOOD", width_cm=30,
            )
            e = event("create-piece", "INTRODUCE_ENTITY", 145,
                      entity_id="piece1", entity=piece, parent_id="bench")
            store.commit("world", expected_revision=0,
                         events=[e], approvals=approved(e))
            self.assertEqual(store.entity_at("world", "piece1")["parent_id"], "bench")
            self.assertIsNone(store.entity_at("world", "piece1", revision=0))
            self.assertEqual(store.entity_history("world", "piece1")[0]["before"], None)

    def test_character_knowledge_and_traits_need_explicit_events(self):
        s = base()
        learn = event("learn", "LEARN_FACT", 145,
                      character_id="mara", fact_id="watch_stopped_0207")
        s = single(s, learn)
        self.assertIn("watch_stopped_0207", loadout(s, "mara")["knowledge"])
        e = event("goal", "UPDATE_CHARACTER_TRAIT", 146,
                  character_id="mara", trait="goal",
                  old="Investigate the missing train",
                  new="Report the bounded evidence")
        s = single(s, e)
        self.assertEqual(loadout(s, "mara")["traits"]["goal"],
                         "Report the bounded evidence")

    def test_an_interaction_generates_history_without_state_changes(self):
        with WorldStore() as store:
            store.create("world", base())
            e = event("look-watch", "INTERACT_ENTITY", 140,
                      entity_id="vane_watch", actor_id="vane",
                      interaction="LOOK_AT")
            store.commit("world", expected_revision=0,
                         events=[e], approvals=approved(e))
            hist = store.entity_history("world", "vane_watch")
            self.assertEqual(len(hist), 1)
            self.assertEqual(hist[0]["before"], hist[0]["after"])
            self.assertTrue(store.verify_replay("world"))

    def test_store_is_idempotent_and_optimistic_revision_locked(self):
        with WorldStore() as store:
            store.create("world", base())
            e = event("scene1", "ADVANCE_SCENE", 140, scene_key="scene1")
            first = store.commit("world", expected_revision=0,
                                 events=[e], approvals=approved(e))
            repeat = store.commit("world", expected_revision=0,
                                  events=[e], approvals=approved(e))
            self.assertEqual(first, repeat)
            bad = event("scene2", "ADVANCE_SCENE", 145, scene_key="scene2")
            self.assert_error(
                "OPTIMISTIC_REVISION_CONFLICT",
                lambda: store.commit("world", expected_revision=0,
                                     events=[bad], approvals=approved(bad)),
            )
            different = deepcopy(e)
            different["reason"] = "altered reason"
            self.assert_error(
                "EVENT_ID_CONFLICT",
                lambda: store.commit("world", expected_revision=1,
                                     events=[different],
                                     approvals=approved(different)),
            )

    def test_transaction_rolls_back_entire_bad_batch(self):
        with WorldStore() as store:
            store.create("world", base())
            e1 = event("a", "ADVANCE_SCENE", 140, scene_key="scene1")
            e2 = event("b", "CHANGE_APPEARANCE", 141, entity_id="vane_watch",
                       field="color", old="RED", new="GREEN")
            self.assert_error(
                "APPEARANCE_CAS_MISMATCH",
                lambda: store.commit(
                    "world", expected_revision=0, events=[e1, e2],
                    approvals={**approved(e1), **approved(e2)},
                ),
            )
            self.assertEqual(store.head("world")["revision"], 0)
            self.assertEqual(store.entity_history("world", "vane_watch"), [])
            self.assertTrue(store.verify_replay("world"))

    def test_sqlite_history_triggers_are_append_only(self):
        with WorldStore() as store:
            store.create("world", base())
            e = event("scene1", "ADVANCE_SCENE", 140, scene_key="scene1")
            store.commit("world", expected_revision=0,
                         events=[e], approvals=approved(e))
            with self.assertRaises(sqlite3.DatabaseError):
                store.db.execute(
                    "DELETE FROM world_events WHERE stream_id=?",
                    ("world",),
                )
            with self.assertRaises(sqlite3.DatabaseError):
                store.db.execute(
                    "UPDATE world_snapshots SET state_sha='tampered'",
                )
            self.assertTrue(store.verify_replay("world"))

    def test_sqlite_file_persists_across_reopen(self):
        with TemporaryDirectory() as d:
            path = Path(d) / "sera-world.db"
            with WorldStore(path) as store:
                store.create("world", base(), travel_minutes=ROUTES)
                e = event("scene1", "ADVANCE_SCENE", 140, scene_key="scene1")
                store.commit("world", expected_revision=0,
                             events=[e], approvals=approved(e))
            with WorldStore(path) as reopened:
                self.assertEqual(reopened.head("world")["revision"], 1)
                self.assertTrue(reopened.verify_replay("world"))
                self.assertEqual(
                    reopened.entity_at("world", "vane_watch",
                                       story_minute=135)["appearance"]["color"],
                    "SILVER",
                )

    def test_event_schema_invalid_empty_and_extra_fields(self):
        s = base()
        extra = event("strange", "ADVANCE_SCENE", 140,
                      scene_key="scene1", unknown_field="hello")
        self.assert_error("EVENT_PAYLOAD_INVALID", lambda: single(s, extra))
        bad = event("empty", "TRANSFER_HOLDER", 140)
        self.assert_error("EVENT_PAYLOAD_INVALID", lambda: single(s, bad))

    def test_snapshot_client_mutation_cannot_change_store(self):
        with WorldStore() as store:
            store.create("world", base())
            s = store.head("world")
            s["entities"]["mara_coat"]["appearance"]["color"] = "RED"
            self.assertEqual(store.head("world")["entities"]
                             ["mara_coat"]["appearance"]["color"], "BLUE")
            self.assertTrue(store.verify_replay("world"))


if __name__ == "__main__":
    unittest.main()
