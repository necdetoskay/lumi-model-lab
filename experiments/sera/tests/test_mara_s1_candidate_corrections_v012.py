"""Offline SERA v0.12 corrections: adversarial synthetic contract tests."""
from __future__ import annotations

from copy import deepcopy
import json
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_v04_audit import PATH,EXPECTED_SHA
from experiments.sera.mara_s1_candidate_corrections_v012 import (
    propose,validate_model_bundle,EVIDENCE_IDS,EXPECTED_OPINIONS,
)

PROSE=json.loads(PATH.read_text(encoding="utf-8"))["prose"]

def sample_event(*,eid,quote,kind,effect,epistemic,sid):
    start=PROSE.index(quote)
    return {
        "event_id":eid,"start":start,"end":start+len(quote),
        "quote":quote,"kind":kind,"effect":effect,
        "epistemic":epistemic,"sentence_id":sid,
        "entity_refs":["mara"],"reason":"Synthetic test only",
    }

def sample_report():
    # Explicit, correct evidence only; all extra 22 events are synthetic
    # placeholders used to exercise the 25-event count gate, not gold.
    important=[
        sample_event(eid="batch_004:s014:e1",quote="turned to the platform clock’s strike record",
                     kind="MOVE",effect="CHARACTER_KNOWLEDGE",
                     epistemic="OBSERVED_ACTION",sid="s014"),
        sample_event(eid="batch_006:s021:e1",quote="added",
                     kind="COMMUNICATE",effect="NONE",
                     epistemic="OBSERVED_ACTION",sid="s021"),
        sample_event(eid="batch_003:s011:e1",quote="closed",
                     kind="CLOSE",effect="OBJECT",
                     epistemic="OBSERVED_ACTION",sid="s011"),
    ]
    synthetic=[sample_event(
        eid=f"synthetic:s001:e{i}",quote="Mara",kind="OBSERVE",
        effect="NONE",epistemic="UNCERTAIN",sid="s001",
    ) for i in range(22)]
    return {
        "schema":"sera.blind-sweep-bound.v0.10",
        "source_prose_sha256":EXPECTED_SHA,
        "scene_key":"hook_empty_platform",
        "sentences_accounted_for":28,
        "status":"HOLD_MODEL_SEMANTICS_UNVERIFIED",
        "candidate_events":important+synthetic,
        "canonical_commit_authorized":False,
        "world_state_writes":0,
    }

def opinions():
    fragments={
        "task_001":("turned to","s014"),
        "task_002":("added","s021"),
        "task_003":("his pocket watch open in his palm","s004"),
    }
    result={}
    for task in EVIDENCE_IDS:
        evidence, sentence_id=fragments[task]
        start=PROSE.index(evidence)
        verdict,operation,effect=EXPECTED_OPINIONS[task]
        result[task]={
            "task_id":task,
            "source_prose_sha256":EXPECTED_SHA,
            "request_sha256_in_current_binder":EVIDENCE_IDS[task],
            "canonical_commit_authorized":False,
            "human_adjudicated":False,
            "model_calls_during_recovery":0,
            "status":"RECOVERED_ADVISORY_SOURCE_BOUND_SEMANTIC_HOLD",
            "unmodified_proposed_semantics":{
                "verdict":verdict,"operation_kind":operation,
                "effect":effect,"reason":"Synthetic independent opinion"
            },
            "bound_advisory":{
                "source_prose_sha256":EXPECTED_SHA,
                "canonical_commit_authorized":False,
                "status":"HOLD_MODEL_RESPONSE_NOT_AUTHORITY",
                "verdict_model_proposed":verdict,
                "kind_model_proposed":operation,
                "effect_model_proposed":effect,
                "possible_source_evidence":[{
                    "sentence_id":sentence_id,
                    "start":start,"end":start+len(evidence),
                    "quote":evidence,
                }],
            },
        }
    return result

class MaraProposedCorrectionsTests(unittest.TestCase):
    def test_two_event_replacements_and_three_facet_proposals_stay_pending(self):
        output=propose(
            prose=PROSE,full_report=sample_report(),bundle=opinions())
        self.assertEqual(output["original_model_event_count"],25)
        self.assertEqual(len(output["replacements"]),2)
        self.assertEqual(len(output["shadow_facet_proposals"]),3)
        self.assertEqual(output["replacements"][0]
                         ["proposed_replacement"]["kind"],"OBSERVE")
        self.assertEqual(output["replacements"][1]
                         ["proposed_replacement"]["kind"],"WRITE")
        self.assertEqual(output["replacements"][1]
                         ["proposed_replacement"]["entity_refs"],
                         ["mara","mara_notebook"])
        self.assertEqual(output["shadow_facet_proposals"][0]
                         ["old"],"UNKNOWN")
        self.assertEqual(output["shadow_facet_proposals"][0]
                         ["new"],"OPEN")
        self.assertEqual(output["shadow_facet_proposals"][1]
                         ["old"],"OPEN")
        self.assertEqual(output["shadow_facet_proposals"][1]
                         ["new"],"CLOSED")
        self.assertEqual(output["shadow_facet_proposals"][2]
                         ["operation"],"APPEND_VERBATIM")
        self.assertEqual(output["status"],"PROPOSED_REPAIR_ONLY_CANNOT_COMMIT")
        self.assertFalse(output["canonical_commit_authorized"])
        self.assertEqual(output["world_state_writes"],0)
        self.assertFalse(output["human_gold_qualified"])
        self.assertEqual(len(output["blockers"]),7)

    def test_model_opinion_without_exact_source_quote_is_blocked(self):
        bad=opinions()
        bad["task_002"]["bound_advisory"]["possible_source_evidence"][0]["quote"]=
            "invented notebook contents"
        with self.assertRaisesRegex(CoverageError,
                                    "V012_ADVICE_EVIDENCE_NOT_EXACT"):
            propose(prose=PROSE,full_report=sample_report(),bundle=bad)

    def test_only_expected_real_pinned_event_semantics_can_be_corrected(self):
        fake=sample_report()
        fake["candidate_events"][0]["kind"]="CLAIM_MENTION"
        with self.assertRaisesRegex(CoverageError,
                                    "V012_TARGET_ORIGINAL_EVENT_CHANGED"):
            propose(prose=PROSE,full_report=fake,bundle=opinions())

    def test_candidate_model_cannot_self_approve(self):
        fake=opinions()
        fake["task_001"]["canonical_commit_authorized"]=True
        with self.assertRaisesRegex(CoverageError,
                                    "V012_ADVICE_PROVENANCE_INVALID"):
            propose(prose=PROSE,full_report=sample_report(),bundle=fake)

    def test_wrong_fingerprint_or_tampered_scene_fails(self):
        with self.assertRaisesRegex(CoverageError,"V012_SOURCE_NOT_FROZEN"):
            propose(prose=PROSE+" changed",full_report=sample_report(),
                    bundle=opinions())
        fake=sample_report()
        fake["candidate_events"][0]["quote"]="wrong quote"
        with self.assertRaisesRegex(CoverageError,
                                    "V012_EVENT_EVIDENCE_TAMPERED"):
            propose(prose=PROSE,full_report=fake,bundle=opinions())

    def test_changed_independent_model_meaning_cannot_be_consensus(self):
        fake=opinions()
        fake["task_003"]["bound_advisory"]["effect_model_proposed"]="NONE"
        with self.assertRaisesRegex(CoverageError,
                                    "V012_ADVICE_SEMANTIC_MISMATCH"):
            validate_model_bundle(bundle=fake,prose=PROSE)

if __name__=="__main__":
    unittest.main()
