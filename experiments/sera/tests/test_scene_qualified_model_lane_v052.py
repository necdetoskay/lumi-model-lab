"""SERA v0.52 real-adapter shape with OFFLINE providers only; NO paid calls."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.scene_qualified_model_lane_v052 import (
    FAKE_KEY, frozen_mara_offline, run_offline_lane,
)
from experiments.sera.tests.test_fresh_scene_evidence_worker_v022 import (
    SOURCE_1, SOURCE_2, entry, fake_model,
)

MODELS = {
    "extraction": "synthetic/v052-source",
    "semantic": "synthetic/v052-semantic",
    "typed": "synthetic/v052-facets",
    "writer": "synthetic/v052-auto-writer",
}


def bridge_provider(calls):
    base = fake_model(calls)

    def provider(*, key, model, prepared):
        assert key == FAKE_KEY
        req = prepared["request"]
        encoded = json.dumps(req, ensure_ascii=False)
        assert all(forbidden not in encoded for forbidden in (
            "max_tokens", "max_completion_tokens", "max_output_tokens",
            "max_new_tokens", "max_generation_tokens",
        ))
        if model != MODELS["writer"]:
            return base(key=key, model=model, prepared=prepared)
        packet = json.loads(req["messages"][1]["content"])
        assert packet["scene_prose"] == SOURCE_1
        assert packet["source_prose_sha256"] == prose_hash(SOURCE_1)
        assert packet["verified_defect_candidates"]
        calls.append((model, deepcopy(packet)))
        answer = {
            "source_prose_sha256": prose_hash(SOURCE_1),
            "revised_scene_prose": SOURCE_2,
        }
        return {
            "error": None,
            "raw": {
                "id": "v052-ari-revision-real-adapter-shape",
                "model": model,
                "usage": {"cost": "0"},
                "choices": [{
                    "finish_reason": "stop",
                    "message": {"content": json.dumps(answer)},
                }],
            },
        }
    return provider


def ari(root, call, *, prose=SOURCE_1, world=None, models=MODELS,
        max_rewrites=2):
    return run_offline_lane(
        prose=prose, world=world if world is not None else entry(),
        output_root=root, scene_key="v052-ari-qualified-control",
        registry={"ari":["Ari"],"box":["box"]},
        candidate_lexicon={},
        typed_registry={"openables":["box"],"documents":[]},
        provider_call=call, models=models,
        max_rewrites=max_rewrites,
    )


class SeraV052ModelTransportIntegrationTests(unittest.TestCase):
    def test_ari_real_adapters_rewrite_and_full_v023_gate_then_replay(self):
        calls=[]
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            first=ari(root,bridge_provider(calls))
            from experiments.sera.artifact_scene_checker_v021 import create_checker
            checker=create_checker(evidence_root=root/"evidence",
                                   full_qualification=True)
            checked=checker(prose=SOURCE_2,world=entry())
            self.assertIn("qualification", checked)
            self.assertEqual(checked["qualification"]["defects"], [])
            second=ari(root,lambda **kw:self.fail("no paid or fake POST on replay"))
            self.assertTrue((root/"evidence"/
                             (prose_hash(SOURCE_1)+".json")).exists())
            self.assertTrue((root/"evidence"/
                             (prose_hash(SOURCE_2)+".json")).exists())
            self.assertEqual(first,second)
        self.assertEqual(first["status"],
                         "FULL_SCENE_QUALIFIED_CANDIDATE_NONCANONICAL")
        self.assertEqual(first["automatic_rewrites"],1)
        self.assertEqual(first["final_source_sha256"],prose_hash(SOURCE_2))
        self.assertEqual(first["source_sentence_count"],2)
        self.assertFalse(first["full_28_sentence_genuine_model_semantics_approved"])
        self.assertFalse(first["provider_is_real"])
        self.assertEqual(first["new_paid_model_calls"],0)
        self.assertEqual(first["production_db_writes"],0)
        self.assertEqual(first["manual_story_or_json_edits"],0)
        self.assertEqual([x[0] for x in calls].count(MODELS["writer"]),1)
        self.assertGreater(len(calls),3)

    def test_full_frozen_mara_28_sentences_fail_safe_without_canon(self):
        calls=[]
        def incomplete(*,key,model,prepared):
            self.assertEqual(key,FAKE_KEY)
            self.assertNotEqual(model,MODELS["writer"])
            calls.append(model)
            return {"error":None,"raw":{
                "id":"v052-mara-incomplete-"+str(len(calls)),
                "model":model, "usage":{"cost":"0"},
                "choices":[{"finish_reason":"stop",
                            "message":{"content":'{"rows":[]}'}}],
            }}
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            first=frozen_mara_offline(
                output_root=root, provider_call=incomplete, models=MODELS,
            )
            count=len(calls)
            second=frozen_mara_offline(
                output_root=root,
                provider_call=lambda **kw:self.fail("Mara should not repost"),
                models=MODELS,
            )
        self.assertEqual(first,second)
        self.assertEqual(count,len(calls))
        self.assertEqual(first["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(first["source_sentence_count"],28)
        self.assertEqual(first["automatic_rewrites"],0)
        self.assertFalse(first["full_28_sentence_genuine_model_semantics_approved"])
        self.assertFalse(first["canonical_commit_authorized"])
        self.assertEqual(first["new_paid_model_calls"],0)

    def test_real_model_name_is_never_allowed_in_offline_mode(self):
        calls=[]
        with TemporaryDirectory() as tmp:
            bad=dict(MODELS,extraction="google/gemini-3.7-flash")
            with self.assertRaisesRegex(
                CoverageError,"V052_OFFLINE_PROVIDER_MODEL_POLICY_INVALID",
            ):
                ari(Path(tmp),bridge_provider(calls),models=bad)
        self.assertEqual(calls,[])

    def test_source_world_resume_fingerprint_rejects_drift(self):
        calls=[]
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            ari(root,bridge_provider(calls))
            count=len(calls)
            with self.assertRaisesRegex(
                CoverageError,"V052_RESTART_SOURCE_WORLD_OR_MODEL_POLICY_DRIFT",
            ):
                ari(root,lambda **kw:self.fail("source drift posted"),
                    prose=SOURCE_2)
            changed=entry()
            changed["revision"] += 1
            with self.assertRaisesRegex(
                CoverageError,"V052_RESTART_SOURCE_WORLD_OR_MODEL_POLICY_DRIFT",
            ):
                ari(root,lambda **kw:self.fail("world drift posted"),
                    world=changed)
            self.assertEqual(len(calls),count)

    def test_unreceived_provider_result_stops_and_no_replay(self):
        calls=[]
        def unknown(*,key,model,prepared):
            calls.append(model)
            raise ConnectionError("unknown if billed")
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            first=ari(root,unknown)
            second=ari(root,lambda **kw:self.fail("no repost after unknown"))
        self.assertEqual(first,second)
        self.assertEqual(first["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(len(calls),1)
        self.assertEqual(first["automatic_rewrites"],0)
        self.assertFalse(first["canonical_commit_authorized"])

    def test_zero_rewrites_cannot_be_overridden_by_synthetic_advice(self):
        calls=[]
        with TemporaryDirectory() as tmp:
            result=ari(Path(tmp),bridge_provider(calls),max_rewrites=0)
        self.assertEqual(result["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(result["automatic_rewrites"],0)
        self.assertEqual([x[0] for x in calls].count(MODELS["writer"]),0)

    def test_forged_final_record_cannot_claim_canon(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            ari(root,bridge_provider([]))
            f=root/"final.json"
            payload=json.loads(f.read_text(encoding="utf-8"))
            payload["canonical_commit_authorized"]=True
            f.write_text(json.dumps(payload)+"\n",encoding="utf-8")
            with self.assertRaisesRegex(
                CoverageError,"V052_SAVED_RESULT_UNSAFE",
            ):
                ari(root,lambda **kw:self.fail("no POST on forged replay"))

    def test_no_scripted_model_output_token_budget(self):
        calls=[]
        with TemporaryDirectory() as tmp:
            ari(Path(tmp),bridge_provider(calls))
        self.assertGreater(len(calls),0)
        self.assertEqual(
            [x[0] for x in calls].count(MODELS["writer"]),1,
        )


if __name__ == "__main__":
    unittest.main()
