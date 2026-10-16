"""SERA v0.23 full runner: synthetic provider, no paid LLM calls."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.composed_scene_runner_v023 import run
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.tests.test_fresh_scene_evidence_worker_v022 import (
    SOURCE_1, SOURCE_2, entry, fake_model,
)

WRITER="synthetic/scene-writer"
SWEEP="synthetic/sweep-independent"
SEMANTIC="synthetic/semantic-independent"
FACET="synthetic/typed-independent"

def provider_fixture(calls):
    extractor=fake_model(calls)
    def provider(*,key,model,prepared):
        packet=json.loads(prepared["request"]["messages"][1]["content"])
        if "scene_prose" in packet:
            calls.append((model,packet))
            old=packet["scene_prose"]
            assert old==SOURCE_1
            return {"error":None,"raw":{
                "id":"synthetic-writer-001","model":model,
                "usage":{"cost":"0.001"},
                "choices":[{"finish_reason":"stop","message":{"content":
                    json.dumps({"source_prose_sha256":prose_hash(old),
                                "revised_scene_prose":SOURCE_2})}}],
            }}
        return extractor(key=key,model=model,prepared=prepared)
    return provider

def invoke(root, provider, *, prose=SOURCE_1, model=WRITER, context=None):
    return run(
        prose=prose,world=entry(),scene_key="generic-box-scene",
        work_root=root,api_key="synthetic",
        registry={"ari":["Ari"],"box":["box"]},
        candidate_lexicon={},
        typed_registry={"openables":["box"],"documents":[]},
        writer_model=model,sweep_model=SWEEP,semantic_model=SEMANTIC,
        facet_model=FACET,provider_call=provider,
        immutable_story_context=context or {"canonical":"never spawn train"},
        max_rewrites=2,
    )

class ComposedWorkerV023Tests(unittest.TestCase):
    def test_complete_unattended_noncanonical_rewrite_and_full_scene_gates(self):
        calls=[]
        with TemporaryDirectory() as d:
            root=Path(d)/"scene"
            out=invoke(root,provider_fixture(calls))
            files=list((root/"evidence").glob("*.json"))
        self.assertEqual(out["status"],"SCENE_CANDIDATE_READY_NONCANONICAL")
        self.assertEqual(len(files),2)
        self.assertEqual(out["rewrite_count"],1)
        self.assertEqual(len([x for x in calls if x[0]==WRITER]),1)
        self.assertFalse(out["canonical_commit_authorized"])
        self.assertFalse(out["requires_manual_intervention"])
        self.assertEqual(out["world_db_writes"],0)

    def test_restart_with_receipts_never_rebills_provider(self):
        calls=[]
        with TemporaryDirectory() as d:
            root=Path(d)/"scene"
            result=invoke(root,provider_fixture(calls))
            count=len(calls)
            def must_not_send(**kwargs):
                raise AssertionError("provider charged twice")
            resumed=invoke(root,must_not_send)
        self.assertEqual(result,resumed)
        self.assertGreater(count,1)

    def test_changed_writer_model_refuses_old_scene_contract(self):
        calls=[]
        with TemporaryDirectory() as d:
            root=Path(d)/"scene"
            invoke(root,provider_fixture(calls))
            with self.assertRaisesRegex(
                CoverageError,"V020_REWRITE_RESUME_CONTRACT_MISMATCH"
            ):
                invoke(root,provider_fixture(calls),model="synthetic/changed")

    def test_changed_immutable_context_refuses_old_receipts(self):
        calls=[]
        with TemporaryDirectory() as d:
            root=Path(d)/"scene"
            invoke(root,provider_fixture(calls))
            with self.assertRaisesRegex(
                CoverageError,"V020_REWRITE_RESUME_CONTRACT_MISMATCH"
            ):
                invoke(root,provider_fixture(calls),
                       context={"canonical":"different policy"})

    def test_already_safe_draft_does_not_call_writer(self):
        calls=[]
        with TemporaryDirectory() as d:
            result=invoke(Path(d)/"scene",provider_fixture(calls),
                          prose=SOURCE_2)
        self.assertEqual(result["status"],"SCENE_CANDIDATE_READY_NONCANONICAL")
        self.assertEqual(result["rewrite_count"],0)
        self.assertEqual(len([x for x in calls if x[0]==WRITER]),0)

    def test_no_world_authority_mislabeled_on_success(self):
        calls=[]
        with TemporaryDirectory() as d:
            out=invoke(Path(d)/"scene",provider_fixture(calls))
        self.assertEqual(out["next_automatic_action"],
                         "CONTINUE_OTHER_FULL_STORY_GATES")
        self.assertFalse(out["canonical_commit_authorized"])

if __name__=="__main__":
    unittest.main()
