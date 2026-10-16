"""v0.33 G2 HTTP client tests: all transports are synthetic, no network."""
from copy import deepcopy
import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlsplit
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.g2_authenticated_http_reader_v033 import (
    API_PATH, READ_PERMISSION, create_reader, signed_message,
)
from experiments.sera.g2_readonly_scope_bridge_v032 import (
    SCHEMA, SCOPE, digest, resolve, run_readonly_g2,
)
from experiments.sera.tests.test_g2_readonly_scope_v032 import (
    IDS, synthetic_rows, req, authenticate as old_fixture_verifier,
)
from experiments.sera.tests.test_storyforge_bridge_v028 import (
    FACETS, REGISTRY, ROLES, SCENE, SOURCE, fake_attestor, fake_result,
)
from experiments.sera.tests.test_world_state_v02 import base

SECRET=b"synthetic-application-signing-key-not-real"
ENDPOINT="https://authority.project-lumi.example" + API_PATH
T0=1792159200.0


def scope():
    return {k:IDS[k] for k in SCOPE}


def make_service(*, content_mutator=None, signatures=True, clock=lambda:T0,
                 requests=None):
    requests = [] if requests is None else requests

    def sign(message):
        return hmac.new(SECRET,message,hashlib.sha256).hexdigest()

    def verifier(message, signature, key_id):
        return key_id == "g2-source-signer-v1" and hmac.compare_digest(
            sign(message),signature)

    def transport(*,url,authorization,timeout,max_bytes):
        assert url.startswith(ENDPOINT+"?contractId=")
        assert authorization == "synthetic-internal-readonly-credential"
        assert timeout == 15
        assert max_bytes == 1_500_000
        params=parse_qs(urlsplit(url).query)
        assert params["contractId"] == [IDS["contractId"]]
        assert len(params["nonce"][0]) >= 24
        requests.append({"url":url,"method":"GET"})
        rows=synthetic_rows()
        provenance={
            "source":"PROJECT_LUMI_G2_READONLY",
            "contract_id":IDS["contractId"],
            "snapshot_id":"synthetic-g2-repeatable-read-transaction-1",
            "rows_sha256":digest(rows),
            "scope_sha256":digest(scope()),
            "permission":READ_PERMISSION,
            "nonce":params["nonce"][0],
            "issuer":"project-lumi-internal-g2",
            "audience":"sera-readonly-experiment",
            "key_id":"g2-source-signer-v1",
            "issued_at":clock(),
            "expires_at":clock()+60,
        }
        if content_mutator is not None:
            content_mutator(rows,provenance)
        if signatures:
            provenance["signature"]=sign(signed_message(rows,provenance))
        else:
            provenance["signature"]="0"*64
        return {
            "schema":SCHEMA,"rows":rows,"provenance":provenance,
        }
    return transport,verifier,requests


def configured(*,mutate=None,signatures=True,now=lambda:T0,
               calls=None,nonce="unique-nonce-string-with-more-than-24"):
    transport,verifier,reqs=make_service(
        content_mutator=mutate, signatures=signatures,
        clock=now,requests=calls,
    )
    getter,proof=create_reader(
        endpoint=ENDPOINT,
        bearer_token="synthetic-internal-readonly-credential",
        expected_scope=scope(),
        issuer="project-lumi-internal-g2",
        audience="sera-readonly-experiment",
        trusted_key_id="g2-source-signer-v1",
        verify_signature=verifier,transport=transport,
        clock=now,nonce_factory=lambda:nonce,
    )
    return getter,proof,reqs


def resolve_g2(getter,proof):
    return resolve(
        contract_id=IDS["contractId"],expected_scope=scope(),
        request=req(),result=fake_result(),world=base(),
        readonly_lookup=getter,verify_source=proof,
    )


class AuthenticatedG2HTTPReaderV033Tests(unittest.TestCase):
    def test_fresh_pinned_signed_read_can_feed_actual_v032_scope_gate(self):
        calls=[]
        getter,proof,_=configured(calls=calls)
        authority=resolve_g2(getter,proof)
        self.assertTrue(authority["authenticated_source_preflight"])
        self.assertEqual(authority["scope"],scope())
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0]["method"],"GET")
        self.assertFalse(authority["canonical_commit_authorized"])
        self.assertIsNone(authority["g2_commit_request"])

    def test_same_signer_can_issue_new_nonce_per_separate_read_only_job(self):
        seen=[]
        next_nonce=iter([
            "fresh-first-nonce-abcdefghijklmnopqrstuvwxyz",
            "fresh-second-nonce-abcdefghijklmnopqrstuvwxyz",
        ])
        transport,verify,_=make_service(requests=seen)
        get,check=create_reader(
            endpoint=ENDPOINT,bearer_token="synthetic-internal-readonly-credential",
            expected_scope=scope(),issuer="project-lumi-internal-g2",
            audience="sera-readonly-experiment",
            trusted_key_id="g2-source-signer-v1",
            transport=transport,verify_signature=verify,
            clock=lambda:T0,nonce_factory=lambda:next(next_nonce),
        )
        first=resolve_g2(get,check)
        second=resolve_g2(get,check)
        self.assertEqual(first["accepted_english_sha256"],
                         second["accepted_english_sha256"])
        self.assertNotEqual(seen[0]["url"],seen[1]["url"])

    def test_false_signature_rejected_even_if_all_data_structurally_valid(self):
        getter,proof,_=configured(signatures=False)
        with self.assertRaisesRegex(
            CoverageError,"V033_G2_SOURCE_SIGNATURE_INVALID"
        ):
            resolve_g2(getter,proof)

    def test_old_or_future_signed_snapshot_fails_freshness_before_signature(self):
        for mutation in (
            lambda r,p:p.update(expires_at=T0-1),
            lambda r,p:p.update(issued_at=T0+180,expires_at=T0+200),
            lambda r,p:p.update(issued_at=T0-200,expires_at=T0+10),
            lambda r,p:p.update(expires_at=T0+300),
        ):
            with self.subTest(mutation=mutation):
                getter,proof,_=configured(mutate=mutation)
                with self.assertRaisesRegex(
                    CoverageError,
                    "V033_SIGNED_SCOPE_FRESHNESS_OR_PERMISSION_INVALID"
                ):
                    resolve_g2(getter,proof)

    def test_other_profile_world_audience_nonce_or_key_is_denied(self):
        cases=[
            lambda r,p:p.update(scope_sha256="0"*64),
            lambda r,p:p.update(permission="story.mutate"),
            lambda r,p:p.update(audience="wrong-system"),
            lambda r,p:p.update(issuer="untrusted-vendor"),
            lambda r,p:p.update(key_id="unsigned-remote-key"),
            lambda r,p:p.update(nonce="replayed-server-nonce"),
        ]
        for mutate in cases:
            with self.subTest(mutate=mutate):
                getter,proof,_=configured(mutate=mutate)
                with self.assertRaisesRegex(
                    CoverageError,
                    "V033_SIGNED_SCOPE_FRESHNESS_OR_PERMISSION_INVALID"
                ):
                    resolve_g2(getter,proof)

    def test_wrong_source_english_does_not_pass_even_with_valid_signature(self):
        def alter(rows,prov):
            rows["accepted_story"]["storyText"]+=" forged"
            prov["rows_sha256"]=digest(rows)
        getter,proof,_=configured(mutate=alter)
        with self.assertRaisesRegex(
            CoverageError,"V032_G2_ACCEPTED_ENGLISH_BYTES_MISMATCH"
        ):
            resolve_g2(getter,proof)

    def test_replayed_verifier_after_success_is_one_use(self):
        getter,proof,_=configured()
        document=getter(contract_id=IDS["contractId"])
        self.assertIs(proof(document["rows"],document["provenance"]),True)
        with self.assertRaisesRegex(
            CoverageError,"V033_READ_NOT_REQUESTED_OR_ALREADY_CONSUMED"
        ):
            proof(document["rows"],document["provenance"])

    def test_client_rejects_http_credentials_ipv4_redirect_bypass_paths(self):
        for endpoint in (
            "http://authority.project-lumi.example"+API_PATH,
            "https://user:pass@authority.project-lumi.example"+API_PATH,
            "https://127.0.0.1"+API_PATH,
            "https://localhost"+API_PATH,
            "https://authority.project-lumi.example/any-other-path",
            "https://authority.project-lumi.example"+API_PATH+"?x=1",
            "https://authority.project-lumi.example:8080"+API_PATH,
        ):
            with self.subTest(endpoint=endpoint):
                with self.assertRaisesRegex(
                    CoverageError,"V033_ENDPOINT_NOT_PINNED_HTTPS"
                ):
                    create_reader(
                        endpoint=endpoint,
                        bearer_token="synthetic-internal-readonly-credential",
                        expected_scope=scope(),
                        issuer="project-lumi-internal-g2",
                        audience="sera-readonly-experiment",
                        trusted_key_id="g2-source-signer-v1",
                        verify_signature=lambda *a:True,
                    )

    def test_missing_real_authentication_or_service_cannot_be_approximated(self):
        with self.assertRaisesRegex(
            CoverageError,"V033_READONLY_CREDENTIAL_INVALID"
        ):
            create_reader(
                endpoint=ENDPOINT,bearer_token="",
                expected_scope=scope(),issuer="project-lumi-internal-g2",
                audience="sera-readonly-experiment",
                trusted_key_id="g2-source-signer-v1",
                verify_signature=lambda *args:True,
            )
        getter,proof,_=configured()
        with self.assertRaisesRegex(
            CoverageError,"V033_CONTRACT_ID_INVALID"
        ):
            getter(contract_id="invented-name-instead-of-uuid")

    def test_authenticated_source_allows_only_zero_paid_storyforge_preflight(self):
        getter,proof,calls=configured()
        with TemporaryDirectory() as d:
            options=dict(
                contract_id=IDS["contractId"],expected_scope=scope(),
                readonly_lookup=getter,verify_source=proof,
                request=req(),result=fake_result(),world=base(),
                scene_span={"start":0,"end":len(SOURCE)},
                models=deepcopy(ROLES),model_attestor=fake_attestor,
                scene_key=SCENE,job_id="signed-http-g2-v033",
                work_root=Path(d),registry=deepcopy(REGISTRY),
                candidate_lexicon={},typed_registry=deepcopy(FACETS),
                provider_call=lambda **kw:self.fail("No paid POST allowed"),
            )
            result=run_readonly_g2(**options)
        self.assertEqual(result["status"],
                         "G2_AUTHENTICATED_READONLY_PREFLIGHT_NONCANONICAL")
        self.assertEqual(result["storyforge"]["provider_calls"],0)
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(len(calls),1)


if __name__=="__main__":
    unittest.main()
