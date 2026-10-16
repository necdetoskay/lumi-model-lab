"""Offline tests for full 25-event qualification census, not gold."""
from __future__ import annotations

from copy import deepcopy
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_typed_live_v05 import entry_state
from experiments.sera.mara_s1_event_census_v013 import run
from experiments.sera.tests.test_mara_s1_candidate_corrections_v012 import (
    PROSE,sample_report,opinions,
)
from experiments.sera.mara_s1_candidate_corrections_v012 import propose
from experiments.sera.mara_s1_versioned_facets_v013 import run as versioned_run

def sources():
    full=sample_report()
    repairs=propose(prose=PROSE,full_report=full,bundle=opinions())
    projection=versioned_run(corrections=repairs)
    return full,repairs,projection

class EventCensusV013Tests(unittest.TestCase):
    def test_all_25_events_have_hold_and_no_self_authority(self):
        full,repairs,versioned=sources()
        report=run(prose=PROSE,world=entry_state(),full_report=full,
                   repairs=repairs,versioned_simulation=versioned)
        self.assertEqual(report["source_sentence_count"],28)
        self.assertEqual(report["source_model_event_count"],25)
        self.assertEqual(report["candidate_repair_count"],2)
        self.assertEqual(report["versioned_facet_events_simulated"],3)
        self.assertEqual(report["events_qualified_for_canonical_commit"],0)
        self.assertEqual(report["production_database_writes"],0)
        self.assertEqual(report["real_model_calls_in_census"],0)
        self.assertTrue(all(r["status"]=="HOLD_NOT_CANONICAL" and
                            r["canonical_commit_authorized"] is False
                            for r in report["rows"]))
        self.assertEqual(sum(report["source_event_types"].values()),25)
        self.assertEqual(report["status"],
                         "ALL_25_EVENTS_AUDITED_SEMANTIC_AND_AUTHORITY_HOLD")

    def test_corrected_source_ids_must_match_original_model_fields(self):
        full,repairs,versioned=sources()
        wrong=deepcopy(full)
        wrong["candidate_events"][0]["kind"]="OPEN"
        with self.assertRaisesRegex(
            CoverageError,"V013_CENSUS_REPAIR_TARGET_NO_LONGER_MATCHES"
        ):
            run(prose=PROSE,world=entry_state(),full_report=wrong,
                repairs=repairs,versioned_simulation=versioned)

    def test_spurious_reported_claims_cannot_be_physical_authority(self):
        full,repairs,versioned=sources()
        item=full["candidate_events"][4]
        item["kind"]="CLAIM_MENTION"
        item["epistemic"]="REPORTED_CLAIM"
        item["effect"]="NONE"
        report=run(prose=PROSE,world=entry_state(),full_report=full,
                   repairs=repairs,versioned_simulation=versioned)
        claim=next(x for x in report["rows"] if x["source_event_id"]==item["event_id"])
        self.assertEqual(claim["qualification_category"],"REPORTED_CLAIM_ONLY")
        self.assertIn("REPORTED_OR_UNCERTAIN_CLAIM_NOT_OBJECTIVE_STATE",
                      claim["blockers"])
        self.assertFalse(claim["canonical_commit_authorized"])

    def test_wrong_source_quote_and_synthetic_approval_fail_closed(self):
        full,repairs,versioned=sources()
        tampered=deepcopy(full)
        tampered["candidate_events"][0]["quote"]="fabricated arrival"
        with self.assertRaisesRegex(CoverageError,
                                    "V013_CENSUS_EVENT_NOT_SOURCE_BOUND"):
            run(prose=PROSE,world=entry_state(),full_report=tampered,
                repairs=repairs,versioned_simulation=versioned)
        fake=deepcopy(versioned);fake["real_canonical_authorization"]=True
        with self.assertRaisesRegex(CoverageError,
                                    "V013_CENSUS_VERSIONED_TEST_PROOF_INVALID"):
            run(prose=PROSE,world=entry_state(),full_report=full,
                repairs=repairs,versioned_simulation=fake)

    def test_new_entity_refs_not_auto_registered(self):
        full,repairs,versioned=sources()
        full["candidate_events"][3]["entity_refs"]=["new:bench","new:vane_thumb"]
        report=run(prose=PROSE,world=entry_state(),full_report=full,
                   repairs=repairs,versioned_simulation=versioned)
        self.assertIn("new:bench",report["unregistered_or_provisional_refs"])
        self.assertIn("new:vane_thumb",report["body_part_candidate_refs"])
        self.assertEqual(report["events_qualified_for_canonical_commit"],0)

if __name__=="__main__":
    unittest.main()
