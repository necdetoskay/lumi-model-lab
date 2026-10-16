"""v0.44: fail-closed explanation contract, no fabricated real-model truth.

The synthetic report here tests shape/authority adversaries. Real receipt
provenance is qualified separately by v0.43 + the self-hosted v0.44 smoke.
"""
from copy import deepcopy
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.real_blind_benchmark_v040 import EXPECTED_SHA, MODELS, prepare
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.scene_trace_evidence_challenge_v044 import (
    narrow_policy, evaluate_predeclared_contrasts, build_challenges,
)


def simulated_v043_envelope():
    text=prepare()["prose"]
    parts=sentences(text)
    sample={f"s{i:03d}" for i in (1,2,3,4,21,22,23,24)}
    timeline=[]
    for j,part in enumerate(parts,1):
        sid=part["id"]
        models=[]
        for model in MODELS:
            if sid not in sample:
                status="NOT_EXTRACTED"
            elif model==MODELS[1] and sid in ("s021","s024"):
                status="QUARANTINED"
            else:
                status="SOURCE_BOUND"
            kinds=(
                ["CHANGE_STATE"] if sid=="s004" and model==MODELS[1] else
                ["MOVE"] if sid=="s022" and model==MODELS[0] else
                []
            )
            models.append({"model":model,"status":status,
                           "candidate_event_kinds":kinds})
        timeline.append({
            "sentence_id":sid,"narrative_ordinal":j,
            "quote":part["quote"],
            "source_sha256":EXPECTED_SHA,
            "world_state_write_authorized":False,
            "exact_story_second":None,
            "model_candidates":models,
        })
    risks=[]
    for sid,model,kind,code in [
        ("s004",MODELS[1],"CHANGE_STATE",
         "STATIC_WATCH_PREDICATE_MISREAD_AS_TRANSITION_RISK"),
        ("s022",MODELS[0],"MOVE",
         "PENCIL_MOTION_OBSERVED_BUT_CAUSAL_ACTOR_UNKNOWN"),
    ]:
        source=next(p for p in parts if p["id"]==sid)
        risks.append({
            "source_sentence_id":sid,"model":model,
            "risk_code":code,
            "source_quote":source["quote"],
            "source_start":source["start"],
            "source_end":source["end"],
            "semantic_truth_verified":False,
            "world_state_write_authorized":False,
        })
    report={
        "schema":"sera.scenetrace-dual-receipt-comparison.v0.43",
        "original_prose_sha256":EXPECTED_SHA,
        "source_sentence_count":28,
        "real_paid_runs":[38936451931,38938438488],
        "additional_paid_requests":0,
        "canonical_commit_authorized":False,
        "production_db_writes":0,
        "source_timeline":timeline,
        "source_bound_semantic_risk_flags":risks,
        "source_bound_event_candidate_disagreements":6,
    }
    return text,report


class SceneTraceEvidenceChallengeV044Tests(unittest.TestCase):
    def test_predeclared_static_and_motion_contrasts_without_semantic_pass(self):
        cases=evaluate_predeclared_contrasts()
        self.assertEqual(cases["case_count"],8)
        self.assertEqual(cases["pass_count"],8)
        self.assertFalse(cases["full_story_semantic_gold"])
        self.assertFalse(cases["nonmatching_policy_means_semantic_pass"])
        self.assertEqual(
            narrow_policy(
                prose_sentence="Vane watched the pencil move.",
                model_kind="MOVE",
            ),"BLOCK_UNATTRIBUTED_CAUSAL_AGENT",
        )
        self.assertEqual(
            narrow_policy(
                prose_sentence="Mara moved the pencil.",
                model_kind="MOVE",
            ),"NO_POLICY_BLOCK_SEMANTIC_UNVERIFIED",
        )

    def test_challenge_cards_are_source_bound_and_repair_is_only_recommended(self):
        text,report=simulated_v043_envelope()
        result=build_challenges(archived_comparison=report,
                                frozen_prose=text)
        self.assertEqual(result["model_response_challenge_count"],2)
        self.assertEqual(result["source_sentences_sampled_by_any_real_model"],8)
        self.assertEqual(result["source_sentences_not_sampled"],20)
        self.assertTrue(result["machine_action_recommendations_only"])
        self.assertFalse(result["repair_automatic_execution_qualified"])
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(result["mutation_proposals_previously_committed"],0)
        self.assertEqual(result["new_real_model_errors_proven"],0)
        self.assertFalse(result["independent_semantic_event_recall_proven"])
        self.assertEqual(result["additional_paid_model_requests"],0)
        self.assertEqual(result["production_db_writes"],0)
        for x in result["challenges"]:
            span=x["source_evidence_span"]
            self.assertEqual(text[span["start"]:span["end"]],
                             span["quote"])
            self.assertFalse(x["world_state_transition_authorized"])
            self.assertFalse(x["repair_was_executed"])
            self.assertTrue(x["missing_evidence"])

    def test_forged_source_span_is_rejected(self):
        text,report=simulated_v043_envelope()
        report["source_bound_semantic_risk_flags"][0]["source_start"]+=1
        with self.assertRaisesRegex(
            CoverageError,"SCENETRACE_V044_RISK_QUOTE_NOT_SOURCE_BOUND"
        ):
            build_challenges(archived_comparison=report,frozen_prose=text)

    def test_model_with_no_bound_candidate_cannot_inject_blocking_risk(self):
        text,report=simulated_v043_envelope()
        risk=report["source_bound_semantic_risk_flags"][0]
        report["source_timeline"][3]["model_candidates"][1][
            "candidate_event_kinds"
        ]=[]
        with self.assertRaisesRegex(
            CoverageError,"SCENETRACE_V044_RISK_EVENT_NOT_VERIFIED"
        ):
            build_challenges(archived_comparison=report,frozen_prose=text)

    def test_original_source_or_paid_receipts_cannot_be_swapped(self):
        text,report=simulated_v043_envelope()
        report["original_prose_sha256"]="0"*64
        with self.assertRaisesRegex(
            CoverageError,"SCENETRACE_V044_REAL_ARCHIVE_SCOPE_UNQUALIFIED"
        ):
            build_challenges(archived_comparison=report,frozen_prose=text)

    def test_no_commit_or_model_claims_even_if_report_was_modified(self):
        text,report=simulated_v043_envelope()
        report["source_timeline"][3]["world_state_write_authorized"]=True
        with self.assertRaisesRegex(
            CoverageError,"SCENETRACE_V044_SOURCE_PROJECTION_MISMATCH"
        ):
            build_challenges(archived_comparison=report,frozen_prose=text)

    def test_duplicate_risk_proposals_never_become_duplicate_challenges(self):
        text,report=simulated_v043_envelope()
        report["source_bound_semantic_risk_flags"][1]=deepcopy(
            report["source_bound_semantic_risk_flags"][0])
        with self.assertRaisesRegex(
            CoverageError,"SCENETRACE_V044_DUPLICATE_SAFETY_CHALLENGE"
        ):
            build_challenges(archived_comparison=report,frozen_prose=text)

    def test_quarantined_row_never_becomes_an_accepted_model_event(self):
        text,report=simulated_v043_envelope()
        report["source_timeline"][3]["model_candidates"][1][
            "status"
        ]="QUARANTINED"
        with self.assertRaisesRegex(
            CoverageError,"SCENETRACE_V044_RISK_EVENT_NOT_VERIFIED"
        ):
            build_challenges(archived_comparison=report,frozen_prose=text)


if __name__=="__main__":
    unittest.main()
