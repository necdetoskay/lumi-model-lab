"""v0.32: actual G2 field names, authenticated read-only row binding.

ALL rows in this suite are synthetic. No production G2 DB, API, paid
model, migration, transaction or WorldState/EventGraph write is used.
"""
from copy import deepcopy
import hashlib
import hmac
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.g2_readonly_scope_bridge_v032 import (
    SCHEMA, SCOPE, digest, resolve, run_readonly_g2,
)
from experiments.sera.tests.test_storyforge_bridge_v028 import (
    FACETS, REGISTRY, ROLES, SCENE, SOURCE, fake_attestor, fake_request,
    fake_result,
)
from experiments.sera.tests.test_world_state_v02 import base

# Fake IDs are explicit and never treated as production identities.
IDS = {
    "householdId":"10000000-0000-4000-8000-000000000001",
    "profileId":"10000000-0000-4000-8000-000000000002",
    "universeId":"10000000-0000-4000-8000-000000000003",
    "worldInstanceId":"10000000-0000-4000-8000-000000000004",
    "primaryCharacterId":"10000000-0000-4000-8000-000000000005",
    "contractId":"10000000-0000-4000-8000-000000000006",
    "storyIntentId":"10000000-0000-4000-8000-000000000007",
    "productionRunId":"10000000-0000-4000-8000-000000000008",
    "acceptedStoryArtifactId":"10000000-0000-4000-8000-000000000009",
    "universeRevisionId":"10000000-0000-4000-8000-00000000000a",
    "worldInstanceRevisionId":"10000000-0000-4000-8000-00000000000b",
    "characterSnapshotId":"10000000-0000-4000-8000-00000000000c",
}
SECRET = b"laboratory-only-auth-secret-never-a-real-prod-key"


def req():
    result = fake_request()
    result["active_world_id"] = IDS["worldInstanceId"]
    return result


def synthetic_rows():
    scope = {k:IDS[k] for k in SCOPE}
    c = {**scope, "id":IDS["contractId"],
         "storyIntentId":IDS["storyIntentId"],
         "universeRevisionId":IDS["universeRevisionId"],
         "worldInstanceRevisionId":IDS["worldInstanceRevisionId"],
         "universeFingerprint":"a"*64,
         "worldInstanceFingerprint":"b"*64}
    before = {
        "householdId":scope["householdId"],
        "profileId":scope["profileId"],
        "characterId":scope["primaryCharacterId"],
        "snapshotId":IDS["characterSnapshotId"],"fingerprint":"c"*64,
        "revisionNo":5, "headVersion":8,
        "statePayload":{"facts":{"knows_story":False},"emotions":{}},
    }
    rows = {
        "contract":c,
        "intent":{**scope,"id":IDS["storyIntentId"],"status":"STORY_STARTED"},
        "production_run":{
            **scope,"id":IDS["productionRunId"],
            "contractId":IDS["contractId"],"status":"ACCEPTED",
        },
        "accepted_story":{
            **scope,"id":IDS["acceptedStoryArtifactId"],
            "contractId":IDS["contractId"],
            "productionRunId":IDS["productionRunId"],
            "storyText":SOURCE,
            # Domain fingerprint and raw English SHA are NOT identical.
            "storyFingerprint":"e"*64,
        },
        "universe_head":{
            "householdId":scope["householdId"],
            "universeId":scope["universeId"],
            "currentRevisionId":IDS["universeRevisionId"],
            "currentFingerprint":"a"*64,
        },
        "world_head":{
            "householdId":scope["householdId"],
            "profileId":scope["profileId"],
            "universeId":scope["universeId"],
            "worldInstanceId":scope["worldInstanceId"],
            "currentRevisionId":IDS["worldInstanceRevisionId"],
            "currentFingerprint":"b"*64,
        },
        "character_before":before,
        "character_head":{
            "householdId":scope["householdId"],
            "profileId":scope["profileId"],
            "characterId":scope["primaryCharacterId"],
            "currentSnapshotId":before["snapshotId"],
            "currentRevisionNo":before["revisionNo"],
            "currentFingerprint":before["fingerprint"],
            "version":before["headVersion"],
        },
        "snapshot_refs":[{
            **scope,"contractId":IDS["contractId"],
            "snapshotKind":"CHARACTER_STATE",
            "sourceRef":"character-story-state:" + IDS["characterSnapshotId"],
            "sourceFingerprint":"c"*64,
        }],
    }
    return rows


def signed_document(rows):
    contents=deepcopy(rows)
    payload=digest(contents)
    signed=hmac.new(SECRET,payload.encode("ascii"),
                    hashlib.sha256).hexdigest()
    return {
        "schema":SCHEMA, "rows":contents,
        "provenance":{
            "source":"PROJECT_LUMI_G2_READONLY",
            "contract_id":IDS["contractId"],
            "snapshot_id":"synthetic-authoritative-revision-1",
            "rows_sha256":payload,
            "signature":signed,
        },
    }


def authenticate(rows, provenance):
    expected=hmac.new(SECRET,digest(rows).encode("ascii"),
                      hashlib.sha256).hexdigest()
    return hmac.compare_digest(
        expected, provenance.get("signature",""),
    ) and provenance.get("snapshot_id") == (
        "synthetic-authoritative-revision-1"
    )


def accepted(*, mutate=None, sign=True):
    rows=synthetic_rows()
    if mutate is not None:
        mutate(rows)
    d=signed_document(rows)
    if not sign:
        d["provenance"]["signature"]="0"*64
    return d


def verified(*, mutate=None, sign=True, request=None, result=None,
             expected=None, world=None):
    data=accepted(mutate=mutate,sign=sign)
    return resolve(
        contract_id=IDS["contractId"],
        expected_scope=expected or {k:IDS[k] for k in SCOPE},
        request=request or req(),result=result or fake_result(),
        world=world or base(),
        readonly_lookup=lambda *,contract_id:data,
        verify_source=authenticate,
    )


class G2ReadonlyScopeBridgeV032Tests(unittest.TestCase):
    def test_signed_exact_story_and_five_key_heads_create_noncanonical_scope(self):
        world=base()
        original=deepcopy(world)
        got=verified(world=world)
        self.assertTrue(got["authenticated_source_preflight"])
        self.assertEqual(got["scope"],{k:IDS[k] for k in SCOPE})
        self.assertEqual(got["g2_contract_id"],IDS["contractId"])
        self.assertEqual(got["g2_domain_story_fingerprint"],"e"*64)
        self.assertNotEqual(got["g2_domain_story_fingerprint"],
                            got["accepted_english_sha256"])
        self.assertFalse(got["canonical_commit_authorized"])
        self.assertEqual(got["world_db_writes"],0)
        self.assertIsNone(got["g2_commit_request"])
        self.assertEqual(world,original)

    def test_missing_auth_source_is_not_a_valid_prod_binding(self):
        with self.assertRaisesRegex(
            CoverageError,"V032_AUTHENTICATED_READONLY_SOURCE_REQUIRED"
        ):
            resolve(contract_id=IDS["contractId"],
                expected_scope={k:IDS[k] for k in SCOPE},
                request=req(),result=fake_result(),world=base(),
                readonly_lookup=None,verify_source=authenticate)
        with self.assertRaisesRegex(
            CoverageError,"V032_G2_READ_DOCUMENT_INVALID"
        ):
            resolve(contract_id=IDS["contractId"],
                expected_scope={k:IDS[k] for k in SCOPE},
                request=req(),result=fake_result(),world=base(),
                readonly_lookup=lambda **kw:None,
                verify_source=authenticate)

    def test_tampered_unsigned_or_wrong_retrieval_source_denied(self):
        with self.assertRaisesRegex(
            CoverageError,"V032_G2_SOURCE_NOT_AUTHENTICATED"
        ):
            verified(sign=False)
        doc=accepted()
        doc["rows"]["contract"]["attemptNo"]=77
        with self.assertRaisesRegex(
            CoverageError,"V032_G2_SOURCE_NOT_AUTHENTICATED"
        ):
            resolve(contract_id=IDS["contractId"],
                expected_scope={k:IDS[k] for k in SCOPE},
                request=req(),result=fake_result(),world=base(),
                readonly_lookup=lambda **kw:doc,
                verify_source=authenticate)

    def test_wrong_profile_world_and_character_cannot_reuse_authority(self):
        for key in SCOPE:
            def mismatch(rows,key=key):
                rows["accepted_story"][key] = (
                    "20000000-0000-4000-8000-000000000099"
                )
            with self.subTest(key=key):
                with self.assertRaisesRegex(
                    CoverageError,"V032_ACCEPTED_STORY_SCOPE_MISMATCH"
                ):
                    verified(mutate=mismatch)
        bad=req()
        bad["active_world_id"]="other-world"
        with self.assertRaisesRegex(
            CoverageError,"V032_STORYFORGE_G2_WORLD_OR_REQUEST_MISMATCH"
        ):
            verified(request=bad)

    def test_cross_contract_or_unaccepted_run_fails_closed(self):
        def bad_run(rows):
            rows["production_run"]["status"]="STARTED"
        with self.assertRaisesRegex(
            CoverageError,"V032_G2_PRODUCTION_NOT_ACCEPTED"
        ):
            verified(mutate=bad_run)
        def wrong_contract(rows):
            rows["accepted_story"]["contractId"]=IDS["storyIntentId"]
        with self.assertRaisesRegex(
            CoverageError,"V032_G2_ACCEPTED_ENGLISH_BYTES_MISMATCH"
        ):
            verified(mutate=wrong_contract)

    def test_changed_accepted_source_cannot_reuse_another_story(self):
        def diff(rows):
            rows["accepted_story"]["storyText"]=SOURCE+" invented sentence."
        with self.assertRaisesRegex(
            CoverageError,"V032_G2_ACCEPTED_ENGLISH_BYTES_MISMATCH"
        ):
            verified(mutate=diff)
        def fp_not_raw(rows):
            rows["accepted_story"]["storyFingerprint"]="f"*64
        got=verified(mutate=fp_not_raw)
        self.assertEqual(got["g2_domain_story_fingerprint"],"f"*64)

    def test_stale_world_universe_and_character_heads_all_denied(self):
        for mutate,code in [
            (lambda rows: rows["world_head"].update(
                currentFingerprint="d"*64), "V032_G2_WORLD_HEAD_STALE"),
            (lambda rows: rows["universe_head"].update(
                currentRevisionId=IDS["contractId"]), "V032_G2_UNIVERSE_HEAD_STALE"),
            (lambda rows: rows["character_head"].update(
                currentRevisionNo=9), "V032_G2_CHARACTER_STATE_STALE"),
            (lambda rows: rows["character_head"].update(
                version=9), "V032_G2_CHARACTER_STATE_STALE"),
            (lambda rows: rows["snapshot_refs"][0].update(
                sourceFingerprint="f"*64), "V032_G2_CHARACTER_REF_MISMATCH"),
        ]:
            with self.subTest(code=code):
                with self.assertRaisesRegex(CoverageError,code):
                    verified(mutate=mutate)

    def test_missing_character_ref_and_partial_records_rejected(self):
        def none(rows):
            rows["snapshot_refs"]=[]
        with self.assertRaisesRegex(
            CoverageError,"V032_G2_CHARACTER_REF_NOT_UNIQUE"
        ):
            verified(mutate=none)
        def extra(rows):
            rows.pop("world_head")
        with self.assertRaisesRegex(
            CoverageError,"V032_G2_AUTHORITY_ROWS_INCOMPLETE"
        ):
            verified(mutate=extra)

    def test_storyforge_dryrun_only_from_verified_g2_not_editorial_flag(self):
        with TemporaryDirectory() as d:
            kwargs=dict(
                contract_id=IDS["contractId"],
                expected_scope={k:IDS[k] for k in SCOPE},
                readonly_lookup=lambda *,contract_id:accepted(),
                verify_source=authenticate,
                request=req(),result=fake_result(),
                world=base(),
                scene_span={"start":0,"end":len(SOURCE)},
                models=deepcopy(ROLES),model_attestor=fake_attestor,
                scene_key=SCENE,job_id="synthetic-g2-story-run",
                work_root=Path(d),registry=deepcopy(REGISTRY),
                candidate_lexicon={},typed_registry=deepcopy(FACETS),
                provider_call=lambda **kw:self.fail("no provider"),
            )
            first=run_readonly_g2(**kwargs)
            second=run_readonly_g2(**kwargs)
        self.assertEqual(first,second)
        self.assertEqual(first["status"],
                         "G2_AUTHENTICATED_READONLY_PREFLIGHT_NONCANONICAL")
        self.assertEqual(first["storyforge"]["provider_calls"],0)
        self.assertEqual(first["storyforge"]["model_cost_usd"],"0")
        self.assertEqual(first["storyforge"]["status"],
                         "DRY_RUN_READY_NO_MODEL_CALLS_NONCANONICAL")
        self.assertFalse(first["canonical_commit_authorized"])
        self.assertIsNone(first["g2_commit_request"])

    def test_signed_identity_drift_cannot_resume_prior_story_job(self):
        with TemporaryDirectory() as d:
            rows=synthetic_rows()
            def lookup(*,contract_id):
                return signed_document(rows)
            kw=dict(
                contract_id=IDS["contractId"],
                expected_scope={k:IDS[k] for k in SCOPE},
                readonly_lookup=lookup,verify_source=authenticate,
                request=req(),result=fake_result(),world=base(),
                scene_span={"start":0,"end":len(SOURCE)},
                models=deepcopy(ROLES),model_attestor=fake_attestor,
                scene_key=SCENE,job_id="same-g2-job",
                work_root=Path(d),registry=deepcopy(REGISTRY),
                candidate_lexicon={},typed_registry=deepcopy(FACETS),
            )
            run_readonly_g2(**kw)
            rows["character_before"]["statePayload"]["facts"]["knows_story"]=True
            with self.assertRaisesRegex(
                CoverageError,"V028_IMMUTABLE_JOB_CONTRACT_CHANGED"
            ):
                run_readonly_g2(**kw)

    def test_real_model_billing_is_forbidden_by_readonly_g2_bridge(self):
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(
                CoverageError,"V032_G2_PAID_WORKER_NOT_AUTHORIZED"
            ):
                run_readonly_g2(
                    contract_id=IDS["contractId"],
                    expected_scope={k:IDS[k] for k in SCOPE},
                    readonly_lookup=lambda **kw:self.fail("cannot query"),
                    verify_source=authenticate,
                    request=req(),result=fake_result(),world=base(),
                    paid_authorized=True,work_root=Path(d),
                )


if __name__=="__main__":
    unittest.main()
