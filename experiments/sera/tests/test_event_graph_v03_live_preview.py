"""Real Mara first-scene event-graph inspection; source verified, NO canon commit.

The nine candidate annotations were analyst curated from archived live prose.
They are not JEV qualified and MUST remain HOLD.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest

from experiments.sera.tests.test_world_state_v02 import base, event, approved
from experiments.sera.event_graph_v03 import (
    EventGraphStore, WorldStateError, validate_proposal,
)

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "fixtures/mara_s1_real_eventgraph_candidates_v03.json"
)


class RealMaraEventGraphPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(SOURCE.read_text(encoding="utf-8"))

    def test_source_is_exact_unchanged_live_243_word_prose(self):
        obj = self.fixture
        self.assertEqual(obj["source_type"],
                         "ANALYST_CURATED_LIVE_SCENE_INSPECTION")
        self.assertEqual(obj["source_run_id"], 38808450095)
        self.assertEqual(obj["continuation_run_id"], 38809210994)
        self.assertEqual(
            sha256(obj["prose"].encode("utf-8")).hexdigest(),
            "80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03",
        )
        self.assertEqual(obj["word_count"], len(obj["prose"].split()))

    def test_each_real_candidate_quote_matches_exact_prose_span(self):
        obj = self.fixture
        self.assertEqual(len(obj["candidates"]), 9)
        self.assertEqual(len({e["candidate_id"] for e in obj["candidates"]}), 9)
        for i, candidate in enumerate(obj["candidates"], start=1):
            with self.subTest(candidate=candidate["candidate_id"]):
                start = candidate["evidence"]["start"]
                end = candidate["evidence"]["end"]
                self.assertEqual(obj["prose"][start:end],
                                 candidate["evidence"]["quote"])
                self.assertEqual(candidate["time"]["scene_ordinal"], i)
                self.assertIsNone(candidate["time"]["exact_minute"])
                self.assertIsNone(candidate["typed_world_event"])
                self.assertEqual(candidate["status"], "HOLD")
                self.assertEqual(candidate["state_effects"], "NOT_COMPUTED")
                self.assertFalse(obj["production_commit_authorized"])

    def test_noncanonical_objects_remain_candidates_not_entities(self):
        obj = self.fixture
        discovered = {
            entity["id"]
            for candidate in obj["candidates"]
            for entity in candidate["objects"]
            if entity["id"].startswith("new:")
        }
        self.assertEqual(discovered, {"new:bench", "new:pencil"})
        pencil = next(c for c in obj["candidates"]
                      if c["candidate_id"] == "evt_s1_09")
        self.assertIn("PENCIL_MOTION_ACTOR_UNKNOWN", pencil["blockers"])
        witness = next(c for c in obj["candidates"]
                       if c["candidate_id"] == "evt_s1_03")
        self.assertEqual(witness["epistemic"], "REPORTED_CLAIM")
        self.assertIn("CLAIM_NOT_PHYSICAL_ARRIVAL", witness["blockers"])

    def test_live_curation_cannot_be_passed_off_as_verified_world_event(self):
        with EventGraphStore() as graph:
            graph.create("mara", base())
            draft = deepcopy(self.fixture["candidates"][0])
            with self.assertRaises(WorldStateError):
                validate_proposal(
                    draft, prose=self.fixture["prose"],
                    state=graph.head("mara"),
                )
            self.assertEqual(graph.head("mara")["revision"], 0)

    def test_detect_unrepresented_world_event_during_replay(self):
        with EventGraphStore() as graph:
            graph.create("mara", base())
            # Simulate a side-channel v0.2 event: graph replay must detect it.
            e = event("out-of-graph", "ADVANCE_SCENE", 140, scene_key="s1")
            graph.world.commit("mara", expected_revision=0,
                               events=[e], approvals=approved(e))
            with self.assertRaisesRegex(
                WorldStateError, "NARRATIVE_WORLD_EVENT_COVERAGE_MISMATCH"
            ):
                graph.verify("mara")


if __name__ == "__main__":
    unittest.main()
