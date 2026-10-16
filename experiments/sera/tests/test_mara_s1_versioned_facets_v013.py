"""SERA v0.13 Mara real-source adapter security regressions (offline)."""
from __future__ import annotations

from copy import deepcopy
import unittest
import json

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_v04_audit import PATH
from experiments.sera.mara_s1_versioned_facets_v013 import adapt,run
from experiments.sera.tests.test_mara_s1_candidate_corrections_v012 import (
    PROSE,sample_report,opinions,
)
from experiments.sera.mara_s1_candidate_corrections_v012 import propose

def fixture():
    return propose(prose=PROSE,full_report=sample_report(),bundle=opinions())

class MaraVersionedV013Tests(unittest.TestCase):
    def test_converts_three_source_facets_into_typed_events(self):
        events=adapt(prose=PROSE,corrections=fixture())
        self.assertEqual([x["type"] for x in events],[
            "OBSERVE_OPENABLE","SET_OPENABLE","APPEND_DOCUMENT_ENTRY"
        ])
        self.assertEqual([x["sentence_id"] for x in events],[
            "s004","s011","s021",
        ])
        self.assertEqual(events[0]["payload"],{
            "expected":"UNKNOWN","observed":"OPEN"
        })
        self.assertEqual(events[1]["payload"],{
            "expected":"OPEN","next":"CLOSED"
        })
        self.assertEqual(events[2]["payload"],{
            "expected_append_count":0,
            "text":"Discrepancy documented; explanation unknown."
        })
        self.assertEqual(len(events),3)
        self.assertNotIn("at_minute",json.dumps(events))
        for event in events:
            quote=event["evidence"]
            self.assertEqual(PROSE[quote["start"]:quote["end"]],quote["quote"])

    def test_detached_real_mara_replay_never_alters_v02(self):
        report=run(corrections=fixture())
        self.assertEqual(report["simulated_reducer_events"],3)
        self.assertTrue(report["world_v02_snapshot_unchanged"])
        self.assertTrue(report["history_verifies_deterministically"])
        self.assertTrue(report["reconstructed_initial_snapshot_unchanged"])
        self.assertEqual(report["versioned_aspects"]["vane_watch"]["position"],
                         "CLOSED")
        self.assertEqual(report["versioned_aspects"]["mara_notebook"]
                         ["preexisting_content"],"UNKNOWN")
        self.assertEqual(report["versioned_aspects"]["mara_notebook"]
                         ["observed_appends"][0]["text"],
                         "Discrepancy documented; explanation unknown.")
        self.assertEqual(report["actual_source_action_times_set"],0)
        self.assertEqual(report["production_database_writes"],0)
        self.assertFalse(report["real_canonical_authorization"])
        self.assertFalse(report["gold_reference_qualified"])
        self.assertEqual(report["status"],
                         "VERSIONED_TYPED_REDUCER_SIMULATION_GREEN_CANONICAL_S1_HOLD")

    def test_refuses_unapproved_scene_timestamps_and_unauthorized_facet(self):
        bad=fixture()
        bad["shadow_facet_proposals"][1]["action_time_minute"]=127
        with self.assertRaisesRegex(
            CoverageError,"V013_MARA_PROPOSAL_CONTRACT_CHANGED"
        ):
            adapt(prose=PROSE,corrections=bad)
        bad=fixture()
        bad["shadow_facet_proposals"][0]["new"]="CLOSED"
        with self.assertRaisesRegex(
            CoverageError,"V013_MARA_WATCH_OPEN_BASELINE_UNPROVEN"
        ):
            adapt(prose=PROSE,corrections=bad)
        bad=fixture()
        bad["shadow_facet_proposals"][2]["quoted_entry"]="The train definitely arrived"
        with self.assertRaisesRegex(
            CoverageError,"V013_MARA_DOCUMENT_ENTRY_NOT_EXACT"
        ):
            adapt(prose=PROSE,corrections=bad)

    def test_rejects_forged_quote_and_world_commit_flag(self):
        bad=fixture()
        bad["shadow_facet_proposals"][0]["evidence"]["quote"]="invented"
        with self.assertRaisesRegex(
            CoverageError,"V013_MARA_PROPOSAL_SOURCE_INVALID"
        ):
            adapt(prose=PROSE,corrections=bad)
        bad=fixture()
        bad["canonical_commit_authorized"]=True
        with self.assertRaisesRegex(
            CoverageError,"V013_MARA_SOURCE_OR_AUTHORITY_INVALID"
        ):
            adapt(prose=PROSE,corrections=bad)

    def test_rejects_reversed_proposals_and_modified_story(self):
        bad=fixture()
        bad["shadow_facet_proposals"].reverse()
        with self.assertRaises(CoverageError):
            adapt(prose=PROSE,corrections=bad)
        with self.assertRaisesRegex(
            CoverageError,"V013_MARA_SOURCE_OR_AUTHORITY_INVALID"
        ):
            adapt(prose=PROSE+" different",corrections=fixture())

if __name__=="__main__":
    unittest.main()
