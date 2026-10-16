"""SERA v0.11 targeted semantic risk tests, synthetic evidence only."""
from __future__ import annotations

from copy import deepcopy
import unittest

from experiments.sera.coverage import CoverageError,prose_hash
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.semantic_risks_v011 import (
    audit_risks,make_task_request,bind_task_response,
)

SOURCE=(
    "Vane stood with his pocket watch open in his palm. "
    "Vane closed the case. "
    "Mara opened her notebook and wrote: “Arrival recorded at 02:10.” "
    "She paused, then added, “Discrepancy unknown.” "
    "Mara turned to the clock."
)


def report():
    spans=sentences(SOURCE)
    def event(idx,kind,effect,quote,refs=()):
        sentence=spans[idx]
        loc=SOURCE.index(quote,sentence["start"],sentence["end"])
        return {
            "event_id":f"synthetic:e{idx+1}",
            "sentence_id":sentence["id"],
            "kind":kind,
            "epistemic":"OBSERVED_ACTION",
            "effect":effect,
            "start":loc,"end":loc+len(quote),
            "quote":quote,"entity_refs":list(refs),
            "reason":"Synthetic deliberately disputed event",
        }
    e_close=event(1,"CLOSE","OBJECT","closed",("new:watch_case",))
    e_write=event(2,"WRITE","DOCUMENT","wrote",("mara_notebook",))
    e_add=event(3,"COMMUNICATE","NONE","added",("mara",))
    e_move=event(4,"MOVE","CHARACTER_KNOWLEDGE","turned",("mara",))
    return {
        "schema":"sera.blind-sweep-bound.v0.10",
        "source_prose_sha256":prose_hash(SOURCE),
        "sentences_accounted_for":len(spans),
        "status":"HOLD_MODEL_SEMANTICS_UNVERIFIED",
        "canonical_commit_authorized":False,
        "world_state_writes":0,
        "candidate_events":[e_close,e_write,e_add,e_move],
        "targeted_probes":[
            {
                "sentence_id":spans[1]["id"],
                "kind":"ACTION","probe_id":"probe_001",
                "exact_source_quote":"closed the case",
                "candidate_ref_or_kind":"PHYSICAL_CHANGE",
                "target_source_sentence":spans[1]["quote"],
                "question":"Confirm physical case closure",
                "model_cannot_self_approve":True,
            },
            {
                "sentence_id":spans[2]["id"],
                "kind":"ACTION","probe_id":"probe_002",
                "exact_source_quote":"recorded",
                "candidate_ref_or_kind":"DOCUMENT_CHANGE",
                "target_source_sentence":spans[2]["quote"],
                "question":"Is quoted arrival record an action?",
                "model_cannot_self_approve":True,
            },
        ],
    }


class SemanticRiskV011Tests(unittest.TestCase):
    def test_synthetic_context_finds_real_risks_not_lexical_false_probes(self):
        out=audit_risks(prose=SOURCE,report=report())
        findings=out["findings"]
        self.assertTrue(any(x.startswith("DOCUMENT_APPEND_MISREAD_AS_SPEECH")
                            for x in findings))
        self.assertTrue(any(x.startswith("MOVE_KIND_EFFECT_MISMATCH")
                            for x in findings))
        self.assertTrue(any(x.startswith("OPENABLE_BEFORE_CLOSE_NEEDS_TYPED_ASPECT")
                            for x in findings))
        self.assertTrue(any(x.startswith("LEXICAL_CUE_EVENT_OVERLAP_ALREADY_FOUND")
                            for x in findings))
        self.assertTrue(any(x.startswith("ATTRIBUTED_DOCUMENT_TEXT_CUE")
                            for x in findings))
        self.assertEqual(out["targeted_task_count"],3)
        self.assertEqual(out["automatic_state_writes"],0)
        self.assertFalse(out["canonical_commit_authorized"])

    def test_targeted_probe_uses_raw_source_not_previous_model_diagnosis(self):
        a=audit_risks(prose=SOURCE,report=report())
        task=next(x for x in a["targeted_tasks"]
                  if x["finding_code"].startswith("DOCUMENT_APPEND_MISREAD"))
        prompt=make_task_request(audit=a,task_id=task["task_id"])
        self.assertEqual(prompt["response_format"],{"type":"json_object"})
        self.assertEqual(prompt["model_output_token_limit"],
                         "NOT_SET_BY_APPLICATION")
        self.assertNotIn("max_tokens",str(prompt))
        self.assertNotIn("previous_model_response",str(prompt))
        self.assertNotIn("model previously said",str(prompt))
        self.assertEqual(len(task["exact_source_context"]),4)
        sample=bind_task_response(audit=a,request=prompt,raw={
            "verdict":"DOCUMENT_WRITE",
            "operation_kind":"WRITE",
            "effect":"DOCUMENT",
            "evidence_quote":"added",
            "reason":"The notebook context makes an additional written line plausible",
        })
        self.assertFalse(sample["canonical_commit_authorized"])
        self.assertEqual(sample["status"],"HOLD_MODEL_RESPONSE_NOT_AUTHORITY")
        self.assertEqual(sample["possible_source_evidence"][0]["quote"],"added")

    def test_model_cannot_invent_quote_or_authorize_world(self):
        a=audit_risks(prose=SOURCE,report=report())
        task=a["targeted_tasks"][0]
        prompt=make_task_request(audit=a,task_id=task["task_id"])
        with self.assertRaisesRegex(CoverageError,
                                    "SEMANTIC_TASK_EVIDENCE_NOT_IN_SOURCE"):
            bind_task_response(audit=a,request=prompt,raw={
                "verdict":"ACTION",
                "operation_kind":"OPEN",
                "effect":"WORLD",
                "evidence_quote":"train 41 physically arrived",
                "reason":"Fabricated",
            })
        forged=deepcopy(prompt)
        forged["request_sha256"]="forged"
        with self.assertRaisesRegex(CoverageError,
                                    "SEMANTIC_TASK_REQUEST_TAMPERED"):
            bind_task_response(audit=a,request=forged,raw={
                "verdict":"UNCERTAIN",
                "operation_kind":"NONE",
                "effect":"UNKNOWN",
                "evidence_quote":"Vane",
                "reason":"Unknown",
            })

    def test_cannot_promote_claim_to_physical_event_without_review(self):
        original=report()
        s=sentences(SOURCE)[2]
        start=SOURCE.index("Arrival recorded",s["start"],s["end"])
        original["candidate_events"].append({
            "event_id":"e_fake_arrival",
            "sentence_id":s["id"],
            "kind":"CLAIM_MENTION",
            "epistemic":"REPORTED_CLAIM",
            "effect":"WORLD",
            "start":start,"end":start+len("Arrival recorded"),
            "quote":"Arrival recorded",
            "entity_refs":["new:train"],
            "reason":"Synthetic wrong world promotion",
        })
        risk=audit_risks(prose=SOURCE,report=original)
        self.assertTrue(any(x.startswith("REPORTED_CLAIM_PHYSICAL_PROMOTION")
                            for x in risk["findings"]))

    def test_incorrect_source_and_forged_model_evidence_rejected(self):
        original=report()
        with self.assertRaisesRegex(CoverageError,
                                    "SEMANTIC_RISK_SOURCE_OR_AUTHORITY_INVALID"):
            audit_risks(prose=SOURCE+" something",report=original)
        original["candidate_events"][0]["quote"]="not the source"
        with self.assertRaisesRegex(CoverageError,
                                    "SEMANTIC_RISK_EVENT_EVIDENCE_INVALID"):
            audit_risks(prose=SOURCE,report=original)


if __name__=="__main__":
    unittest.main()
