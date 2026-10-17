"""Mara 28-sentence FULL source-sweep mechanical control (NOT an LLM).

Synthetic test-side rows are generated from the immutable original source
scanner rather than handwritten gold events. They prove all 7 four-sentence
batch contracts and exact source cues can be accounted for without alias
loss, not that 28-sentence semantics or Writer/v0.23 qualification succeeded.
Every proposed event is UNCERTAIN and must remain NONCANONICAL.
"""
from __future__ import annotations

from copy import deepcopy
import re
import unittest

from experiments.sera.coverage import prose_hash
from experiments.sera.real_blind_benchmark_v040 import prepare,EXPECTED_SHA
from experiments.sera.sentence_sweep_v010 import bind_batch,aggregate


def _occurrence(source,needle,start):
    positions=[x.start() for x in re.finditer(re.escape(needle),source)]
    return positions.index(start)


def simulate_blind_coverage(plan,prose):
    """Mechanical SOURCE-driven test double; never used as actual extraction."""
    source={s["id"]:s for s in plan["source_sentences"]}
    scan=plan["source_scan"]
    cues={r["sentence_id"]:r for r in scan["sentence_cues"]}
    hints={}
    for h in scan["hints"]:
        hints.setdefault(h["sentence_id"],[]).append(h)
    output={}
    for batch in plan["batches"]:
        rows=[]
        for sid in batch["sentence_ids"]:
            s=source[sid]
            mentions=[]
            for h in hints.get(sid,[]):
                start=h["start"]-s["start"]
                mentions.append({
                    "entity_ref":h["ref"],
                    "role":"MENTIONED",
                    "evidence_quote":h["quote"],
                    "occurrence":_occurrence(s["quote"],h["quote"],start),
                })
            events=[]
            for cue in cues[sid]["cues"]:
                if cue["family"] not in ("PHYSICAL_CHANGE","DOCUMENT_CHANGE"):
                    continue
                start=cue["start"]-s["start"]
                word=cue["quote"].casefold()
                kind=("CLOSE" if word.startswith(("closed","shut")) else
                      "OPEN" if word.startswith("opened") else
                      "WRITE" if cue["family"]=="DOCUMENT_CHANGE" else
                      "CHANGE_STATE")
                events.append({
                    "kind":kind,"epistemic":"UNCERTAIN",
                    "effect":"DOCUMENT" if cue["family"]=="DOCUMENT_CHANGE"
                             else "OBJECT",
                    "evidence_quote":cue["quote"],
                    "occurrence":_occurrence(s["quote"],cue["quote"],start),
                    "entity_refs":[],
                    "reason":"SOURCE_LEXICAL_CUE_ONLY_NOT_A_MODEL_FACT",
                })
            rows.append({
                "sentence_id":sid,
                "disposition":"STATE_EVENT" if events else
                              "CLAIM_ONLY" if hints.get(sid) or
                              cues[sid]["cues"] else "TEXTURE",
                "reason":"AUTOMATED_MECHANICAL_SOURCE_COVERAGE_ONLY",
                "mentions":mentions,"events":events,
            })
        output[batch["batch_id"]]={"rows":rows}
    return output


def bind_all(plan,prose,raw):
    return aggregate(plan=plan,prose=prose,bound_batches=[
        bind_batch(plan=plan,batch_id=b["batch_id"],
                   raw=raw[b["batch_id"]],prose=prose)
        for b in plan["batches"]
    ])


class MaraFull28MechanicalCoverage(unittest.TestCase):
    def setUp(self):
        source=prepare()
        self.plan=source["plan"]
        self.prose=source["prose"]
        self.raw=simulate_blind_coverage(self.plan,self.prose)

    def test_all_28_source_sentences_cues_and_lexical_entities_are_bound(self):
        self.assertEqual(prose_hash(self.prose),EXPECTED_SHA)
        self.assertEqual(len(self.plan["source_sentences"]),28)
        self.assertEqual(len(self.plan["batches"]),7)
        report=bind_all(self.plan,self.prose,self.raw)
        self.assertEqual(report["sentences_accounted_for"],28)
        self.assertEqual(report["batches_bound"],7)
        self.assertFalse(any(f.startswith((
            "SWEEP_MISSING_ENTITY_HINT",
            "SWEEP_UNACCOUNTED_ACTION_CUE",
            "SWEEP_EXPECTED_EVENT_NOT_EXTRACTED",
        )) for f in report["findings"]),report["findings"])
        self.assertGreater(len(report["candidate_events"]),0)
        self.assertTrue(all(e["epistemic"]=="UNCERTAIN"
                            for e in report["candidate_events"]))
        self.assertEqual(report["status"],"HOLD_MODEL_SEMANTICS_UNVERIFIED")
        self.assertFalse(report["semantic_recall_proven"])
        self.assertFalse(report["canonical_commit_authorized"])
        self.assertEqual(report["world_state_writes"],0)
        self.assertEqual(report,bind_all(
            self.plan,self.prose,simulate_blind_coverage(self.plan,self.prose)))

    def test_one_broad_write_cannot_hide_notebook_open_action(self):
        broken=deepcopy(self.raw)
        target=next(s for s in self.plan["source_sentences"]
                    if "Mara opened her notebook and wrote" in s["quote"])
        for batch in self.plan["batches"]:
            row=next((r for r in broken[batch["batch_id"]]["rows"]
                      if r["sentence_id"]==target["id"]),None)
            if row is None:
                continue
            row["events"]=[{
                "kind":"WRITE","epistemic":"UNCERTAIN",
                "effect":"DOCUMENT","evidence_quote":target["quote"],
                "occurrence":0,"entity_refs":[],
                "reason":"ADVERSARIAL_ONE_EVENT_SWALLOWS_OPEN_AND_WRITE",
            }]
            row["disposition"]="STATE_EVENT"
            break
        output=bind_all(self.plan,self.prose,broken)
        self.assertEqual(output["sentences_accounted_for"],28)
        self.assertTrue(any(f.startswith(
            "SWEEP_COMPOUND_OPEN_WRITE_COLLAPSED:"
        ) for f in output["findings"]),output["findings"])
        self.assertTrue(output["targeted_probes"])
        self.assertFalse(output["semantic_recall_proven"])
        self.assertFalse(output["canonical_commit_authorized"])

    def test_omitting_source_cued_physical_change_blocks_coverage(self):
        broken=deepcopy(self.raw)
        source_cues={r["sentence_id"]:r for r in self.plan["source_scan"]["sentence_cues"]}
        affected=None
        for batch in self.plan["batches"]:
            for row in broken[batch["batch_id"]]["rows"]:
                if any(c["family"]=="PHYSICAL_CHANGE"
                       for c in source_cues[row["sentence_id"]]["cues"]):
                    affected=row["sentence_id"]
                    row["events"]=[]
                    row["disposition"]="NO_TRACKED_CHANGE"
                    break
            if affected:break
        self.assertIsNotNone(affected)
        out=bind_all(self.plan,self.prose,broken)
        self.assertIn("SWEEP_UNACCOUNTED_ACTION_CUE", "\n".join(out["findings"]))
        self.assertFalse(out["semantic_recall_proven"])
        self.assertFalse(out["canonical_commit_authorized"])


if __name__=="__main__":
    unittest.main()
