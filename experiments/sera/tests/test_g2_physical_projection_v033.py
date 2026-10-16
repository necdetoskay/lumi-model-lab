"""v0.33 physical registry mapping is strictly separate from G2 text facts."""
from copy import deepcopy
import hashlib
import hmac
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.g2_readonly_scope_bridge_v032 import digest
from experiments.sera.g2_physical_projection_v033 import SCHEMA, project
from experiments.sera.tests.test_g2_readonly_scope_v032 import IDS, verified

SECRET=b"synthetic-g2-physical-issuer-NEVER-production"
LOC_A="30000000-0000-4000-8000-000000000001"
LOC_B="30000000-0000-4000-8000-000000000002"
BOX="30000000-0000-4000-8000-000000000003"
FACT="registered-fact-source-1"


def data(authority):
    return {
        "scope":deepcopy(authority["scope"]),
        "g2ContractId":authority["g2_contract_id"],
        "worldRevisionId":authority["frozen_world_revision_id"],
        "worldFingerprint":authority["frozen_world_fingerprint"],
        "characterSnapshotId":authority["character_snapshot_id"],
        "regions":[
            {"id":LOC_A,"weather":"UNKNOWN"},
            {"id":LOC_B,"weather":"UNKNOWN"},
        ],
        "entities":[
            {
                "id":IDS["primaryCharacterId"],"kind":"CHARACTER",
                "locationId":LOC_A,"lifecycle":"ACTIVE",
                "ownerId":None,"holderId":None,"wornById":None,
                "knowledgeFactIds":[FACT],
            },
            {
                "id":BOX,"kind":"OBJECT","locationId":LOC_A,
                "lifecycle":"ACTIVE","ownerId":IDS["primaryCharacterId"],
                "holderId":IDS["primaryCharacterId"],
                "wornById":None,"knowledgeFactIds":[],
            },
        ],
        "verifiedFactRegistry":{
            FACT:{"truth_status":"VERIFIED",
                  "knowledge_scope":IDS["primaryCharacterId"]},
        },
        "registeredRoutes":[{
            "fromLocationId":LOC_A,"toLocationId":LOC_B,
            "minTravelMinutes":10,
        }],
    }


def sign(authority,snapshot):
    data=deepcopy(snapshot)
    p={
        "source":"PROJECT_LUMI_G2_PHYSICAL_READONLY",
        "snapshot_sha256":digest(data),
        "g2_authority_sha256":digest(authority),
    }
    msg=digest({"snapshot":data,"provenance":p}).encode("ascii")
    p["signature"]=hmac.new(SECRET,msg,hashlib.sha256).hexdigest()
    return {"schema":SCHEMA,"snapshot":data,"provenance":p}


def verify_provenance(snapshot,provenance):
    p=deepcopy(provenance)
    signature=p.pop("signature","")
    msg=digest({"snapshot":snapshot,"provenance":p}).encode("ascii")
    return hmac.compare_digest(
        signature,hmac.new(SECRET,msg,hashlib.sha256).hexdigest()
    )


def simulate(*, mutate=None, signed=True, authority=None):
    a=authority or verified()
    snap=data(a)
    if mutate:
        mutate(snap)
    pack=sign(a,snap)
    if not signed:
        pack["provenance"]["signature"]="0"*64
    return project(authority=a,projection=pack,
                   verify_projection=verify_provenance)


class G2PhysicalProjectionV033Tests(unittest.TestCase):
    def test_complete_signed_projection_never_creates_native_world_commit(self):
        authority=verified()
        original=deepcopy(authority)
        got=simulate(authority=authority)
        self.assertEqual(got["status"],
                         "REGISTERED_PHYSICAL_PREVIEW_NONCANONICAL")
        self.assertEqual(got["world"]["entities"][BOX]["holder"],
                         IDS["primaryCharacterId"])
        self.assertEqual(got["world"]["entities"][BOX]["location"],LOC_A)
        self.assertEqual(got["world"]["entities"][
            IDS["primaryCharacterId"]]["knowledge"],[FACT])
        self.assertEqual(got["world"]["regions"][LOC_A]["weather"],"UNKNOWN")
        self.assertEqual(got["world"]["entities"][BOX]["appearance"]
                         ["color"],"UNKNOWN")
        self.assertEqual(len(got["registered_routes"]),1)
        self.assertEqual(got["native_g2_world_fingerprint"],"b"*64)
        self.assertNotEqual(got["world_sha256"],"b"*64)
        self.assertEqual(authority,original)
        self.assertFalse(got["canonical_commit_authorized"])
        self.assertEqual(got["world_db_writes"],0)
        self.assertIsNone(got["g2_commit_request"])

    def test_missing_physical_record_must_not_be_filled_from_character_facts(self):
        a=verified()
        with self.assertRaisesRegex(
            CoverageError,"V033_PHYSICAL_REGISTRY_NOT_AVAILABLE"
        ):
            project(authority=a,projection=None,
                    verify_projection=verify_provenance)
        def missing_locations(s):
            s.pop("regions")
        with self.assertRaisesRegex(
            CoverageError,"V033_PHYSICAL_REGISTRY_INCOMPLETE"
        ):
            simulate(mutate=missing_locations)

    def test_tampered_registry_cannot_pass_untrusted_signature(self):
        a=verified()
        package=sign(a,data(a))
        package["snapshot"]["entities"][0]["locationId"]=LOC_B
        with self.assertRaisesRegex(
            CoverageError,"V033_PHYSICAL_SNAPSHOT_NOT_AUTHENTICATED_OR_STALE"
        ):
            project(authority=a,projection=package,
                    verify_projection=verify_provenance)
        with self.assertRaisesRegex(
            CoverageError,"V033_PHYSICAL_SNAPSHOT_NOT_AUTHENTICATED_OR_STALE"
        ):
            simulate(signed=False)

    def test_cross_world_and_stale_revision_cannot_reuse_registered_map(self):
        for mutate in (
            lambda s:s.update(worldRevisionId=IDS["universeRevisionId"]),
            lambda s:s.update(worldFingerprint="d"*64),
            lambda s:s.update(characterSnapshotId=IDS["contractId"]),
            lambda s:s["scope"].update(profileId=IDS["contractId"]),
        ):
            with self.subTest(mutate=mutate):
                with self.assertRaisesRegex(
                    CoverageError,
                    "V033_PHYSICAL_SNAPSHOT_NOT_AUTHENTICATED_OR_STALE"
                ):
                    simulate(mutate=mutate)

    def test_registered_character_must_have_known_location(self):
        def unknown_location(s):
            s["entities"][0]["locationId"]="not-a-registered-place"
        with self.assertRaisesRegex(
            CoverageError,"V033_G2_ENTITY_ROLE_OR_LOCATION_UNQUALIFIED"
        ):
            simulate(mutate=unknown_location)
        def no_primary(s):
            s["entities"].pop(0)
        with self.assertRaisesRegex(
            CoverageError,"V033_PRIMARY_CHARACTER_MISSING"
        ):
            simulate(mutate=no_primary)

    def test_rumor_or_wrong_character_knowledge_is_not_promoted_to_fact(self):
        for change in (
            lambda s:s["verifiedFactRegistry"][FACT].update(
                truth_status="RUMORED"),
            lambda s:s["verifiedFactRegistry"][FACT].update(
                knowledge_scope=IDS["contractId"]),
        ):
            with self.subTest(change=change):
                with self.assertRaisesRegex(
                    CoverageError,"V033_G2_FACT_NOT_VERIFIED_OR_OUT_OF_SCOPE"
                ):
                    simulate(mutate=change)

    def test_custody_must_be_registered_and_spatially_consistent(self):
        def forged_carrier(s):
            s["entities"][1]["holderId"]=IDS["contractId"]
        with self.assertRaisesRegex(
            Exception, "ENTITY_REFERENCE_INVALID|ENTITY_KIND_INVALID"
        ):
            simulate(mutate=forged_carrier)
        def separated_item(s):
            s["entities"][1]["locationId"]=LOC_B
        with self.assertRaisesRegex(
            Exception,"HOLDER_LOCATION_MISMATCH"
        ):
            simulate(mutate=separated_item)

    def test_no_implicit_travel_or_weather_assertions(self):
        def imaginary_route(s):
            s["registeredRoutes"][0]["minTravelMinutes"]=0
        with self.assertRaisesRegex(
            CoverageError,"V033_TRAVEL_ROUTE_UNREGISTERED"
        ):
            simulate(mutate=imaginary_route)
        def unsupported_rain(s):
            s["regions"][0]["weather"]="RAIN"
        with self.assertRaisesRegex(
            CoverageError,"V033_WEATHER_REQUIRES_TYPED_MEASUREMENT"
        ):
            simulate(mutate=unsupported_rain)

    def test_unsigned_character_snapshot_cannot_gain_physical_scope(self):
        authority=verified()
        authority["authenticated_source_preflight"]=False
        with self.assertRaisesRegex(
            CoverageError,"V033_G2_SCOPE_UNQUALIFIED"
        ):
            simulate(authority=authority)


if __name__=="__main__":
    unittest.main()
