"""SERA physical GET v0.53: signed fake HTTPS, zero real network or writes."""
from __future__ import annotations

from copy import deepcopy
from urllib.parse import parse_qs,urlsplit
import unittest
import tempfile
from pathlib import Path

from experiments.sera.coverage import CoverageError
from experiments.sera.g2_physical_authenticated_http_v053 import (
    API_PATH,create_physical_reader,physical_https_origin,
)
from experiments.sera.tests import test_g2_physical_pinned_reader_v036 as fixture
from experiments.sera.tests.test_g2_readonly_scope_v032 import IDS
from experiments.sera.tests.test_storyforge_bridge_v028 import fake_result
from experiments.sera.g2_physical_nonce_store_v053 import (
    LocalPhysicalNonceStore,provision_nonce_store)
from experiments.sera.sentence_ledger_v06 import sentences

ENDPOINT="https://g2-authority.project-lumi.example"+API_PATH
KEY="synthetic-physical-read-token-very-long"
PROSE=fake_result()["english_story"]
SCENE="signed-http-physical-source-offline-v053"


class ReadonlySignedPhysicalHTTPTests(unittest.TestCase):
    def setUp(self):
        self.signed=fixture.PinnedPhysicalTests(
            methodName="test_signed_physical_source_is_shadow_only_and_replay_is_denied")
        self.signed.setUp()
        self.calls=[]
        self.consume=self.signed.consume
        self.transport=self.make_transport()

    def make_transport(self,*,mutate=None):
        def get(*,url,authorization,timeout,max_bytes):
            self.assertEqual(authorization,KEY)
            self.assertEqual(timeout,15)
            self.assertLessEqual(max_bytes,1_500_000)
            parts=urlsplit(url)
            self.assertEqual(parts.scheme,"https")
            self.assertEqual(parts.path,API_PATH)
            query=parse_qs(parts.query)
            self.assertEqual(query["contractId"],
                             [self.signed.authority["g2_contract_id"]])
            nonce=query["nonce"][0]
            self.calls.append({
                "method":"GET","nonce":nonce,"url":url,
            })
            signed_packet=self.signed.signed(
                update_proof=lambda p:p.update(nonce=nonce))
            if mutate is not None:
                mutate(signed_packet)
            return signed_packet
        return get

    def reader(self,**changes):
        kwargs=dict(endpoint=ENDPOINT,bearer_token=KEY,
                    public_key_pem=self.signed.pem,
                    raw_public_key_sha256=self.signed.fingerprint,
                    key_id=fixture.KEY_ID,issuer=fixture.ISSUER,
                    audience=fixture.AUDIENCE,
                    consume_nonce=self.consume,
                    transport=self.transport,
                    nonce_factory=lambda:fixture.NONCE,
                    clock=lambda:fixture.NOW+1)
        kwargs.update(changes)
        return create_physical_reader(**kwargs)

    def call(self,reader=None,**changes):
        kwargs=dict(contract_id=self.signed.authority["g2_contract_id"],
                    authority=self.signed.authority,prose=PROSE,
                    scene_key=SCENE,registry={},candidate_lexicon={})
        kwargs.update(changes)
        return (reader or self.reader())(**kwargs)

    def test_one_https_get_and_signed_physical_entry_no_world_mutation(self):
        original=deepcopy(self.signed.authority)
        response=self.call()
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.calls[0]["method"],"GET")
        self.assertEqual(response["source_sentence_count"],len(sentences(PROSE)))
        self.assertGreater(response["registered_physical_entry_entity_count"],0)
        self.assertEqual(response["physical_baseline_status"],"SIGNED_G2_ENTRY_ONLY")
        self.assertEqual(response["verified_future_event_count"],0)
        self.assertEqual(response["world_db_writes"],0)
        self.assertFalse(response["canonical_commit_authorized"])
        self.assertEqual(self.signed.authority,original)

    def test_unrelated_story_rejected_before_any_https_get(self):
        from experiments.sera.real_blind_benchmark_v040 import prepare
        mara=prepare()["prose"]
        with self.assertRaisesRegex(
                CoverageError,"V053_G2_PHYSICAL_ACCEPTED_PROSE_SHA_MISMATCH"):
            self.call(prose=mara)
        self.assertEqual(self.calls,[])
        self.assertEqual(self.signed.used,set())

    def test_invalid_endpoint_rejected_without_any_network(self):
        bad=[
            "http://g2-authority.project-lumi.example"+API_PATH,
            "https://localhost"+API_PATH,
            "https://127.0.0.1"+API_PATH,
            "https://user:pass@g2-authority.project-lumi.example"+API_PATH,
            "https://g2-authority.project-lumi.example"+API_PATH+"?x=1",
            "https://g2-authority.project-lumi.example/api/untrusted",
            "https://g2-authority.project-lumi.example:4434"+API_PATH,
            "https://g2-authority.project-lumi.example."+API_PATH,
        ]
        for endpoint in bad:
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(CoverageError):
                    self.reader(endpoint=endpoint)
        self.assertEqual(self.calls,[])

    def test_unsigned_or_bad_g2_authority_denied_before_get(self):
        corrupt=dict(self.signed.authority,authenticated_source_preflight=False)
        with self.assertRaisesRegex(CoverageError,
                                    "V053_G2_AUTHORITY_NOT_AUTHENTICATED"):
            self.call(authority=corrupt)
        with self.assertRaisesRegex(CoverageError,
                                    "V053_G2_AUTHORITY_NOT_AUTHENTICATED"):
            self.call(contract_id=IDS["primaryCharacterId"])
        self.assertEqual(self.calls,[])

    def test_forged_signature_fails_closed_even_if_snapshot_looks_right(self):
        def corrupt(packet):
            packet["provenance"]["signature"]="AA=="
        source=self.reader(transport=self.make_transport(mutate=corrupt))
        with self.assertRaisesRegex(CoverageError,
                                    "PHYSICAL_SIGNATURE_INVALID"):
            self.call(reader=source)
        self.assertEqual(self.signed.used,set())

    def test_wrong_nonce_is_never_accepted_as_fresh(self):
        def corrupt(packet):
            packet["provenance"]["nonce"]="old-forged-challenge-1234567890123"
        source=self.reader(transport=self.make_transport(mutate=corrupt))
        with self.assertRaisesRegex(CoverageError,
                                    "PHYSICAL_SCOPE_OR_PROOF_MISMATCH"):
            self.call(reader=source)
        self.assertEqual(self.signed.used,set())

    def test_broken_physical_snapshot_refused_without_nonce_use(self):
        def corrupt(packet):
            packet["snapshot"]["worldFingerprint"]="f"*64
        source=self.reader(transport=self.make_transport(mutate=corrupt))
        with self.assertRaisesRegex(CoverageError,
                                    "PHYSICAL_SCOPE_OR_PROOF_MISMATCH"):
            self.call(reader=source)
        self.assertEqual(self.signed.used,set())

    def test_real_durable_nonce_store_blocks_replay_across_reader_restarts(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"protected-physical-nonces.db"
            provision_nonce_store(path)
            reader_1=self.reader(
                consume_nonce=LocalPhysicalNonceStore(path).consume)
            result=self.call(reader=reader_1)
            self.assertEqual(result["world_db_writes"],0)
            # Simulates another worker/restart on the SAME host. Callback is
            # rebuilt from the existing protected SQLite nonce record.
            reader_2=self.reader(
                consume_nonce=LocalPhysicalNonceStore(path).consume)
            with self.assertRaisesRegex(CoverageError,"PHYSICAL_NONCE_REPLAY"):
                self.call(reader=reader_2)
            self.assertEqual(len(self.calls),2)

    def test_same_challenge_cannot_be_replayed_to_get_second_authority(self):
        self.call()
        with self.assertRaisesRegex(CoverageError,"PHYSICAL_NONCE_REPLAY"):
            self.call()
        self.assertEqual(len(self.calls),2)

    def test_missing_durable_nonce_guard_or_bad_key_pin(self):
        with self.assertRaisesRegex(CoverageError,
                                    "V053_PHYSICAL_TRUST_NOT_CONFIGURED"):
            self.reader(consume_nonce=None)
        read=self.reader(raw_public_key_sha256="f"*64)
        with self.assertRaisesRegex(CoverageError,"PUBLIC_KEY_PIN_MISMATCH"):
            self.call(reader=read)
        self.assertEqual(self.signed.used,set())

    def test_provider_or_g2_network_not_available_fails_not_fallback(self):
        def unreachable(**_kwargs):
            raise CoverageError("V053_SIGNED_G2_PHYSICAL_GET_UNAVAILABLE")
        reader=self.reader(transport=unreachable)
        with self.assertRaisesRegex(CoverageError,
                                    "SIGNED_G2_PHYSICAL_GET_UNAVAILABLE"):
            self.call(reader=reader)
        self.assertEqual(self.signed.used,set())

    def test_wrong_snapshot_response_schema_denied(self):
        reader=self.reader(transport=lambda **_kwargs:{
            "schema":"not-a-g2-source","snapshot":{},"provenance":{}})
        with self.assertRaisesRegex(CoverageError,
                                    "V053_PHYSICAL_HTTP_DOCUMENT_INVALID"):
            self.call(reader=reader)
        self.assertEqual(self.signed.used,set())


if __name__=="__main__":
    unittest.main()
