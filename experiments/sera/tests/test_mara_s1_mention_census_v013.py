"""SERA v0.13 entity-mention contract tests: no provider, no authority."""
from __future__ import annotations

from copy import deepcopy
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_mention_census_v013 import run
from experiments.sera.mara_s1_typed_live_v05 import entry_state
from experiments.sera.tests.test_sentence_sweep_v010 import (
    mara_plan,synthetic_complete_set,MARA,
)

def synthetic():
    plan=mara_plan()
    reports=synthetic_complete_set(plan)
    source={r["id"]:r for r in plan["source_sentences"]}
    def insert(sid,quote,ref,role):
        b=next(b for b in reports if sid in
               [r["sentence_id"] for r in b["rows"]])
        row=next(r for r in b["rows"] if r["sentence_id"]==sid)
        s=source[sid]
        idx=s["quote"].find(quote)
        if idx<0:raise RuntimeError(f"unknown fixture {sid}:{quote}")
        row["mentions"].append({
            "entity_ref":ref,"role":role,"raw_model_role":role,
            "role_binding":"EXACT",
            "quote":quote,"start":s["start"]+idx,
            "end":s["start"]+idx+len(quote),
        })
    for s in plan["source_sentences"]:
        if "bench" in s["quote"]:
            insert(s["id"],"bench","new:bench","PRESENT")
            break
    for s in plan["source_sentences"]:
        if "thumb" in s["quote"]:
            insert(s["id"],"thumb","new:vane_thumb","MENTIONED")
            break
    for s in plan["source_sentences"]:
        if "train" in s["quote"].lower():
            q="train"
            # Case-sensitive and exact source match.
            pos=s["quote"].lower().find(q)
            q=s["quote"][pos:pos+len(q)]
            insert(s["id"],q,"new:train_41","REPORTED_ONLY")
            break
    return plan,reports

class MentionCensusV013Tests(unittest.TestCase):
    def test_eventless_bench_anatomy_and_claim_topics_are_not_auto_created(self):
        p,sets=synthetic()
        result=run(prose=MARA,world=entry_state(),
                   plan=p,bound_batches=sets)
        self.assertEqual(result["source_sentence_count"],28)
        self.assertEqual(result["bound_source_batches"],7)
        self.assertEqual(result["total_source_bound_mentions"],3)
        self.assertIn("new:bench",result["unregistered_or_provisional_mentions"])
        self.assertIn("new:vane_thumb",result["anatomical_parts_not_inventory"])
        item={x["entity_ref"]:x for x in result["items"]}
        self.assertEqual(item["new:train_41"]["classification"],
                         "REPORTED_TOPIC_DO_NOT_CREATE_PHYSICAL_TRAIN")
        self.assertEqual(item["new:bench"]["classification"],
                         "PROVISIONAL_ENTITY_IDENTITY_NEEDS_REVIEW")
        self.assertFalse(item["new:bench"]["suggest_introduce_entity"])
        self.assertEqual(result["automatic_new_entities_created"],0)
        self.assertFalse(result["physical_train_arrival_authorized"])
        self.assertFalse(result["canonical_commit_authorized"])

    def test_missing_batch_or_repeated_batch_fails(self):
        p,sets=synthetic()
        with self.assertRaisesRegex(
            CoverageError,"V013_MENTIONS_PLAN_OR_SOURCE_INVALID"
        ):
            run(prose=MARA,world=entry_state(),plan=p,
                bound_batches=sets[:-1])
        wrong=deepcopy(sets)
        wrong[-1]=deepcopy(wrong[0])
        with self.assertRaisesRegex(
            CoverageError,"V013_MENTIONS_BATCH_NOT_SOURCE_BOUND"
        ):
            run(prose=MARA,world=entry_state(),plan=p,
                bound_batches=wrong)

    def test_wrong_source_span_fails_without_auto_fix(self):
        p,sets=synthetic()
        bad=deepcopy(sets)
        target=next(m for b in bad for r in b["rows"]
                    for m in r["mentions"])
        target["quote"]="invented physical arrival"
        with self.assertRaisesRegex(
            CoverageError,"V013_MENTION_SOURCE_EVIDENCE_INVALID"
        ):
            run(prose=MARA,world=entry_state(),plan=p,
                bound_batches=bad)

if __name__=="__main__":
    unittest.main()
