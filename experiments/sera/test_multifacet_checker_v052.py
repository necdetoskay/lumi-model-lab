"""Real v0.22 → v0.21 → v0.54 → v0.23 wiring with overlapping object capabilities.

Only scripted provider envelopes; test fixtures are NOT model quality evidence.
The actual original 28-sentence Mara still needs independent model semantics.
"""
from __future__ import annotations
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.artifact_scene_checker_v021 import create_checker
from experiments.sera.coverage import prose_hash
from experiments.sera.fresh_scene_evidence_worker_v022 import create_preparer
from experiments.sera.tests.test_fresh_scene_evidence_worker_v022 import (
    SOURCE_2,entry,fake_model,EXTRACT,SEMANTIC,TYPED,
)


class MultifacetCheckerWiringV052(unittest.TestCase):
    def worker(self,root,provider):
        return create_preparer(
            evidence_root=root/"evidence",work_root=root/"work",
            scene_key="multifacet-independent-two-sentence-control",
            registry={"ari":["Ari"],"box":["box"]},candidate_lexicon={},
            typed_registry={"openables":["box"],"documents":["box"]},
            api_key="SCRIPTED_OFFLINE_ONLY",extraction_model=EXTRACT,
            semantic_model=SEMANTIC,typed_model=TYPED,
            provider_call=provider,max_model_requests=15,
            observed_spend_guard_usd="0.30",
        )

    def source_model(self,*,omit_actor=False):
        calls=[]
        fake=fake_model(calls)
        def provider(*,key,model,prepared):
            response=fake(key=key,model=model,prepared=prepared)
            req=json.loads(prepared["request"]["messages"][-1]["content"])
            if model==EXTRACT and "target_sentences" in req:
                packet=json.loads(response["raw"]["choices"][0]["message"]["content"])
                for row in packet["rows"]:
                    for event in row["events"]:
                        if not omit_actor:
                            event["entity_refs"]=["ari","box"]
                response["raw"]["choices"][0]["message"]["content"]=json.dumps(packet)
            return response
        return provider,calls

    def test_shared_document_openable_object_passes_actual_full_checker(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            provider,calls=self.source_model()
            preparer=self.worker(root,provider)
            evidence=preparer(prose=SOURCE_2,world=entry())
            self.assertEqual(evidence["status"],"EVIDENCE_READY_NONCANONICAL",
                             evidence)
            report=create_checker(
                evidence_root=root/"evidence",full_qualification=True)(
                    prose=SOURCE_2,world=entry())
            self.assertEqual(report["typed"]["status"],
                             "TYPED_MULTIFACET_SIMULATED_NONCANONICAL")
            self.assertEqual(report["qualification"]["status"],
                             "FULL_SCENE_COVERAGE_CANDIDATE_NONCANONICAL")
            self.assertFalse(report["qualification"]["canonical_commit_authorized"])
            self.assertEqual(report["qualification"]["world_db_writes"],0)
            count=len(calls)
            self.assertEqual(self.worker(root,lambda **_:self.fail(
                "cached source must not call provider again"))(
                    prose=SOURCE_2,world=entry()),evidence)
            self.assertEqual(count,len(calls))

    def test_independent_extractor_must_name_actor_before_facet_action_passes(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            provider,_=self.source_model(omit_actor=True)
            evidence=self.worker(root,provider)(
                prose=SOURCE_2,world=entry())
            self.assertEqual(evidence["status"],"EVIDENCE_READY_NONCANONICAL")
            with self.assertRaisesRegex(
                Exception,"V054_NOT_BACKED_BY_INDEPENDENT_SOURCE_EVENT"):
                create_checker(
                    evidence_root=root/"evidence",full_qualification=True)(
                        prose=SOURCE_2,world=entry())


if __name__=="__main__":
    unittest.main()
