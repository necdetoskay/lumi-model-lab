"""SERA v0.52 real HTTP adapter: NO-NETWORK adversarial receipts."""
import base64
import json
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from experiments.sera.openrouter_real_transport_v052 import (
    make_openrouter_transport, ENDPOINT)
from experiments.sera.provider_grant_journal_v052 import (
    ProviderJournal, JournalBlocked, _canonical)
from experiments.sera.journaled_provider_bridge_v052 import (
    create_journaled_provider, fingerprint_for_request)

MODELS = dict(extraction="google/example-1", semantic="anthropic/example-2",
              typed="google/example-3", writer="anthropic/example-4")
SOURCE = dict(source_sha256="a"*64, world_sha256="b"*64,
              scene_key="v052-frozen-mara-s1-28", policy_sha256="c"*64)


class FakeResponse:
    def __init__(self, content):
        self.content = content
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return self.content


class RealTransportOfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.journal=ProviderJournal(Path(self.tmp.name)/"billing.db")
        self.signer=Ed25519PrivateKey.generate()
        self.trusted=self.signer.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        self.request={"messages":[{"role":"user","content":"blind Mara source"}],
                      "response_format":{"type":"json_object"}}
        self.fingerprint=fingerprint_for_request(
            stage="extraction",model=MODELS["extraction"],request=self.request,**SOURCE)
        self.grants={self.fingerprint:{"grant_id":"sera-grant-test",
                                       "request_id":"sera-request-test"}}
        self.binding=dict(**SOURCE,model=MODELS["extraction"],
                          stage="extraction",request_fingerprint=self.fingerprint)
        self.sent=[]
        self.raw={"id":"gen-live-example","model":MODELS["extraction"],
                  "choices":[{"finish_reason":"stop","message":{"content":"{}"}}],
                  "usage":{"prompt_tokens":39,"completion_tokens":11,"cost":0.0012}}

    def sign(self):
        manifest=dict(scope="SERA_V052_MARA_NONCANONICAL_PAID",**SOURCE,
                      approved_models=MODELS, grants=self.grants,
                      expires_at=int(time.time())+1800, approval_id="sera-only-test")
        return {"manifest":manifest,"signature":base64.b64encode(
            self.signer.sign(_canonical(manifest).encode("utf-8"))).decode("ascii")}

    def opener(self,req,timeout):
        self.sent.append((req,timeout))
        return FakeResponse(json.dumps(self.raw).encode("utf-8"))

    def transport(self,opener=None):
        return make_openrouter_transport(api_key="placeholder-not-live",
                                         opener=opener or self.opener)

    def bridge(self,opener=None,approval=None):
        return create_journaled_provider(
            journal=self.journal, approved_models=MODELS, grants=self.grants,
            transport=self.transport(opener), approval=approval or self.sign(),
            trusted_public_key=self.trusted,**SOURCE)

    def invoke(self,callback):
        return callback(key="never-used",model=MODELS["extraction"],
                        prepared={"request":self.request})

    def test_constructing_adapter_does_not_call_network(self):
        self.transport()
        self.assertEqual(self.sent,[])
        self.assertEqual(self.journal.status("sera-grant-test"),"NOT_STARTED")

    def test_real_wire_shape_and_replay_no_repost(self):
        self.journal.register_grant(grant_id="sera-grant-test",
                                    binding=self.binding,authorized=True)
        result=self.invoke(self.bridge())
        again=self.invoke(self.bridge())
        self.assertEqual(result,again)
        self.assertEqual(result["raw"]["id"],"gen-live-example")
        self.assertEqual(result["raw"]["usage"]["cost"],0.0012)
        self.assertEqual(len(self.sent),1)
        req,timeout=self.sent[0]
        self.assertEqual(req.full_url,ENDPOINT)
        self.assertEqual(req.get_method(),"POST")
        body=json.loads(req.data)
        self.assertEqual(body["model"],MODELS["extraction"])
        self.assertIs(body["stream"],False)
        self.assertNotIn("max_tokens",body)
        self.assertEqual(self.journal.status("sera-grant-test"),"RECEIPTED")

    def test_network_uncertainty_prevents_duplicate_bill(self):
        self.journal.register_grant(grant_id="sera-grant-test",
                                    binding=self.binding,authorized=True)
        attempted=[]
        def outage(req,timeout):
            attempted.append(req)
            raise URLError("socket reset")
        with self.assertRaises(URLError):
            self.invoke(self.bridge(opener=outage))
        with self.assertRaisesRegex(JournalBlocked,"UNKNOWN_INFLIGHT"):
            self.invoke(self.bridge())
        self.assertEqual(len(attempted),1)
        self.assertEqual(self.sent,[])
        self.assertEqual(self.journal.status("sera-grant-test"),"STARTED")

    def test_malformed_json_stays_started_no_repost(self):
        self.journal.register_grant(grant_id="sera-grant-test",
                                    binding=self.binding,authorized=True)
        def broken(req,timeout):
            self.sent.append((req,timeout))
            return FakeResponse(b"{")
        with self.assertRaises(json.JSONDecodeError):
            self.invoke(self.bridge(opener=broken))
        with self.assertRaisesRegex(JournalBlocked,"UNKNOWN_INFLIGHT"):
            self.invoke(self.bridge())
        self.assertEqual(len(self.sent),1)

    def test_http_rejection_receipted_but_not_success(self):
        self.journal.register_grant(grant_id="sera-grant-test",
                                    binding=self.binding,authorized=True)
        def rejected(req,timeout):
            self.sent.append((req,timeout))
            raise HTTPError(ENDPOINT,429,"rate limit",{},None)
        result=self.invoke(self.bridge(opener=rejected))
        self.assertEqual(result["error"],"HTTP_429")
        self.assertIsNone(result["raw"])
        self.assertEqual(self.journal.status("sera-grant-test"),"RECEIPTED")
        self.assertEqual(len(self.sent),1)

    def test_stream_and_model_mismatch_rejected_without_send(self):
        t=self.transport()
        with self.assertRaisesRegex(JournalBlocked,"STREAMED"):
            t(model=MODELS["extraction"],
              payload={"messages":[],"stream":True},request_id="id")
        with self.assertRaisesRegex(JournalBlocked,"MODEL_DRIFT"):
            t(model=MODELS["extraction"],
              payload={"messages":[],"model":"wrong"},request_id="id")
        self.assertEqual(self.sent,[])

    def test_unsigned_approval_cannot_reach_transport(self):
        with self.assertRaisesRegex(JournalBlocked,"SIGNED_APPROVAL"):
            self.bridge(approval={"manifest":{},"signature":""})
        self.assertEqual(self.sent,[])

    def test_truncated_usage_is_only_receipt_not_semantic_pass(self):
        self.journal.register_grant(grant_id="sera-grant-test",
                                    binding=self.binding,authorized=True)
        self.raw["choices"][0]["finish_reason"]="length"
        envelope=self.invoke(self.bridge())
        self.assertEqual(envelope["raw"]["choices"][0]["finish_reason"],"length")
        self.assertEqual(self.journal.status("sera-grant-test"),"RECEIPTED")
        # v0.21/v0.22 checker must separately refuse non-stop results.

if __name__ == "__main__":
    unittest.main()
