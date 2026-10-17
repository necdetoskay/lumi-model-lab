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

from experiments.sera.artifact_scene_checker_v021 import create_checker
from experiments.sera.coverage import prose_hash
from experiments.sera.fresh_scene_evidence_worker_v022 import create_preparer
from experiments.sera.mara_scene_capabilities_v054 import registered_mara_facets
from experiments.sera.mara_s1_typed_live_v05 import entry_state,REGISTRY
from experiments.sera.real_blind_benchmark_v040 import prepare,LEXICON,EXPECTED_SHA
from experiments.sera.test_mara_28_mechanical_source_control_v052 import simulate_blind_coverage
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
