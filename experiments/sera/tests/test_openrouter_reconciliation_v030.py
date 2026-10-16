"""v0.30 authenticated known-generation recovery, no extra paid POST."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.openrouter_reconciliation_v030 import (
    SCHEMA, fingerprint, make_reconciler, recover,
)
from experiments.sera.openrouter_scene_writer_v021 import (
    _durable_provider_response, make_request,
)

MODEL = "synthetic/qualified-writer"
SOURCE = "Ari looked at the box. Ari closed the box."
DEFECTS = ["Missing initial open observation"]
GEN = "gen-trusted-exact-001"


def request():
    return make_request(source=SOURCE, defects=DEFECTS,
                        story_context={"world": "test"})


def bound(req, *, model=MODEL, generation=GEN):
    return {
        "schema": SCHEMA, "model": model,
        "request_sha256": fingerprint(model=model, request=req),
        "generation_id": generation,
        "evidence_source": "AUTHENTICATED_PROVIDER_GENERATION",
    }


def read_fixture(req, *, model=MODEL, completion=None):
    content = json.dumps({
        "source_prose_sha256": prose_hash(SOURCE),
        "revised_scene_prose":
            "Ari saw the box open. Ari closed the box.",
    }) if completion is None else completion
    calls = []
    def get(*, api_key, generation_id, part):
        calls.append((generation_id, part))
        if part == "metadata":
            return {"data": {
                "id": generation_id, "model": model,
                "finish_reason": "stop", "total_cost": 0.004,
                "request_id": "req-openrouter-001",
            }}
        return {"data": {
            "input": {"messages": deepcopy(req["messages"])},
            "output": {"completion": content},
        }}
    return calls, get


def verifier(binding):
    return (binding.get("schema") == SCHEMA and
            binding.get("generation_id") == GEN and
            binding.get("evidence_source") ==
                "AUTHENTICATED_PROVIDER_GENERATION")


class KnownGenerationReconciliationV030Tests(unittest.TestCase):
    def test_authenticated_generation_content_and_charge_recovery(self):
        req = request()
        calls, reader = read_fixture(req)
        got = recover(
            model=MODEL, request=req, api_key="fake-secret",
            binding_lookup=lambda **_: bound(req),
            verify_binding=verifier, get_generation=reader,
        )
        self.assertEqual(calls, [(GEN, "metadata"), (GEN, "content")])
        self.assertEqual(got["raw"]["model"], MODEL)
        self.assertEqual(got["raw"]["usage"]["cost"], "0.004")
        self.assertEqual(got["raw"]["choices"][0]["finish_reason"], "stop")
        self.assertEqual(got["read_only_recovery"]
                         ["provider_post_operations"], 0)
        self.assertFalse(got["read_only_recovery"]
                         ["canonical_commit_authorized"])

    def test_no_known_id_prevents_even_provider_get_and_all_post(self):
        req=request()
        calls,reader=read_fixture(req)
        with self.assertRaisesRegex(
            CoverageError, "V030_GENERATION_ID_UNAVAILABLE_NO_RESEND"
        ):
            recover(
                model=MODEL, request=req, api_key="fake",
                binding_lookup=lambda **kw: None,
                verify_binding=verifier, get_generation=reader,
            )
        self.assertEqual(calls, [])

    def test_generation_binding_requires_external_authenticity_and_exact_sha(self):
        req=request()
        calls,reader=read_fixture(req)
        with self.assertRaisesRegex(CoverageError,
                                    "V030_GENERATION_BINDING_UNTRUSTED"):
            recover(model=MODEL, request=req, api_key="fake",
                    binding_lookup=lambda **kw: {
                        **bound(req), "request_sha256": "0"*64,
                    },verify_binding=verifier,get_generation=reader)
        self.assertEqual(calls, [])
        with self.assertRaisesRegex(CoverageError,
                                    "V030_GENERATION_BINDING_UNTRUSTED"):
            recover(model=MODEL, request=req, api_key="fake",
                    binding_lookup=lambda **kw: bound(req),
                    verify_binding=lambda _: False,
                    get_generation=reader)
        self.assertEqual(calls, [])

    def test_wrong_model_or_stored_prompt_never_becomes_paid_receipt(self):
        req=request()
        calls,reader=read_fixture(req, model="synthetic/other-model")
        with self.assertRaisesRegex(CoverageError,
                                    "V030_PROVIDER_PROVENANCE_MISMATCH"):
            recover(model=MODEL, request=req,api_key="fake",
                    binding_lookup=lambda **_: bound(req),
                    verify_binding=verifier,get_generation=reader)
        self.assertEqual(len(calls),2)
        changed=deepcopy(req)
        changed["messages"][1]["content"]="other source story"
        calls2,reader2=read_fixture(changed)
        with self.assertRaisesRegex(CoverageError,
                                    "V030_PROVIDER_PROVENANCE_MISMATCH"):
            recover(model=MODEL, request=req,api_key="fake",
                    binding_lookup=lambda **_: bound(req),
                    verify_binding=verifier,get_generation=reader2)
        self.assertEqual(len(calls2),2)

    def test_missing_stored_text_or_invalid_cost_remains_safe(self):
        req=request()
        _,reader=read_fixture(req, completion="")
        with self.assertRaisesRegex(CoverageError,
                                    "V030_COMPLETION_CONTENT_NOT_STORED"):
            recover(model=MODEL,request=req,api_key="fake",
                    binding_lookup=lambda **_:bound(req),
                    verify_binding=verifier,get_generation=reader)
        def invalid_cost(**kwargs):
            val=read_fixture(req)[1](**kwargs)
            if kwargs["part"]=="metadata":
                val["data"]["total_cost"]="-1"
            return val
        with self.assertRaisesRegex(CoverageError,
                                    "V030_GENERATION_COST_UNAVAILABLE"):
            recover(model=MODEL,request=req,api_key="fake",
                    binding_lookup=lambda **_:bound(req),
                    verify_binding=verifier,get_generation=invalid_cost)

    def test_crashed_paid_writer_recovers_without_second_post_and_archives(self):
        req=request()
        calls,reader=read_fixture(req)
        recovered=make_reconciler(
            api_key="fake-key",
            binding_lookup=lambda **_:bound(req),
            verify_binding=verifier,get_generation=reader,
        )
        attempted=[]
        def interrupted(**kw):
            attempted.append(kw)
            raise RuntimeError("provider response lost after bill")
        with TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaisesRegex(RuntimeError,"lost after bill"):
                _durable_provider_response(
                    root=root,model=MODEL,request=req,
                    api_key="fake",provider_call=interrupted)
            self.assertEqual(len(attempted),1)
            result=_durable_provider_response(
                root=root,model=MODEL,request=req,
                api_key="fake",
                provider_call=lambda **_: self.fail("duplicate charge"),
                reconciler=recovered,
            )
            # Exact archived reply is immutable on the next restart.
            replay=_durable_provider_response(
                root=root,model=MODEL,request=req,
                api_key="fake",
                provider_call=lambda **_: self.fail("duplicate charge"),
                reconciler=lambda **_: self.fail("redundant generation GET"),
            )
            files=list(root.glob("*.response.json"))
        self.assertEqual(len(files),1)
        self.assertEqual(result,replay)
        self.assertEqual(len(calls),2)
        self.assertEqual(len(attempted),1)

    def test_crashed_writer_without_id_stops_and_cannot_retry(self):
        req=request()
        first=[]
        with TemporaryDirectory() as d:
            root=Path(d)
            def simulated_timeout(**kw):
                first.append(1)
                return {"error":"TRANSPORT_UNAVAILABLE","raw":None}
            with self.assertRaisesRegex(CoverageError,
                                        "V021_UNRECEIPTED_PROVIDER_RESULT"):
                _durable_provider_response(
                    root=root, model=MODEL, request=req,
                    api_key="fake",provider_call=simulated_timeout)
            rec=make_reconciler(
                api_key="fake",
                binding_lookup=lambda **kw:None,
                verify_binding=verifier,
                get_generation=lambda **kw:self.fail("GET not authorized"))
            with self.assertRaisesRegex(
                CoverageError,"V030_GENERATION_ID_UNAVAILABLE_NO_RESEND"
            ):
                _durable_provider_response(
                    root=root,model=MODEL,request=req,
                    api_key="fake",reconciler=rec,
                    provider_call=lambda **kw:self.fail("duplicate paid POST"))
        self.assertEqual(len(first),1)

    def test_synthetically_modified_provider_prompt_not_accepted_as_proof(self):
        req=request()
        wrong=deepcopy(req)
        wrong["messages"][0]["content"]="different instructions"
        with self.assertRaisesRegex(
            CoverageError,"V030_RECOVERY_REQUEST_DIGEST_MISMATCH"
        ):
            make_reconciler(
                api_key="fake",
                binding_lookup=lambda **_:bound(req),
                verify_binding=verifier,
            )(model=MODEL,request=wrong,
              request_sha256=fingerprint(model=MODEL,request=req))


if __name__=="__main__":
    unittest.main()
