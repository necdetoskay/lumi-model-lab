"""v0.38 SQLite -> real v0.6/v0.24/v0.25 gates -> simulation CAS."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.multi_character_world_lab_v037 import ScenarioLab
from experiments.sera.story_scene_rehearsal_v038 import rehearsal
from experiments.sera.world_state_v02 import WorldStateError, fingerprint

FIXTURE = (Path(__file__).resolve().parents[1] /
           "fixtures/multi_character_story_v037.json")
WORLD = "lab-mara-ensemble-world-a"
ALIASES = {
    "mara": ["Mara"], "elin": ["Elin"], "rho": ["Rho"],
    "pocket-watch": ["pocket-watch"], "notebook": ["notebook"],
    "pencil": ["pencil"], "rho-cloak": ["rho-cloak"],
}


def source(event_id, text, kind, refs, *, epistemic="OBSERVED_ACTION"):
    return {
        "event_id": event_id, "sentence_id": "s001", "kind": kind,
        "effect": "OBJECT" if kind == "TRANSFER" else "WORLD",
        "epistemic": epistemic, "entity_refs": refs,
        "start": 0, "end": len(text), "quote": text,
    }


def reducer(event_id, scene_key, text, kind, payload, minute):
    return {
        "event_id": event_id, "type": kind, "at_minute": minute,
        "reason": "independently specified lab fixture event",
        "evidence_ref": ("synthetic-scene:" + scene_key + ":" +
                         prose_hash(text)),
        "payload": payload,
    }


def transfer_scene(lab, *, run_id="mara-s1", revision=0, **changes):
    text = "Mara handed the pocket-watch to Elin."
    scene = "Mara-S1"
    e = reducer("mara-watch-gift", scene, text, "TRANSFER_HOLDER", {
        "entity_id": "pocket-watch", "from_id": "mara", "to_id": "elin",
    }, 1)
    source_event = source(e["event_id"], text, "TRANSFER",
                          ["mara", "pocket-watch", "elin"])
    spec = [{
        "source_event_id": e["event_id"], "operation": "TRANSFER_HOLDER",
        "object_id": "pocket-watch", "from_id": "mara", "to_id": "elin",
        "fact_id": None,
    }]
    kwargs = dict(
        lab=lab, run_id=run_id, expected_revision=revision,
        scene_key=scene, prose=text, source_event=source_event,
        reducer_event=e, registered_aliases=ALIASES,
        candidate_lexicon={}, fixture_grants={e["event_id"]: fingerprint(e)},
        relation_case={
            "entry": lab.head(WORLD), "registered_aliases": deepcopy(ALIASES),
            "verified_fact_registry": {}, "transitions": spec,
            "policy_id": "fixture:v038:watch-handoff",
        },
    )
    kwargs.update(changes)
    return rehearsal(**kwargs)


def movement_scene(lab, *, run_id="elin-s2", revision=1, **changes):
    text = "Elin carried the pocket-watch into hallway."
    scene = "Elin-S2"
    e = reducer("elin-carries-watch", scene, text, "MOVE_CHARACTER", {
        "character_id": "elin", "to_location": "hallway",
    }, 4)
    spec = {
        "event_id": e["event_id"], "ordinal": 1, "actor_id": "elin",
        "kind": "MOVEMENT", "to_location": "hallway",
        "earliest_minute": None, "latest_minute": None,
        "exact_minute": None, "depends_on": [],
    }
    kwargs = dict(
        lab=lab, run_id=run_id, expected_revision=revision,
        scene_key=scene, prose=text,
        source_event=source(e["event_id"], text, "MOVE",
                            ["elin", "pocket-watch"]),
        reducer_event=e, registered_aliases=ALIASES,
        candidate_lexicon={}, fixture_grants={e["event_id"]: fingerprint(e)},
        temporal_case={
            "entry": lab.head(WORLD), "scene_key": scene,
            "scene_window": {
                "scene_key": scene, "entry_revision": revision,
                "earliest_minute": 1, "latest_minute": 12,
            },
            "events": [spec],
            "travel_minutes": {
                "workshop->hallway": 3, "hallway->workshop": 3,
                "hallway->garden": 4, "garden->hallway": 4,
            },
        },
    )
    kwargs.update(changes)
    return rehearsal(**kwargs)


class StorySceneRehearsalV038Tests(unittest.TestCase):
    def setUp(self):
        self.lab = ScenarioLab()
        self.lab.seed(json.loads(FIXTURE.read_text(encoding="utf-8")))
        self.lab.begin_story(run_id="mara-s1", world_id=WORLD,
                             character_id="mara")
        self.lab.begin_story(run_id="elin-s2", world_id=WORLD,
                             character_id="elin")

    def tearDown(self):
        self.lab.close()

    def test_real_source_gate_and_simulation_handoff_across_characters(self):
        one = transfer_scene(self.lab)
        two = movement_scene(self.lab)
        self.assertEqual((one["entry_revision"], one["exit_revision"]), (0,1))
        self.assertEqual((two["entry_revision"], two["exit_revision"]), (1,2))
        self.assertEqual(one["preview_kind"],
                         "sera.relation-knowledge-preview.v0.25")
        self.assertEqual(two["preview_kind"], "sera.spatial-preview.v0.24")
        self.assertEqual(one["scene_assurance_status"], "HOLD")
        self.assertEqual(two["scene_assurance_status"], "HOLD")
        self.assertFalse(one["independent_semantic_qualification"])
        self.assertEqual(one["provider_calls"]+two["provider_calls"],0)
        self.assertFalse(one["canonical_commit_authorized"])
        self.assertFalse(two["canonical_commit_authorized"])
        self.assertEqual(one["production_db_writes"]+
                         two["production_db_writes"], 0)
        self.assertTrue(self.lab.store.verify_replay(WORLD))
        world = self.lab.head(WORLD)
        self.assertEqual(world["revision"],2)
        self.assertEqual(world["entities"]["pocket-watch"]["owner"],"mara")
        self.assertEqual(world["entities"]["pocket-watch"]["holder"],"elin")
        self.assertEqual(world["entities"]["pocket-watch"]["location"],"hallway")
        self.assertEqual(world["entities"]["elin"]["location"],"hallway")
        self.assertEqual(world["entities"]["mara"]["location"],"workshop")
        self.assertEqual(self.lab.context("mara-s1")["revision"],2)
        self.assertNotIn("secret-elins-note",
                         json.dumps(self.lab.context("mara-s1")))
        self.assertEqual(self.lab.db.execute(
            "SELECT count(*) FROM lab_run_events").fetchone()[0],2)

    def test_simulation_grant_absent_makes_no_mutation(self):
        with self.assertRaisesRegex(WorldStateError,
                                    "V038_SOURCE_OR_FIXTURE_GRANT_INVALID"):
            transfer_scene(self.lab, fixture_grants={})
        self.assertEqual(self.lab.head(WORLD)["revision"],0)

    def test_reported_action_cannot_be_physical_fact(self):
        text = "Mara handed the pocket-watch to Elin."
        report = source("mara-watch-gift",text,"TRANSFER",
                        ["mara","pocket-watch","elin"],
                        epistemic="REPORTED_CLAIM")
        with self.assertRaisesRegex(WorldStateError,
                                    "V038_SOURCE_OR_FIXTURE_GRANT_INVALID"):
            transfer_scene(self.lab,source_event=report)
        self.assertEqual(self.lab.head(WORLD)["revision"],0)

    def test_forged_quote_and_second_unreported_sentence_are_rejected(self):
        report = source("mara-watch-gift","Mara handed the watch to Elin.",
                        "TRANSFER",["mara","pocket-watch","elin"])
        with self.assertRaisesRegex(WorldStateError,
                                    "V038_SOURCE_OR_FIXTURE_GRANT_INVALID"):
            transfer_scene(self.lab,source_event=report)
        with self.assertRaisesRegex(WorldStateError,
                                    "V038_SOURCE_OR_FIXTURE_GRANT_INVALID"):
            transfer_scene(
                self.lab, prose="Mara handed the pocket-watch to Elin. "
                                "Then Rho disappeared.",
            )
        self.assertEqual(self.lab.head(WORLD)["revision"],0)

    def test_untrusted_route_does_not_overwrite_registered_sqlite_rules(self):
        transfer_scene(self.lab)
        altered = movement_scene_arguments(self.lab)
        altered["temporal_case"]["travel_minutes"]["workshop->hallway"]=0
        with self.assertRaisesRegex(WorldStateError,
                                    "V038_SPATIAL_POLICY_MISMATCH"):
            movement_scene(self.lab,temporal_case=altered["temporal_case"])
        self.assertEqual(self.lab.head(WORLD)["revision"],1)

    def test_stale_revision_never_mutates_second_scene(self):
        transfer_scene(self.lab)
        with self.assertRaisesRegex(WorldStateError,
                                    "V037_SCENE_ENTRY_REVISION_CONFLICT"):
            movement_scene(self.lab,revision=0)
        self.assertEqual(self.lab.head(WORLD)["revision"],1)

    def test_wrong_custody_fails_before_commit(self):
        transfer_scene(self.lab)
        # The first story already gave the watch away; another transfer
        # from Mara to Elin at new revision is physically impossible.
        with self.assertRaisesRegex(CoverageError,
                                    "V025_HOLDER_CAS_OR_COLOCATION_FAILED"):
            transfer_scene(self.lab,revision=1)
        self.assertEqual(self.lab.head(WORLD)["revision"],1)

    def test_disclosed_private_registry_not_taken_from_model_report(self):
        unsafe = deepcopy(ALIASES)
        unsafe.pop("pencil")
        with self.assertRaisesRegex(WorldStateError,
                                    "V038_REGISTERED_ALIASES_INCOMPLETE"):
            transfer_scene(self.lab,registered_aliases=unsafe)
        self.assertEqual(self.lab.head(WORLD)["revision"],0)

    def test_impossible_scene_arrival_time_is_rejected(self):
        transfer_scene(self.lab)
        kw = movement_scene_arguments(self.lab)
        kw["temporal_case"]["scene_window"]["latest_minute"] = 2
        with self.assertRaises(CoverageError):
            movement_scene(self.lab,temporal_case=kw["temporal_case"])
        self.assertEqual(self.lab.head(WORLD)["revision"],1)

    def test_restart_restores_cross_character_continuity(self):
        with tempfile.TemporaryDirectory() as path:
            file = str(Path(path)/"scene-story.sqlite")
            with ScenarioLab(file) as first:
                first.seed(json.loads(FIXTURE.read_text(encoding="utf-8")))
                first.begin_story(run_id="mara-s1",world_id=WORLD,
                                  character_id="mara")
                first.begin_story(run_id="elin-s2",world_id=WORLD,
                                  character_id="elin")
                transfer_scene(first)
            with ScenarioLab(file) as second:
                result = movement_scene(second)
                self.assertEqual(result["exit_revision"],2)
                self.assertTrue(second.store.verify_replay(WORLD))
                self.assertEqual(second.head(WORLD)["entities"]["pocket-watch"]
                                 ["holder"],"elin")


def movement_scene_arguments(lab):
    # Construct the trusted temporal case from the same helper shape
    # without executing the scene or modifying SQLite.
    state=lab.head(WORLD)
    return {
        "temporal_case": {
            "entry": state, "scene_key": "Elin-S2",
            "scene_window": {
                "scene_key": "Elin-S2", "entry_revision": state["revision"],
                "earliest_minute": 1, "latest_minute": 12,
            },
            "events": [{
                "event_id":"elin-carries-watch","ordinal":1,
                "actor_id":"elin","kind":"MOVEMENT",
                "to_location":"hallway","earliest_minute":None,
                "latest_minute":None,"exact_minute":None,"depends_on":[],
            }],
            "travel_minutes":{
                "workshop->hallway":3, "hallway->workshop":3,
                "hallway->garden":4, "garden->hallway":4,
            },
        }
    }


if __name__ == "__main__":
    unittest.main()
