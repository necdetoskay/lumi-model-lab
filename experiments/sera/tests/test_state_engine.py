"""Offline SERA v0.1 regression tests; no API calls and no production writes."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from experiments.sera.spine_contracts import (
    SOURCE_BLOB_SHA, SOURCE_RELATIVE_PATH,
    SpineContractError, compile_scene_contracts, git_blob_sha, load_frozen_spine,
)
from experiments.sera.state_engine import (
    StateError, apply_scene, base_snapshot, validate_snapshot, verify_exit_state,
)

SOURCE_PATH = Path(__file__).resolve().parents[3] / SOURCE_RELATIVE_PATH
ROUTES = {
    "north_quay_station->signal_archive": 10,
    "signal_archive->rail_yard": 15,
    "rail_yard->north_quay_station": 15,
    "signal_archive->north_quay_station": 10,
}
QUOTE_TELL = "Vane told Mara that his watch stopped at 02:07."
QUOTE_WRITE = "Mara wrote the time in her notebook."
QUOTE_WALK = "Mara reached the signal archive after the walk."
QUOTE_HAND = "Vane placed the watch in Mara's hand."
QUOTE_OBJECT = "Mara adjusted the pocket watch."
QUOTE_CREATE = "A brass lantern appeared on the platform."


def fixture():
    return base_snapshot(
        minute=135,
        facts={
            "watch_stopped_0207": {
                "claim": "Vane's watch stopped at 02:07",
                "certainty": "OBSERVED",
            },
            "manifest_0210": {
                "claim": "Manifest lists an arrival at 02:10",
                "certainty": "OBSERVED",
            },
        },
        entities={
            "mara": {
                "kind": "CHARACTER",
                "location": "north_quay_station",
                "last_action_minute": 135,
                "knowledge": ["manifest_0210"],
            },
            "vane": {
                "kind": "CHARACTER",
                "location": "north_quay_station",
                "last_action_minute": 135,
                "knowledge": ["watch_stopped_0207"],
            },
            "corde": {
                "kind": "CHARACTER",
                "location": "signal_archive",
                "last_action_minute": 135,
                "knowledge": [],
            },
            "vane_watch": {
                "kind": "OBJECT",
                "location": "north_quay_station",
                "holder": "vane",
                "properties": {"status": "stopped"},
                "recorded_facts": [],
            },
            "mara_notebook": {
                "kind": "OBJECT",
                "location": "north_quay_station",
                "holder": "mara",
                "properties": {"status": "open"},
                "recorded_facts": [],
            },
            "platform_clock": {
                "kind": "OBJECT",
                "location": "north_quay_station",
                "holder": None,
                "properties": {"strike_for_41": False},
                "recorded_facts": [],
            },
        },
    )


def evt(eid, kind, time, quote, **fields):
    return {
        "event_id": eid, "type": kind, "at": time,
        "evidence_text": quote, **fields,
    }


def run_scene(state, events, prose, **kwargs):
    return apply_scene(
        state, events, scene_key="hook_empty_platform", prose=prose,
        travel_minutes=ROUTES, **kwargs,
    )


class SeraStateTests(unittest.TestCase):
    def assert_code(self, code, callable_):
        with self.assertRaises(StateError) as cm:
            callable_()
        self.assertTrue(
            cm.exception.code.startswith(code),
            f"expected {code!r}, got {cm.exception.code!r}",
        )

    def test_zero_events_keeps_all_entities_and_objects(self):
        state = fixture()
        result = run_scene(state, [], "The station remained quiet.")
        self.assertEqual(state["entities"], result["entities"])
        self.assertEqual(result["scene_index"], 1)
        self.assertEqual(state["scene_index"], 0)

    def test_tell_and_record_fact_update_knowledge_and_notebook(self):
        state = fixture()
        events = [
            evt("e1", "TELL_FACT", 140, QUOTE_TELL,
                from_id="vane", to_id="mara", fact_id="watch_stopped_0207"),
            evt("e2", "RECORD_FACT", 141, QUOTE_WRITE,
                character_id="mara", object_id="mara_notebook",
                fact_id="watch_stopped_0207"),
        ]
        result = run_scene(state, events, QUOTE_TELL + " " + QUOTE_WRITE)
        self.assertIn("watch_stopped_0207",
                      result["entities"]["mara"]["knowledge"])
        self.assertEqual(
            result["entities"]["mara_notebook"]["recorded_facts"],
            ["watch_stopped_0207"],
        )
        self.assertEqual(result["entities"]["vane_watch"],
                         state["entities"]["vane_watch"])
        self.assertEqual(len(result["event_log"]), 2)
        self.assertEqual(state["event_log"], [])

    def test_walk_too_fast_rejected(self):
        event = evt("e1", "MOVE_CHARACTER", 140, QUOTE_WALK,
                    character_id="mara", to="signal_archive")
        self.assert_code("TRAVEL_TOO_FAST",
                         lambda: run_scene(fixture(), [event], QUOTE_WALK))

    def test_valid_walk_moves_all_held_objects_automatically(self):
        result = run_scene(fixture(), [
            evt("e1", "MOVE_CHARACTER", 145, QUOTE_WALK,
                character_id="mara", to="signal_archive"),
        ], QUOTE_WALK)
        self.assertEqual(result["entities"]["mara"]["location"], "signal_archive")
        self.assertEqual(result["entities"]["mara_notebook"]["location"],
                         "signal_archive")
        self.assertEqual(result["entities"]["vane_watch"]["location"],
                         "north_quay_station")
        self.assertEqual(result["entities"]["platform_clock"]["location"],
                         "north_quay_station")

    def test_no_teleport_to_sealed_dispatch_office(self):
        event = evt("e1", "MOVE_CHARACTER", 200, QUOTE_WALK,
                    character_id="mara", to="sealed_dispatch_office")
        self.assert_code("FORBIDDEN_DESTINATION",
                         lambda: run_scene(fixture(), [event], QUOTE_WALK))

    def test_transfer_between_separated_people_rejected(self):
        event = evt("e1", "TRANSFER_OBJECT", 140, QUOTE_HAND,
                    object_id="vane_watch", from_id="vane", to_id="corde")
        self.assert_code("TRANSFER_NOT_COLOCATED",
                         lambda: run_scene(fixture(), [event], QUOTE_HAND))

    def test_valid_transfer_changes_owner_and_preserves_identity(self):
        result = run_scene(fixture(), [
            evt("e1", "TRANSFER_OBJECT", 140, QUOTE_HAND,
                object_id="vane_watch", from_id="vane", to_id="mara"),
        ], QUOTE_HAND)
        self.assertEqual(result["entities"]["vane_watch"]["holder"], "mara")
        self.assertEqual(len(result["entities"]), len(fixture()["entities"]))

    def test_missing_span_rejected(self):
        event = evt("e1", "TRANSFER_OBJECT", 140, QUOTE_HAND,
                    object_id="vane_watch", from_id="vane", to_id="mara")
        self.assert_code("EVIDENCE_SPAN_NOT_FOUND",
                         lambda: run_scene(fixture(), [event], "The night was quiet."))

    def test_unknown_event_type_rejected(self):
        event = evt("e1", "MAGIC_TELEPORT", 140, QUOTE_HAND)
        self.assert_code("EVENT_TYPE_INVALID",
                         lambda: run_scene(fixture(), [event], QUOTE_HAND))

    def test_knowledge_source_must_know_fact(self):
        event = evt("e1", "TELL_FACT", 140, QUOTE_TELL,
                    from_id="mara", to_id="vane", fact_id="watch_stopped_0207")
        self.assert_code("UNAUTHORIZED_KNOWLEDGE_SOURCE",
                         lambda: run_scene(fixture(), [event], QUOTE_TELL))

    def test_object_update_requires_actor_same_location(self):
        event = evt("e1", "UPDATE_OBJECT", 140, QUOTE_OBJECT,
                    actor_id="corde", object_id="vane_watch",
                    property="status", value="running")
        self.assert_code("OBJECT_OUT_OF_REACH",
                         lambda: run_scene(fixture(), [event], QUOTE_OBJECT))

    def test_object_identity_fields_protected(self):
        event = evt("e1", "UPDATE_OBJECT", 140, QUOTE_OBJECT,
                    actor_id="vane", object_id="vane_watch",
                    property="holder", value="corde")
        self.assert_code("OBJECT_FIELD_PROTECTED",
                         lambda: run_scene(fixture(), [event], QUOTE_OBJECT))

    def test_creation_requires_authority(self):
        entity = {
            "kind": "OBJECT", "location": "north_quay_station",
            "holder": None, "properties": {"lit": False},
            "recorded_facts": [],
        }
        event = evt("e1", "CREATE_ENTITY", 140, QUOTE_CREATE,
                    entity_id="lantern", entity=entity)
        self.assert_code("ENTITY_CREATION_NOT_AUTHORIZED",
                         lambda: run_scene(fixture(), [event], QUOTE_CREATE))
        result = run_scene(
            fixture(), [event], QUOTE_CREATE,
            allowed_new_entity_ids=("lantern",),
        )
        self.assertIn("lantern", result["entities"])
        self.assertIn("platform_clock", result["entities"])

    def test_duplicate_event_id_rejected(self):
        events = [
            evt("same", "OPEN_THREAD", 140, "Mara opened a question.",
                thread_id="q1"),
            evt("same", "OPEN_THREAD", 141, "Mara opened another question.",
                thread_id="q2"),
        ]
        self.assert_code(
            "DUPLICATE_EVENT_ID",
            lambda: run_scene(fixture(), events,
                              "Mara opened a question. Mara opened another question."),
        )

    def test_event_time_backwards_rejected(self):
        events = [
            evt("e1", "OPEN_THREAD", 145, "A question emerged.", thread_id="q1"),
            evt("e2", "OPEN_THREAD", 140, "A second question emerged.", thread_id="q2"),
        ]
        self.assert_code(
            "EVENT_TIME_INVALID",
            lambda: run_scene(fixture(), events,
                              "A question emerged. A second question emerged."),
        )

    def test_thread_must_be_open_to_resolve(self):
        event = evt("e1", "RESOLVE_THREAD", 140, "The question was answered.",
                    thread_id="q1")
        self.assert_code("THREAD_UNKNOWN",
                         lambda: run_scene(fixture(), [event],
                                           "The question was answered."))

    def test_tampered_handoff_dropped_object_rejected(self):
        entry = fixture()
        valid = run_scene(entry, [], "Quiet.")
        tampered = deepcopy(valid)
        del tampered["entities"]["vane_watch"]
        self.assert_code(
            "EXIT_STATE_NOT_REDUCER_RESULT",
            lambda: verify_exit_state(
                entry, [], tampered, scene_key="hook_empty_platform",
                prose="Quiet.", travel_minutes=ROUTES,
            ),
        )

    def test_tampered_handoff_ownership_rejected(self):
        entry = fixture()
        valid = run_scene(entry, [], "Quiet.")
        tampered = deepcopy(valid)
        tampered["entities"]["vane_watch"]["holder"] = "mara"
        self.assert_code(
            "EXIT_STATE_NOT_REDUCER_RESULT",
            lambda: verify_exit_state(
                entry, [], tampered, scene_key="hook_empty_platform",
                prose="Quiet.", travel_minutes=ROUTES,
            ),
        )

    def test_fact_epistemic_class_validated(self):
        state = fixture()
        state["facts"]["watch_stopped_0207"]["certainty"] = "CERTAIN_CULPRIT"
        self.assert_code("FACT_CERTAINTY_INVALID",
                         lambda: validate_snapshot(state))

    def test_prose_and_proposed_events_are_not_completeness_proof(self):
        # Deliberate limitation: prose may contain an unreported movement;
        # independent extraction/JEV must detect this in a later phase.
        result = run_scene(
            fixture(), [],
            "Vane slipped the watch into a cabinet. The station was quiet.",
        )
        self.assertEqual(result["entities"]["vane_watch"]["holder"], "vane")


class SeraSpineTests(unittest.TestCase):
    def test_original_source_sha_and_nine_scenes(self):
        self.assertEqual(git_blob_sha(SOURCE_PATH.read_bytes()), SOURCE_BLOB_SHA)
        spine = load_frozen_spine(SOURCE_PATH)
        contracts = compile_scene_contracts(spine)
        self.assertEqual(len(contracts), 9)
        self.assertEqual(contracts[0]["key"], "hook_empty_platform")
        self.assertEqual(contracts[-1]["key"], "payoff_report_filed")
        self.assertTrue(all(c["spine_blob_sha"] == SOURCE_BLOB_SHA
                            for c in contracts))
        self.assertEqual(contracts[6]["phase"], "DECISION")
        self.assertTrue(contracts[6]["decision_outcome_uncommitted"])

    def test_compiler_rejects_unknown_prior_dependency(self):
        spine = deepcopy(load_frozen_spine(SOURCE_PATH))
        spine["beats"][1]["causal_dependency_keys"] = ["future_scene"]
        with self.assertRaises(SpineContractError):
            compile_scene_contracts(spine)

    def test_compiler_does_not_mutate_original_structure(self):
        spine = load_frozen_spine(SOURCE_PATH)
        before = deepcopy(spine)
        compile_scene_contracts(spine)
        self.assertEqual(spine, before)


if __name__ == "__main__":
    unittest.main()
