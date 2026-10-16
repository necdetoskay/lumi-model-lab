"""v0.41.2 real source-bound row salvage must never fake full coverage."""
import unittest
from experiments.sera.real_pencil_benchmark_v041 import prepare
from experiments.sera.real_pencil_partial_rows_v0412 import isolate_rows
from experiments.sera.coverage import CoverageError


class RealPencilPartialRowsV0412Tests(unittest.TestCase):
    def test_good_pencil_row_survives_unrelated_bad_quote(self):
        plan=prepare()
        expected=plan["batch"]["sentence_ids"]
        rows=[{"sentence_id":sid,"disposition":"AMBIGUOUS",
               "reason":"synthetic bounded parser test","mentions":[],"events":[]}
              for sid in expected]
        target=expected.index(plan["target_sentence_id"])
        rows[target]={
            "sentence_id":plan["target_sentence_id"],
            "disposition":"STATE_EVENT",
            "reason":"model candidate not verified",
            "mentions":[{
                "entity_ref":"new:pencil","role":"PRESENT",
                "evidence_quote":"pencil","occurrence":0,
            }],
            "events":[{
                "kind":"OBSERVE","epistemic":"OBSERVED_ACTION",
                "effect":"NONE",
                "evidence_quote":"watched the pencil move",
                "occurrence":0,
                "entity_refs":["new:pencil"],
                "reason":"motion observed, mover unknown",
            }],
        }
        other=0 if target!=0 else 1
        rows[other]["mentions"]=[{
            "entity_ref":"new:forged",
            "role":"MENTIONED","evidence_quote":"not in source ever",
            "occurrence":0,
        }]
        good,bad=isolate_rows(plan=plan,parsed={"rows":rows},
                              prose=plan["prose"])
        self.assertEqual(len(bad),1)
        self.assertEqual(bad[0]["sentence_id"],expected[other])
        targetrow=next(row for row in good if
                       row["sentence_id"]==plan["target_sentence_id"])
        self.assertEqual(targetrow["candidate_mentions"][0]["entity_ref"],
                         "new:pencil")
        self.assertEqual(targetrow["candidate_events"][0]["kind"],"OBSERVE")
        self.assertFalse(targetrow["semantic_truth_verified"])

    def test_missing_model_row_cannot_be_silently_synthesized(self):
        plan=prepare()
        with self.assertRaisesRegex(CoverageError,
                                    "V0412_SOURCE_ROWS_ID_OR_COUNT_INVALID"):
            isolate_rows(plan=plan,parsed={"rows":[]},prose=plan["prose"])


if __name__=="__main__":
    unittest.main()
