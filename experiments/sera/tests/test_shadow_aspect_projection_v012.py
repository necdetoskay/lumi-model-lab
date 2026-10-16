"""SERA v0.12 shadow aspect reducer source/authority regression tests."""
from __future__ import annotations
from copy import deepcopy
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_typed_live_v05 import entry_state
from experiments.sera.mara_s1_candidate_corrections_v012 import propose
from experiments.sera.tests.test_mara_s1_candidate_corrections_v012 import (
    PROSE,sample_report,opinions,
)
from experiments.sera.shadow_aspect_projection_v012 import (
    initialize,apply_shadow,project_mara,world_fingerprint,
)

def proposals():
    return propose(prose=PROSE,full_report=sample_report(),bundle=opinions())

class ShadowAspectV012Tests(unittest.TestCase):
    def test_shadow_projection_replays_open_close_append_without_world_writes(self):
        state=entry_state()
        original=deepcopy(state)
        proof=project_mara(world=state,prose=PROSE,corrections=proposals())
        self.assertEqual(state,original)
        self.assertEqual(proof["source_world_sha256"],
                         proof["world_sha256_after_projection"])
        self.assertTrue(proof["world_state_unchanged"])
        self.assertEqual(proof["facets_applied_noncanonically"],3)
        self.assertEqual(proof["source_action_clock_minutes_invented"],0)
        self.assertEqual(proof["canonical_db_writes"],0)
        self.assertFalse(proof["canonical_commit_authorized"])
        projected=proof["typed_shadow_facet_state"]
        self.assertEqual(projected["facets"]["openable"]
                         ["case_position"],"CLOSED")
        self.assertTrue(projected["facets"]["openable"]["source_observed"])
        self.assertEqual(projected["facets"]["document"]
                         ["preexisting_content"],"UNKNOWN")
        self.assertEqual(projected["facets"]["document"]
                         ["observed_appends"][0]["text"],
                         "Discrepancy documented; explanation unknown.")
        self.assertEqual(len(projected["applied_source_evidence"]),3)

    def test_cannot_close_before_open_baseline(self):
        state=entry_state()
        draft=proposals()["shadow_facet_proposals"]
        initial=initialize(world=state,prose=PROSE,
                           openable_object_id="vane_watch",
                           document_id="mara_notebook")
        with self.assertRaisesRegex(CoverageError,
                                    "SHADOW_OPENABLE_CAS_MISMATCH"):
            apply_shadow(shadow=initial,world=state,prose=PROSE,
                         proposal=draft[1])

    def test_cannot_replay_or_reorder_event_source(self):
        state=entry_state()
        draft=proposals()["shadow_facet_proposals"]
        initial=initialize(world=state,prose=PROSE,
                           openable_object_id="vane_watch",
                           document_id="mara_notebook")
        opened=apply_shadow(shadow=initial,world=state,prose=PROSE,
                            proposal=draft[0])
        with self.assertRaisesRegex(CoverageError,
                                    "SHADOW_NARRATIVE_ORDER_OR_REPLAY_INVALID"):
            apply_shadow(shadow=opened,world=state,prose=PROSE,
                         proposal=draft[0])

    def test_note_notebook_blank_not_assumed(self):
        state=entry_state()
        facets=proposals()
        proof=project_mara(world=state,prose=PROSE,corrections=facets)
        record=proof["typed_shadow_facet_state"]["facets"]["document"]
        self.assertEqual(record["preexisting_content"],"UNKNOWN")
        self.assertEqual(len(record["observed_appends"]),1)
        self.assertEqual(state["entities"]["mara_notebook"]
                         ["appearance"]["markings"],"UNKNOWN")

    def test_wrong_evidence_or_fabricated_action_minute_rejected(self):
        state=entry_state()
        original=proposals()
        corrupted=deepcopy(original)
        corrupted["shadow_facet_proposals"][0]["evidence"]["quote"]="invented"
        with self.assertRaisesRegex(CoverageError,
                                    "SHADOW_PROPOSED_SOURCE_EVIDENCE_INVALID"):
            project_mara(world=state,prose=PROSE,corrections=corrupted)
        bad_time=deepcopy(original)
        bad_time["shadow_facet_proposals"][0]["action_time_minute"]=135
        with self.assertRaisesRegex(CoverageError,
                                    "SHADOW_PROPOSAL_TIME_OR_STATUS_UNAUTHORIZED"):
            project_mara(world=state,prose=PROSE,corrections=bad_time)

    def test_unqualified_canonical_commit_override_fails(self):
        state=entry_state()
        value=proposals()
        value["canonical_commit_authorized"]=True
        with self.assertRaisesRegex(CoverageError,
                                    "SHADOW_UNQUALIFIED_CORRECTIONS"):
            project_mara(world=state,prose=PROSE,corrections=value)
        value=proposals()
        value["shadow_facet_proposals"][1]["owner_object_id"]="new:watch_case"
        with self.assertRaisesRegex(CoverageError,
                                    "SHADOW_TARGET_NOT_WORLD_OBJECT"):
            project_mara(world=state,prose=PROSE,corrections=value)

if __name__=="__main__":
    unittest.main()
