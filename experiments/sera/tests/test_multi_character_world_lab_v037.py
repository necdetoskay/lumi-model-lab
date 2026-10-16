"""SERA v0.37 multi-character real SQLite regression, no provider calls."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from experiments.sera.multi_character_world_lab_v037 import (
    SCHEMA, ScenarioLab, prepare,
)
from experiments.sera.world_state_v02 import (
    WorldStateError, fingerprint, loadout,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "multi_character_story_v037.json"


def seed():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def event(eid, typ, minute, payload):
    return {
        "event_id": eid, "type": typ, "at_minute": minute,
        "reason": "fixture-only source-backed scene regression",
        "evidence_ref": "synthetic-scene:" + eid,
        "payload": payload,
    }


def grant(events):
    # A deliberately TEST-ONLY fingerprint supplied from outside the model.
    return {e["event_id"]: fingerprint(e) for e in events}


class MultiCharacterScenarioV037Tests(unittest.TestCase):
    def setUp(self):
        self.lab = ScenarioLab()
        self.fixture = seed()
        self.lab.seed(self.fixture)

    def tearDown(self):
        self.lab.close()

    def test_three_characters_share_physical_world_but_not_private_knowledge(self):
        world = self.lab.head(self.fixture["world_id"])
        self.assertEqual(world["revision"], 0)
        self.assertEqual({k for k,v in world["entities"].items()
                          if v["kind"] == "CHARACTER"},
                         {"mara", "elin", "rho"})
        ctx_mara = self.lab.begin_story(
            run_id="mara-s1", world_id=self.fixture["world_id"],
            character_id="mara")
        ctx_elin = self.lab.begin_story(
            run_id="elin-s1", world_id=self.fixture["world_id"],
            character_id="elin")
        self.assertEqual(ctx_mara["location"], "workshop")
        self.assertIn("clockwork-principle", ctx_mara["loadout"]["knowledge"])
        self.assertNotIn("secret-elins-note", json.dumps(ctx_mara))
        self.assertNotIn("observant", json.dumps(ctx_mara))
        self.assertNotIn("robot-sensor-calibration", json.dumps(ctx_mara))
        self.assertIn("secret-elins-note", ctx_elin["loadout"]["knowledge"])
        self.assertEqual(ctx_mara["source"], "SYNTHETIC_SQLITE_WORLD")
        self.assertFalse(ctx_mara["canonical_commit_authorized"])
        self.assertEqual(ctx_mara["production_db_writes"], 0)

    def test_custody_and_location_follow_events_across_distinct_story_runs(self):
        self.lab.begin_story(run_id="mara-s1",
                             world_id=self.fixture["world_id"],
                             character_id="mara")
        self.lab.begin_story(run_id="elin-s1",
                             world_id=self.fixture["world_id"],
                             character_id="elin")
        handoff = event("scene1-pencil", "TRANSFER_HOLDER", 1, {
            "entity_id": "pencil", "from_id": None, "to_id": "elin"})
        commit1 = self.lab.commit_story_fixture(
            run_id="mara-s1", expected_revision=0,
            events=[handoff], fixture_approvals=grant([handoff]))
        self.assertEqual(commit1["revision"], 1)
        moving = event("scene2-elin-exit", "MOVE_CHARACTER", 3, {
            "character_id": "elin", "to_location": "hallway"})
        commit2 = self.lab.commit_story_fixture(
            run_id="elin-s1", expected_revision=1,
            events=[moving], fixture_approvals=grant([moving]))
        self.assertEqual(commit2["revision"], 2)
        state = self.lab.head(self.fixture["world_id"])
        self.assertEqual(state["entities"]["elin"]["location"], "hallway")
        self.assertEqual(state["entities"]["pencil"]["location"], "hallway")
        self.assertEqual(state["entities"]["pencil"]["holder"], "elin")
        self.assertEqual(state["entities"]["mara"]["location"], "workshop")
        self.assertEqual(loadout(state,"mara")["held"], ["pocket-watch"])
        self.assertEqual(loadout(state,"elin")["held"], ["pencil"])
        self.assertEqual(self.lab.context("elin-s1")["revision"], 2)
        self.assertNotIn("elin", [x["id"] for x in
                                 self.lab.context("mara-s1")["visible_entities"]])
        self.assertFalse(commit2["canonical_commit_authorized"])
        self.assertIsNone(commit2["g2_commit_request"])

    def test_atomic_failed_batch_keeps_every_character_and_event_intact(self):
        self.lab.begin_story(run_id="mara-s1",
                             world_id=self.fixture["world_id"],
                             character_id="mara")
        before = self.lab.head(self.fixture["world_id"])
        transfer = event("valid-first", "TRANSFER_HOLDER", 1, {
            "entity_id": "pencil", "from_id": None, "to_id": "elin"})
        invalid = event("invalid-second", "MOVE_CHARACTER", 2, {
            "character_id": "elin", "to_location": "garden"})
        with self.assertRaisesRegex(WorldStateError, "MOVE_UNKNOWN_ROUTE"):
            self.lab.commit_story_fixture(
                run_id="mara-s1", expected_revision=0,
                events=[transfer, invalid],
                fixture_approvals=grant([transfer, invalid]))
        self.assertEqual(before, self.lab.head(self.fixture["world_id"]))
        self.assertEqual(self.lab.db.execute(
            "SELECT count(*) FROM lab_run_events").fetchone()[0], 0)
        self.assertEqual(self.lab.db.execute(
            "SELECT count(*) FROM world_events").fetchone()[0], 0)

    def test_revision_conflicts_and_cross_run_replay_are_rejected(self):
        for actor in ("mara", "elin"):
            self.lab.begin_story(run_id=actor + "-run",
                                 world_id=self.fixture["world_id"],
                                 character_id=actor)
        change = event("transfer", "TRANSFER_HOLDER", 1, {
            "entity_id": "pencil", "from_id": None, "to_id": "elin"})
        self.lab.commit_story_fixture(run_id="mara-run",expected_revision=0,
            events=[change], fixture_approvals=grant([change]))
        again = self.lab.commit_story_fixture(run_id="mara-run",
            expected_revision=0, events=[change],
            fixture_approvals=grant([change]))
        self.assertEqual(again["revision"], 1)
        with self.assertRaisesRegex(WorldStateError,
                                    "V037_EVENT_OWNED_BY_ANOTHER_RUN"):
            self.lab.commit_story_fixture(run_id="elin-run",
                expected_revision=1, events=[change],
                fixture_approvals=grant([change]))
        different = event("transfer-2", "INTERACT_ENTITY", 2, {
            "entity_id": "pocket-watch", "actor_id": "mara",
            "interaction": "OBSERVE"})
        with self.assertRaisesRegex(WorldStateError,
                                    "OPTIMISTIC_REVISION_CONFLICT"):
            self.lab.commit_story_fixture(run_id="mara-run",
                expected_revision=0, events=[different],
                fixture_approvals=grant([different]))
        self.assertEqual(self.lab.head(self.fixture["world_id"])["revision"], 1)

    def test_model_self_approval_never_enters_world(self):
        self.lab.begin_story(run_id="mara-run",
                             world_id=self.fixture["world_id"],
                             character_id="mara")
        move = event("make-believe-move", "MOVE_CHARACTER", 3, {
            "character_id":"mara","to_location":"hallway"})
        with self.assertRaisesRegex(WorldStateError,
                                    "V037_FIXTURE_GRANT_REQUIRED"):
            self.lab.commit_story_fixture(run_id="mara-run",
                expected_revision=0, events=[move], fixture_approvals={})
        self.assertEqual(self.lab.head(self.fixture["world_id"])["revision"],0)

    def test_another_world_can_reuse_character_id_without_state_bleed(self):
        second = seed()
        second["world_id"] = "lab-world-b"
        second["scenario_id"] = "alternate-mara-branch"
        second["universe_id"] = "synthetic-universe-b"
        second["characters"][0]["location_id"] = "garden"
        second["objects"][0]["location_id"] = "garden"
        self.lab.seed(second)
        self.lab.begin_story(run_id="mara-world-b",world_id="lab-world-b",
                             character_id="mara")
        self.lab.begin_story(run_id="mara-world-a",
                             world_id=self.fixture["world_id"],
                             character_id="mara")
        self.assertEqual(self.lab.context("mara-world-b")["location"],"garden")
        self.assertEqual(self.lab.context("mara-world-a")["location"],"workshop")
        self.assertNotEqual(self.lab.context("mara-world-a")["state_sha256"],
                            self.lab.context("mara-world-b")["state_sha256"])
        with self.assertRaisesRegex(WorldStateError,
                                    "V037_CHARACTER_NOT_IN_WORLD"):
            self.lab.begin_story(run_id="unknown",world_id="lab-world-b",
                                 character_id="different-character")

    def test_invalid_object_or_bad_route_cannot_seed_new_world(self):
        bad = seed()
        bad["world_id"] = "bad-world"
        bad["objects"][0]["holder_id"] = "rho"
        with self.assertRaisesRegex(WorldStateError, "HOLDER_LOCATION_MISMATCH"):
            self.lab.seed(bad)
        self.assertIsNone(self.lab.db.execute(
            "SELECT 1 FROM world_streams WHERE stream_id='bad-world'"
        ).fetchone())
        bad = seed()
        bad["world_id"] = "bad-routes"
        bad["routes"].append(deepcopy(bad["routes"][0]))
        with self.assertRaisesRegex(WorldStateError, "V037_DUPLICATE_ROUTE"):
            self.lab.seed(bad)

    def test_writer_sees_only_character_view_while_validator_sees_entire_world(self):
        self.lab.begin_story(run_id="mara-scene",world_id=self.fixture["world_id"],
                             character_id="mara")
        inputs = self.lab.scene_inputs("mara-scene", expected_revision=0)
        self.assertIn("secret-elins-note",
                      inputs["validator_world"]["entities"]["elin"]["knowledge"])
        self.assertNotIn("secret-elins-note",
                         json.dumps(inputs["writer_context"]))
        self.assertTrue(inputs["validator_only_private_state"])
        self.assertFalse(inputs["canonical_commit_authorized"])
        with self.assertRaisesRegex(WorldStateError,
                                    "V037_SCENE_ENTRY_REVISION_CONFLICT"):
            self.lab.scene_inputs("mara-scene", expected_revision=1)

    def test_metadata_insert_failure_rolls_back_initial_stream_and_snapshot(self):
        self.lab.db.executescript("""
            CREATE TRIGGER sabotage_seed
            BEFORE INSERT ON lab_characters
            WHEN NEW.world_id='rejected-seed'
            BEGIN SELECT RAISE(ABORT,'INJECTED_LAB_SEED_FAILURE'); END;
        """)
        broken = seed()
        broken["world_id"] = "rejected-seed"
        with self.assertRaisesRegex(sqlite3.DatabaseError,
                                    "INJECTED_LAB_SEED_FAILURE"):
            self.lab.seed(broken)
        for table in ("world_streams","world_snapshots","lab_worlds",
                      "lab_characters"):
            self.assertEqual(self.lab.db.execute(
                "SELECT count(*) FROM " + table + " WHERE " +
                ("stream_id" if table.startswith("world_") else "world_id") +
                "='rejected-seed'").fetchone()[0], 0)

    def test_origin_and_saga_identifiers_reserved_but_stages_are_disabled(self):
        self.assertEqual(self.lab.db.execute(
            "SELECT origin_fixture_ref,saga_fixture_ref FROM lab_characters "
            "WHERE world_id=? AND character_id='mara'",
            (self.fixture["world_id"],)).fetchone(),
            ("origin:mara-proposed", "saga:mara-proposed"))
        for stage in ("ORIGIN","SAGA"):
            with self.assertRaisesRegex(WorldStateError,
                                        "V037_FUTURE_STAGE_NOT_ACTIVE"):
                self.lab.reserved_stage(stage)
        self.assertEqual(self.lab.db.execute(
            "SELECT count(*) FROM lab_runs").fetchone()[0],0)

    def test_sqlite_file_can_reopen_and_reconstruct_a_story_run(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world-fixtures.sqlite"
            with ScenarioLab(path) as first:
                fixture = seed()
                fixture["world_id"] = "persisted-world"
                first.seed(fixture)
                first.begin_story(run_id="persisted-story",
                                  world_id="persisted-world",
                                  character_id="mara")
                change = event("persisted-observation","INTERACT_ENTITY", 1, {
                    "entity_id":"pocket-watch","actor_id":"mara",
                    "interaction":"OBSERVE"})
                first.commit_story_fixture(run_id="persisted-story",
                    expected_revision=0,events=[change],
                    fixture_approvals=grant([change]))
            with ScenarioLab(path) as second:
                self.assertEqual(second.head("persisted-world")["revision"],1)
                self.assertEqual(second.context("persisted-story")["revision"],1)
                self.assertEqual(second.store.snapshot("persisted-world",0)
                                 ["revision"],0)
                self.assertEqual(len(second.store.entity_history(
                    "persisted-world","pocket-watch")),1)

    def test_finishing_story_does_not_enable_other_generation_modes(self):
        self.lab.begin_story(run_id="finishable",
                             world_id=self.fixture["world_id"],
                             character_id="rho")
        ended = self.lab.finish_story("finishable")
        self.assertEqual(ended["run_status"],"COMPLETE")
        ev = event("no-more","ADVANCE_SCENE",1,{"scene_key":"S1"})
        with self.assertRaisesRegex(WorldStateError,"V037_STORY_RUN_NOT_OPEN"):
            self.lab.commit_story_fixture(run_id="finishable",
                expected_revision=0,events=[ev],
                fixture_approvals=grant([ev]))
        self.assertEqual(self.lab.head(self.fixture["world_id"])["revision"],0)


if __name__ == "__main__":
    unittest.main()
