"""v0.48 prelaunch: no paid requests, source bound coverage cannot fake truth."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from experiments.sera.coverage import CoverageError
from experiments.sera.real_blind_benchmark_v040 import MODELS
from experiments.sera.real_full_scene_blind_v048 import (
    MAX_ATTEMPTS,MAX_SPEND_USD,GRANT,GRANT_SCHEMA,
    prepare,require_grant,request_payload,assess_received,analyze_plan_coverage,
    live,
)


def sample(source, index=0, *, wrong_quote=False, short=False):
    batch=source["plan"]["batches"][index]
    rows=[]
    for i,sid in enumerate(batch["sentence_ids"]):
        row={
            "sentence_id":sid,"disposition":"NO_TRACKED_CHANGE",
            "reason":"synthetic source quote fixture NOT semantic gold",
            "mentions":[],"events":[],
        }
        if wrong_quote and i==1:
            row["mentions"]=[{
                "entity_ref":"new:imaginary_transport",
                "role":"MENTIONED",
                "evidence_quote":"teleport that never happened",
                "occurrence":0,
            }]
        rows.append(row)
    if short:
        rows=rows[:-1]
    reply={
        "model":MODELS[0],
        "batch_id":batch["batch_id"],
        "request_sha256":batch["request_sha256"],
        "provider_envelope":{"error":None,"raw":{
            "id":"synthetic-proof-no-real-provider",
            "model":MODELS[0],"usage":{"cost":"0"},
            "choices":[{"finish_reason":"stop",
                        "message":{"content":json.dumps({"rows":rows})}}],
        }},
    }
    return batch,reply


class RealFullSceneBlindV048Tests(TestCase):
    def test_28_exact_sentences_in_7_distinct_blind_batches(self):
        source,manifest=prepare()
        self.assertEqual(manifest["source_sentence_count"],28)
        self.assertEqual(manifest["planned_provider_attempts"],14)
        self.assertEqual(len(manifest["batches"]),7)
        self.assertEqual(len({
            sid for b in manifest["batches"] for sid in b["sentence_ids"]
        }),28)
        self.assertEqual(len({
            b["request_sha256"] for b in manifest["batches"]
        }),7)
        self.assertFalse(manifest["canonical_commit_authorized"])
        self.assertFalse(manifest["independent_semantic_truth_proven"])
        self.assertEqual(manifest["real_provider_calls_during_preparation"],0)
        for batch in source["plan"]["batches"]:
            wire=request_payload(batch)
            self.assertEqual(wire["response_format"],{"type":"json_object"})
            for banned in (
                "max_tokens","max_output_tokens","max_completion_tokens",
                "max_new_tokens","max_generation_tokens",
            ):
                self.assertNotIn(banned,wire)
            self.assertNotIn("prior_model_answer",json.dumps(wire))

    def test_missing_or_invalid_authorization_never_passes_validation(self):
        # The SAME suite runs both during preparation (GRANT absent)
        # and after a separately approved grant-only commit (GRANT present).
        # Existence is not authorization: wrong shape must always fail.
        _,manifest=prepare()
        self.assertEqual(str(MAX_SPEND_USD),"0.25")
        self.assertEqual(MAX_ATTEMPTS,14)
        with self.assertRaisesRegex(
            CoverageError,"V048_EXACT_PAID_GRANT_REQUIRED",
        ):
            require_grant(manifest,{"authorized":False})

    def test_invented_quote_is_individually_quarantined(self):
        source,_=prepare()
        batch,reply=sample(source,wrong_quote=True)
        checked=assess_received(
            source=source,batch=batch,model=MODELS[0],receipt=reply,
        )
        self.assertEqual(len(checked["source_bound_rows"]),3)
        self.assertEqual(len(checked["quarantined_rows"]),1)
        self.assertFalse(any(x.get("semantic_truth_verified",True)
                             for x in checked["source_bound_rows"]))
        scope=analyze_plan_coverage(source,[{
            "model":MODELS[0],"assessment":checked,
        }])
        self.assertEqual(
            scope["model_results"][MODELS[0]]["source_bound_sentence_count"],3,
        )
        self.assertEqual(
            scope["model_results"][MODELS[0]]["quarantined_sentence_count"],1,
        )
        self.assertEqual(
            scope["model_results"][MODELS[1]]["unsampled_sentence_count"],28,
        )
        self.assertFalse(scope["story_ready_for_g2_commit"])

    def test_missing_a_model_row_never_becomes_full_batch_coverage(self):
        source,_=prepare()
        batch,reply=sample(source,short=True)
        result=assess_received(
            source=source,batch=batch,model=MODELS[0],receipt=reply,
        )
        self.assertEqual(len(result["source_bound_rows"]),0)
        self.assertEqual(len(result["quarantined_rows"]),4)
        self.assertFalse(result["risk_flags"])

    def test_all_synthetically_bound_does_not_prove_recall_or_g2(self):
        source,_=prepare()
        evidence=[]
        for i in range(7):
            batch,reply=sample(source,i)
            bound=assess_received(
                source=source,batch=batch,model=MODELS[0],receipt=reply,
            )
            evidence.append({"model":MODELS[0],"assessment":bound})
            evidence.append({"model":MODELS[1],"assessment":bound})
        scores=analyze_plan_coverage(source,evidence)
        self.assertTrue(scores["source_complete_candidate_binding_all_models"])
        self.assertFalse(scores["semantic_recall_precision_proven"])
        self.assertFalse(scores["story_ready_for_g2_commit"])
        self.assertFalse(scores["canonical_commit_authorized"])
        self.assertEqual(scores["model_results"][MODELS[1]]
                         ["source_bound_sentence_count"],28)

    def test_unauthorized_live_cannot_create_output_or_call_provider(self):
        source,_=prepare()
        with TemporaryDirectory() as root:
            target=Path(root)/"trial"/"results.json"
            with self.assertRaisesRegex(
                CoverageError,"V048_EXACT_PAID_GRANT_REQUIRED",
            ):
                live(output=target,
                     launch_id="sera-v048-full-once-test",
                     key="untrusted-key",grant={"authorized":False})
            self.assertFalse(target.exists())

    def test_invalid_model_scope_or_batch_identity_is_rejected(self):
        source,_=prepare()
        batch,reply=sample(source)
        reply["request_sha256"]="bad"
        with self.assertRaisesRegex(
            CoverageError,"V048_PROVIDER_RECEIPT_SOURCE_OR_MODEL_MISMATCH",
        ):
            assess_received(source=source,batch=batch,model=MODELS[0],
                            receipt=reply)

    def test_missing_charge_never_proves_provider_economics(self):
        source,_=prepare()
        batch,reply=sample(source)
        del reply["provider_envelope"]["raw"]["usage"]
        out=assess_received(source=source,batch=batch,model=MODELS[0],
                            receipt=reply)
        self.assertIsNone(out["charge_usd"])


if __name__=="__main__":
    import unittest
    unittest.main()
