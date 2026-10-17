"""SERA v0.52: autonomously recover a syntactically valid BUT incomplete typed reply.

Real v0.22 preparer, blind sentence sweep, independent semantic stage and
v0.23 checker; provider is scripted, never billable. Source-only retry
does not receive previous model outputs, gold or a hand-corrected scene.
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
    SOURCE_2, entry, fake_model, EXTRACT, SEMANTIC, TYPED,
)


def response(model,payload,idx):
    return {
        "error":None,
        "raw":{
            "id":"test-typed-source-gap-"+str(idx),"model":model,
            "usage":{"cost":"0.001"},
            "choices":[{"finish_reason":"stop",
                        "message":{"content":json.dumps(payload)}}],
        }
    }


FALLBACK="synthetic/independent-facet-fallback"


class TypedSourceOnlyAutorepair(unittest.TestCase):
    def worker(self,root,provider,*,fallback_model=None,
               typed_batch_recovery=False):
        return create_preparer(
            evidence_root=root/"evidence",work_root=root/"jobs",
            scene_key="synthetic-typed-source-reread",
            registry={"ari":["Ari"],"box":["box"]},
            candidate_lexicon={},
            typed_registry={"openables":["box"],"documents":[]},
            api_key="OFFLINE_SYNTHETIC_NO_NETWORK",
            extraction_model=EXTRACT,semantic_model=SEMANTIC,
            typed_model=TYPED,provider_call=provider,
            fallback_model=fallback_model,
            max_model_requests=18,max_source_repair_attempts=1,
            observed_spend_guard_usd="0.30",
            typed_batch_recovery=typed_batch_recovery,
        )

    def mock(self,*,always_empty=False,typed_timeout=False):
        self.requests=[]
        original=fake_model([])
        self.typed_seen=0

        def provider(*,key,model,prepared):
            request=prepared["request"]
            packet=json.loads(request["messages"][-1]["content"])
            self.requests.append((model,request,packet))
            forbidden=("max_tokens","max_completion_tokens",
                       "max_output_tokens","max_new_tokens")
            self.assertFalse(any(
                key in request for key in forbidden))
            if model==TYPED and "original_prose" in packet:
                self.typed_seen+=1
                if typed_timeout:
                    raise TimeoutError("possibly billed typed model POST")
                if always_empty or self.typed_seen==1:
                    return response(model,{"typed_candidates":[]},len(self.requests))
            return original(key=key,model=model,prepared=prepared)
        return provider

    def test_valid_but_missing_typed_close_reextracted_and_full_v023_passes(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            mock=self.mock()
            worker=self.worker(root,mock)
            prepared=worker(prose=SOURCE_2,world=entry())
            self.assertEqual(prepared["status"],"EVIDENCE_READY_NONCANONICAL",
                             prepared)
            self.assertEqual(self.typed_seen,2)
            typed=[x for x in self.requests if x[0]==TYPED]
            self.assertEqual(len(typed),2)
            self.assertEqual(typed[0][2],typed[1][2])
            self.assertNotEqual(typed[0][1]["messages"][0]["content"],
                                typed[1][1]["messages"][0]["content"])
            self.assertIn("SOURCE-ONLY TYPED",typed[1][1]["messages"][0]["content"])
            self.assertNotIn("prior typed",typed[1][1]["messages"][1]["content"].lower())
            checked=create_checker(
                evidence_root=root/"evidence",full_qualification=True)(
                    prose=SOURCE_2,world=entry())
            self.assertEqual(checked["qualification"]["status"],
                             "FULL_SCENE_COVERAGE_CANDIDATE_NONCANONICAL")
            before=len(self.requests)
            restart=self.worker(root,lambda **_:self.fail(
                "Receipted source replay must never repost"))
            self.assertEqual(restart(prose=SOURCE_2,world=entry()),prepared)
            self.assertEqual(len(self.requests),before)

    def test_explicit_independent_fallback_recovers_valid_but_incomplete_facet(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            mock=self.mock(always_empty=True)
            output=self.worker(root,mock,fallback_model=FALLBACK)(
                prose=SOURCE_2,world=entry())
            self.assertEqual(output["status"],"EVIDENCE_READY_NONCANONICAL",
                             output)
            self.assertEqual(self.typed_seen,2)
            self.assertEqual([x[0] for x in self.requests].count(FALLBACK),1)
            backup=[x for x in self.requests if x[0]==FALLBACK][0]
            self.assertEqual(backup[2]["original_prose"],SOURCE_2)
            self.assertIn("SOURCE-ONLY TYPED",backup[1]["messages"][0]["content"])
            self.assertNotIn("max_tokens",backup[1])
            checked=create_checker(
                evidence_root=root/"evidence",full_qualification=True)(
                    prose=SOURCE_2,world=entry())
            self.assertEqual(checked["qualification"]["status"],
                             "FULL_SCENE_COVERAGE_CANDIDATE_NONCANONICAL")
            before=len(self.requests)
            replay=self.worker(root,lambda **_:self.fail(
                "Cached receipts must prevent fallback rePOST"),
                fallback_model=FALLBACK)
            self.assertEqual(output,replay(prose=SOURCE_2,world=entry()))
            self.assertEqual(len(self.requests),before)

    def test_second_semantically_missing_typed_reply_fails_safe_with_no_new_post(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            mock=self.mock(always_empty=True)
            worker=self.worker(root,mock)
            failed=worker(prose=SOURCE_2,world=entry())
            self.assertEqual(failed["status"],"FAILED_SAFE_FINAL")
            self.assertIn("V022_CRITICAL_TYPED_EVENT_NOT_ACCOUNTED",
                          failed["failure_code"])
            self.assertEqual(self.typed_seen,2)
            previous=len(self.requests)
            again=worker(prose=SOURCE_2,world=entry())
            self.assertEqual(failed,again)
            self.assertEqual(len(self.requests),previous)
            self.assertFalse((root/"evidence"/
                (prose_hash(SOURCE_2)+".json")).exists())

    def test_exact_source_window_recovers_incomplete_full_typed_rereads(self):
        # The mock is a source parser for the unrelated two-sentence Ari
        # control, NOT an analyst-filled Mara event answer.
        with TemporaryDirectory() as temp:
            root=Path(temp)
            calls=[]
            parser=fake_model(calls)
            typed_attempts=[]
            sent=[]
            def provider(*,key,model,prepared):
                request=prepared["request"]
                packet=json.loads(request["messages"][-1]["content"])
                sent.append((model,request,packet))
                if model==TYPED and "original_prose" in packet:
                    typed_attempts.append(request)
                    if len(typed_attempts)<=2:
                        return response(model,{"typed_candidates":[]},len(sent))
                return parser(key=key,model=model,prepared=prepared)
            result=self.worker(root,provider,typed_batch_recovery=True)(
                prose=SOURCE_2,world=entry())
            self.assertEqual(result["status"],"EVIDENCE_READY_NONCANONICAL",
                             result)
            self.assertEqual(len(typed_attempts),3)
            window=typed_attempts[-1]
            self.assertIn("EXACT SOURCE WINDOW TYPED RE-EXTRACTION",
                          window["messages"][0]["content"])
            self.assertEqual(window["messages"][1],typed_attempts[0]["messages"][1])
            self.assertNotIn("prior typed",window["messages"][1]["content"].lower())
            self.assertNotIn("max_tokens",window)
            check=create_checker(
                evidence_root=root/"evidence",full_qualification=True)(
                    prose=SOURCE_2,world=entry())
            self.assertEqual(check["qualification"]["status"],
                             "FULL_SCENE_COVERAGE_CANDIDATE_NONCANONICAL")
            before=len(sent)
            replay=self.worker(
                root,lambda **_:self.fail("cached window receipt repost"),
                typed_batch_recovery=True)
            self.assertEqual(replay(prose=SOURCE_2,world=entry()),result)
            self.assertEqual(len(sent),before)

    def test_window_response_outside_exact_sentence_is_rejected(self):
        from experiments.sera.fresh_scene_evidence_worker_v022 import (
            _typed_source_window_request, _validate_typed_window,
        )
        from experiments.sera.sentence_ledger_v06 import sentences
        source=sentences(SOURCE_2)
        original={"messages":[
            {"role":"system","content":"independent typed test"},
            {"role":"user","content":json.dumps({
                "original_prose":SOURCE_2, "registered_roles":{
                    "openables":["box"],"documents":[]}})}],
            "response_format":{"type":"json_object"}}
        scoped=_typed_source_window_request(
            original=original,target_sentences=[source[0]])
        self.assertEqual(scoped["messages"][1],original["messages"][1])
        parser=fake_model([])
        produced=parser(key="synthetic",model=TYPED,
                        prepared={"request":original})
        reply=json.loads(produced["raw"]["choices"][0]["message"]["content"])
        with self.assertRaisesRegex(
                Exception,"V022_TYPED_WINDOW_OUTSIDE_TARGET"):
            _validate_typed_window(SOURCE_2,reply,[source[0]])
        self.assertFalse(any(
            k in scoped for k in ("max_tokens","max_completion_tokens")))

    def test_unknown_typed_post_never_triggers_blind_retry(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            mock=self.mock(typed_timeout=True)
            out=self.worker(root,mock)(prose=SOURCE_2,world=entry())
            self.assertEqual(out["status"],"FAILED_SAFE_FINAL")
            self.assertEqual(self.typed_seen,1)
            self.assertIn("V021_UNCONFIRMED_IN_FLIGHT_PROVIDER_CALL",
                          out["failure_code"])


if __name__=="__main__":
    unittest.main()
