"""SceneTrace v0.42 sidecar: exact evidence, all source rows, no world writes."""
import unittest
from copy import deepcopy

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_typed_live_v05 import REGISTRY,entry_state
from experiments.sera.real_blind_benchmark_v040 import LEXICON
from experiments.sera.real_pencil_benchmark_v041 import prepare
from experiments.sera.scene_trace_shadow_v042 import build_trace,comparison
import json


def inputs():
    src=prepare()
    registry={k:v for k,v in REGISTRY.items() if
              k in entry_state()["entities"]}
    candidates=json.loads(LEXICON.read_text(encoding="utf-8"))["candidates"]
    return src,registry,candidates


def candidate_row(src):
    sentence=next(x for x in src["plan"]["source_sentences"]
                  if x["id"]==src["target_sentence_id"])
    part=sentence["quote"].index("pencil")
    at=sentence["start"]+part
    return {
        "sentence_id":sentence["id"],"source_spans_checked":True,
        "model_disposition":"AMBIGUOUS",
        "semantic_truth_verified":False,
        "candidate_mentions":[{
            "entity_ref":"candidate:pencil","start":at,
            "end":at+6,"quote":"pencil","role":"MENTIONED",
        }],
        "candidate_events":[],
    }


class SceneTraceShadowV042Tests(unittest.TestCase):
    def test_full_real_source_has_all_28_rows_unknown_clock_and_no_commit(self):
        src,registry,candidates=inputs()
        trace=build_trace(
            prose=src["prose"],scene_id="hook_empty_platform",
            registry=registry,candidate_lexicon=candidates,
            source_bound_rows=[candidate_row(src)],
        )
        self.assertEqual(trace["source_sentence_count"],28)
        self.assertEqual(trace["source_bound_model_sentence_count"],1)
        self.assertEqual(trace["source_only_model_unassessed_sentence_count"],27)
        self.assertFalse(trace["canonical_commit_authorized"])
        self.assertFalse(trace["semantic_completeness_proven"])
        self.assertEqual(trace["external_model_calls"],0)
        self.assertEqual(trace["newly_validated_state_changes"],0)
        self.assertTrue(all(r["narrative_ordinal"]==i+1 for i,r
                            in enumerate(trace["rows"])))
        self.assertTrue(all(r["exact_story_second"] is None and
                            r["story_time_window"] is None and
                            r["state_transition_authorized"] is False
                            for r in trace["rows"]))
        self.assertTrue(all(a["state_delta"] is None and
                            a["actor_id"] is None and
                            a["world_commit_authorized"] is False
                            for row in trace["rows"] for a in row["atoms"]))
        benchmark=comparison(
            trace,baseline_model_rows=1,baseline_quarantined_rows=0,
        )
        self.assertFalse(benchmark["extraction_recall_improvement_proven"])
        self.assertEqual(benchmark["cost_usd_incremental"],"0")

    def test_bench_static_watch_and_unknown_pencil_actor_diagnosed(self):
        src,registry,candidates=inputs()
        trace=build_trace(prose=src["prose"],scene_id="mara",
                          registry=registry,candidate_lexicon=candidates)
        bench=next(x for x in trace["rows"] if
                   "stood beside the bench" in x["quote"])
        self.assertTrue(any(a["ref"]=="candidate:bench"
                            for a in bench["atoms"]))
        watch=next(x for x in trace["rows"] if
                   "pocket watch open in his palm" in x["quote"])
        self.assertIn("STATIC_WATCH_DESCRIPTION_NOT_EVIDENCE_OF_OPEN_ACTION",
                      watch["risk_hints"])
        pencil=next(x for x in trace["rows"] if
                    "watched the pencil move" in x["quote"])
        self.assertIn("OBSERVED_MOTION_DOES_NOT_IDENTIFY_CAUSAL_ACTOR",
                      pencil["risk_hints"])
        self.assertTrue(any(a["ref"]=="candidate:pencil"
                            for a in pencil["atoms"]))
        self.assertIsNone(pencil["exact_story_second"])

    def test_reported_0210_is_not_claimed_action_time(self):
        src,reg,lex=inputs()
        trace=build_trace(prose=src["prose"],scene_id="mara",
                          registry=reg,candidate_lexicon=lex)
        refs=[a for x in trace["rows"] for a in x["atoms"]
              if a["kind"]=="TIME_EXPRESSION_MENTION" and "02:10" in a["quote"]]
        self.assertTrue(refs)
        self.assertTrue(all(a["reported_time_only"] for a in refs))
        self.assertTrue(all(x["exact_story_second"] is None for x in trace["rows"]))

    def test_source_quote_forgery_never_enters_sidecar(self):
        src,reg,lex=inputs()
        wrong=candidate_row(src)
        wrong["candidate_mentions"][0]["quote"]="someone else's pencil"
        with self.assertRaisesRegex(CoverageError,
                                    "SCENETRACE_SOURCE_SPAN_UNVERIFIED"):
            build_trace(prose=src["prose"],scene_id="mara",
                        registry=reg,candidate_lexicon=lex,
                        source_bound_rows=[wrong])

    def test_quarantine_cannot_be_mistaken_for_accepted_candidate(self):
        src,reg,lex=inputs()
        accepted=candidate_row(src)
        quarantine={
            "sentence_id":accepted["sentence_id"],
            "reason":"SWEEP_QUOTE_NOT_IN_TARGET_SENTENCE",
            "source_spans_checked":False,
            "automated_repair_not_possible_without_reextraction":True,
        }
        with self.assertRaisesRegex(CoverageError,
                                    "SCENETRACE_QUARANTINE_PROOF_INVALID"):
            build_trace(prose=src["prose"],scene_id="mara",
                        registry=reg,candidate_lexicon=lex,
                        source_bound_rows=[accepted],
                        quarantined_rows=[quarantine])

    def test_model_self_approval_never_passes_row_contract(self):
        src,reg,lex=inputs()
        forged=candidate_row(src)
        forged["canonical_commit_authorized"]=True
        with self.assertRaisesRegex(CoverageError,
                                    "SCENETRACE_UNQUALIFIED_SOURCE_BOUND_MODEL_ROW"):
            build_trace(prose=src["prose"],scene_id="mara",
                        registry=reg,candidate_lexicon=lex,
                        source_bound_rows=[forged])

    def test_model_evidence_has_one_exact_provenance_atom(self):
        src,reg,lex=inputs()
        proof=candidate_row(src)
        trace=build_trace(prose=src["prose"],scene_id="mara",
                          registry=reg,candidate_lexicon=lex,
                          source_bound_rows=[proof])
        sentence=next(x for x in trace["rows"] if
                      x["sentence_id"]==src["target_sentence_id"])
        atoms=[a for a in sentence["atoms"] if
               a["kind"]=="SOURCE_BOUND_MODEL_ENTITY_CANDIDATE"]
        self.assertEqual(len(atoms),1)
        self.assertEqual(atoms[0]["quote"],"pencil")
        self.assertEqual(atoms[0]["evidence_authority"],
                         "MODEL_SOURCE_SPAN_ONLY")
        self.assertFalse(atoms[0]["world_commit_authorized"])


if __name__=="__main__":
    unittest.main()
