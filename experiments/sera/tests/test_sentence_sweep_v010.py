"""SERA v0.10 automatic extraction + repair regressions (offline/no model)."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.sentence_sweep_v010 import (
    SCHEMA, create_plan, bind_batch, aggregate, summarize_partial,
    prepare_probe_request, bind_probe_response,
)
from experiments.sera.mara_s1_v04_audit import PATH, EXPECTED_SHA
from experiments.sera.mara_s1_typed_live_v05 import REGISTRY, entry_state

LEXICON = json.loads((Path(__file__).resolve().parents[1] /
                      "fixtures/object_candidate_lexicon_v0.1.json")
                     .read_text(encoding="utf-8"))["candidates"]
MARA = json.loads(PATH.read_text(encoding="utf-8"))["prose"]


def mara_plan():
    known = entry_state()["entities"]
    registered = {k: v for k, v in REGISTRY.items() if k in known}
    return create_plan(
        prose=MARA, scene_key="hook_empty_platform", entry_revision=0,
        registry=registered, candidate_lexicon=LEXICON,
    )


def empty_raw(batch):
    return {
        "rows": [{
            "sentence_id": sid, "disposition": "NO_TRACKED_CHANGE",
            "reason": "Synthetic deliberately incomplete model fixture",
            "mentions": [], "events": [],
        } for sid in batch["sentence_ids"]
        ],
    }


def synthetic_complete_set(plan):
    return [bind_batch(plan=plan, batch_id=b["batch_id"],
                       raw=empty_raw(b), prose=MARA)
            for b in plan["batches"]]


class PlanV010Tests(unittest.TestCase):
    def test_mara_source_partition_28_sentences_7_batches_no_writer_leak(self):
        plan = mara_plan()
        self.assertEqual(plan["schema"], SCHEMA)
        self.assertEqual(plan["sentence_count"], 28)
        self.assertEqual(plan["source_prose_sha256"], EXPECTED_SHA)
        self.assertEqual(len(plan["batches"]), 7)
        self.assertFalse(plan["prior_writer_report_included"])
        self.assertFalse(plan["prior_analyst_events_included"])
        self.assertFalse(plan["canonical_commit_authorized"])
        ids = [sid for b in plan["batches"] for sid in b["sentence_ids"]]
        self.assertEqual(ids, [f"s{i:03}" for i in range(1, 29)])
        for b in plan["batches"]:
            self.assertLessEqual(len(b["sentence_ids"]), 4)
            self.assertEqual(b["response_format"], {"type": "json_object"})
            self.assertTrue(b["request_sha256"])
            self.assertEqual([x["role"] for x in b["messages"]],
                             ["system", "user"])
            for message in b["messages"]:
                self.assertNotIn("max_tokens", message)
                self.assertNotIn("max_completion_tokens", message)
                self.assertNotIn("max_output_tokens", message)
                self.assertNotIn("evt_s1_01", message["content"])
                self.assertNotIn("writer_report", message["content"])
        self.assertEqual(plan["model_output_token_limit"],
                         "NOT_SET_BY_APPLICATION")

    def test_exact_physical_action_and_claim_bind_to_own_source_sentence(self):
        plan = mara_plan()
        target = next(b for b in plan["batches"] if any(
            "closed the case" in row["quote"]
            for row in plan["source_sentences"]
            if row["id"] in b["sentence_ids"]
        ))
        raw = empty_raw(target)
        row = next(r for r in raw["rows"]
                   if "closed the case" in next(
                       s["quote"] for s in plan["source_sentences"]
                       if s["id"] == r["sentence_id"]))
        row["disposition"] = "STATE_EVENT"
        row["events"] = [{
            "kind": "CLOSE", "epistemic": "OBSERVED_ACTION",
            "effect": "OBJECT", "evidence_quote": "closed the case",
            "occurrence": 0, "entity_refs": ["vane_watch"],
            "reason": "Vane's pocket watch case physically closed",
        }]
        bound = bind_batch(
            plan=plan, batch_id=target["batch_id"], raw=raw, prose=MARA,
        )
        ev = next(r["events"][0] for r in bound["rows"] if r["events"])
        self.assertEqual(MARA[ev["start"]:ev["end"]], "closed the case")
        self.assertEqual(ev["epistemic"], "OBSERVED_ACTION")
        self.assertFalse(bound["canonical_commit_authorized"])

    def test_nonexistent_quote_and_wrong_sentence_fail_closed(self):
        plan = mara_plan()
        batch = plan["batches"][0]
        raw = empty_raw(batch)
        raw["rows"][0]["events"] = [{
            "kind": "MOVE", "epistemic": "OBSERVED_ACTION",
            "effect": "WORLD", "evidence_quote": "A train magically arrived.",
            "occurrence": 0, "entity_refs": ["train_41"],
            "reason": "Fabricated quote",
        }]
        with self.assertRaisesRegex(CoverageError,
                                    "SWEEP_QUOTE_NOT_IN_TARGET_SENTENCE"):
            bind_batch(plan=plan, batch_id=batch["batch_id"],
                       raw=raw, prose=MARA)

    def test_duplicate_or_missing_sentence_row_blocks_response(self):
        plan = mara_plan()
        batch = plan["batches"][0]
        raw = empty_raw(batch)
        raw["rows"].pop()
        with self.assertRaisesRegex(CoverageError,
                                    "SWEEP_SENTENCE_MISSING_OR_DUPLICATE"):
            bind_batch(plan=plan, batch_id=batch["batch_id"],
                       raw=raw, prose=MARA)
        raw = empty_raw(batch)
        raw["rows"][1]["sentence_id"] = raw["rows"][0]["sentence_id"]
        with self.assertRaisesRegex(CoverageError,
                                    "SWEEP_SENTENCE_MISSING_OR_DUPLICATE"):
            bind_batch(plan=plan, batch_id=batch["batch_id"],
                       raw=raw, prose=MARA)

    def test_wrong_source_hash_and_wrong_type_rejected(self):
        plan = mara_plan()
        batch = plan["batches"][0]
        raw = empty_raw(batch)
        with self.assertRaisesRegex(CoverageError, "SWEEP_PLAN_SOURCE_MISMATCH"):
            bind_batch(plan=plan, batch_id=batch["batch_id"],
                       raw=raw, prose=MARA+" altered")
        raw["rows"][0]["disposition"] = "VERIFIED_GOLD"
        with self.assertRaisesRegex(CoverageError, "SWEEP_ROW_SCHEMA_INVALID"):
            bind_batch(plan=plan, batch_id=batch["batch_id"],
                       raw=raw, prose=MARA)

    def test_multiple_identical_quotes_need_valid_zero_based_occurrence(self):
        prose = "Mara wrote wrote in her notebook."
        plan = create_plan(
            prose=prose, scene_key="synthetic", entry_revision=0,
            registry={"mara":["Mara"], "notebook":["notebook"]},
            candidate_lexicon={},
        )
        raw = empty_raw(plan["batches"][0])
        raw["rows"][0]["sentence_id"] = "s001"
        raw["rows"][0]["disposition"] = "STATE_EVENT"
        raw["rows"][0]["events"] = [{
            "kind":"WRITE", "epistemic":"OBSERVED_ACTION",
            "effect":"DOCUMENT", "evidence_quote":"wrote",
            "occurrence":1, "entity_refs":["notebook"],
            "reason":"Second explicit occurrence",
        }]
        bound = bind_batch(
            plan=plan, batch_id="batch_001", raw=raw, prose=prose,
        )
        e = bound["rows"][0]["events"][0]
        self.assertEqual(e["start"], prose.rindex("wrote"))
        self.assertEqual(e["quote"], "wrote")
        raw["rows"][0]["events"][0]["occurrence"] = 2
        with self.assertRaisesRegex(CoverageError,
                                    "SWEEP_QUOTE_NOT_IN_TARGET_SENTENCE"):
            bind_batch(plan=plan,batch_id="batch_001",raw=raw,prose=prose)


class AggregateAndRecoveryV010Tests(unittest.TestCase):
    def test_mara_28_rows_report_t2_bench_pencil_and_close_write_gaps(self):
        plan=mara_plan()
        output=aggregate(plan=plan,bound_batches=synthetic_complete_set(plan),
                         prose=MARA)
        self.assertEqual(output["status"],"HOLD_MODEL_SEMANTICS_UNVERIFIED")
        self.assertEqual(output["sentences_accounted_for"],28)
        self.assertEqual(output["batches_bound"],7)
        self.assertEqual(output["candidate_events"],[])
        self.assertTrue(any("candidate:bench" in x for x in
                            output["findings"]))
        self.assertTrue(any("candidate:pencil" in x for x in
                            output["findings"]))
        self.assertTrue(any("SWEEP_UNACCOUNTED_ACTION_CUE" in x and "closed"
                            in x for x in output["findings"]))
        self.assertTrue(any("SWEEP_UNACCOUNTED_ACTION_CUE" in x and "wrote"
                            in x for x in output["findings"]))
        self.assertTrue(any(x["kind"]=="ENTITY" and
                            x["candidate_ref_or_kind"]=="candidate:bench"
                            for x in output["targeted_probes"]))
        self.assertFalse(output["gold_reference_available"])
        self.assertFalse(output["canonical_commit_authorized"])
        self.assertEqual(output["world_state_writes"],0)

    def test_claim_with_report_event_never_canonizes_world(self):
        plan=mara_plan()
        raws=[empty_raw(b) for b in plan["batches"]]
        for batch,raw in zip(plan["batches"],raws):
            for row in raw["rows"]:
                sid = row["sentence_id"]
                sentence = next(s for s in plan["source_sentences"]
                                if s["id"] == sid)
                if "Arrival recorded: 02:10" in sentence["quote"]:
                    row["disposition"]="CLAIM_ONLY"
                    row["events"]=[{
                        "kind":"CLAIM_MENTION", "epistemic":"REPORTED_CLAIM",
                        "effect":"NONE", "evidence_quote":"Arrival recorded: 02:10",
                        "occurrence":0, "entity_refs":["archive_telegram"],
                        "reason":"Quote of archive data, not real train arrival",
                    }]
        bound=[bind_batch(plan=plan,batch_id=b["batch_id"],raw=raw,prose=MARA)
               for b,raw in zip(plan["batches"],raws)]
        out=aggregate(plan=plan,bound_batches=bound,prose=MARA)
        claim=next(x for x in out["candidate_events"]
                   if x["kind"]=="CLAIM_MENTION")
        self.assertEqual(claim["epistemic"],"REPORTED_CLAIM")
        self.assertEqual(claim["effect"],"NONE")
        self.assertTrue(any(x.startswith("SWEEP_DISPOSITION_EVENT_CONFLICT:")
                            for x in out["findings"]))
        self.assertFalse(out["canonical_commit_authorized"])

    def test_model_claim_becoming_objective_state_is_flagged(self):
        plan=mara_plan()
        raws=[empty_raw(b) for b in plan["batches"]]
        for batch, raw in zip(plan["batches"],raws):
            for row in raw["rows"]:
                sentence=next(s for s in plan["source_sentences"]
                              if s["id"]==row["sentence_id"])
                if "Arrival recorded: 02:10" in sentence["quote"]:
                    row["disposition"]="CLAIM_ONLY"
                    row["events"]=[{
                        "kind":"CHANGE_STATE","epistemic":"OBSERVED_ACTION",
                        "effect":"WORLD","evidence_quote":"Arrival recorded: 02:10",
                        "occurrence":0,"entity_refs":["train_41"],
                        "reason":"Synthetic model hallucination",
                    }]
        bound=[bind_batch(plan=plan,batch_id=b["batch_id"],raw=raw,prose=MARA)
               for b,raw in zip(plan["batches"],raws)]
        output=aggregate(plan=plan,bound_batches=bound,prose=MARA)
        self.assertTrue(any(x.startswith("SWEEP_CLAIM_PROMOTED_TO_WORLD:")
                            for x in output["findings"]))
        self.assertFalse(output["canonical_commit_authorized"])

    def test_missing_batch_makes_recoverable_hold_not_fake_pass(self):
        plan=mara_plan()
        partial=synthetic_complete_set(plan)[:-1]
        queue=summarize_partial(plan=plan,bound_batches=partial)
        self.assertEqual(queue["status"],"HOLD_INCOMPLETE_SOURCE")
        self.assertEqual(queue["pending_batch_ids"],["batch_007"])
        self.assertFalse(queue["auto_approve_completed_batches"])
        with self.assertRaisesRegex(CoverageError,
                                    "SWEEP_BATCH_COVERAGE_INCOMPLETE"):
            aggregate(plan=plan,bound_batches=partial,prose=MARA)

    def test_recovery_receipt_bound_to_original_request_hash(self):
        plan=mara_plan()
        partial=synthetic_complete_set(plan)[:-1]
        last=plan["batches"][-1]
        reason={
            "batch_id": last["batch_id"], "failure_code":"HTTP_400",
            "request_sha256": last["request_sha256"],
        }
        queue=summarize_partial(plan=plan,bound_batches=partial,
                                failure_receipts=[reason])
        self.assertEqual(queue["failure_receipts"],[reason])
        reason["request_sha256"]="forged"
        with self.assertRaisesRegex(CoverageError,
                                    "SWEEP_FAILURE_RECEIPT_INVALID"):
            summarize_partial(plan=plan,bound_batches=partial,
                              failure_receipts=[reason])

    def test_repeated_batch_cannot_override_first_independent_evidence(self):
        plan=mara_plan()
        reports=synthetic_complete_set(plan)
        with self.assertRaisesRegex(CoverageError,
                                    "SWEEP_AGGREGATE_BATCH_MISMATCH"):
            aggregate(plan=plan,bound_batches=reports+[reports[0]],prose=MARA)

    def test_targeted_probe_only_sees_source_and_cannot_self_approve(self):
        plan=mara_plan()
        report=aggregate(plan=plan,bound_batches=synthetic_complete_set(plan),
                         prose=MARA)
        probe=next(x for x in report["targeted_probes"]
                   if x["candidate_ref_or_kind"]=="candidate:bench")
        request=prepare_probe_request(plan=plan,probe=probe)
        self.assertEqual(request["response_format"],{"type":"json_object"})
        user=json.loads(request["messages"][1]["content"])
        self.assertEqual(user["sentence"],probe["target_source_sentence"])
        self.assertNotIn("first_model_answer",str(request))
        self.assertNotIn("max_tokens",str(request))
        source=next(s for s in plan["source_sentences"]
                    if s["id"]==probe["sentence_id"])
        result=bind_probe_response(
            plan=plan,probe=probe,request=request,
            raw={
                "verdict":"EVIDENCED","evidence_quote":"bench",
                "occurrence":0,"reason":"The bench is explicitly named",
            })
        self.assertEqual(MARA[result["exact_source_evidence"]["start"]:
                              result["exact_source_evidence"]["end"]],"bench")
        self.assertEqual(result["status"],"HOLD_SECOND_MODEL_NOT_AUTHORITY")
        self.assertFalse(result["canonical_commit_authorized"])
        with self.assertRaisesRegex(CoverageError,
                                    "SWEEP_QUOTE_NOT_IN_TARGET_SENTENCE"):
            bind_probe_response(plan=plan,probe=probe,request=request,raw={
                "verdict":"EVIDENCED","evidence_quote":"pink elephant",
                "occurrence":0,"reason":"Fabricated",
            })

if __name__ == "__main__":
    unittest.main()
