"""Frozen original Mara 28 through ACTUAL v0.22 evidence worker (OFFLINE).

Scripted model replies derive *only* from the existing lexical source scanner,
never from 9 hand-annotated analyst "gold" events or a successful model run.
This is a deliberately conservative diagnostics/control run; all lexical
actions are UNCERTAIN. A noncanonical HOLD is correct, never a success claim.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from experiments.sera.artifact_scene_checker_v021 import create_checker
from experiments.sera.coverage import prose_hash
from experiments.sera.fresh_scene_evidence_worker_v022 import (
    create_preparer,_deterministic_physical_source_focus,
    _typed_only_coverage_retry_request,
    _check_critical_coverage,
    _missing_critical_typed_sentence_ids,
)
from experiments.sera.coverage import CoverageError
from experiments.sera.mara_scene_capabilities_v054 import registered_mara_facets
from experiments.sera.mara_s1_typed_live_v05 import entry_state,REGISTRY
from experiments.sera.real_blind_benchmark_v040 import prepare,LEXICON,EXPECTED_SHA
from experiments.sera.test_mara_28_mechanical_source_control_v052 import (
    simulate_blind_coverage, bind_all,
)
from experiments.sera.sentence_ledger_v06 import sentences


class FrozenMaraRealWorkerDiagnostic(unittest.TestCase):
    def setUp(self):
        src=prepare()
        self.prose=src["prose"]
        self.plan=src["plan"]
        self.world=entry_state()
        self.responses=simulate_blind_coverage(self.plan,self.prose)
        self.calls=[]
        self.by_sentence_batch={
            tuple(batch["sentence_ids"]):batch["batch_id"]
            for batch in self.plan["batches"]
        }

    def scripted(self,*,key,model,prepared):
        request=prepared["request"]
        data=json.loads(request["messages"][-1]["content"])
        self.calls.append((model,data))
        self.assertFalse(any(x in request for x in (
            "max_tokens","max_completion_tokens","max_output_tokens",
            "max_new_tokens")))
        if "target_sentences" in data:
            ids=tuple(s["id"] for s in data["target_sentences"])
            batch_id=self.by_sentence_batch[ids]
            response=self.responses[batch_id]
        elif "exact_chronological_sentences" in data:
            excerpt=data["exact_chronological_sentences"][-1]["quote"]
            response={
                "verdict":"UNCERTAIN","operation_kind":"NONE",
                "effect":"UNKNOWN","evidence_quote":excerpt[:12],
                "reason":"scripted lexical control is not independent semantics",
            }
        elif "original_prose" in data:
            self.assertEqual(prose_hash(data["original_prose"]),EXPECTED_SHA)
            self.assertEqual(data["registered_roles"],
                             registered_mara_facets(self.world))
            response={"typed_candidates":[]}
        else:
            raise AssertionError("unexpected scripted control stage")
        return {
            "error":None,
            "raw":{
                "id":"mara-28-source-control-"+str(len(self.calls)),
                "model":model,
                "usage":{"cost":"0.001"},
                "choices":[{
                    "finish_reason":"stop",
                    "message":{"content":json.dumps(response,ensure_ascii=False)},
                }],
            },
        }

    def worker(self,root,provider):
        aliases={k:v for k,v in REGISTRY.items() if k in self.world["entities"]}
        lexicon=json.loads(LEXICON.read_text(encoding="utf-8"))["candidates"]
        return create_preparer(
            evidence_root=root/"evidence",work_root=root/"jobs",
            scene_key="mara-s1-full-28-lexical-diagnostic",
            registry=aliases,candidate_lexicon=lexicon,
            typed_registry=registered_mara_facets(self.world),
            api_key="SCRIPTED_ONLY_NO_REAL_PROVIDER",
            extraction_model="synthetic/mara-source-batches",
            semantic_model="synthetic/mara-independent-semantics",
            typed_model="synthetic/mara-typed-facets",
            provider_call=provider,max_source_repair_attempts=1,
            max_model_requests=28,
            observed_spend_guard_usd="0.30",
            typed_batch_recovery=True,
        )

    def test_real_28_worker_uses_all_seven_batches_and_remains_honest(self):
        self.assertEqual(prose_hash(self.prose),EXPECTED_SHA)
        self.assertEqual(len(sentences(self.prose)),28)
        with TemporaryDirectory() as directory:
            root=Path(directory)
            worker=self.worker(root,self.scripted)
            output=worker(prose=self.prose,world=self.world)
            batch_sets=[
                tuple(s["id"] for s in data["target_sentences"])
                for _,data in self.calls if "target_sentences" in data
            ]
            self.assertEqual(set(batch_sets),set(self.by_sentence_batch))
            self.assertGreaterEqual(len(batch_sets),7)
            # All seven source extraction batches are read; typed recovery
            # asks ONLY windows selected by missing critical source events.
            # This is mechanical source routing, never a Mara gold answer.
            report=bind_all(self.plan,self.prose,self.responses)
            gaps=_missing_critical_typed_sentence_ids(report,[])
            selected=[b for b in self.plan["batches"]
                      if gaps.intersection(b["sentence_ids"])]
            typed_packets = [payload for _, payload in self.calls
                             if "original_prose" in payload]
            self.assertEqual(len(typed_packets),2+len(selected))
            self.assertLessEqual(len(selected),7)
            self.assertTrue(all(prose_hash(p["original_prose"])==EXPECTED_SHA
                                for p in typed_packets))
            self.assertEqual(output["status"],"FAILED_SAFE_FINAL",
                             "uncertain scanner evidence must never be promoted")
            self.assertFalse(output["canonical_commit_authorized"])
            self.assertEqual(output["world_db_writes"],0)
            self.assertFalse(output["requires_manual_intervention"])
            self.assertEqual(output["prose_sha256"],EXPECTED_SHA)
            print("MARA_28_REAL_V022_STAGE_DIAGNOSTIC first_blocker="+
                  str(output["failure_code"])+
                  " requests="+str(len(self.calls))+
                  " source_batches="+str(len(set(batch_sets))))
            before=len(self.calls)
            replay=self.worker(root,lambda **_:self.fail(
                "finished diagnostic must never re-send billable requests"))(
                    prose=self.prose,world=self.world)
            self.assertEqual(output,replay)
            self.assertEqual(before,len(self.calls))

    def test_public_frozen_mara_offline_entry_is_not_empty_facets(self):
        from experiments.sera.scene_qualified_model_lane_v052 import frozen_mara_offline
        stub={
            "source_sha256":EXPECTED_SHA,"source_sentence_count":28,
            "provider_is_real":False,"status":"FAILED_SAFE_FINAL",
            "canonical_commit_authorized":False,"production_db_writes":0,
        }
        # Contract-only spy: it must NOT fabricate a full scene PASS.
        with patch("experiments.sera.scene_qualified_model_lane_v052.run_offline_lane",
                   return_value=stub) as runner:
            output=frozen_mara_offline(
                output_root="/unwritten-mara-test",
                provider_call=lambda **_:self.fail("No network"),
                models={})
        self.assertEqual(output["status"],"FAILED_SAFE_FINAL")
        opts=runner.call_args.kwargs
        self.assertEqual(opts["typed_registry"],
                         registered_mara_facets(self.world))
        self.assertEqual(opts["max_source_repair_attempts"],1)
        self.assertIs(opts["typed_batch_recovery"],True)
        self.assertEqual(opts["prose"],self.prose)
        self.assertEqual(opts["world"],self.world)

    def test_typed_retry_focus_is_only_exact_original_mara_sentences(self):
        source_focus=_deterministic_physical_source_focus(self.plan)
        self.assertGreaterEqual(len(source_focus),2)
        quotes=[row["source_quote"] for row in source_focus]
        self.assertTrue(any("Vane closed the case" in q for q in quotes))
        self.assertTrue(any("Mara opened her notebook" in q for q in quotes))
        source_rows={s["id"]:s["quote"] for s in self.plan["source_sentences"]}
        self.assertTrue(all(source_rows[r["sentence_id"]]==r["source_quote"]
                            for r in source_focus))
        original={
            "messages":[
                {"role":"system","content":"Independent synthetic typed test"},
                {"role":"user","content":json.dumps({
                    "original_prose":self.prose,
                    "registered_roles":registered_mara_facets(self.world)})},
            ],
            "response_format":{"type":"json_object"},
        }
        amended=_typed_only_coverage_retry_request(
            original=original,attempt=1,source_focus=source_focus)
        prompt=amended["messages"][0]["content"]
        self.assertIn("LEXICAL SOURCE ATTENTION ONLY",prompt)
        self.assertIn("Mara opened her notebook",prompt)
        self.assertIn("Vane closed the case",prompt)
        self.assertNotIn("evt_s1_01",prompt)
        self.assertNotIn("typed_world_event",prompt)
        self.assertEqual(original["messages"][1],amended["messages"][1])
        self.assertFalse(any(k in amended for k in (
            "max_tokens","max_completion_tokens","max_output_tokens")))
        contaminated=[dict(source_focus[0],source_quote="model fabricated movement")]
        with self.assertRaisesRegex(
                CoverageError,"V022_TYPED_FOCUS_NOT_VERBATIM_SOURCE"):
            _typed_only_coverage_retry_request(
                original=original,attempt=1,source_focus=contaminated)

    def test_source_stated_open_cannot_be_covered_by_state_observation(self):
        # Mechanical source provenance only, not a prepared model answer.
        unit=next(x for x in self.plan["source_sentences"]
                  if "Mara opened her notebook" in x["quote"])
        offset=self.prose.index("Mara opened her notebook")
        quote="Mara opened her notebook"
        report={
            "candidate_events":[{
                "sentence_id":unit["id"],"kind":"OPEN","effect":"OBJECT",
                "start":offset,"end":offset+len(quote),"quote":quote,
            }],
            "findings":[],
        }
        passive=[{
            "type":"OBSERVE_OPENABLE","sentence_id":unit["id"],
            "evidence":{"start":offset,"end":offset+len(quote),
                        "quote":quote},
        }]
        with self.assertRaisesRegex(
            CoverageError,"V022_CRITICAL_TYPED_EVENT_NOT_ACCOUNTED"):
            _check_critical_coverage(report,passive)
        transition=[dict(passive[0],type="SET_OPENABLE",
                         payload={"expected":"UNKNOWN","next":"OPEN"})]
        _check_critical_coverage(report,transition)

    def test_no_analyst_gold_or_manual_scene_edits_enter_requests(self):
        with TemporaryDirectory() as directory:
            result=self.worker(Path(directory),self.scripted)(
                prose=self.prose,world=self.world)
        self.assertEqual(result["status"],"FAILED_SAFE_FINAL")
        for _,packet in self.calls:
            forbidden=("evt_s1_01","analyst_curated","state_effects",
                       "typed_world_event","prior_analyst_events")
            wire=json.dumps(packet,ensure_ascii=False).casefold()
            for term in forbidden[:4]:
                self.assertNotIn(term,wire)
        self.assertFalse(result["canonical_commit_authorized"])


if __name__=="__main__":
    unittest.main()
